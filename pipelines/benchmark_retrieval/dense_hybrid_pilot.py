"""Measured parity comparison across BM25, Dense, and RRF Hybrid retrieval (M6.1)."""

from __future__ import annotations

import argparse
import hashlib
import json
import math
import os
import platform
import random
import resource
import time
from datetime import UTC, datetime
from pathlib import Path
from typing import Any, Literal

from packages.analytics import load_verified_corpus
from packages.data_contracts.query import NicheQueryFilter, RetrievalRequest
from packages.retrieval import HybridRetrievalService
from packages.retrieval.dense import LocalDenseIndex, load_saved_encoder
from packages.retrieval.sparse.bm25 import BM25Index
from pipelines.benchmark_retrieval.__main__ import _ensure_eval_queries


def _sha256_file(path: Path) -> str:
    digest = hashlib.sha256()
    with path.open("rb") as stream:
        for chunk in iter(lambda: stream.read(1024 * 1024), b""):
            digest.update(chunk)
    return digest.hexdigest()


def _read_total_ram_gb() -> float:
    meminfo = Path("/proc/meminfo")
    if not meminfo.is_file():
        return 0.0
    for line in meminfo.read_text(encoding="utf-8").splitlines():
        if line.startswith("MemTotal:"):
            kb = float(line.split()[1])
            return round(kb / (1024.0 * 1024.0), 2)
    return 0.0


def paired_bootstrap_ci(
    scores_a: list[float],
    scores_b: list[float],
    *,
    n_resamples: int = 1000,
    seed: int = 42,
) -> dict[str, float]:
    """Compute mean paired difference (A - B) and 95% bootstrap confidence interval."""
    if len(scores_a) != len(scores_b):
        raise ValueError("Paired bootstrap inputs must have identical lengths")
    n = len(scores_a)
    if n == 0:
        return {"n": 0.0, "mean_diff": 0.0, "ci_low": 0.0, "ci_high": 0.0}
    diffs = [a - b for a, b in zip(scores_a, scores_b)]
    observed = sum(diffs) / n
    rng = random.Random(seed)
    means: list[float] = []
    for _ in range(n_resamples):
        sample_mean = sum(diffs[rng.randrange(n)] for _ in range(n)) / n
        means.append(sample_mean)
    means.sort()
    lo_idx = max(0, min(len(means) - 1, int(0.025 * len(means))))
    hi_idx = max(0, min(len(means) - 1, int(0.975 * len(means))))
    return {
        "n": float(n),
        "mean_diff": round(observed, 4),
        "ci_low": round(means[lo_idx], 4),
        "ci_high": round(means[hi_idx], 4),
    }


def _evaluate_parity_mode(
    service: HybridRetrievalService,
    queries: list[dict[str, Any]],
    eligible_ids: set[str],
    mode: Literal["bm25", "dense", "hybrid_rrf"],
    rerank: bool,
    k: int = 10,
) -> tuple[dict[str, float], list[float], list[float]]:
    recalls: list[float] = []
    precisions: list[float] = []
    mrrs: list[float] = []
    ndcgs: list[float] = []
    latencies: list[float] = []

    for q in queries:
        rel_set = set(q["relevant_video_ids"]) & eligible_ids
        if not rel_set:
            continue
        req = RetrievalRequest(
            query=q["query"],
            mode=mode,
            top_k=k,
            rerank=rerank,
            filters=NicheQueryFilter(**q.get("filters", {})),
        )
        resp = service.search(req)
        latencies.append(float(resp.timings_ms.get("total_ms", 0.0)))

        retrieved_ids = [card.citation.video_id for card in resp.items[:k]]
        hits = [1 if vid in rel_set else 0 for vid in retrieved_ids]

        recalls.append(sum(hits) / len(rel_set))
        precisions.append(sum(hits) / k)

        rr = 0.0
        for rank_idx, is_hit in enumerate(hits, start=1):
            if is_hit:
                rr = 1.0 / rank_idx
                break
        mrrs.append(rr)

        dcg = sum(is_hit / math.log2(rank_idx + 1) for rank_idx, is_hit in enumerate(hits, start=1))
        ideal_hits = min(len(rel_set), k)
        idcg = sum(1.0 / math.log2(rank_idx + 1) for rank_idx in range(1, ideal_hits + 1))
        ndcgs.append(dcg / idcg if idcg > 0 else 0.0)

    n = max(len(recalls), 1)
    sorted_lat = sorted(latencies) if latencies else [0.0]
    p50_idx = min(len(sorted_lat) - 1, int(0.50 * len(sorted_lat)))
    p95_idx = min(len(sorted_lat) - 1, int(0.95 * len(sorted_lat)))
    summary = {
        "query_count": float(len(recalls)),
        f"recall_at_{k}": round(sum(recalls) / n, 4),
        f"precision_at_{k}": round(sum(precisions) / n, 4),
        f"mrr_at_{k}": round(sum(mrrs) / n, 4),
        f"ndcg_at_{k}": round(sum(ndcgs) / n, 4),
        "p50_latency_ms": round(sorted_lat[p50_idx], 2),
        "p95_latency_ms": round(sorted_lat[p95_idx], 2),
    }
    return summary, mrrs, ndcgs


def _measure_warm_latency(
    service: HybridRetrievalService,
    queries: list[dict[str, Any]],
    mode: Literal["bm25", "dense", "hybrid_rrf"],
    rerank: bool,
    repetitions: int = 100,
) -> dict[str, float | int]:
    if not queries:
        return {"requests": 0, "cold_ms": 0.0, "warm_p50_ms": 0.0, "warm_p95_ms": 0.0}

    first_q = queries[0]
    cold_t0 = time.perf_counter()
    service.search(
        RetrievalRequest(
            query=first_q["query"],
            mode=mode,
            top_k=10,
            rerank=rerank,
            filters=NicheQueryFilter(**first_q.get("filters", {})),
        )
    )
    cold_ms = round((time.perf_counter() - cold_t0) * 1000.0, 2)

    warm_times: list[float] = []
    for i in range(repetitions):
        q = queries[i % len(queries)]
        t0 = time.perf_counter()
        service.search(
            RetrievalRequest(
                query=q["query"],
                mode=mode,
                top_k=10,
                rerank=rerank,
                filters=NicheQueryFilter(**q.get("filters", {})),
            )
        )
        warm_times.append((time.perf_counter() - t0) * 1000.0)

    warm_sorted = sorted(warm_times)
    p50_idx = min(len(warm_sorted) - 1, int(0.50 * len(warm_sorted)))
    p95_idx = min(len(warm_sorted) - 1, int(0.95 * len(warm_sorted)))
    return {
        "requests": repetitions,
        "cold_ms": cold_ms,
        "warm_p50_ms": round(warm_sorted[p50_idx], 2),
        "warm_p95_ms": round(warm_sorted[p95_idx], 2),
    }


def run_dense_hybrid_pilot(
    *,
    corpus_dir: Path,
    bm25_dir: Path,
    dense_dir: Path,
    queries_path: Path,
    output_path: Path,
    repetitions: int = 100,
) -> dict[str, Any]:
    if output_path.exists():
        raise FileExistsError(f"Benchmark receipt already exists: {output_path}")

    manifest, _, df_videos = load_verified_corpus(corpus_dir)
    bm25 = BM25Index.load(bm25_dir)
    dense = LocalDenseIndex.load(dense_dir)
    encoder = load_saved_encoder(dense_dir)

    dense_receipt = json.loads((dense_dir / "dense-receipt.json").read_text(encoding="utf-8"))
    if dense_receipt.get("corpus_snapshot_id") != manifest.snapshot_id:
        raise ValueError("Dense index corpus_snapshot_id does not match corpus manifest")
    if len(dense.video_ids) > 5000:
        raise ValueError(f"M6.1 pilot exceeds 5,000-record cap: {len(dense.video_ids)}")

    eligible_ids = set(dense.video_ids)
    df_parity = df_videos[df_videos["video_id"].astype(str).isin(eligible_ids)].copy()
    queries = _ensure_eval_queries(queries_path, df_videos)

    service = HybridRetrievalService(
        df_videos=df_parity,
        bm25_index=bm25,
        dense_index=dense,
        dense_encoder=encoder,
        restrict_to_df=True,
    )

    bm25_base, bm25_mrr, bm25_ndcg = _evaluate_parity_mode(service, queries, eligible_ids, "bm25", rerank=False)
    bm25_rerank, bm25r_mrr, bm25r_ndcg = _evaluate_parity_mode(service, queries, eligible_ids, "bm25", rerank=True)
    dense_base, dense_mrr, dense_ndcg = _evaluate_parity_mode(service, queries, eligible_ids, "dense", rerank=False)
    rrf_base, rrf_mrr, rrf_ndcg = _evaluate_parity_mode(service, queries, eligible_ids, "hybrid_rrf", rerank=False)
    rrf_rerank, rrfr_mrr, rrfr_ndcg = _evaluate_parity_mode(service, queries, eligible_ids, "hybrid_rrf", rerank=True)

    latency_100 = {
        "bm25": _measure_warm_latency(service, queries, "bm25", rerank=False, repetitions=repetitions),
        "dense": _measure_warm_latency(service, queries, "dense", rerank=False, repetitions=repetitions),
        "hybrid_rrf": _measure_warm_latency(service, queries, "hybrid_rrf", rerank=False, repetitions=repetitions),
        "hybrid_rrf_reranked": _measure_warm_latency(service, queries, "hybrid_rrf", rerank=True, repetitions=repetitions),
    }
    peak_rss_mb = round(resource.getrusage(resource.RUSAGE_SELF).ru_maxrss / 1024.0, 2)

    paired_deltas = {
        "dense_minus_bm25": {
            "mrr_at_10": paired_bootstrap_ci(dense_mrr, bm25_mrr),
            "ndcg_at_10": paired_bootstrap_ci(dense_ndcg, bm25_ndcg),
        },
        "hybrid_rrf_minus_bm25": {
            "mrr_at_10": paired_bootstrap_ci(rrf_mrr, bm25_mrr),
            "ndcg_at_10": paired_bootstrap_ci(rrf_ndcg, bm25_ndcg),
        },
        "hybrid_rrf_reranked_minus_bm25_reranked": {
            "mrr_at_10": paired_bootstrap_ci(rrfr_mrr, bm25r_mrr),
            "ndcg_at_10": paired_bootstrap_ci(rrfr_ndcg, bm25r_ndcg),
        },
    }

    hybrid_gain_ndcg = paired_deltas["hybrid_rrf_minus_bm25"]["ndcg_at_10"]["mean_diff"]
    hybrid_gain_mrr = paired_deltas["hybrid_rrf_minus_bm25"]["mrr_at_10"]["mean_diff"]
    latency_budget_ok = all(float(v["warm_p95_ms"]) <= 1000.0 for v in latency_100.values())
    ram_budget_ok = peak_rss_mb <= 8192.0

    report: dict[str, Any] = {
        "benchmark_id": output_path.stem,
        "task_id": "M6.1",
        "evaluated_at": datetime.now(UTC).isoformat(),
        "corpus_snapshot_id": manifest.snapshot_id,
        "parity_cohort": {
            "record_count": len(eligible_ids),
            "max_records_cap": 5000,
            "query_count_evaluated": int(bm25_base["query_count"]),
            "queries_file": str(queries_path),
            "label_source": "lexical_metadata_weak_labels",
            "independent_human_qrels_available": False,
        },
        "hardware": {
            "platform": platform.platform(),
            "processor": platform.processor() or "x86_64",
            "logical_cpus": os.cpu_count() or 1,
            "total_ram_gb": _read_total_ram_gb(),
            "concurrency": 1,
        },
        "resource_measurements": {
            "dense_index_bytes": dense_receipt.get("index_bytes"),
            "dense_build_time_sec": dense_receipt.get("build_time_sec"),
            "peak_rss_mb": peak_rss_mb,
            "peak_rss_within_8gib": ram_budget_ok,
            "all_warm_p95_within_1000ms": latency_budget_ok,
            "latency_100_requests_ms": latency_100,
        },
        "configurations": {
            "bm25": bm25_base,
            "bm25_reranked": bm25_rerank,
            "dense": dense_base,
            "hybrid_rrf": rrf_base,
            "hybrid_rrf_reranked": rrf_rerank,
        },
        "paired_bootstrap_95ci": paired_deltas,
        "decision_summary": {
            "hybrid_minus_bm25_ndcg": hybrid_gain_ndcg,
            "hybrid_minus_bm25_mrr": hybrid_gain_mrr,
            "recommendation": (
                "Keep simplest BM25 baseline as production default until M2.2 human-judged qrels confirm a statistically positive hybrid gain."
                if hybrid_gain_ndcg <= 0.0 and hybrid_gain_mrr <= 0.0
                else "Observed positive spike delta under weak labels; re-verify on frozen M2.2 human-judged qrels before replacing BM25."
            ),
        },
        "provenance": {
            "corpus_manifest_sha256": _sha256_file(corpus_dir / "manifest.json"),
            "dense_receipt": dense_receipt,
            "queries_sha256": _sha256_file(queries_path),
        },
    }

    output_path.parent.mkdir(parents=True, exist_ok=True)
    with output_path.open("x", encoding="utf-8") as stream:
        stream.write(json.dumps(report, ensure_ascii=False, indent=2) + "\n")
    return report


def main() -> None:
    parser = argparse.ArgumentParser(description="Run M6.1 parity benchmark across BM25, Dense, and Hybrid RRF.")
    parser.add_argument("--corpus", type=Path, default=Path("data/corpus/20261117_recovered_v1"))
    parser.add_argument("--bm25", type=Path, default=Path("artifacts/indexes/bm25-v2"))
    parser.add_argument("--dense", type=Path, default=Path("artifacts/indexes/dense-svd-v1"))
    parser.add_argument("--queries", type=Path, default=Path("data/evaluation/v1/queries.jsonl"))
    parser.add_argument("--output", type=Path, default=Path("artifacts/benchmarks/m6_1_dense_hybrid_spike.json"))
    parser.add_argument("--repetitions", type=int, default=100)
    args = parser.parse_args()

    report = run_dense_hybrid_pilot(
        corpus_dir=args.corpus,
        bm25_dir=args.bm25,
        dense_dir=args.dense,
        queries_path=args.queries,
        output_path=args.output,
        repetitions=args.repetitions,
    )
    print(json.dumps(report, ensure_ascii=False, indent=2))


if __name__ == "__main__":
    main()
