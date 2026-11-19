from __future__ import annotations

import pandas as pd
import pytest

from packages.retrieval import BM25Index, HybridRetrievalService
from pipelines.benchmark_retrieval.__main__ import _evaluate_run


@pytest.fixture
def small_service() -> HybridRetrievalService:
    # Four real BM25 hits, exactly two relevant: ranking does not affect R/P.
    videos = pd.DataFrame(
        [
            {
                "video_id": vid,
                "has_transcript": True,
                "transcript": "noodle soup",
                "caption": "noodle soup",
            }
            for vid in ["relevant-1", "relevant-2", "other-1", "other-2"]
        ]
    )
    index = BM25Index.build(videos["video_id"].tolist(), videos["transcript"].tolist())
    return HybridRetrievalService(videos, index)


@pytest.mark.parametrize("rerank", [False, True])
def test_recall_uses_all_relevant_ids_even_when_more_than_cutoff(
    small_service: HybridRetrievalService, rerank: bool
) -> None:
    # 2 relevant retrieved / 20 relevant overall = 0.1, not 2/min(20,10).
    result = _evaluate_run(
        small_service,
        [{"query": "noodle", "relevant_video_ids": [f"relevant-{i}" for i in range(1, 21)]}],
        rerank=rerank,
    )
    assert result["recall_at_10"] == 0.1
    # The theoretical best recall is 10/20 even for a perfect ranker.
    assert result["recall_at_10_ceiling"] == 0.5


def test_precision_penalizes_missing_slots_in_short_result_list(
    small_service: HybridRetrievalService,
) -> None:
    result = _evaluate_run(
        small_service,
        [{"query": "noodle", "relevant_video_ids": ["relevant-1", "relevant-2"]}],
        rerank=False,
    )
    assert result["recall_at_10"] == 1.0
    # P@10 is 2/10, not 2/4 returned or 2/2 relevant.
    assert result["precision_at_10"] == 0.2
    assert result["recall_at_10_ceiling"] == 1.0


def test_zero_relevant_queries_are_explicitly_excluded_from_macro_average(
    small_service: HybridRetrievalService,
) -> None:
    result = _evaluate_run(
        small_service, [{"query": "noodle", "relevant_video_ids": []}], rerank=False
    )
    assert result["query_count"] == 0
    assert result["input_query_count"] == 1
    assert result["zero_relevant_query_count"] == 1
    assert result["recall_at_10"] == 0.0
    assert result["precision_at_10"] == 0.0
    assert result["mrr_at_10"] == 0.0
    assert result["ndcg_at_10"] == 0.0
    assert result["recall_at_10_ceiling"] == 0.0


def test_empty_query_set_is_safe(small_service: HybridRetrievalService) -> None:
    result = _evaluate_run(small_service, [], rerank=False)
    assert result["query_count"] == 0
    assert result["recall_at_10"] == 0.0
    assert result["mean_latency_ms"] == 0.0
    assert result["p95_latency_ms"] == 0.0


def test_hand_calculated_pooled_metrics_at_10() -> None:
    import math

    from pipelines.benchmark_retrieval.pilot_m2_2 import compute_pooled_query_metrics

    # Hits at rank 1 ("v1") and rank 3 ("v2") out of 4 judged relevant docs in pool
    m = compute_pooled_query_metrics(
        retrieved_ids=["v1", "v_irrel", "v2"],
        relevant_ids={"v1", "v2", "v3", "v4"},
        k=10,
    )
    assert m["pooled_recall_at_10"] == 0.5
    assert m["precision_at_10"] == 0.2
    assert m["mrr_at_10"] == 1.0
    expected_dcg = 1.0 / math.log2(2) + 1.0 / math.log2(4)
    expected_idcg = sum(1.0 / math.log2(r + 1) for r in range(1, 5))
    assert m["ndcg_at_10"] == pytest.approx(expected_dcg / expected_idcg, abs=1e-6)


def test_pilot_split_handles_zero_pool_uncertain_labels_and_no_answer_abstention(
    small_service: HybridRetrievalService,
) -> None:
    from pipelines.benchmark_retrieval.pilot_m2_2 import evaluate_pilot_split

    queries = [
        {"query_id": "q_ans", "query": "noodle", "expect_no_answer": False, "phenomenon": "synonym"},
        {"query_id": "q_zero_pool", "query": "noodle", "expect_no_answer": False, "phenomenon": "filtered"},
        {
            "query_id": "q_no_ans_ok",
            "query": "thịt kangaroo hầm rượu vang",
            "expect_no_answer": True,
            "phenomenon": "no_answer",
        },
        {
            "query_id": "q_no_ans_fabricated",
            "query": "noodle",
            "expect_no_answer": True,
            "phenomenon": "no_answer",
        },
    ]
    qrels = {
        "q_ans": {"relevant-1": "1", "relevant-2": "1", "other-1": "U", "other-2": "0"},
        "q_zero_pool": {"relevant-1": "0", "other-1": "U"},
        "q_no_ans_ok": {},
        "q_no_ans_fabricated": {},
    }
    res = evaluate_pilot_split(small_service, queries, qrels, rerank=False, k=10)
    assert res["answerable_query_count"] == 2
    assert res["evaluated_answerable_count"] == 1
    assert res["zero_relevant_pool_count"] == 1
    assert res["uncertain_judgment_count"] == 2
    assert res["pooled_recall_at_10"] == 1.0
    assert res["precision_at_10"] == 0.2
    assert res["no_answer_query_count"] == 2
    assert res["no_answer_abstention_rate"] == 0.5
    assert res["fabricated_support_count"] == 1


def test_pilot_paired_bootstrap_ci_is_deterministic() -> None:
    from pipelines.benchmark_retrieval.pilot_m2_2 import paired_bootstrap_ci

    ci1 = paired_bootstrap_ci([0.5, 0.25, 1.0, 0.5], [1.0, 0.5, 1.0, 0.75], n_boot=500, seed=42)
    ci2 = paired_bootstrap_ci([0.5, 0.25, 1.0, 0.5], [1.0, 0.5, 1.0, 0.75], n_boot=500, seed=42)
    assert ci1 == ci2
    assert ci1["mean_a"] == pytest.approx(0.5625, abs=1e-6)
    assert ci1["mean_b"] == pytest.approx(0.8125, abs=1e-6)
    assert ci1["mean_diff"] == pytest.approx(0.25, abs=1e-6)
    assert ci1["ci95_low"] <= ci1["mean_diff"] <= ci1["ci95_high"]
    assert ci1["ci95_a_low"] <= ci1["mean_a"] <= ci1["ci95_a_high"]
    assert ci1["ci95_b_low"] <= ci1["mean_b"] <= ci1["ci95_b_high"]


def test_pilot_split_tracks_false_abstention_all_answerable_and_per_query_abstention(
    small_service: HybridRetrievalService,
) -> None:
    from pipelines.benchmark_retrieval.pilot_m2_2 import evaluate_pilot_split

    queries = [
        {"query_id": "q_ok", "query": "noodle", "expect_no_answer": False, "phenomenon": "synonym"},
        {
            "query_id": "q_false_abstain",
            "query": "thịt kangaroo hầm rượu vang",
            "expect_no_answer": False,
            "phenomenon": "synonym",
        },
    ]
    qrels = {
        "q_ok": {"relevant-1": "1"},
        "q_false_abstain": {},
    }
    res = evaluate_pilot_split(small_service, queries, qrels, rerank=False, k=10)
    assert res["answerable_query_count"] == 2
    assert res["answerable_abstained_count"] == 1
    assert res["false_abstention_rate"] == 0.5
    assert res["mrr_at_10"] == 1.0
    assert res["mrr_at_10_all_answerable"] == 0.5
    assert res["ndcg_at_10_all_answerable"] == 0.5
    by_id = {row["query_id"]: row for row in res["per_query"]}
    assert by_id["q_ok"]["insufficient_evidence"] is False
    assert by_id["q_false_abstain"]["insufficient_evidence"] is True
    assert by_id["q_false_abstain"]["abstain_reason"] is not None


def test_pool_builder_script_uses_repo_local_evidence_without_machine_paths() -> None:
    from pathlib import Path

    evidence_dir = Path("docs/reports/milestones/M2.2/evidence")
    script_path = evidence_dir / "build_m2_2_pool_and_judgments.py"
    src = script_path.read_text(encoding="utf-8")
    assert "SCRATCH_DIR" not in src
    assert ".gemini" not in src
    assert "Users\\lanph" not in src and "Users/lanph" not in src
    for fname in (
        "judgments_K_dev.jsonl",
        "judgments_K_test.jsonl",
        "judgments_N_dev.jsonl",
        "judgments_N_test.jsonl",
    ):
        assert (evidence_dir / fname).is_file(), fname


