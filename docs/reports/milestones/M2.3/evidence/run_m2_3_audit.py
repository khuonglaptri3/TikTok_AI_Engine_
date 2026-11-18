#!/usr/bin/env python3
"""Run GroundedScriptEngine (offline_grounded, 0 provider calls) on N's 15 authored briefs."""

from __future__ import annotations

import json
from pathlib import Path
from typing import Any

import pandas as pd

from packages.analytics import NicheAnalyticsEngine
from packages.common.settings import AppSettings
from packages.data_contracts.query import ScriptGenerationRequest
from packages.llm import BoundedGeminiClient
from packages.retrieval import HybridRetrievalService
from packages.script_engine import GroundedScriptEngine

OUT_DIR = Path(__file__).resolve().parent
QUERIES_PATH = OUT_DIR / "nguyen_15_queries.jsonl"
OUT_CSV = OUT_DIR / "nguyen_15_drafts_audit.csv"
OUT_JSON = OUT_DIR / "nguyen_15_summary.json"


def main() -> None:
    settings = AppSettings.from_env().model_copy(update={"gemini_api_key": ""})
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

    queries = [
        json.loads(line)
        for line in QUERIES_PATH.read_text(encoding="utf-8").splitlines()
        if line.strip()
    ]

    rows: list[dict[str, Any]] = []
    fabricated_total = 0
    for q in queries:
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

        beats_preview = " || ".join(f"[{b.time_range}] {b.dialogue}" for b in resp.beats)
        rows.append(
            {
                "draft_id": q["draft_id"],
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
                "N_total_factual_claims": "",
                "N_supported_factual_claims": "",
                "N_citation_coverage_ok": "",
                "K_review_ok": "",
                "K_notes": "",
            }
        )

    df_out = pd.DataFrame(rows)
    df_out.to_csv(OUT_CSV, index=False)

    summary = {
        "corpus_snapshot_id": analytics.manifest.snapshot_id,
        "generation_mode": "offline_grounded",
        "provider_calls": 0,
        "total_drafts": len(rows),
        "fabricated_id_count": fabricated_total,
        "guardrail_passed_count": int(df_out["guardrail_passed"].sum()),
        "timing_valid_count": int(df_out["timing_valid"].sum()),
        "valid_membership_100_count": int((df_out["valid_citations_ratio"] == 1.0).sum()),
        "citation_coverage_100_count": int((df_out["citation_coverage_ratio"] == 1.0).sum()),
        "human_claim_audit_completed": False,
        "note": "Structural/membership checks completed on N's 15 drafts; human claim entailment audit and K's 15 queries remain pending.",
    }
    OUT_JSON.write_text(json.dumps(summary, ensure_ascii=False, indent=2), encoding="utf-8")
    print(json.dumps(summary, ensure_ascii=False, indent=2))


if __name__ == "__main__":
    main()
