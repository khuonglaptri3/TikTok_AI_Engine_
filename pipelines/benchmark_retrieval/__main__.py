from __future__ import annotations

import argparse
import hashlib
import json
import math
from datetime import UTC, datetime
from pathlib import Path
from typing import Any

import pandas as pd

from packages.analytics import load_verified_corpus
from packages.data_contracts.query import NicheQueryFilter, RetrievalRequest
from packages.retrieval import HybridRetrievalService


def _ensure_eval_queries(queries_path: Path, df_videos: pd.DataFrame) -> list[dict[str, Any]]:
    """Build or load keyword/metadata weak labels, not independent relevance judgments."""
    if queries_path.is_file():
        return [
            json.loads(line)
            for line in queries_path.read_text(encoding="utf-8").splitlines()
            if line.strip()
        ]

    queries_path.parent.mkdir(parents=True, exist_ok=True)
    tr = df_videos[df_videos["has_transcript"]].copy()

    specs: list[tuple[str, str, dict[str, str], str, str | None]] = [
        ("q01", "quán ốc bình dân ăn đêm ở Sài Gòn", {"city_norm": "hồ chí minh"}, "ốc", "hồ chí minh"),
        ("q02", "công thức làm gà rang bơ tỏi đơn giản tại nhà", {"video_format": "Hướng dẫn nấu ăn"}, "gà rang bơ tỏi", None),
        ("q03", "review buffet lẩu nướng giá rẻ ở Hà Nội", {"city_norm": "hà nội"}, "buffet", "hà nội"),
        ("q04", "cơm tấm sườn bì chả ngon ở Hồ Chí Minh", {"food_category": "Cơm & Bữa chính"}, "cơm tấm", "hồ chí minh"),
        ("q05", "review phở bò chuẩn vị Hà Nội", {"food_category": "Món nước & Sợi"}, "phở bò", "hà nội"),
        ("q06", "ăn vặt bánh tráng trộn xế chiều sinh viên", {"food_category": "Ăn vặt & Đường phố"}, "bánh tráng trộn", None),
        ("q07", "mukbang mì cay hải sản siêu cay", {"video_format": "Mukbang"}, "mì cay", None),
        ("q08", "quán cà phê bánh ngọt đẹp ở Đà Lạt", {"city_norm": "đà lạt"}, "cà phê", "đà lạt"),
        ("q09", "review bún đậu mắm tôm đầy đặn", {"food_category": "Món nước & Sợi"}, "bún đậu", None),
        ("q10", "món chay healthy salad ức gà giữ dáng", {"food_category": "Ẩm thực Chay & Healthy"}, "salad", None),
        ("q11", "bún bò Huế đậm đà nước dùng ngon", {"food_category": "Món nước & Sợi"}, "bún bò", None),
        ("q12", "bánh mì thịt nướng giòn rụm buổi sáng", {"food_category": "Ăn vặt & Đường phố"}, "bánh mì", None),
        ("q13", "hướng dẫn nấu canh chua cá kho bữa cơm gia đình", {"video_format": "Hướng dẫn nấu ăn"}, "cá kho", None),
        ("q14", "trà sữa matcha kem cheese béo ngậy", {"food_category": "Đồ ngọt, Trà & Cà phê"}, "matcha", None),
        ("q15", "khám phá ẩm thực đặc sản Đà Nẵng", {"city_norm": "đà nẵng"}, "mì quảng", "đà nẵng"),
        ("q16", "chân gà sả tắc chua cay lai rai cùng bạn bè", {"food_category": "Ăn vặt & Đường phố"}, "chân gà", None),
    ]

    rows: list[dict[str, Any]] = []
    for qid, query_text, f_dict, kw, req_city in specs:
        mask = tr["caption"].str.lower().str.contains(kw, na=False) | tr["transcript"].str.lower().str.contains(
            kw, na=False
        )
        if req_city:
            mask &= tr["city_norm"].fillna("") == req_city
        if "video_format" in f_dict:
            mask &= tr["video_format"].fillna("") == f_dict["video_format"]
        if "food_category" in f_dict:
            mask &= tr["food_category"].fillna("") == f_dict["food_category"]
        rel_df = tr.loc[mask]
        rel_ids = rel_df["video_id"].astype(str).tolist()
        if rel_ids:
            rows.append(
                {
                    "query_id": qid,
                    "query": query_text,
                    "filters": f_dict,
                    "relevant_video_ids": rel_ids,
                }
            )

    with queries_path.open("w", encoding="utf-8") as fp:
        for item in rows:
            fp.write(json.dumps(item, ensure_ascii=False) + "\n")
    return rows


def _evaluate_run(
    service: HybridRetrievalService,
    queries: list[dict[str, Any]],
    rerank: bool,
    k: int = 10,
) -> dict[str, float]:
    recalls: list[float] = []
    precisions: list[float] = []
    recall_ceilings: list[float] = []
    mrrs: list[float] = []
    ndcgs: list[float] = []
    latencies: list[float] = []
    if k <= 0:
        raise ValueError("Metric cutoff k must be positive")

    for q in queries:
        rel_set = set(q["relevant_video_ids"])
        if not rel_set:
            continue
        req = RetrievalRequest(
            query=q["query"],
            mode="bm25",
            top_k=k,
            rerank=rerank,
            filters=NicheQueryFilter(**q.get("filters", {})),
        )
        resp = service.search(req)
        latencies.append(float(resp.timings_ms.get("total_ms", 0.0)))

        retrieved_ids = [card.citation.video_id for card in resp.items[:k]]
        hits = [1 if vid in rel_set else 0 for vid in retrieved_ids]

        # Standard recall counts all relevant documents; missing result slots
        # are non-relevant for precision. A perfect top-k can still recall <1.
        recalls.append(sum(hits) / len(rel_set))
        precisions.append(sum(hits) / k)
        recall_ceilings.append(min(len(rel_set), k) / len(rel_set))

        # MRR@K
        rr = 0.0
        for rank_idx, is_hit in enumerate(hits, start=1):
            if is_hit:
                rr = 1.0 / rank_idx
                break
        mrrs.append(rr)

        # nDCG@K
        dcg = sum(is_hit / math.log2(rank_idx + 1) for rank_idx, is_hit in enumerate(hits, start=1))
        ideal_hits = min(len(rel_set), k)
        idcg = sum(1.0 / math.log2(rank_idx + 1) for rank_idx in range(1, ideal_hits + 1))
        ndcgs.append(dcg / idcg if idcg > 0 else 0.0)

    n = max(len(recalls), 1)
    sorted_lat = sorted(latencies) if latencies else [0.0]
    p95_idx = min(len(sorted_lat) - 1, int(0.95 * len(sorted_lat)))
    return {
        "query_count": len(recalls),
        "input_query_count": len(queries),
        "zero_relevant_query_count": len(queries) - len(recalls),
        f"recall_at_{k}": round(sum(recalls) / n, 4),
        f"precision_at_{k}": round(sum(precisions) / n, 4),
        f"recall_at_{k}_ceiling": round(sum(recall_ceilings) / n, 4),
        f"mrr_at_{k}": round(sum(mrrs) / n, 4),
        f"ndcg_at_{k}": round(sum(ndcgs) / n, 4),
        "mean_latency_ms": round(sum(latencies) / max(len(latencies), 1), 2),
        "p95_latency_ms": round(sorted_lat[p95_idx], 2),
    }


def _sha256_file(path: Path) -> str:
    digest = hashlib.sha256()
    with path.open("rb") as stream:
        for chunk in iter(lambda: stream.read(1024 * 1024), b""):
            digest.update(chunk)
    return digest.hexdigest()


def main() -> None:
    parser = argparse.ArgumentParser(description="Benchmark Vietnamese BM25 + Reranking retrieval quality.")
    parser.add_argument("--corpus", type=Path, default=Path("data/corpus/20261117_recovered_v1"))
    parser.add_argument("--bm25", "--index", dest="bm25", type=Path, default=Path("artifacts/indexes/bm25-v2"))
    parser.add_argument("--queries", type=Path, default=Path("data/evaluation/v1/queries.jsonl"))
    parser.add_argument("--benchmark-id", default="retrieval_v2")
    parser.add_argument("--output", type=Path, help="New receipt path (default: artifacts/benchmarks/<benchmark-id>.json); existing files are never replaced.")
    args = parser.parse_args()
    if not args.benchmark_id or any(c not in "abcdefghijklmnopqrstuvwxyzABCDEFGHIJKLMNOPQRSTUVWXYZ0123456789_.-" for c in args.benchmark_id):
        parser.error("benchmark-id must contain only letters, digits, underscores, dots or hyphens")
    output = args.output or Path("artifacts/benchmarks") / f"{args.benchmark_id}.json"
    if output.exists():
        raise FileExistsError(f"Benchmark receipt already exists: {output}")

    manifest, _, df_videos = load_verified_corpus(args.corpus)
    receipt_path = args.bm25 / "bm25-receipt.json"
    index_receipt = json.loads(receipt_path.read_text(encoding="utf-8"))
    if index_receipt.get("corpus_snapshot_id") != manifest.snapshot_id:
        raise ValueError("Index receipt corpus snapshot does not match the verified corpus snapshot")
    queries = _ensure_eval_queries(args.queries, df_videos)
    service = HybridRetrievalService.from_dirs(df_videos=df_videos, bm25_dir=args.bm25)

    bm25_only = _evaluate_run(service, queries, rerank=False, k=10)
    bm25_reranked = _evaluate_run(service, queries, rerank=True, k=10)

    report = {
        "benchmark_id": args.benchmark_id,
        "metric_schema_version": 2,
        "corpus_snapshot_id": manifest.snapshot_id,
        "evaluated_at": datetime.now(UTC).isoformat(),
        "indexed_videos": int(df_videos["has_transcript"].sum()),
        "queries_file": str(args.queries),
        "evaluation": {
            "label_source": "lexical_metadata_weak_labels",
            "independent_relevance_judgments": False,
            "limitation": "Keyword/metadata weak labels measure regression against these rules, not independently annotated relevance quality or current trends.",
            "aggregation": "macro over queries with at least one relevant video",
            "zero_relevant_policy": "exclude and report count; all-empty inputs yield zero metrics",
            "metric_definitions": {
                "recall_at_10": "relevant retrieved in top 10 / all relevant video IDs",
                "precision_at_10": "relevant retrieved in top 10 / 10 (missing slots count as non-relevant)",
                "recall_at_10_ceiling": "macro mean of min(10, relevant count) / relevant count",
            },
            "relevant_video_counts": {
                str(q.get("query_id", i)): len(set(q["relevant_video_ids"]))
                for i, q in enumerate(queries, start=1)
            },
        },
        "provenance": {
            "corpus_manifest_sha256": _sha256_file(args.corpus / "manifest.json"),
            "corpus_files_sha256": {entry.filename: entry.sha256 for entry in manifest.files},
            "queries_sha256": _sha256_file(args.queries),
            "index_files_sha256": {
                filename: _sha256_file(args.bm25 / filename)
                for filename in ("bm25-receipt.json", "video_ids.json", "vocab.json", "bm25_csr.npz")
            },
            "code_files_sha256": {
                filename: _sha256_file(Path(__file__).resolve().parents[2] / filename)
                for filename in (
                    "pipelines/benchmark_retrieval/__main__.py",
                    "packages/retrieval/service.py",
                    "packages/retrieval/sparse/bm25.py",
                    "packages/retrieval/fusion/rrf.py",
                    "packages/retrieval/rerank/scorer.py",
                )
            },
            "configuration": {"mode": "bm25", "top_k": 10, "index_receipt": index_receipt},
        },
        "configurations": {
            "bm25_viral_boost": bm25_only,
            "bm25_viral_boost_reranked": bm25_reranked,
        },
    }

    output.parent.mkdir(parents=True, exist_ok=True)
    with output.open("x", encoding="utf-8") as stream:
        stream.write(json.dumps(report, ensure_ascii=False, indent=2))
    print(json.dumps(report, ensure_ascii=False, indent=2))


if __name__ == "__main__":
    main()
