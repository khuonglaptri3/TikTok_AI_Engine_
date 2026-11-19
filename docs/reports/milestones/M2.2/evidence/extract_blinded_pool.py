"""Extract deterministic blinded top-10 candidate pools (BM25 U BM25+rerank) and raw no-answer top-5 audit."""
from __future__ import annotations

import json
import random
import unicodedata
from pathlib import Path
from typing import Any

from packages.analytics import load_verified_corpus
from packages.data_contracts.query import NicheQueryFilter, RetrievalRequest
from packages.retrieval import HybridRetrievalService

ROOT = Path(__file__).resolve().parents[5]
EVIDENCE_DIR = Path(__file__).resolve().parent
PILOT_DIR = ROOT / "data/evaluation/v2_pilot"


def _load_jsonl(path: Path) -> list[dict[str, Any]]:
    return [json.loads(line) for line in path.read_text(encoding="utf-8").splitlines() if line.strip()]


def main() -> int:
    _, _, df_videos = load_verified_corpus(ROOT / "data/corpus/20261118_taxonomy_fix_v1")
    service = HybridRetrievalService.from_dirs(
        df_videos=df_videos,
        bm25_dir=ROOT / "artifacts/indexes/bm25-v3",
    )

    all_queries = _load_jsonl(PILOT_DIR / "dev_queries.jsonl") + _load_jsonl(PILOT_DIR / "test_queries.jsonl")
    rng = random.Random(20261119)

    blinded_rows: list[dict[str, Any]] = []
    provenance_map: dict[str, Any] = {}
    no_answer_raw_rows: list[dict[str, Any]] = []

    for q in all_queries:
        qid = str(q["query_id"])
        q_nfc_display = unicodedata.normalize("NFC", str(q["query"]))
        filters = q.get("filters", {})

        resp_bm25 = service.search(
            RetrievalRequest(query=str(q["query"]), mode="bm25", top_k=10, rerank=False, filters=NicheQueryFilter(**filters))
        )
        resp_rerank = service.search(
            RetrievalRequest(query=str(q["query"]), mode="bm25", top_k=10, rerank=True, filters=NicheQueryFilter(**filters))
        )

        bm25_ranks = {c.citation.video_id: c.rank for c in resp_bm25.items[:10]}
        rerank_ranks = {c.citation.video_id: c.rank for c in resp_rerank.items[:10]}
        union_vids = sorted(set(bm25_ranks) | set(rerank_ranks))
        rng.shuffle(union_vids)

        provenance_map[qid] = {
            "split": q["split"],
            "phenomenon": q["phenomenon"],
            "expect_no_answer": q["expect_no_answer"],
            "bm25_abstained": resp_bm25.insufficient_evidence,
            "rerank_abstained": resp_rerank.insufficient_evidence,
            "bm25_top10": [c.citation.video_id for c in resp_bm25.items[:10]],
            "rerank_top10": [c.citation.video_id for c in resp_rerank.items[:10]],
            "pool_size": len(union_vids),
            "slot_origins": {},
        }

        for slot_idx, vid in enumerate(union_vids, start=1):
            slot_id = f"{qid}_s{slot_idx:02d}"
            row = service.video_lookup[vid]
            provenance_map[qid]["slot_origins"][slot_id] = {
                "video_id": vid,
                "bm25_rank": bm25_ranks.get(vid),
                "rerank_rank": rerank_ranks.get(vid),
            }
            blinded_rows.append(
                {
                    "slot_id": slot_id,
                    "query_id": qid,
                    "split": q["split"],
                    "author": q["author"],
                    "phenomenon": q["phenomenon"],
                    "query_nfc": q_nfc_display,
                    "filters": filters,
                    "video_id": vid,
                    "city_norm": row.get("city_norm") if str(row.get("city_norm")) != "nan" else None,
                    "district_norm": row.get("district_norm") if str(row.get("district_norm")) != "nan" else None,
                    "video_format": str(row.get("video_format") or ""),
                    "food_category": str(row.get("food_category") or ""),
                    "poi_name": row.get("poi_name") if str(row.get("poi_name")) != "nan" else None,
                    "caption": str(row.get("caption") or "")[:300],
                    "transcript": str(row.get("transcript") or "")[:900],
                }
            )

        if q.get("expect_no_answer"):
            raw_hits = service.bm25.search(q_nfc_display, top_k=5)
            for raw_rank, (vid, raw_score) in enumerate(raw_hits, start=1):
                row = service.video_lookup.get(vid, {})
                no_answer_raw_rows.append(
                    {
                        "query_id": qid,
                        "split": q["split"],
                        "query_nfc": q_nfc_display,
                        "filters": json.dumps(filters, ensure_ascii=False),
                        "guarded_returned_count": len(resp_rerank.items),
                        "guarded_abstain_reason": resp_rerank.abstain_reason or "",
                        "raw_ungoarded_bm25_rank": raw_rank,
                        "raw_bm25_score": round(float(raw_score), 4),
                        "video_id": vid,
                        "city_norm": row.get("city_norm") if str(row.get("city_norm")) != "nan" else "",
                        "caption": str(row.get("caption") or "")[:220],
                        "transcript_excerpt": str(row.get("transcript") or "")[:320],
                    }
                )

    (EVIDENCE_DIR / "blinded_candidates_only.jsonl").write_text(
        "\n".join(json.dumps(r, ensure_ascii=False) for r in blinded_rows) + "\n",
        encoding="utf-8",
    )
    (EVIDENCE_DIR / "pool_provenance_map.json").write_text(
        json.dumps(provenance_map, ensure_ascii=False, indent=2) + "\n",
        encoding="utf-8",
    )
    (EVIDENCE_DIR / "no_answer_raw_candidates.jsonl").write_text(
        "\n".join(json.dumps(r, ensure_ascii=False) for r in no_answer_raw_rows) + "\n",
        encoding="utf-8",
    )
    print(f"Extracted {len(blinded_rows)} blinded candidate pairs and {len(no_answer_raw_rows)} raw no-answer audit rows.")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
