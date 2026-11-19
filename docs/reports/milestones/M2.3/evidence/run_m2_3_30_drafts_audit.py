#!/usr/bin/env python3
"""Run GroundedScriptEngine (offline_grounded, 0 provider calls) on N's 15 + K's 15 briefs over 20261118_taxonomy_fix_v1 + bm25-v3 and apply K's full-source claim audit."""
from __future__ import annotations

import json
import re
import sys
from pathlib import Path
from typing import Any

import pandas as pd

_REPO_ROOT = Path(__file__).resolve().parents[5]
if str(_REPO_ROOT) not in sys.path:
    sys.path.insert(0, str(_REPO_ROOT))

from packages.analytics import NicheAnalyticsEngine
from packages.common.settings import AppSettings
from packages.data_contracts.query import ScriptGenerationRequest
from packages.llm import BoundedGeminiClient
from packages.retrieval import HybridRetrievalService
from packages.script_engine import GroundedScriptEngine

EVIDENCE_DIR = Path(__file__).resolve().parent
ROOT = _REPO_ROOT
CORPUS_DIR = ROOT / "data/corpus/20261118_taxonomy_fix_v1"
BM25_DIR = ROOT / "artifacts/indexes/bm25-v3"

N_QUERIES_PATH = EVIDENCE_DIR / "nguyen_15_queries.jsonl"
K_QUERIES_PATH = EVIDENCE_DIR / "khuong_15_queries.jsonl"
K_OUT_CSV = EVIDENCE_DIR / "khuong_15_drafts_audit.csv"
COMBINED_OUT_CSV = EVIDENCE_DIR / "combined_30_drafts_audit.csv"
COMBINED_JSONL = EVIDENCE_DIR / "combined_30_drafts_detailed.jsonl"
K_CLAIM_AUDIT_JSONL = EVIDENCE_DIR / "khuong_30_drafts_claim_audit.jsonl"
COMBINED_SUMMARY_JSON = EVIDENCE_DIR / "combined_30_summary.json"

_PREFIX_RE = re.compile(r'^Nguồn cũ:\s*"[^"]*"\.\s*')
_SENT_SPLIT_RE = re.compile(r"(?<=[.?!])\s+")

# K's adjudicated full-transcript claim audit per draft (see khuong_c1_c5_adjudication.json)
K_ADJUDICATED_AUDIT: dict[str, dict[str, Any]] = {
    "n01": {
        "unsupported_beats": [1, 2],
        "review_ok": False,
        "notes": "C1+C4: Beats 1-2 cite 7357939713132580103 whose transcript is background song lyrics; Beats 3-4 are genuine HCMC 29k-35k snail shop reviews in Tan Phu and District 1 (no District 4 shop).",
    },
    "n02": {
        "unsupported_beats": [],
        "review_ok": True,
        "notes": "4/4 beats supported by genuine Hanoi morning pho bo / pho tai lan reviews (7399513981842476289, 7405822896305605904, 7401000577330613521).",
    },
    "n03": {
        "unsupported_beats": [],
        "review_ok": True,
        "notes": "4/4 beats supported by HCMC BBQ/seafood buffet reviews including Binh Thanh 159k (7403729944905387272) and D2 129k (7343188962674068744).",
    },
    "n04": {
        "unsupported_beats": [4],
        "review_ok": False,
        "notes": "C1: Beats 1-3 supported by genuine home bun bo Hue cooking guides; Beat 4 cites 7406631345100721425 whose cta_text is a song lyric.",
    },
    "n05": {
        "unsupported_beats": [1, 2],
        "review_ok": False,
        "notes": "C2: Beats 1-2 cite 7306523711614487810 ('vibe Da Lat' themed cafe rather than verified Da Lat venue, per M2.2 Q4 rule); Beats 3-4 are genuine Da Lat cafes.",
    },
    "n06": {
        "unsupported_beats": [],
        "review_ok": True,
        "notes": "4/4 beats supported by HCMC banh mi thit nuong / pate reviews (Beats 1-3 in District 1; Beat 4 Cao Thang District 3).",
    },
    "n07": {
        "unsupported_beats": [],
        "review_ok": True,
        "notes": "4/4 beats supported by level-7 spicy noodle / spicy seafood mukbangs; secondary dish chan ga sa tac is absent in cited clips.",
    },
    "n08": {
        "unsupported_beats": [],
        "review_ok": True,
        "notes": "4/4 beats supported by HCMC com tam / popular rice shop reviews including Com Tam Tai in Go Vap (Beat 3).",
    },
    "n09": {
        "unsupported_beats": [],
        "review_ok": True,
        "notes": "4/4 beats supported by healthy salad / pan-seared chicken / eat-clean meal-prep guides.",
    },
    "n10": {
        "unsupported_beats": [],
        "review_ok": True,
        "notes": "4/4 beats supported by student milk-tea videos (Beats 1-2 teacher homemade milk tea for FPT Polytechnic club; Beats 3-4 student milk-tea/matcha shops).",
    },
    "n11": {
        "unsupported_beats": [3],
        "review_ok": False,
        "notes": "C2: Beats 1-2 (Cau Giay) and Beat 4 (Ta Quang Buu) are genuine Hanoi bun dau reviews; Beat 3 cites 7387712842968943880 in Binh Tho Thu Duc (HCMC) due to upstream corpus city_norm='ha noi' mislabel.",
    },
    "n12": {
        "unsupported_beats": [],
        "review_ok": True,
        "notes": "4/4 beats supported by Saigon ca vien chien snack clips (Beat 4 caption-sourced on voice-free clip 7378469899221470472; banh trang tron not in top-3 cited).",
    },
    "n13": {
        "unsupported_beats": [],
        "review_ok": True,
        "notes": "4/4 beats supported by Da Nang family dining and traditional local specialty clips.",
    },
    "n14": {
        "unsupported_beats": [],
        "review_ok": False,
        "notes": "C4: 4/4 excerpts factually entailed by convenience-store snack haul 7447910275665120520, but flagged review_ok=False because the store filmed is in China.",
    },
    "n15": {
        "unsupported_beats": [],
        "review_ok": True,
        "notes": "C3/C4: Beats 1-2 contrast hu tieu Sa Te Nai with hu tieu Nam Vang in District 5/6; Beats 3-4 review HCMC hu tieu Nam Vang in District 7.",
    },
    "k01": {
        "unsupported_beats": [],
        "review_ok": True,
        "notes": "C3/C4: 4/4 beats from genuine Hanoi bun cha nuong than hoa clips (Cau Giay, Thanh Xuan, Hanoi); Beat 4 quotes visa-help CTA from 30k bun cha clip 7351969886769302800.",
    },
    "k02": {
        "unsupported_beats": [1, 2],
        "review_ok": False,
        "notes": "C1: Beats 1-2 cite 7421397039306624276 whose spoken audio is rap lyrics despite #banhcanhcuaquan3 caption; Beats 3-4 are genuine HCMC banh canh cua nuoc set reviews.",
    },
    "k03": {
        "unsupported_beats": [],
        "review_ok": True,
        "notes": "4/4 beats supported by homemade crispy cha gio hai san family-feast cooking tutorials.",
    },
    "k04": {
        "unsupported_beats": [],
        "review_ok": True,
        "notes": "4/4 beats supported by HCMC lau bo nhung dam nuoc dua reviews including two Go Vap venues (7435157644496637191, 7465720817251257608).",
    },
    "k05": {
        "unsupported_beats": [3],
        "review_ok": False,
        "notes": "C1: Beats 1-2 (Xe banh flan Huynh Anh Tan Binh, kem muoi) and Beat 4 (The Flan) supported; Beat 3 cites song-mood summary in 7334299969131793672.",
    },
    "k06": {
        "unsupported_beats": [1, 2],
        "review_ok": False,
        "notes": "C1: Beats 1-2 cite 7419586889218395399 whose spoken transcript is song lyrics; Beats 3-4 are genuine honey-marinade / air-fryer grilled meat guides.",
    },
    "k07": {
        "unsupported_beats": [],
        "review_ok": True,
        "notes": "4/4 beats supported by Vung Tau live-seafood and sea-view restaurant reviews.",
    },
    "k08": {
        "unsupported_beats": [3],
        "review_ok": False,
        "notes": "C1: Beats 1, 2, 4 supported by ga ran sot pho mai reviews; Beat 3 cites breakup-song summary in 7444556348412415248.",
    },
    "k09": {
        "unsupported_beats": [],
        "review_ok": True,
        "notes": "4/4 beats supported by peaceful/warm vegetarian restaurant reviews in Hanoi.",
    },
    "k10": {
        "unsupported_beats": [],
        "review_ok": True,
        "notes": "C4: 4/4 beats supported by HCMC fresh tra mang cau / fruit-tea reviews in Tan Phu, District 3, and Binh Thanh (no District 1 shop).",
    },
    "k11": {
        "unsupported_beats": [],
        "review_ok": True,
        "notes": "4/4 beats supported by Hanoi hand-steamed banh cuon nhan thit moc nhi reviews including two Dong Da venues.",
    },
    "k12": {
        "unsupported_beats": [],
        "review_ok": False,
        "notes": "C3: 4/4 excerpts supported by home-cooked sour fish soup clips (ca chuon, ca ngat, ca loc) and draft honestly says 'Com & Bua chinh', but flagged review_ok=False due to missing salmon (ca hoi).",
    },
    "k13": {
        "unsupported_beats": [],
        "review_ok": True,
        "notes": "4/4 beats supported by Hanoi bun rieu cua dong top mo reviews including 41 Quang Trung, Hoan Kiem (Beat 4).",
    },
    "k14": {
        "unsupported_beats": [],
        "review_ok": True,
        "notes": "C4: 4/4 beats supported by HCMC evening quan nhau lai rai reviews in Tan Binh, District 1, and Binh Thanh (adjacent to Phu Nhuan).",
    },
    "k15": {
        "unsupported_beats": [],
        "review_ok": True,
        "notes": "4/4 beats supported by HCMC crispy banh xeo reviews including Binh Thanh 7k Central-style banh xeo (Beats 1-2).",
    },
}


def _load_queries(path: Path, author: str) -> list[dict[str, Any]]:
    return [
        {**json.loads(line), "author": author}
        for line in path.read_text(encoding="utf-8").splitlines()
        if line.strip()
    ]


def _count_creative_sentences(dialogue: str) -> int:
    remainder = _PREFIX_RE.sub("", dialogue.strip()).strip()
    if not remainder:
        return 0
    return len([s for s in _SENT_SPLIT_RE.split(remainder) if s.strip()])


def main() -> None:
    settings = AppSettings.from_env().model_copy(
        update={
            "gemini_api_key": "",
            "corpus_dir": CORPUS_DIR,
            "bm25_index_dir": BM25_DIR,
        }
    )
    analytics = NicheAnalyticsEngine.from_corpus_dir(settings.corpus_dir)
    retrieval = HybridRetrievalService.from_dirs(
        df_videos=analytics.df_videos,
        bm25_dir=settings.bm25_index_dir,
        qdrant_url=settings.qdrant_url,
        qdrant_collection=settings.qdrant_collection,
        reranker_enabled=settings.reranker_enabled,
    )
    engine = GroundedScriptEngine(
        analytics_engine=analytics,
        retrieval_service=retrieval,
        gemini_client=BoundedGeminiClient(settings=settings),
    )

    n_queries = _load_queries(N_QUERIES_PATH, "N")
    k_queries = _load_queries(K_QUERIES_PATH, "K")
    all_queries = n_queries + k_queries

    vid_lookup = (
        analytics.df_videos.assign(video_id=analytics.df_videos["video_id"].astype(str))
        .set_index("video_id")
        .to_dict(orient="index")
    )

    rows: list[dict[str, Any]] = []
    detailed_lines: list[str] = []
    claim_audit_lines: list[str] = []
    fabricated_total = 0

    for q in all_queries:
        draft_id = q["draft_id"]
        req = ScriptGenerationRequest(
            brief=q["brief"],
            target_duration_sec=int(q["target_duration_sec"]),
            top_k_evidence=5,
            generation_mode="offline_grounded",
        )
        resp = engine.generate(req)
        evidence_ids = {card.citation.video_id for card in resp.evidence_cards}
        cited_ids = [vid for beat in resp.beats for vid in beat.cited_video_ids]
        foreign = [vid for vid in cited_ids if vid not in evidence_ids]
        fabricated_total += len(foreign)

        audit_meta = K_ADJUDICATED_AUDIT[draft_id]
        unsupported_set = set(audit_meta["unsupported_beats"])
        total_factual = len(resp.beats)
        cited_factual = sum(1 for b in resp.beats if b.cited_video_ids)
        supported_factual = sum(
            1
            for idx, b in enumerate(resp.beats, start=1)
            if b.cited_video_ids and idx not in unsupported_set
        )
        creative_dirs = sum(_count_creative_sentences(b.dialogue) for b in resp.beats)

        beats_preview = " || ".join(f"[{b.time_range}] {b.dialogue}" for b in resp.beats)
        row = {
            "draft_id": draft_id,
            "author": q["author"],
            "brief": q["brief"],
            "generation_mode": resp.generation_mode,
            "draft_status": resp.draft_status,
            "grounding_verified": resp.grounding_verified,
            "target_duration_sec": resp.guardrail.target_duration_sec,
            "estimated_duration_sec": resp.guardrail.estimated_duration_sec,
            "timing_valid": resp.guardrail.timing_valid,
            "valid_citations_ratio": resp.guardrail.valid_citations_ratio,
            "citation_coverage_ratio": resp.guardrail.citation_coverage_ratio,
            "guardrail_passed": resp.guardrail.passed,
            "fabricated_id_count": len(foreign),
            "evidence_ids": "|".join(sorted(evidence_ids)),
            "cited_video_ids": "|".join(dict.fromkeys(cited_ids)),
            "beats_preview": beats_preview,
            "K_total_factual_claims": total_factual,
            "K_supported_factual_claims": supported_factual,
            "K_factual_cited_claims": cited_factual,
            "K_creative_directions_count": creative_dirs,
            "K_review_ok": bool(audit_meta["review_ok"]),
            "K_notes": str(audit_meta["notes"]),
            "N_total_factual_claims": "",
            "N_supported_factual_claims": "",
            "N_citation_coverage_ok": "",
        }
        rows.append(row)

        cited_sources: dict[str, dict[str, Any]] = {}
        for vid in dict.fromkeys(cited_ids):
            v = vid_lookup.get(str(vid), {})
            cited_sources[str(vid)] = {
                "city_norm": v.get("city_norm"),
                "district_norm": v.get("district_norm"),
                "video_format": v.get("video_format"),
                "food_category": v.get("food_category"),
                "poi_name": v.get("poi_name"),
                "caption": str(v.get("caption") or ""),
                "hook_text": str(v.get("hook_text") or ""),
                "body_beats": [str(x) for x in (v.get("body_beats") if v.get("body_beats") is not None else [])],
                "cta_text": str(v.get("cta_text") or ""),
                "transcript": str(v.get("transcript") or ""),
            }
        detailed_lines.append(
            json.dumps(
                {
                    "draft_id": draft_id,
                    "author": q["author"],
                    "brief": q["brief"],
                    "target_duration_sec": resp.guardrail.target_duration_sec,
                    "estimated_duration_sec": resp.guardrail.estimated_duration_sec,
                    "timing_valid": resp.guardrail.timing_valid,
                    "guardrail_passed": resp.guardrail.passed,
                    "valid_citations_ratio": resp.guardrail.valid_citations_ratio,
                    "citation_coverage_ratio": resp.guardrail.citation_coverage_ratio,
                    "fabricated_id_count": len(foreign),
                    "caption_draft": resp.caption_draft,
                    "hook_options": resp.hook_options,
                    "beats": [b.model_dump() for b in resp.beats],
                    "cited_sources": cited_sources,
                },
                ensure_ascii=False,
            )
        )
        claim_audit_lines.append(
            json.dumps(
                {
                    "draft_id": draft_id,
                    "author": q["author"],
                    "brief": q["brief"],
                    "K_total_factual_claims": total_factual,
                    "K_supported_factual_claims": supported_factual,
                    "K_factual_cited_claims": cited_factual,
                    "K_creative_directions_count": creative_dirs,
                    "K_review_ok": bool(audit_meta["review_ok"]),
                    "K_notes": str(audit_meta["notes"]),
                    "per_beat_audit": [
                        {
                            "beat_idx": idx,
                            "cited_video_ids": b.cited_video_ids,
                            "dialogue": b.dialogue,
                            "supported_culinary_claim": (idx not in unsupported_set and bool(b.cited_video_ids)),
                        }
                        for idx, b in enumerate(resp.beats, start=1)
                    ],
                },
                ensure_ascii=False,
            )
        )

    df_all = pd.DataFrame(rows)
    df_k = df_all[df_all["author"] == "K"].copy()
    df_k.to_csv(K_OUT_CSV, index=False)
    df_all.to_csv(COMBINED_OUT_CSV, index=False)
    COMBINED_JSONL.write_text("\n".join(detailed_lines) + "\n", encoding="utf-8")
    K_CLAIM_AUDIT_JSONL.write_text("\n".join(claim_audit_lines) + "\n", encoding="utf-8")

    total_claims = int(df_all["K_total_factual_claims"].sum())
    supported_claims = int(df_all["K_supported_factual_claims"].sum())
    cited_claims = int(df_all["K_factual_cited_claims"].sum())
    creative_total = int(df_all["K_creative_directions_count"].sum())
    review_ok_count = int(df_all["K_review_ok"].sum())

    summary = {
        "corpus_snapshot_id": analytics.manifest.snapshot_id,
        "bm25_index_dir": str(BM25_DIR.relative_to(ROOT)),
        "generation_mode": "offline_grounded",
        "provider_calls": 0,
        "total_drafts": len(rows),
        "n_drafts": len(n_queries),
        "k_drafts": len(k_queries),
        "fabricated_id_count": fabricated_total,
        "guardrail_passed_count": int(df_all["guardrail_passed"].sum()),
        "timing_valid_count": int(df_all["timing_valid"].sum()),
        "valid_membership_100_count": int((df_all["valid_citations_ratio"] == 1.0).sum()),
        "citation_coverage_100_count": int((df_all["citation_coverage_ratio"] == 1.0).sum()),
        "K_human_audit": {
            "auditor": "Trần Đình Khương (K)",
            "audit_status": "K_verified_full_transcripts_N_pending",
            "total_factual_claims": total_claims,
            "supported_factual_claims": supported_claims,
            "supported_factual_claims_ratio": round(supported_claims / total_claims, 4),
            "factual_cited_claims": cited_claims,
            "factual_cited_claims_ratio": round(cited_claims / total_claims, 4),
            "creative_directions_total": creative_total,
            "editorial_review_ok_drafts": review_ok_count,
            "editorial_review_ok_ratio": round(review_ok_count / len(rows), 4),
            "unsupported_breakdown": {
                "C1_song_lyrics_or_music_notes_beats": 9,
                "C2_cross_city_mislabel_or_vibe_city_beats": 3,
            },
        },
    }
    COMBINED_SUMMARY_JSON.write_text(json.dumps(summary, ensure_ascii=False, indent=2) + "\n", encoding="utf-8")
    print(json.dumps(summary, ensure_ascii=False, indent=2))


if __name__ == "__main__":
    main()
