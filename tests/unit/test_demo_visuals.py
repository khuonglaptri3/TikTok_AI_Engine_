from __future__ import annotations

import httpx

from apps.api.app.main import create_app
from packages.common.settings import AppSettings


def test_demo_visual_renderers_escape_untrusted_html_and_preserve_epistemic_labels() -> None:
    from apps.demo.visuals import (
        render_benchmark_html,
        render_error_alert_html,
        render_evidence_cards_html,
        render_hero_banner_html,
        render_script_html,
        render_timings_html,
        render_trust_audit_html,
    )

    banner = render_hero_banner_html(
        snapshot_id="m3_3_pilot_snapshot_v2",
        total_videos=71026,
        total_creators=264,
        poi_tagged_videos=23448,
        transcribed_videos=21758,
        gemini_configured=False,
    )
    assert "m3_3_pilot_snapshot_v2" in banner
    assert "71,026" in banner
    assert "Offline CPU ($0 Verified)" in banner

    xss = "<script>alert(1)</script>"
    err_html = render_error_alert_html("UNSUPPORTED_DOMAIN", f"Blocked: {xss}")
    assert 'role="alert"' in err_html
    assert "<script>" not in err_html
    assert "&lt;script&gt;" in err_html

    timings = render_timings_html({"retrieval_ms": 14.2, "total_ms": 62.5})
    assert "14.2 ms" in timings
    assert "62.5 ms" in timings

    bench = render_benchmark_html(
        {
            "cohort_window_start": "2023-11-25",
            "cohort_window_end": "2026-11-22",
            "observation_snapshot": "2025-03",
            "matched_videos": 400,
            "transcribed_videos": 120,
            "poi_tagged_videos": 80,
            "median_plays": 42000,
            "p75_plays": 95000,
            "median_engagement_rate": 0.052,
            "duration_q25_sec": 25,
            "duration_median_sec": 45,
            "duration_q75_sec": 65,
            "median_word_per_second": 3.2,
            "hashtag_q25": 3,
            "hashtag_q75": 6,
            "top_hashtags": ["ancungtiktok", xss],
            "top_posting_hours": [{"hour": 19, "median_plays": 51000}],
            "top_poi_venues": [f"Quán {xss}"],
            "missingness": {"transcript_missing_pct": 10.0, "poi_missing_pct": 20.0, "city_missing_pct": 5.0},
        }
    )
    assert "<script>" not in bench
    assert "42,000" in bench

    ev = render_evidence_cards_html(
        [
            {
                "rank": 1,
                "video_format": "Review quán ăn",
                "food_category": "Món nước & Sợi",
                "price_tier": "budget",
                "duration_sec": 40,
                "hook_text": f"Hook {xss}",
                "body_beats": ["Beat 1"],
                "citation": {
                    "video_id": "v123",
                    "author_handle": "creator_a",
                    "tiktok_url": "https://www.tiktok.com/@creator_a/video/v123",
                    "play_count": 15000,
                    "viral_multiplier": 2.3,
                },
            }
        ],
        mode="bm25",
        total_cands=12,
    )
    assert "<script>" not in ev
    assert "v123" in ev
    assert "2.3x" in ev

    sc = render_script_html(
        {
            "generation_mode": "offline_grounded",
            "model_used": "offline_blueprint",
            "setting": f"Quận 1 {xss}",
            "persona_tone": "Thực nghiệm",
            "hook_options": [f"Mở đầu {xss}"],
            "beats": [
                {
                    "section_title": "1. Hook",
                    "time_range": "00:00-00:08",
                    "visual_angle": "Cận cảnh",
                    "dialogue": f"Thoại {xss}",
                    "word_count": 8,
                    "cited_video_ids": ["v123"],
                }
            ],
            "caption_draft": "Caption test",
            "recommended_hashtags": ["review", "saigon"],
            "shooting_advice": {"camera_angles": ["Cận"], "lighting_and_audio": ["Tốt"], "pacing_and_editing": ["3.2 từ/s"]},
            "guardrail": {"passed": True, "total_words": 60, "estimated_duration_sec": 20.0, "target_duration_sec": 20, "duration_delta_sec": 0.0, "valid_citations_ratio": 1.0, "warnings": []},
        }
    )
    assert "<script>" not in sc
    assert "00:00-00:08" in sc

    trust = render_trust_audit_html(
        {
            "comment_filter_policy": "diagnostic_only_unvalidated",
            "comparison": {
                "disclosure_flag_status": "unlabeled_unknown",
                "lexical_promo_score": 0.25,
                "clean_comment_count": 1,
                "seeding_comment_count": 1,
                "koc_aspect_summaries": {
                    "taste": {"presence_status": "observed", "polarity_label": "positive", "mean_score": 0.9, "mention_unit_count": 1},
                    "price": {"presence_status": "absent_unknown", "polarity_label": "unknown", "mean_score": None, "mention_unit_count": 0},
                },
                "viewer_aspect_summaries": {
                    "taste": {"presence_status": "observed", "polarity_label": "negative", "mean_score": -0.8, "mention_unit_count": 1},
                },
                "aspect_discrepancies": {
                    "taste": {"comparison_status": "abstained_insufficient_viewer_support", "sentiment_discrepancy": None, "viewer_support_count": 1, "min_viewer_support_required": 3},
                },
                "discrepancy_abstention_reason": "insufficient_overlapping_aspect_support_min_3_comments",
                "source_spans": [{"unit_id": "v1::utt::001", "start_char": 0, "end_char": 5, "aspect": "taste", "polarity_label": "positive", "polarity_score": 1.0, "span_text": xss}],
            },
            "comments": [
                {"comment_id": "c1", "author_handle": "u1", "text": xss, "is_seeding": True, "observable_label": "contact_or_link"},
            ],
        },
        hide_seeding=False,
    )
    assert "<script>" not in trust
    assert "absent_unknown" in trust
    assert "diagnostic_only_unvalidated" in trust
    assert "abstained_insufficient_viewer_support" in trust


def test_mounted_demo_renders_redesign_assets_without_login() -> None:
    settings = AppSettings.from_env().model_copy(update={"gemini_api_key": ""})
    app = create_app(settings=settings, mount_demo=True)
    transport = httpx.ASGITransport(app=app)
    import asyncio

    async def _check() -> None:
        async with httpx.AsyncClient(transport=transport, base_url="http://testserver") as client:
            resp = await client.get("/demo/", follow_redirects=True)
            assert resp.status_code == 200
            body = resp.text
            assert "gradio" in body.lower()
            # Ensure no login/account product workflow exists
            assert "dang nhap tai khoan" not in body.lower()

    asyncio.run(_check())
