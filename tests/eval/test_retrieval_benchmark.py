from __future__ import annotations

import json
from pathlib import Path


def test_retrieval_benchmark_report_meets_quality_and_latency_gates() -> None:
    report_path = Path("artifacts/benchmarks/retrieval_v1.json")
    assert report_path.is_file(), "Benchmark report must exist; run pipelines.benchmark_retrieval"

    report = json.loads(report_path.read_text(encoding="utf-8"))
    assert report["indexed_videos"] == 21748

    reranked = report["configurations"]["bm25_viral_boost_reranked"]
    assert reranked["query_count"] >= 15
    assert reranked["mrr_at_10"] >= 0.50
    assert reranked["ndcg_at_10"] >= 0.35
    assert reranked["p95_latency_ms"] <= 2000.0
