from __future__ import annotations

import asyncio
from pathlib import Path

import httpx
import pytest

from apps.api.app.main import create_app
from apps.api.app.multimodal_store import MultimodalCorpusStore
from apps.demo.main import create_app as create_demo_app
from apps.demo.visuals import (
    render_disclosure_promo_html,
    render_milestone_evaluations_html,
    render_prosody_segments_html,
)
from packages.common.settings import AppSettings
from packages.prosody import PROSODY_DESCRIPTIVE_NOTE


def test_multimodal_corpus_store_loads_real_gold_tables_and_handles_missing_dir(
    tmp_path: Path,
) -> None:
    empty_store = MultimodalCorpusStore.from_snapshot_dir(tmp_path / "does_not_exist")
    assert empty_store.available is False
    assert empty_store.total_comments == 0
    assert empty_store.total_voice_segments == 0
    assert empty_store.list_videos() == []
    assert empty_store.get_video_bundle("missing") is None

    store = MultimodalCorpusStore.from_repo_defaults(
        primary_corpus_dir=Path("data/corpus/20261117_recovered_v1")
    )
    assert store.available is True
    assert store.snapshot_id == "m3_3_playwright_comments_20261125_v5"
    assert store.total_comments == 2823
    assert len(store.videos_by_id) == 130
    assert store.videos_with_comments == 118
    assert store.total_voice_segments == 436
    assert store.videos_with_voice_segments == 10
    assert store.videos_with_prosody_audio == 29

    voice_vids = store.list_videos(require_voice=True, min_comments=3, limit=10)
    assert len(voice_vids) >= 5
    first_vid = voice_vids[0]["video_id"]
    bundle = store.get_video_bundle(first_vid)
    assert bundle is not None
    assert bundle["video"]["video_id"] == first_vid
    assert len(bundle["comments"]) >= 3
    assert len(bundle["voice_segments"]) >= 1


def test_api_multimodal_endpoints_and_m4_m5_m6_integration() -> None:
    settings = AppSettings.from_env().model_copy(update={"gemini_api_key": ""})
    app = create_app(settings=settings, mount_demo=True)

    async def _run() -> None:
        transport = httpx.ASGITransport(app=app)
        async with httpx.AsyncClient(transport=transport, base_url="http://testserver") as client:
            r_ready = await client.get("/health/ready")
            assert r_ready.status_code == 200
            ready = r_ready.json()
            assert ready["total_videos"] == 70996
            assert ready["indexed_bm25_videos"] == 21748
            assert ready["multimodal_available"] is True
            assert ready["multimodal_snapshot_id"] == "m3_3_playwright_comments_20261125_v5"
            assert ready["multimodal_total_comments"] == 2823
            assert ready["multimodal_voice_segments"] == 436

            r_list = await client.get(
                "/api/v1/trust/corpus-videos",
                params={"require_voice": "true", "min_comments": 3, "limit": 10},
            )
            assert r_list.status_code == 200
            listing = r_list.json()
            assert listing["total_matching"] >= 5
            assert len(listing["items"]) >= 5
            assert all(v >= 0.0 for v in listing["timings_ms"].values())

            vid = listing["items"][0]["video_id"]
            r_vid = await client.get(f"/api/v1/trust/corpus-video/{vid}")
            assert r_vid.status_code == 200
            body = r_vid.json()
            assert body["video"]["video_id"] == vid
            assert body["prosody_and_timing"]["temporal_invariants"]["meets_100pct_invariant_gate"] is True
            assert body["prosody_and_timing"]["descriptive_note"] == PROSODY_DESCRIPTIVE_NOTE
            assert (
                body["disclosure_and_promo"]["sponsorship_ground_truth_status"]
                == "undisclosed_sponsorship_deferred"
            )
            assert body["trust_audit"]["comment_filter_policy"] == "diagnostic_only_unvalidated"
            assert len(body["trust_audit"]["comments"]) >= 3
            assert all(v >= 0.0 for v in body["timings_ms"].values())

            r_404 = await client.get("/api/v1/trust/corpus-video/unknown_video_999999")
            assert r_404.status_code == 404
            assert r_404.json()["code"] == "VIDEO_NOT_FOUND"

            r_disc = await client.post(
                "/api/v1/trust/disclosure-check",
                json={
                    "caption": "Khai trương giảm giá 20% đặt hàng ngay tại giỏ hàng góc trái",
                    "transcript": "Tặng ngay voucher ưu đãi cho anh em mua combo hôm nay nha",
                    "hashtags": ["reviewanngon", "tiktokshop"],
                    "is_ad": False,
                    "is_ec_video": True,
                },
            )
            assert r_disc.status_code == 200
            disc = r_disc.json()
            assert disc["disclosure_flag_status"] == "observed_ecommerce"
            assert disc["lexical_promo_score"] > 0.0
            assert disc["sponsorship_ground_truth_status"] == "undisclosed_sponsorship_deferred"

            r_epistemic = await client.post(
                "/api/v1/trust/disclosure-check",
                json={
                    "caption": "Review bún bò",
                    "transcript": "Nước lèo đậm đà",
                    "question": "Hãy chứng minh chắc chắn video này nhận tiền PR ngầm quảng cáo ngầm",
                },
            )
            assert r_epistemic.status_code == 422
            assert r_epistemic.json()["code"] == "UNSUPPORTED_DOMAIN"

            r_ms = await client.get("/api/v1/evaluation/milestones")
            assert r_ms.status_code == 200
            ms = r_ms.json()
            for key in ("M2.2", "M4.1", "M4.2", "M5.1", "M5.2", "M6.1", "M6.2"):
                assert key in ms["milestones"]
                assert ms["milestones"][key]["available"] is True

    asyncio.run(_run())


def test_demo_main_prefers_fresh_searchable_pilot_snapshot_when_unconfigured(
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    monkeypatch.delenv("TIKTOK_RAG_CORPUS_DIR", raising=False)
    monkeypatch.delenv("TIKTOK_RAG_BM25_INDEX_DIR", raising=False)
    app = create_demo_app()

    async def _check() -> None:
        transport = httpx.ASGITransport(app=app)
        async with httpx.AsyncClient(transport=transport, base_url="http://testserver") as client:
            r_ready = await client.get("/health/ready")
            assert r_ready.status_code == 200
            ready = r_ready.json()
            assert ready["corpus_snapshot_id"] == "m3_3_pilot_snapshot_v2"
            assert ready["indexed_bm25_videos"] == 21758
            assert ready["multimodal_total_comments"] == 2823

    asyncio.run(_check())


def test_new_demo_visual_renderers_escape_xss_and_preserve_m4_m5_guardrails() -> None:
    xss = "<script>alert('xss')</script>"
    prosody_html = render_prosody_segments_html(
        {
            "segment_count": 1,
            "audio_derived_segments": 1,
            "wps_estimated_segments": 0,
            "median_words_per_sec": 3.4,
            "mean_pitch_std_hz": 42.1,
            "mean_energy_cv": 0.61,
            "descriptive_note": PROSODY_DESCRIPTIVE_NOTE,
            "temporal_invariants": {"meets_100pct_invariant_gate": True, "valid_segments": 1, "total_segments": 1},
            "voice_segments": [
                {
                    "segment_id": f"seg_{xss}",
                    "start_sec": 0.0,
                    "end_sec": 2.5,
                    "timestamp_source": "audio_derived",
                    "words_per_sec": 3.4,
                    "pitch_std": 42.1,
                    "energy_cv": 0.61,
                    "text": f"Nước lèo {xss}",
                }
            ],
        }
    )
    assert "<script>" not in prosody_html
    assert "&lt;script&gt;" in prosody_html
    assert "audio_derived" in prosody_html
    assert "never proof of speaker intent" in prosody_html

    disc_html = render_disclosure_promo_html(
        {
            "disclosure_flag_status": "observed_ecommerce",
            "lexical_promo_score": 0.4,
            "matched_categories": ["discount_voucher"],
            "matched_indicators": [f"discount_voucher:{xss}"],
            "sponsorship_ground_truth_status": "undisclosed_sponsorship_deferred",
            "disclosure_target_note": "Platform flags only.",
        }
    )
    assert "<script>" not in disc_html
    assert "observed_ecommerce" in disc_html
    assert "undisclosed_sponsorship_deferred" in disc_html

    eval_html = render_milestone_evaluations_html(
        {
            "milestones": {
                "M5.2": {
                    "available": True,
                    "title": f"ABSA {xss}",
                    "headline": "held_out F1 = 0.9286 / 0.8293",
                    "status": "COMPLETE",
                }
            }
        }
    )
    assert "<script>" not in eval_html
    assert "0.9286" in eval_html
