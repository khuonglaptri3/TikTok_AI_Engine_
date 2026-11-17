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
