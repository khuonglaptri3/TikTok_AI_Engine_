from __future__ import annotations

import argparse
import json
import math
from datetime import datetime, timezone
from pathlib import Path
from typing import Any

import pandas as pd

from packages.analytics import load_verified_corpus
from packages.data_contracts.query import NicheQueryFilter, RetrievalRequest
from packages.retrieval import HybridRetrievalService


def _ensure_eval_queries(queries_path: Path, df_videos: pd.DataFrame) -> list[dict[str, Any]]:
    """Build or load independent metadata-verified Vietnamese F&B evaluation queries."""
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
    mrrs: list[float] = []
    ndcgs: list[float] = []
    latencies: list[float] = []

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

        # Recall@K (capped denominator at min(|rel|, K) for standard bounded top-K recall, plus hit_rate@K)
        denom = min(len(rel_set), k)
        recalls.append(sum(hits) / max(denom, 1))

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
        "recall_at_10": round(sum(recalls) / n, 4),
        "mrr_at_10": round(sum(mrrs) / n, 4),
        "ndcg_at_10": round(sum(ndcgs) / n, 4),
        "mean_latency_ms": round(sum(latencies) / max(len(latencies), 1), 2),
        "p95_latency_ms": round(sorted_lat[p95_idx], 2),
    }


def main() -> None:
    parser = argparse.ArgumentParser(description="Benchmark Vietnamese BM25 + Reranking retrieval quality.")
    parser.add_argument("--corpus", type=Path, default=Path("data/corpus/20261116_v1"))
    parser.add_argument("--bm25", "--index", dest="bm25", type=Path, default=Path("artifacts/indexes/bm25-v1"))
    parser.add_argument("--queries", type=Path, default=Path("data/evaluation/v1/queries.jsonl"))
    parser.add_argument("--output", type=Path, default=Path("artifacts/benchmarks/retrieval_v1.json"))
    args = parser.parse_args()

    manifest, _, df_videos = load_verified_corpus(args.corpus)
    queries = _ensure_eval_queries(args.queries, df_videos)
    service = HybridRetrievalService.from_dirs(df_videos=df_videos, bm25_dir=args.bm25)

    bm25_only = _evaluate_run(service, queries, rerank=False, k=10)
    bm25_reranked = _evaluate_run(service, queries, rerank=True, k=10)

    report = {
        "benchmark_id": "retrieval_v1",
        "corpus_snapshot_id": manifest.snapshot_id,
        "evaluated_at": datetime.now(timezone.utc).isoformat(),
        "indexed_videos": int(df_videos["has_transcript"].sum()),
        "queries_file": str(args.queries),
        "configurations": {
            "bm25_viral_boost": bm25_only,
            "bm25_viral_boost_reranked": bm25_reranked,
        },
    }

    args.output.parent.mkdir(parents=True, exist_ok=True)
    args.output.write_text(json.dumps(report, ensure_ascii=False, indent=2), encoding="utf-8")
    print(json.dumps(report, ensure_ascii=False, indent=2))


if __name__ == "__main__":
    main()
