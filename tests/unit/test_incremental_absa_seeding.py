from __future__ import annotations

import asyncio
import json
from datetime import datetime, timedelta, timezone
from pathlib import Path

import httpx
import pandas as pd

from apps.api.app.main import create_app
from packages.absa import analyze_koc_vs_viewer_absa
from packages.common.settings import AppSettings
from packages.data_contracts.multimodal import (
    RawCommentInput,
    RawIncrementalVideoRecord,
    RawWhisperSegment,
)
from packages.seeding import detect_seeding_comments
from pipelines.crawl_incremental import compute_cutoff_utc, filter_fresh_candidates
from pipelines.ingest_incremental_to_gold import ingest_incremental_batch_to_gold


def test_rolling_4_month_cutoff_skips_old_and_existing_videos() -> None:
    now = datetime(2026, 11, 16, tzinfo=timezone.utc)
    cutoff = compute_cutoff_utc(reference_now=now, window_days=120)

    candidates = [
        {"video_id": "old_2024", "create_time": (now - timedelta(days=400)).isoformat()},
        {"video_id": "already_in_gold", "create_time": (now - timedelta(days=10)).isoformat()},
        {"video_id": "fresh_new_1", "create_time": (now - timedelta(days=15)).isoformat()},
    ]
    filtered = filter_fresh_candidates(
        raw_items=candidates,
        existing_video_ids={"already_in_gold"},
        cutoff_utc=cutoff,
    )
    assert [c["video_id"] for c in filtered] == ["fresh_new_1"]


def test_seeding_detector_and_koc_vs_viewer_absa_hype_gap() -> None:
    raw_comments = [
        RawCommentInput(comment_id="1", author_handle="seed_a", text="Quán ruột của mình mỗi tuần đều ghé ăn ngon lắm"),
        RawCommentInput(comment_id="2", author_handle="seed_b", text="Quán ruột của mình mỗi tuần đều ghé ăn ngon nha"),
        RawCommentInput(comment_id="3", author_handle="spam_c", text="Tuyển CTV liên hệ zalo 0912345678"),
        RawCommentInput(
            comment_id="4",
            author_handle="real_diner",
            text="Nước dùng mặn chát, bàn ghế bẩn đầy khói mà nhân viên phục vụ quá chậm.",
        ),
    ]
    cleansed = detect_seeding_comments("v_test", raw_comments)
    seeding_flags = {c.comment_id: (c.is_seeding, c.seeding_reason) for c in cleansed}

    assert seeding_flags["1"][0] is True
    assert seeding_flags["2"][0] is True
    assert seeding_flags["3"] == (True, "contact_or_link_spam")
    assert seeding_flags["4"] == (False, None)

    comp = analyze_koc_vs_viewer_absa(
        video_id="v_test",
        caption="Khai trương tặng ngay voucher giảm giá!",
        transcript="Nước dùng đậm đà ngon xuất sắc, không gian sạch sẽ thoáng mát nhân viên nhiệt tình dễ thương!",
        comments=cleansed,
    )
    assert comp.seeding_comment_count == 3
    assert comp.clean_comment_count == 1
    assert comp.koc_scores.taste > 0.3
    assert comp.viewer_clean_scores.hygiene < 0.0
    assert comp.pr_hype_gap > 0.5
    assert comp.undisclosed_pr_risk > 0.35
    assert len(comp.viewer_pain_points) >= 1


def test_dual_sink_incremental_ingestion_and_trust_api(tmp_path: Path) -> None:
    # Build a tiny base Gold snapshot in tmp_path so test runs in <0.5s without copying 60MB
    base_dir = tmp_path / "base_corpus"
    base_dir.mkdir(parents=True)
    df_c = pd.DataFrame(
        [
            {
                "author_id": "a1",
                "unique_id": "creator_1",
                "nickname": "Creator 1",
                "verified": False,
                "commerce_user": False,
                "tt_seller": False,
                "follower_count": 200000,
                "follower_tier": "mid",
                "heart_count": 1000000,
                "lifetime_video_count": 50,
                "sample_video_count": 1,
                "median_play_count": 100000.0,
                "median_engagement_rate": 0.05,
                "median_duration_sec": 40.0,
                "avg_videos_per_week": 2.0,
            }
        ]
    )
    df_v = pd.read_parquet(AppSettings().corpus_dir / "fact_videos.parquet").head(3).copy()
    p_c = base_dir / "dim_creators.parquet"
    p_v = base_dir / "fact_videos.parquet"
    df_c.to_parquet(p_c, index=False)
    df_v.to_parquet(p_v, index=False)

    import hashlib

    def _sha(p: Path) -> str:
        return hashlib.sha256(p.read_bytes()).hexdigest()

    (base_dir / "manifest.json").write_text(
        json.dumps(
            {
                "snapshot_id": "mini_base",
                "created_at": "2026-11-16T00:00:00+00:00",
                "date_window_start": "2024-01-01",
                "date_window_end": "2025-03-19",
                "total_creators": 1,
                "total_videos": 3,
                "transcribed_videos": int(df_v["has_transcript"].sum()),
                "poi_tagged_videos": int(df_v["poi_name"].notna().sum()),
                "ec_tagged_videos": 0,
                "files": [
                    {
                        "filename": "dim_creators.parquet",
                        "rows": 1,
                        "columns": len(df_c.columns),
                        "sha256": _sha(p_c),
                        "size_bytes": p_c.stat().st_size,
                    },
                    {
                        "filename": "fact_videos.parquet",
                        "rows": 3,
                        "columns": len(df_v.columns),
                        "sha256": _sha(p_v),
                        "size_bytes": p_v.stat().st_size,
                    },
                ],
                "caveats": ["unit test fixture"],
            }
        ),
        encoding="utf-8",
    )

    inc_jsonl = tmp_path / "videos_4m.jsonl"
    rec = RawIncrementalVideoRecord(
        video_id="7699999999999999999",
        author_id="a_new",
        author_handle="new_reviewer_4m",
        author_nickname="New Reviewer",
        follower_count=150000,
        create_time="2026-11-10T12:00:00+00:00",
        caption="Review bún bò Quận 3 giá 45k bình dân",
        hashtags=["bunbo", "quan3"],
        duration_sec=30,
        play_count=300000,
        digg_count=15000,
        comment_count=120,
        share_count=400,
        collect_count=2000,
        poi_name="Bún Bò Cô Tư",
        poi_address="12 Võ Văn Tần, Quận 3, TP. Hồ Chí Minh",
        poi_city="Ho Chi Minh City",
        transcript="Bún bò Quận 3 giá 45k nước lèo thơm đậm đà, thịt bò mềm tươi lắm nha mọi người.",
        whisper_segments=[
            RawWhisperSegment(
                start_sec=0.0,
                end_sec=10.0,
                text="Bún bò Quận 3 giá 45k nước lèo thơm đậm đà, thịt bò mềm tươi lắm nha mọi người.",
            )
        ],
        comments=[
            RawCommentInput(comment_id="c1", author_handle="u1", text="Nước lèo ngon đậm đà giá hợp lý"),
        ],
    )
    inc_jsonl.write_text(json.dumps(rec.model_dump(), ensure_ascii=False) + "\n", encoding="utf-8")

    out_dir = tmp_path / "gold_v2"
    manifest = ingest_incremental_batch_to_gold(
        base_corpus_dir=base_dir,
        incremental_jsonl=inc_jsonl,
        output_corpus_dir=out_dir,
    )
    assert manifest.total_videos == 4
    assert manifest.total_creators == 2
    assert len(manifest.files) == 5

    df_merged_v = pd.read_parquet(out_dir / "fact_videos.parquet")
    new_row = df_merged_v[df_merged_v["video_id"] == "7699999999999999999"].iloc[0]
    assert new_row["city_norm"] == "hồ chí minh"
    assert new_row["price_tier"] == "budget_lt50k"

    df_segs = pd.read_parquet(out_dir / "fact_voice_segments.parquet")
    assert len(df_segs) == 1
    assert df_segs.iloc[0]["timestamp_source"] == "whisper_exact"

    # Verify /api/v1/trust/audit-video endpoint
    app = create_app(settings=AppSettings.from_env().model_copy(update={"gemini_api_key": ""}), mount_demo=False)

    async def _call_trust() -> None:
        async with httpx.AsyncClient(transport=httpx.ASGITransport(app=app), base_url="http://test") as client:
            r = await client.post(
                "/api/v1/trust/audit-video",
                json={
                    "caption": "Khai trương giảm giá",
                    "transcript": "Món ăn ngon xuất sắc sạch sẽ",
                    "comments": [{"comment_id": "1", "author_handle": "u1", "text": "Đồ ăn nguội ngắt và dơ"}],
                },
            )
            assert r.status_code == 200
            assert r.json()["comparison"]["pr_hype_gap"] > 0.2

    asyncio.run(_call_trust())
