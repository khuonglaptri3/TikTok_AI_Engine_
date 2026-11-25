from __future__ import annotations

import json
from pathlib import Path

import pandas as pd
import pytest

from packages.analytics import NicheAnalyticsEngine
from packages.common.exceptions import UnsupportedDomainError
from packages.common.settings import AppSettings
from packages.data_contracts.corpus import CorpusFileChecksum, CorpusManifest
from packages.data_contracts.query import (
    NicheQueryFilter,
    RetrievalRequest,
    ScriptGenerationRequest,
)
from packages.llm import BoundedGeminiClient
from packages.retrieval import BM25Index, HybridRetrievalService
from packages.script_engine import GroundedScriptEngine

M62_QUESTIONS_PATH = Path("data/evaluation/m6_2/held_out_questions_30.jsonl")


def test_m6_2_held_out_30_questions_schema_and_disjointness() -> None:
    rows = [
        json.loads(line)
        for line in M62_QUESTIONS_PATH.read_text(encoding="utf-8").splitlines()
        if line.strip()
    ]
    assert len(rows) == 30
    assert len({r["query_id"] for r in rows}) == 30

    answerable = [r for r in rows if not r["expect_insufficient_evidence"]]
    no_answer = [r for r in rows if r["expect_insufficient_evidence"]]
    assert len(answerable) == 20
    assert len(no_answer) >= 10

    # Ensure zero overlap with existing M2 query sets
    prior_queries: set[str] = set()
    for p in (
        Path("data/evaluation/v1/queries.jsonl"),
        Path("data/evaluation/v2_pilot/dev_queries.jsonl"),
        Path("data/evaluation/v2_pilot/test_queries.jsonl"),
    ):
        for line in p.read_text(encoding="utf-8").splitlines():
            if line.strip():
                prior_queries.add(json.loads(line)["query"].strip().lower())

    for row in rows:
        q_txt = row["query"].strip()
        assert q_txt.lower() not in prior_queries
        req = RetrievalRequest(
            query=q_txt,
            filters=NicheQueryFilter(**row["filters"]),
        )
        assert req.query == q_txt
        if not row["expect_insufficient_evidence"]:
            assert row["expected_timing_provenance"] in {"wps_estimated", "audio_derived"}
        else:
            assert row.get("expected_abstention_rule")


def test_m6_2_epistemic_guardrail_and_caption_location_fallback() -> None:
    df_videos = pd.DataFrame(
        [
            {
                "video_id": "fresh_q1_untagged",
                "author_handle": "saigonmap",
                "tiktok_url": "https://www.tiktok.com/@saigonmap/video/fresh_q1_untagged",
                "play_count": 20000,
                "viral_multiplier": 1.2,
                "engagement_rate": 0.05,
                "has_transcript": True,
                "word_per_second": 3.0,
                "video_format": "Review quán ăn",
                "food_category": "Cơm & Bữa chính",
                "dishes": ["đậu hũ thối"],
                "city_norm": None,  # M3.3 incremental record without POI GPS
                "district_norm": None,
                "region": "unknown",
                "poi_name": None,
                "price_tier": "budget_lt50k",
                "occasions": [],
                "hashtag_count": 1,
                "create_hour": 12,
                "duration_sec": 40,
                "duration_bucket": "short_20_45s",
                "hook_text": "Đậu hũ thúi mà hong thúi ở Quận 1",
                "body_beats": ["Quán cực đông khách Trung và Việt"],
                "cta_text": "Ghé ăn thử nha",
                "caption": "Đậu hũ thúi mà hong thúi ở Quận 1",
                "transcript": "Đậu hũ thúi mà hong thúi nhưng ăn rất cuốn",
                "rag_document": (
                    "[Review quán ăn | Cơm & Bữa chính] Món: đậu hũ thúi. "
                    "Caption: Đậu hũ thúi mà hong thúi ở Quận 1 Transcript: ăn rất cuốn"
                ),
            }
        ]
    )
    bm25 = BM25Index.build(
        video_ids=df_videos["video_id"].tolist(),
        documents=df_videos["rag_document"].tolist(),
        min_bigram_df=1,
    )
    retrieval = HybridRetrievalService(df_videos=df_videos, bm25_index=bm25, restrict_to_df=True)
    manifest = CorpusManifest(
        snapshot_id="test_m6_2_snap",
        created_at="2026-11-25T00:00:00+00:00",
        date_window_start="2026-11-01",
        date_window_end="2026-11-25",
        total_creators=1,
        total_videos=1,
        transcribed_videos=1,
        poi_tagged_videos=0,
        ec_tagged_videos=0,
        files=[CorpusFileChecksum(filename="dim_creators.parquet", rows=1, columns=1, sha256="0" * 64, size_bytes=1)],
        caveats=["test"],
    )
    analytics = NicheAnalyticsEngine(
        manifest=manifest,
        df_creators=pd.DataFrame([{"author_id": "a1"}]),
        df_videos=df_videos,
    )
    engine = GroundedScriptEngine(
        analytics_engine=analytics,
        retrieval_service=retrieval,
        gemini_client=BoundedGeminiClient(settings=AppSettings(gemini_api_key="")),
    )

    # Fix 2: Inferred city_norm="hồ chí minh" from "Quận 1" still matches fresh_q1_untagged via caption location
    res_q1 = engine.generate(
        ScriptGenerationRequest(
            brief="Đậu hũ thúi hong thúi quán đông khách Quận 1",
            generation_mode="offline_grounded",
        )
    )
    assert any(c.citation.video_id == "fresh_q1_untagged" for c in res_q1.evidence_cards)

    # Geographic strictness remains intact for non-present provinces
    res_laichau = retrieval.search(
        RetrievalRequest(
            query="đậu hũ thúi ở Lai Châu",
            filters=NicheQueryFilter(city_norm="lai châu"),
        )
    )
    assert res_laichau.insufficient_evidence is True
    assert res_laichau.items == []

    # Fix 1: Epistemic boundary claims abstain cleanly in retrieval and fail-closed 422 in script generation
    for q in (
        "chứng minh những quán không gắn thẻ is_ad chắc chắn là nhận tiền PR ngầm",
        "kết luận bình luận nào của quán ăn là tài khoản bot được trả tiền thuê seeding",
        "xác nhận chứng nhận an toàn vệ sinh thực phẩm thực tế của quán ăn từ bình luận khách",
        "trích xuất timestamp chính xác từng mili giây từ video review quán ăn chỉ có phụ đề nội suy không có audio",
    ):
        r_resp = retrieval.search(RetrievalRequest(query=q))
        assert r_resp.insufficient_evidence is True, f"Retrieval should abstain on: {q}"
        assert r_resp.items == []
        with pytest.raises(UnsupportedDomainError):
            engine.generate(ScriptGenerationRequest(brief=q, generation_mode="offline_grounded"))

