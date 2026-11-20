"""M2.2 pooled relevance pilot evaluation, paired bootstrap CIs, and 100-request CPU latency runner."""
from __future__ import annotations

import argparse
import hashlib
import json
import math
import os
import platform
import sys
import time
from datetime import UTC, datetime
from pathlib import Path
from typing import Any, Literal

import numpy as np

from packages.analytics import load_verified_corpus
from packages.common.resources import get_peak_rss_mib
from packages.data_contracts.query import NicheQueryFilter, RetrievalRequest
from packages.retrieval import HybridRetrievalService


def _sha256_file(path: Path) -> str:
    digest = hashlib.sha256()
    with path.open("rb") as stream:
        for chunk in iter(lambda: stream.read(1024 * 1024), b""):
            digest.update(chunk)
    return digest.hexdigest()


def compute_pooled_query_metrics(
    retrieved_ids: list[str],
    relevant_ids: set[str],
    k: int = 10,
) -> dict[str, float]:
    """Compute binary pooled Recall@k, Precision@k, MRR@k, and nDCG@k for one answerable query."""
    if k <= 0:
        raise ValueError("Cutoff k must be positive")
    if not relevant_ids:
        return {
            f"pooled_recall_at_{k}": 0.0,
            f"precision_at_{k}": 0.0,
            f"mrr_at_{k}": 0.0,
            f"ndcg_at_{k}": 0.0,
        }

    top_ids = retrieved_ids[:k]
    hits = [1 if vid in relevant_ids else 0 for vid in top_ids]
    hit_sum = sum(hits)

    pooled_recall = hit_sum / len(relevant_ids)
    precision = hit_sum / k

    rr = 0.0
    for rank_idx, is_hit in enumerate(hits, start=1):
        if is_hit:
            rr = 1.0 / rank_idx
            break

    dcg = sum(is_hit / math.log2(rank_idx + 1) for rank_idx, is_hit in enumerate(hits, start=1))
    ideal_hits = min(len(relevant_ids), k)
    idcg = sum(1.0 / math.log2(rank_idx + 1) for rank_idx in range(1, ideal_hits + 1))
    ndcg = dcg / idcg if idcg > 0 else 0.0

    return {
        f"pooled_recall_at_{k}": round(pooled_recall, 6),
        f"precision_at_{k}": round(precision, 6),
        f"mrr_at_{k}": round(rr, 6),
        f"ndcg_at_{k}": round(ndcg, 6),
    }


def paired_bootstrap_ci(
    vals_a: list[float],
    vals_b: list[float],
    *,
    n_boot: int = 1000,
    seed: int = 42,
) -> dict[str, float]:
    """Paired bootstrap 95% CIs for system A, system B, and mean(vals_b - vals_a)."""
    if len(vals_a) != len(vals_b):
        raise ValueError("Paired vectors must have equal length")
    if not vals_a:
        return {
            "mean_a": 0.0,
            "ci95_a_low": 0.0,
            "ci95_a_high": 0.0,
            "mean_b": 0.0,
            "ci95_b_low": 0.0,
            "ci95_b_high": 0.0,
            "mean_diff": 0.0,
            "ci95_low": 0.0,
            "ci95_high": 0.0,
        }

    arr_a = np.asarray(vals_a, dtype=np.float64)
    arr_b = np.asarray(vals_b, dtype=np.float64)
    diffs = arr_b - arr_a
    n = len(diffs)

    rng = np.random.default_rng(seed)
    idx = rng.integers(0, n, size=(n_boot, n))
    low_a, high_a = np.percentile(arr_a[idx].mean(axis=1), [2.5, 97.5])
    low_b, high_b = np.percentile(arr_b[idx].mean(axis=1), [2.5, 97.5])
    boot_means = diffs[idx].mean(axis=1)
    low, high = np.percentile(boot_means, [2.5, 97.5])

    return {
        "mean_a": round(float(arr_a.mean()), 6),
        "ci95_a_low": round(float(low_a), 6),
        "ci95_a_high": round(float(high_a), 6),
        "mean_b": round(float(arr_b.mean()), 6),
        "ci95_b_low": round(float(low_b), 6),
        "ci95_b_high": round(float(high_b), 6),
        "mean_diff": round(float(diffs.mean()), 6),
        "ci95_low": round(float(low), 6),
        "ci95_high": round(float(high), 6),
    }


def evaluate_pilot_split(
    service: HybridRetrievalService,
    queries: list[dict[str, Any]],
    qrels: dict[str, dict[str, str]],
    *,
    mode: Literal["bm25", "dense", "hybrid_rrf"] = "bm25",
    rerank: bool,
    k: int = 10,
    eligible_video_ids: set[str] | None = None,
) -> dict[str, Any]:
    """Evaluate answerable pooled metrics, U-uncertainty counts, and no-answer abstention."""
    recalls: list[float] = []
    precisions: list[float] = []
    mrrs: list[float] = []
    ndcgs: list[float] = []
    recalls_all: list[float] = []
    precisions_all: list[float] = []
    mrrs_all: list[float] = []
    ndcgs_all: list[float] = []
    per_query: list[dict[str, Any]] = []

    answerable_count = 0
    answerable_abstained_count = 0
    zero_relevant_pool_count = 0
    uncertain_judgment_count = 0
    total_judged_pairs = 0
    answerable_retrieved_slots = 0
    answerable_unjudged_slots = 0

    no_answer_count = 0
    no_answer_abstained = 0
    fabricated_support_count = 0

    by_phenomenon: dict[str, list[dict[str, float]]] = {}

    for q in queries:
        qid = str(q["query_id"])
        expect_no_answer = bool(q.get("expect_no_answer", False))
        phenomenon = str(q.get("phenomenon", "unspecified"))
        req = RetrievalRequest(
            query=str(q["query"]),
            mode=mode,
            top_k=k,
            rerank=rerank,
            filters=NicheQueryFilter(**q.get("filters", {})),
        )
        resp = service.search(req)
        retrieved_ids = [card.citation.video_id for card in resp.items[:k]]

        raw_judgments = qrels.get(qid, {})
        q_judgments = (
            {vid: lbl for vid, lbl in raw_judgments.items() if vid in eligible_video_ids}
            if eligible_video_ids is not None
            else raw_judgments
        )
        total_judged_pairs += len(q_judgments)
        q_uncertain = sum(1 for lbl in q_judgments.values() if str(lbl).upper() == "U")
        uncertain_judgment_count += q_uncertain
        rel_ids = {vid for vid, lbl in q_judgments.items() if str(lbl) == "1"}

        if expect_no_answer:
            no_answer_count += 1
            abstained_cleanly = len(resp.items) == 0 and bool(resp.insufficient_evidence)
            if abstained_cleanly:
                no_answer_abstained += 1
            if len(resp.items) > 0:
                fabricated_support_count += 1
            per_query.append(
                {
                    "query_id": qid,
                    "author": q.get("author"),
                    "phenomenon": phenomenon,
                    "expect_no_answer": True,
                    "abstained": abstained_cleanly,
                    "insufficient_evidence": bool(resp.insufficient_evidence),
                    "abstain_reason": resp.abstain_reason,
                    "returned_count": len(resp.items),
                    "retrieved_ids": retrieved_ids,
                    "latency_ms": float(resp.timings_ms.get("total_ms", 0.0)),
                }
            )
            continue

        answerable_count += 1
        q_unjudged = sum(1 for vid in retrieved_ids if vid not in q_judgments)
        answerable_retrieved_slots += len(retrieved_ids)
        answerable_unjudged_slots += q_unjudged
        if bool(resp.insufficient_evidence):
            answerable_abstained_count += 1
        if not rel_ids:
            zero_relevant_pool_count += 1
            recalls_all.append(0.0)
            precisions_all.append(0.0)
            mrrs_all.append(0.0)
            ndcgs_all.append(0.0)
            per_query.append(
                {
                    "query_id": qid,
                    "author": q.get("author"),
                    "phenomenon": phenomenon,
                    "expect_no_answer": False,
                    "insufficient_evidence": bool(resp.insufficient_evidence),
                    "abstain_reason": resp.abstain_reason,
                    "relevant_pool_size": 0,
                    "uncertain_in_pool": q_uncertain,
                    f"unjudged_in_top_{k}": q_unjudged,
                    "zero_relevant_pool": True,
                    f"pooled_recall_at_{k}": 0.0,
                    f"precision_at_{k}": 0.0,
                    f"mrr_at_{k}": 0.0,
                    f"ndcg_at_{k}": 0.0,
                    "retrieved_ids": retrieved_ids,
                    "latency_ms": float(resp.timings_ms.get("total_ms", 0.0)),
                }
            )
            continue

        qm = compute_pooled_query_metrics(retrieved_ids, rel_ids, k=k)
        recalls.append(qm[f"pooled_recall_at_{k}"])
        precisions.append(qm[f"precision_at_{k}"])
        mrrs.append(qm[f"mrr_at_{k}"])
        ndcgs.append(qm[f"ndcg_at_{k}"])
        recalls_all.append(qm[f"pooled_recall_at_{k}"])
        precisions_all.append(qm[f"precision_at_{k}"])
        mrrs_all.append(qm[f"mrr_at_{k}"])
        ndcgs_all.append(qm[f"ndcg_at_{k}"])
        by_phenomenon.setdefault(phenomenon, []).append(qm)

        per_query.append(
            {
                "query_id": qid,
                "author": q.get("author"),
                "phenomenon": phenomenon,
                "expect_no_answer": False,
                "insufficient_evidence": bool(resp.insufficient_evidence),
                "abstain_reason": resp.abstain_reason,
                "relevant_pool_size": len(rel_ids),
                "uncertain_in_pool": q_uncertain,
                f"unjudged_in_top_{k}": q_unjudged,
                "zero_relevant_pool": False,
                **qm,
                "retrieved_ids": retrieved_ids,
                "latency_ms": float(resp.timings_ms.get("total_ms", 0.0)),
            }
        )

    denom = max(len(recalls), 1)
    denom_all = max(len(recalls_all), 1)
    phenomenon_summary = {
        phen: {
            "count": len(items),
            f"mrr_at_{k}": round(sum(x[f"mrr_at_{k}"] for x in items) / len(items), 4),
            f"ndcg_at_{k}": round(sum(x[f"ndcg_at_{k}"] for x in items) / len(items), 4),
            f"pooled_recall_at_{k}": round(sum(x[f"pooled_recall_at_{k}"] for x in items) / len(items), 4),
            f"precision_at_{k}": round(sum(x[f"precision_at_{k}"] for x in items) / len(items), 4),
        }
        for phen, items in sorted(by_phenomenon.items())
        if items
    }

    return {
        "total_query_count": len(queries),
        "answerable_query_count": answerable_count,
        "evaluated_answerable_count": len(recalls),
        "answerable_abstained_count": answerable_abstained_count,
        "false_abstention_rate": round(answerable_abstained_count / max(answerable_count, 1), 4)
        if answerable_count
        else 0.0,
        "zero_relevant_pool_count": zero_relevant_pool_count,
        "total_judged_pairs": total_judged_pairs,
        "uncertain_judgment_count": uncertain_judgment_count,
        "uncertain_judgment_rate": round(uncertain_judgment_count / max(total_judged_pairs, 1), 4),
        f"unjudged_in_top_{k}_count": answerable_unjudged_slots,
        f"retrieved_answerable_top_{k}_slots": answerable_retrieved_slots,
        f"unjudged_rate_at_{k}": round(
            answerable_unjudged_slots / max(answerable_retrieved_slots, 1), 4
        )
        if answerable_retrieved_slots
        else 0.0,
        f"pooled_recall_at_{k}": round(sum(recalls) / denom, 4) if recalls else 0.0,
        f"precision_at_{k}": round(sum(precisions) / denom, 4) if precisions else 0.0,
        f"mrr_at_{k}": round(sum(mrrs) / denom, 4) if mrrs else 0.0,
        f"ndcg_at_{k}": round(sum(ndcgs) / denom, 4) if ndcgs else 0.0,
        f"pooled_recall_at_{k}_all_answerable": round(sum(recalls_all) / denom_all, 4)
        if recalls_all
        else 0.0,
        f"precision_at_{k}_all_answerable": round(sum(precisions_all) / denom_all, 4)
        if precisions_all
        else 0.0,
        f"mrr_at_{k}_all_answerable": round(sum(mrrs_all) / denom_all, 4) if mrrs_all else 0.0,
        f"ndcg_at_{k}_all_answerable": round(sum(ndcgs_all) / denom_all, 4) if ndcgs_all else 0.0,
        "no_answer_query_count": no_answer_count,
        "no_answer_abstained_count": no_answer_abstained,
        "no_answer_abstention_rate": round(no_answer_abstained / max(no_answer_count, 1), 4)
        if no_answer_count
        else 0.0,
        "fabricated_support_count": fabricated_support_count,
        "by_phenomenon": phenomenon_summary,
        "vectors": {
            f"pooled_recall_at_{k}": recalls,
            f"precision_at_{k}": precisions,
            f"mrr_at_{k}": mrrs,
            f"ndcg_at_{k}": ndcgs,
            f"mrr_at_{k}_all_answerable": mrrs_all,
            f"ndcg_at_{k}_all_answerable": ndcgs_all,
        },
        "per_query": per_query,
    }


def measure_warm_latency(
    service: HybridRetrievalService,
    queries: list[dict[str, Any]],
    *,
    mode: Literal["bm25", "dense", "hybrid_rrf"] = "bm25",
    rerank: bool,
    n_warm: int = 100,
    k: int = 10,
) -> dict[str, Any]:
    """Measure 1 cold request + n_warm sequential requests at concurrency = 1."""
    if not queries:
        raise ValueError("queries must be non-empty for latency measurement")

    first = queries[0]
    cold_t0 = time.perf_counter()
    service.search(
        RetrievalRequest(
            query=str(first["query"]),
            mode=mode,
            top_k=k,
            rerank=rerank,
            filters=NicheQueryFilter(**first.get("filters", {})),
        )
    )
    cold_ms = (time.perf_counter() - cold_t0) * 1000.0

    warm_latencies: list[float] = []
    for idx in range(n_warm):
        q = queries[idx % len(queries)]
        req = RetrievalRequest(
            query=str(q["query"]),
            mode=mode,
            top_k=k,
            rerank=rerank,
            filters=NicheQueryFilter(**q.get("filters", {})),
        )
        t0 = time.perf_counter()
        service.search(req)
        warm_latencies.append((time.perf_counter() - t0) * 1000.0)

    arr = np.asarray(warm_latencies, dtype=np.float64)
    return {
        "concurrency": 1,
        "n_warm_requests": n_warm,
        "cold_ms": round(float(cold_ms), 3),
        "warm_p50_ms": round(float(np.percentile(arr, 50)), 3),
        "warm_p95_ms": round(float(np.percentile(arr, 95)), 3),
        "warm_mean_ms": round(float(arr.mean()), 3),
        "warm_max_ms": round(float(max(warm_latencies)), 3),
        "peak_rss_mib": round(float(get_peak_rss_mib()), 2),
        "peak_rss_unit": "MiB",
        "peak_rss_scope": "process_lifetime",
    }


def _load_jsonl(path: Path) -> list[dict[str, Any]]:
    return [
        json.loads(line)
        for line in path.read_text(encoding="utf-8").splitlines()
        if line.strip()
    ]


def _load_qrels(path: Path) -> tuple[dict[str, dict[str, str]], dict[str, Any]]:
    qrels: dict[str, dict[str, str]] = {}
    k_labels: list[str] = []
    n_labels: list[str] = []
    human_k_verified = True
    human_n_verified = True
    for row in _load_jsonl(path):
        qid = str(row["query_id"])
        vid = str(row["video_id"])
        adj = str(row["adjudicated_rel"])
        qrels.setdefault(qid, {})[vid] = adj
        k_labels.append(str(row.get("K_rel_draft", adj)))
        n_labels.append(str(row.get("N_rel_draft", adj)))
        if not bool(row.get("K_human_verified", False)):
            human_k_verified = False
        if not bool(row.get("N_human_verified", False)):
            human_n_verified = False

    agree = sum(1 for a, b in zip(k_labels, n_labels) if a == b)
    meta = {
        "total_qrel_rows": len(k_labels),
        "draft_raw_agreement": round(agree / max(len(k_labels), 1), 4),
        "K_human_verified_all": human_k_verified,
        "N_human_verified_all": human_n_verified,
        "human_signoff_complete": human_k_verified and human_n_verified,
    }
    return qrels, meta


def _compare_configs(bm25_res: dict[str, Any], rerank_res: dict[str, Any], k: int = 10) -> dict[str, Any]:
    out: dict[str, Any] = {}
    for metric in (
        f"mrr_at_{k}",
        f"ndcg_at_{k}",
        f"pooled_recall_at_{k}",
        f"precision_at_{k}",
        f"mrr_at_{k}_all_answerable",
        f"ndcg_at_{k}_all_answerable",
    ):
        va = bm25_res["vectors"][metric]
        vb = rerank_res["vectors"][metric]
        if len(va) == len(vb) and va:
            out[metric] = paired_bootstrap_ci(va, vb, n_boot=1000, seed=42)
    return out


def main() -> None:
    parser = argparse.ArgumentParser(description="Run M2.2 pooled BM25 relevance pilot and CPU latency benchmark.")
    parser.add_argument("--corpus", type=Path, default=Path("data/corpus/20261118_taxonomy_fix_v1"))
    parser.add_argument("--bm25", type=Path, default=Path("artifacts/indexes/bm25-v3"))
    parser.add_argument("--dev-queries", type=Path, default=Path("data/evaluation/v2_pilot/dev_queries.jsonl"))
    parser.add_argument("--test-queries", type=Path, default=Path("data/evaluation/v2_pilot/test_queries.jsonl"))
    parser.add_argument("--qrels", type=Path, default=Path("data/evaluation/v2_pilot/qrels_pooled_draft.jsonl"))
    parser.add_argument("--benchmark-id", default="retrieval_v3_pilot")
    parser.add_argument("--output", type=Path, default=Path("artifacts/benchmarks/retrieval_v3_pilot.json"))
    args = parser.parse_args()

    if args.output.exists():
        raise FileExistsError(f"Benchmark receipt already exists: {args.output}")

    manifest, _, df_videos = load_verified_corpus(args.corpus)
    index_receipt = json.loads((args.bm25 / "bm25-receipt.json").read_text(encoding="utf-8"))
    if index_receipt.get("corpus_snapshot_id") != manifest.snapshot_id:
        raise ValueError("BM25 index receipt snapshot ID does not match verified corpus snapshot ID")

    dev_queries = _load_jsonl(args.dev_queries)
    test_queries = _load_jsonl(args.test_queries)
    qrels, qrels_meta = _load_qrels(args.qrels)

    dev_texts = {q["query"].strip().lower() for q in dev_queries}
    test_texts = {q["query"].strip().lower() for q in test_queries}
    if dev_texts & test_texts:
        raise ValueError("dev_queries and test_queries must be strictly disjoint")

    service = HybridRetrievalService.from_dirs(df_videos=df_videos, bm25_dir=args.bm25)

    dev_bm25 = evaluate_pilot_split(service, dev_queries, qrels, rerank=False, k=10)
    dev_rerank = evaluate_pilot_split(service, dev_queries, qrels, rerank=True, k=10)
    test_bm25 = evaluate_pilot_split(service, test_queries, qrels, rerank=False, k=10)
    test_rerank = evaluate_pilot_split(service, test_queries, qrels, rerank=True, k=10)

    dev_cmp = _compare_configs(dev_bm25, dev_rerank, k=10)
    test_cmp = _compare_configs(test_bm25, test_rerank, k=10)

    lat_bm25 = measure_warm_latency(service, test_queries, rerank=False, n_warm=100, k=10)
    lat_rerank = measure_warm_latency(service, test_queries, rerank=True, n_warm=100, k=10)

    for bundle in (dev_bm25, dev_rerank, test_bm25, test_rerank):
        bundle.pop("vectors", None)

    repo_root = Path(__file__).resolve().parents[2]
    report = {
        "benchmark_id": args.benchmark_id,
        "metric_schema_version": 3,
        "corpus_snapshot_id": manifest.snapshot_id,
        "evaluated_at": datetime.now(UTC).isoformat(),
        "environment": {
            "platform": platform.platform(),
            "python": sys.version,
            "cpu_count": os.cpu_count(),
        },
        "indexed_videos": int(df_videos["has_transcript"].sum()),
        "evaluation": {
            "label_source": (
                "two_human_verified_pooled_judgments"
                if qrels_meta["human_signoff_complete"]
                else "ai_assisted_pooled_draft_pending_human_K_N_signoff"
            ),
            "independent_two_human_signoff_complete": qrels_meta["human_signoff_complete"],
            "recall_qualification": (
                "pooled_recall_at_10 over union of top-10 BM25 and BM25+rerank candidates; "
                "not exhaustive 21,748-document corpus recall; unjudged documents are not verified negatives."
            ),
            "qrels_completeness": qrels_meta,
            "provisional_locked_test_targets": {
                "answerable_mrr_at_10_min": 0.60,
                "answerable_ndcg_at_10_min": 0.50,
                "no_answer_fabricated_support_max": 0,
                "warm_cpu_p95_ms_max": 500.0,
            },
        },
        "provenance": {
            "corpus_manifest_sha256": _sha256_file(args.corpus / "manifest.json"),
            "corpus_files_sha256": {entry.filename: entry.sha256 for entry in manifest.files},
            "dev_queries_sha256": _sha256_file(args.dev_queries),
            "test_queries_sha256": _sha256_file(args.test_queries),
            "qrels_sha256": _sha256_file(args.qrels),
            "index_files_sha256": {
                fname: _sha256_file(args.bm25 / fname)
                for fname in ("bm25-receipt.json", "video_ids.json", "vocab.json", "bm25_csr.npz")
            },
            "code_files_sha256": {
                fname: _sha256_file(repo_root / fname)
                for fname in (
                    "pipelines/benchmark_retrieval/pilot_m2_2.py",
                    "packages/retrieval/query_intent.py",
                    "packages/retrieval/service.py",
                    "packages/retrieval/sparse/bm25.py",
                    "packages/retrieval/rerank/scorer.py",
                )
            },
            "index_receipt": index_receipt,
        },
        "splits": {
            "dev": {
                "bm25": dev_bm25,
                "bm25_reranked": dev_rerank,
                "paired_bootstrap_reranked_minus_bm25": dev_cmp,
            },
            "locked_test": {
                "bm25": test_bm25,
                "bm25_reranked": test_rerank,
                "paired_bootstrap_reranked_minus_bm25": test_cmp,
            },
        },
        "latency_100_warm_requests": {
            "bm25": lat_bm25,
            "bm25_reranked": lat_rerank,
        },
    }

    # Strip internal vectors from nested comparison helper outputs if any
    args.output.parent.mkdir(parents=True, exist_ok=True)
    with args.output.open("x", encoding="utf-8") as fp:
        fp.write(json.dumps(report, ensure_ascii=False, indent=2) + "\n")
    print(f"PASS: wrote {args.output} (test bm25_reranked MRR@10={test_rerank['mrr_at_10']}, nDCG@10={test_rerank['ndcg_at_10']})")


if __name__ == "__main__":
    main()
