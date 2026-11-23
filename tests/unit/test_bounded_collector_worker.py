from __future__ import annotations

import hashlib
import json
from datetime import UTC, datetime, timedelta
from pathlib import Path
from typing import Any

import pandas as pd
import pytest

from pipelines.crawl_incremental.models import CollectorBounds
from pipelines.crawl_incremental.providers import (
    LiveNetworkDisabledError,
    LiveTikTokCollectorProvider,
    OfflineFixtureAudioConverter,
    OfflineFixtureCollectorProvider,
    TransientCollectorError,
)
from pipelines.crawl_incremental.worker import BoundedIncrementalCollector
from pipelines.ingest_incremental_to_gold import ingest_incremental_batch_to_gold


def _make_candidate(
    video_id: str,
    create_dt: datetime,
    author_handle: str = "creator_a",
    duration_sec: int = 40,
    with_audio: bool = False,
) -> dict[str, Any]:
    return {
        "video_id": video_id,
        "author_id": f"aid_{author_handle}",
        "author_handle": author_handle,
        "author_nickname": author_handle.upper(),
        "follower_count": 10000,
        "create_time": create_dt.isoformat(),
        "caption": f"Review món ngon {video_id} #ancungtiktok",
        "hashtags": ["ancungtiktok"],
        "duration_sec": duration_sec,
        "play_count": 50000,
        "digg_count": 1500,
        "comment_count": 2,
        "share_count": 50,
        "collect_count": 100,
        "transcript": "Quán phở bò nước dùng ngọt thanh sạch sẽ phục vụ nhanh.",
        "audio_fixture_payload": "ID3-FAKE-64K-MP3-PAYLOAD" if with_audio else None,
        "comments": [
            {"comment_id": f"{video_id}_c1", "author_handle": "u1", "text": "Nước dùng ngon giá hợp lý", "like_count": 5}
        ],
    }


def test_cutoff_120d_boundary_and_zero_prefetch_calls_on_historical_ids(tmp_path: Path) -> None:
    as_of = datetime(2026, 11, 19, 12, 0, 0, tzinfo=UTC)
    cutoff = as_of - timedelta(days=120)

    candidates = [
        _make_candidate("hist_70996_01", as_of - timedelta(days=5)),      # historical ID -> must skip BEFORE detail
        _make_candidate("old_120d_minus_1s", cutoff - timedelta(seconds=1)),  # 1s too old -> skip BEFORE detail
        _make_candidate("exact_cutoff_ok", cutoff),                        # exact boundary -> succeed
        _make_candidate("fresh_10d_ok", as_of - timedelta(days=10)),       # fresh -> succeed
        _make_candidate("fresh_10d_ok", as_of - timedelta(days=10)),       # duplicate candidate -> deduplicated/skipped
    ]
    fixture_file = tmp_path / "fixture.jsonl"
    fixture_file.write_text(
        "\n".join(json.dumps(c, ensure_ascii=False) for c in candidates) + "\n",
        encoding="utf-8",
    )

    provider = OfflineFixtureCollectorProvider(fixture_path=fixture_file)
    audio_conv = OfflineFixtureAudioConverter()
    collector = BoundedIncrementalCollector(
        provider=provider,
        audio_converter=audio_conv,
        bounds=CollectorBounds(),
        sleep_fn=lambda _: None,
    )

    out_dir = tmp_path / "batch_out"
    manifest = collector.run(
        output_dir=out_dir,
        as_of_utc=as_of,
        historical_video_ids={"hist_70996_01"},
        base_corpus_snapshot_id="20261118_taxonomy_fix_v1",
    )

    # Zero detail/comment/audio calls on historical or out-of-window IDs
    assert "hist_70996_01" not in provider.detail_called_ids
    assert "old_120d_minus_1s" not in provider.detail_called_ids
    assert provider.detail_called_ids == ["exact_cutoff_ok", "fresh_10d_ok"]

    assert manifest.source_mode == "offline_fixture"
    assert manifest.is_synthetic_fixture is True
    assert manifest.requested_count == 4  # unique discovered candidate IDs
    assert manifest.succeeded_count == 2
    assert manifest.failed_count == 0
    assert manifest.skipped_count == 2
    assert manifest.requested_count == (
        manifest.succeeded_count + manifest.failed_count + manifest.skipped_count
    )
    assert manifest.duplicate_candidates_ignored == 1

    by_id = {item.video_id: item for item in manifest.items}
    assert by_id["hist_70996_01"].status == "skipped"
    assert by_id["hist_70996_01"].reason == "historical_protected_id"
    assert by_id["old_120d_minus_1s"].status == "skipped"
    assert by_id["old_120d_minus_1s"].reason == "outside_120d_rolling_window"
    assert by_id["exact_cutoff_ok"].status == "succeeded"
    assert by_id["fresh_10d_ok"].status == "succeeded"


def test_bounded_ceilings_halt_unlimited_discovery_and_cap_succeeded_videos(tmp_path: Path) -> None:
    as_of = datetime(2026, 11, 19, 12, 0, 0, tzinfo=UTC)
    candidates = [
        _make_candidate(f"v_{idx}", as_of - timedelta(days=idx + 1), author_handle=f"creator_{idx // 2}")
        for idx in range(10)
    ]
    fixture_file = tmp_path / "fixture_10.jsonl"
    fixture_file.write_text(
        "\n".join(json.dumps(c, ensure_ascii=False) for c in candidates) + "\n",
        encoding="utf-8",
    )

    bounds = CollectorBounds(
        max_creators=2,
        max_candidate_videos=4,
        max_succeeded_videos=2,
    )
    provider = OfflineFixtureCollectorProvider(fixture_path=fixture_file)
    collector = BoundedIncrementalCollector(
        provider=provider,
        audio_converter=OfflineFixtureAudioConverter(),
        bounds=bounds,
        sleep_fn=lambda _: None,
    )

    manifest = collector.run(
        output_dir=tmp_path / "bounded_out",
        as_of_utc=as_of,
        historical_video_ids=set(),
        creators=["creator_0", "creator_1", "creator_2", "creator_3"],
    )

    assert len(manifest.creators_queried) == 2
    assert manifest.requested_count == 4
    assert manifest.succeeded_count == 2
    assert manifest.skipped_count == 2
    assert manifest.failed_count == 0
    skipped_reasons = [i.reason for i in manifest.items if i.status == "skipped"]
    assert skipped_reasons == ["max_succeeded_ceiling", "max_succeeded_ceiling"]


def test_capped_retries_secret_redacted_failures_and_idempotent_checkpoint_resume(tmp_path: Path) -> None:
    as_of = datetime(2026, 11, 19, 12, 0, 0, tzinfo=UTC)
    candidates = [
        _make_candidate("v_ok_1", as_of - timedelta(days=2)),
        _make_candidate("v_flaky_once", as_of - timedelta(days=3)),
        _make_candidate("v_always_fails", as_of - timedelta(days=4)),
    ]
    fixture_file = tmp_path / "fixture_retry.jsonl"
    fixture_file.write_text(
        "\n".join(json.dumps(c, ensure_ascii=False) for c in candidates) + "\n",
        encoding="utf-8",
    )

    fake_google_tok = "AIza" + "FakeUnitRedactionToken123"
    fake_ms_tok = "secret_ms_tok_val_789"

    class _FlakyProvider(OfflineFixtureCollectorProvider):
        def __init__(self, path: Path) -> None:
            super().__init__(path)
            self.fail_always = True
            self._flaky_calls = 0

        def fetch_video_detail(self, candidate: dict[str, Any]) -> dict[str, Any]:
            vid = str(candidate.get("video_id") or "")
            if vid == "v_flaky_once":
                self._flaky_calls += 1
                if self._flaky_calls == 1:
                    raise TransientCollectorError("rate limited temporary 429")
            if vid == "v_always_fails" and self.fail_always:
                raise TransientCollectorError(
                    f"upstream error key={fake_google_tok} ms_token={fake_ms_tok} Bearer my_bearer_xyz"
                )
            return super().fetch_video_detail(candidate)

    sleeps: list[float] = []
    provider = _FlakyProvider(fixture_file)
    bounds = CollectorBounds(max_retries=2)
    collector = BoundedIncrementalCollector(
        provider=provider,
        audio_converter=OfflineFixtureAudioConverter(),
        bounds=bounds,
        sleep_fn=sleeps.append,
    )

    out_dir = tmp_path / "resume_batch"
    m1 = collector.run(output_dir=out_dir, as_of_utc=as_of, historical_video_ids=set(), resume=False)

    assert m1.requested_count == 3
    assert m1.succeeded_count == 2
    assert m1.failed_count == 1
    assert m1.skipped_count == 0
    by_id_1 = {i.video_id: i for i in m1.items}
    assert by_id_1["v_ok_1"].attempts == 1
    assert by_id_1["v_flaky_once"].status == "succeeded"
    assert by_id_1["v_flaky_once"].attempts == 2
    assert by_id_1["v_always_fails"].status == "failed"
    assert by_id_1["v_always_fails"].attempts == 3  # 1 initial + 2 retries

    # Secret hygiene: raw credentials must never appear in manifest or checkpoint
    manifest_raw = (out_dir / "crawl_manifest.json").read_text(encoding="utf-8")
    checkpoint_raw = (out_dir / "collector_checkpoint.json").read_text(encoding="utf-8")
    for raw_blob in (manifest_raw, checkpoint_raw):
        assert fake_google_tok not in raw_blob
        assert fake_ms_tok not in raw_blob
        assert "my_bearer_xyz" not in raw_blob
        assert "[REDACTED]" in raw_blob

    # Now fix transient outage and resume=True: already-succeeded items must NOT be re-fetched,
    # previously failed item recovers, and videos_4m.jsonl stays deduplicated with 3 unique IDs!
    provider.detail_called_ids.clear()
    provider.fail_always = False
    m2 = collector.run(output_dir=out_dir, as_of_utc=as_of, historical_video_ids=set(), resume=True)

    assert provider.detail_called_ids == ["v_always_fails"]
    assert m2.requested_count == 3
    assert m2.succeeded_count == 1
    assert m2.skipped_count == 2  # v_ok_1 and v_flaky_once skipped via checkpoint
    assert m2.failed_count == 0
    by_id_2 = {i.video_id: i for i in m2.items}
    assert by_id_2["v_ok_1"].reason == "already_succeeded_in_checkpoint"
    assert by_id_2["v_flaky_once"].reason == "already_succeeded_in_checkpoint"
    assert by_id_2["v_always_fails"].status == "succeeded"

    jsonl_lines = [
        json.loads(line)
        for line in (out_dir / "videos_4m.jsonl").read_text(encoding="utf-8").splitlines()
        if line.strip()
    ]
    assert [r["video_id"] for r in jsonl_lines] == ["v_ok_1", "v_flaky_once", "v_always_fails"]


def test_audio_64k_mp3_receipts_audio_ceiling_and_missing_modalities_stay_missing(tmp_path: Path) -> None:
    as_of = datetime(2026, 11, 19, 12, 0, 0, tzinfo=UTC)
    c_audio = _make_candidate("v_with_audio", as_of - timedelta(days=2), duration_sec=60, with_audio=True)
    c_missing = _make_candidate("v_missing_mod", as_of - timedelta(days=3), duration_sec=45, with_audio=False)
    c_missing["comments"] = []
    c_missing["transcript"] = ""
    c_ceiling = _make_candidate("v_over_audio_cap", as_of - timedelta(days=4), duration_sec=60, with_audio=True)

    fixture_file = tmp_path / "fixture_audio.jsonl"
    fixture_file.write_text(
        "\n".join(json.dumps(c, ensure_ascii=False) for c in (c_audio, c_missing, c_ceiling)) + "\n",
        encoding="utf-8",
    )

    out_dir = tmp_path / "audio_batch"
    collector = BoundedIncrementalCollector(
        provider=OfflineFixtureCollectorProvider(fixture_file),
        audio_converter=OfflineFixtureAudioConverter(),
        bounds=CollectorBounds(max_audio_minutes=1.8),
        sleep_fn=lambda _: None,
    )
    manifest = collector.run(output_dir=out_dir, as_of_utc=as_of, historical_video_ids=set())

    assert manifest.succeeded_count == 3
    assert manifest.converted_audio_count == 1
    assert manifest.accumulated_audio_minutes == 1.0

    by_id = {i.video_id: i for i in manifest.items}
    r1 = by_id["v_with_audio"].audio_receipt
    assert r1 is not None
    assert r1.status == "converted_64k_mp3"
    assert r1.target_bitrate_kbps == 64
    assert r1.audio_bytes > 0
    assert r1.audio_sha256 is not None and len(r1.audio_sha256) == 64
    assert r1.audio_path == "audio_64k/v_with_audio.mp3"
    assert (out_dir / "audio_64k" / "v_with_audio.mp3").is_file()

    r2 = by_id["v_missing_mod"].audio_receipt
    assert r2 is not None and r2.status == "unavailable"
    assert r2.audio_path is None

    r3 = by_id["v_over_audio_cap"].audio_receipt
    assert r3 is not None and r3.status == "skipped_audio_ceiling"
    assert r3.audio_path is None

    written = {
        row["video_id"]: row
        for row in (
            json.loads(line)
            for line in (out_dir / "videos_4m.jsonl").read_text(encoding="utf-8").splitlines()
            if line.strip()
        )
    }
    assert written["v_with_audio"]["audio_path"] == "audio_64k/v_with_audio.mp3"
    assert written["v_missing_mod"]["audio_path"] is None
    assert written["v_missing_mod"]["comments"] == []
    assert written["v_missing_mod"]["transcript"] == ""
    assert written["v_over_audio_cap"]["audio_path"] is None


def test_live_provider_fails_closed_without_explicit_allow_flag_or_ms_token() -> None:
    with pytest.raises(LiveNetworkDisabledError, match="allow_live_network"):
        LiveTikTokCollectorProvider(allow_live_network=False, ms_token="some_token")
    with pytest.raises(LiveNetworkDisabledError, match="MS_TOKEN"):
        LiveTikTokCollectorProvider(allow_live_network=True, ms_token="")


def _build_minimal_base_gold(base_dir: Path) -> dict[str, str]:
    base_dir.mkdir(parents=True, exist_ok=True)
    creators = pd.DataFrame([{
        "author_id": "a1", "unique_id": "fixture_creator", "nickname": "Fixture", "verified": False,
        "commerce_user": False, "tt_seller": False, "follower_count": 1000, "follower_tier": "micro",
        "heart_count": 1000, "lifetime_video_count": 1, "sample_video_count": 1, "median_play_count": 1000.0,
        "median_engagement_rate": 0.1, "median_duration_sec": 30.0, "avg_videos_per_week": 1.0,
    }])
    videos = pd.DataFrame([{
        "video_id": "base_protected_vid", "author_id": "a1", "author_handle": "fixture_creator", "author_nickname": "Fixture",
        "tiktok_url": "https://www.tiktok.com/@fixture_creator/video/base_protected_vid", "follower_count": 1000,
        "follower_tier": "micro", "create_time": "2025-03-01T00:00:00+00:00", "create_hour": 0,
        "year_week": "Y2025_W09", "play_count": 1000, "digg_count": 100, "comment_count": 0,
        "share_count": 0, "collect_count": 0, "engagement_rate": 0.1, "viral_multiplier": 1.0,
        "is_ad": False, "is_ec_video": False, "playlist_id": None, "duration_sec": 30,
        "duration_bucket": "short_20_45s", "caption": "Historical protected video", "hashtags": [], "hashtag_count": 0,
        "has_transcript": False, "transcript": "", "word_count": 0, "word_per_second": 0.0,
        "has_cta": False, "has_curiosity_gap": False, "poi_id": None, "poi_name": None,
        "poi_address": None, "poi_city": None, "poi_category_tiny": None, "city_norm": None,
        "district_norm": None, "region": "unknown", "location_source": "unknown", "video_format": "Review món ăn",
        "food_category": "Ẩm thực Tổng hợp", "dishes": [], "price_tier": "unspecified", "occasions": [],
        "hook_text": "", "body_beats": [], "cta_text": "", "rag_document": "",
    }])
    files = []
    for name, frame in [("dim_creators.parquet", creators), ("fact_videos.parquet", videos)]:
        p = base_dir / name
        frame.to_parquet(p, index=False)
        files.append({
            "filename": name, "rows": len(frame), "columns": len(frame.columns),
            "sha256": hashlib.sha256(p.read_bytes()).hexdigest(), "size_bytes": p.stat().st_size,
        })
    (base_dir / "manifest.json").write_text(json.dumps({
        "snapshot_id": "base_minimal_v1", "created_at": "2026-11-17T00:00:00+00:00",
        "date_window_start": "2025-03-01", "date_window_end": "2025-03-01", "total_creators": 1,
        "total_videos": 1, "transcribed_videos": 0, "poi_tagged_videos": 0, "ec_tagged_videos": 0,
        "files": files, "caveats": ["Minimal base fixture."],
    }), encoding="utf-8")
    return {p.name: hashlib.sha256(p.read_bytes()).hexdigest() for p in base_dir.iterdir() if p.is_file()}


def test_cli_offline_fixture_mode_is_visibly_separate_and_ingests_cleanly_into_m3_1_gold(
    tmp_path: Path,
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    from pipelines.crawl_incremental.__main__ import main as crawl_main

    base_dir = tmp_path / "base_gold"
    before_hashes = _build_minimal_base_gold(base_dir)

    as_of = datetime(2026, 11, 19, 12, 0, 0, tzinfo=UTC)
    candidates = [
        _make_candidate("base_protected_vid", as_of - timedelta(days=2)),
        _make_candidate("fresh_cli_01", as_of - timedelta(days=5), with_audio=True),
    ]
    fixture_file = tmp_path / "cli_fixture.jsonl"
    fixture_file.write_text(
        "\n".join(json.dumps(c, ensure_ascii=False) for c in candidates) + "\n",
        encoding="utf-8",
    )

    batch_dir = tmp_path / "cli_batch_out"
    monkeypatch.setattr(
        "sys.argv",
        [
            "crawl_incremental",
            "--source",
            "offline_fixture",
            "--fixture-path",
            str(fixture_file),
            "--base-corpus",
            str(base_dir),
            "--output-dir",
            str(batch_dir),
            "--as-of",
            as_of.isoformat(),
        ],
    )
    crawl_main()

    manifest_data = json.loads((batch_dir / "crawl_manifest.json").read_text(encoding="utf-8"))
    assert manifest_data["source_mode"] == "offline_fixture"
    assert manifest_data["is_synthetic_fixture"] is True
    assert manifest_data["historical_protected_count"] == 1
    assert manifest_data["requested_count"] == 2
    assert manifest_data["succeeded_count"] == 1
    assert manifest_data["skipped_count"] == 1

    # Round-trip ingest into M3.1 Dual-Sink Gold snapshot
    out_gold = tmp_path / "gold_after_cli"
    gold_manifest = ingest_incremental_batch_to_gold(
        base_corpus_dir=base_dir,
        incremental_jsonl=batch_dir / "videos_4m.jsonl",
        output_corpus_dir=out_gold,
    )
    assert gold_manifest.total_videos == 2
    after_hashes = {p.name: hashlib.sha256(p.read_bytes()).hexdigest() for p in base_dir.iterdir() if p.is_file()}
    assert after_hashes == before_hashes


def test_c1_quoted_json_and_cookie_header_secrets_redacted_and_timeout_not_chained(
    tmp_path: Path,
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    import subprocess as sp

    as_of = datetime(2026, 11, 19, 12, 0, 0, tzinfo=UTC)
    c1 = _make_candidate("v_quoted_secret", as_of - timedelta(days=2))
    fx = tmp_path / "c1.jsonl"
    fx.write_text(json.dumps(c1, ensure_ascii=False) + "\n", encoding="utf-8")

    q_ms = "quoted_ms_tok_secret_111"
    j_sess = "json_session_secret_222"
    hdr_ms = "cookie_header_ms_secret_333"

    class _QuotedLeakProvider(OfflineFixtureCollectorProvider):
        def fetch_video_detail(self, candidate: dict[str, Any]) -> dict[str, Any]:
            raise RuntimeError(
                f'error ms_token="{q_ms}" payload={{"sessionid": "{j_sess}"}} Cookie: msToken={hdr_ms}; foo=bar'
            )

    out_dir = tmp_path / "c1_out"
    collector = BoundedIncrementalCollector(
        provider=_QuotedLeakProvider(fx),
        audio_converter=OfflineFixtureAudioConverter(),
        bounds=CollectorBounds(max_retries=0),
        sleep_fn=lambda _: None,
    )
    collector.run(output_dir=out_dir, as_of_utc=as_of, historical_video_ids=set())
    for fname in ("crawl_manifest.json", "collector_checkpoint.json"):
        blob = (out_dir / fname).read_text(encoding="utf-8")
        assert q_ms not in blob
        assert j_sess not in blob
        assert hdr_ms not in blob

    # Also verify LiveTikTokCollectorProvider TimeoutExpired does not chain raw cmd containing msToken
    raw_live_tok = "live_raw_ms_tok_444"
    live = LiveTikTokCollectorProvider(allow_live_network=True, ms_token=raw_live_tok, timeout_sec=5)

    def _boom_timeout(*args: Any, **kwargs: Any) -> Any:
        cmd = args[0]
        raise sp.TimeoutExpired(cmd=cmd, timeout=5)

    monkeypatch.setattr(sp, "run", _boom_timeout)
    with pytest.raises(TransientCollectorError) as exc_info:
        live.discover_candidates(["some_creator"], max_per_creator=5)
    assert exc_info.value.__cause__ is None
    assert raw_live_tok not in repr(exc_info.value)


def test_c2_mid_batch_interruption_persists_atomic_jsonl_and_resumes_without_data_loss(
    tmp_path: Path,
) -> None:
    as_of = datetime(2026, 11, 19, 12, 0, 0, tzinfo=UTC)
    candidates = [
        _make_candidate("v_pre_crash_1", as_of - timedelta(days=1)),
        _make_candidate("v_pre_crash_2", as_of - timedelta(days=2)),
        _make_candidate("v_crash_here", as_of - timedelta(days=3)),
    ]
    fx = tmp_path / "c2.jsonl"
    fx.write_text("\n".join(json.dumps(c, ensure_ascii=False) for c in candidates) + "\n", encoding="utf-8")

    class _CrashMidRunProvider(OfflineFixtureCollectorProvider):
        def __init__(self, path: Path) -> None:
            super().__init__(path)
            self.crash_now = True

        def fetch_video_detail(self, candidate: dict[str, Any]) -> dict[str, Any]:
            if candidate.get("video_id") == "v_crash_here" and self.crash_now:
                raise KeyboardInterrupt("simulated SIGINT mid-batch")
            return super().fetch_video_detail(candidate)

    provider = _CrashMidRunProvider(fx)
    out_dir = tmp_path / "c2_out"
    collector = BoundedIncrementalCollector(
        provider=provider,
        audio_converter=OfflineFixtureAudioConverter(),
        bounds=CollectorBounds(max_retries=0),
        sleep_fn=lambda _: None,
    )
    with pytest.raises(KeyboardInterrupt):
        collector.run(output_dir=out_dir, as_of_utc=as_of, historical_video_ids=set(), resume=False)

    # Even after abrupt crash, videos_4m.jsonl must already contain the 2 completed items atomically
    assert (out_dir / "videos_4m.jsonl").is_file()
    provider.detail_called_ids.clear()
    provider.crash_now = False

    m_resumed = collector.run(output_dir=out_dir, as_of_utc=as_of, historical_video_ids=set(), resume=True)
    assert provider.detail_called_ids == ["v_crash_here"]
    assert m_resumed.persisted_records_count == 3
    rows = [json.loads(line) for line in (out_dir / "videos_4m.jsonl").read_text(encoding="utf-8").splitlines() if line.strip()]
    assert [r["video_id"] for r in rows] == ["v_pre_crash_1", "v_pre_crash_2", "v_crash_here"]


def test_c3_malformed_bool_and_overflow_timestamps_isolated_per_item(tmp_path: Path) -> None:
    as_of = datetime(2026, 11, 19, 12, 0, 0, tzinfo=UTC)
    c_bool = {**_make_candidate("v_bool_ts", as_of), "create_time": True}
    c_overflow = {**_make_candidate("v_overflow_ts", as_of), "create_time": "99999999999999999999"}
    c_valid = _make_candidate("v_good_ts", as_of - timedelta(days=2))
    fx = tmp_path / "c3.jsonl"
    fx.write_text("\n".join(json.dumps(c, ensure_ascii=False) for c in (c_bool, c_overflow, c_valid)) + "\n", encoding="utf-8")

    manifest = BoundedIncrementalCollector(
        provider=OfflineFixtureCollectorProvider(fx),
        audio_converter=OfflineFixtureAudioConverter(),
        bounds=CollectorBounds(max_retries=0),
        sleep_fn=lambda _: None,
    ).run(output_dir=tmp_path / "c3_out", as_of_utc=as_of, historical_video_ids=set())

    by_id = {i.video_id: i for i in manifest.items}
    assert by_id["v_bool_ts"].status == "failed"
    assert by_id["v_bool_ts"].reason == "invalid_create_time"
    assert by_id["v_overflow_ts"].status == "failed"
    assert by_id["v_overflow_ts"].reason == "invalid_create_time"
    assert by_id["v_good_ts"].status == "succeeded"


def test_c4_flat_discovery_null_timestamp_and_post_detail_historical_or_window_gates(tmp_path: Path) -> None:
    as_of = datetime(2026, 11, 19, 12, 0, 0, tzinfo=UTC)
    c_null_disc_fresh = _make_candidate("v_null_disc_fresh", as_of - timedelta(days=3))
    c_null_disc_old = _make_candidate("v_null_disc_old", as_of - timedelta(days=150))
    c_alias_to_hist = _make_candidate("v_alias_cand", as_of - timedelta(days=2))

    fx = tmp_path / "c4.jsonl"
    fx.write_text(
        "\n".join(json.dumps(c, ensure_ascii=False) for c in (c_null_disc_fresh, c_null_disc_old, c_alias_to_hist)) + "\n",
        encoding="utf-8",
    )

    class _FlatPlaylistProvider(OfflineFixtureCollectorProvider):
        def discover_candidates(self, creators: list[str] | None, max_per_creator: int) -> list[dict[str, Any]]:
            # Simulate yt-dlp --flat-playlist omitting create_time until fetch_video_detail
            base = super().discover_candidates(creators, max_per_creator)
            return [{**item, "create_time": None} for item in base]

        def fetch_video_detail(self, candidate: dict[str, Any]) -> dict[str, Any]:
            detail = super().fetch_video_detail(candidate)
            if candidate.get("video_id") == "v_alias_cand":
                detail["video_id"] = "hist_canonical_999"
            return detail

    manifest = BoundedIncrementalCollector(
        provider=_FlatPlaylistProvider(fx),
        audio_converter=OfflineFixtureAudioConverter(),
        bounds=CollectorBounds(max_retries=1),
        sleep_fn=lambda _: None,
    ).run(
        output_dir=tmp_path / "c4_out",
        as_of_utc=as_of,
        historical_video_ids={"hist_canonical_999"},
    )

    by_id = {i.video_id: i for i in manifest.items}
    assert by_id["v_null_disc_fresh"].status == "succeeded"
    assert by_id["v_null_disc_old"].status == "skipped"
    assert by_id["v_null_disc_old"].reason == "outside_120d_rolling_window"
    assert by_id["v_alias_cand"].status == "skipped"
    assert by_id["v_alias_cand"].reason == "historical_protected_id"


def test_i1_i2_resume_filters_expired_prior_rows_cleans_stale_audio_and_tracks_persisted_counts(
    tmp_path: Path,
) -> None:
    as_of_day1 = datetime(2026, 11, 19, 12, 0, 0, tzinfo=UTC)
    c_borderline = _make_candidate("v_expires_later", as_of_day1 - timedelta(days=119), with_audio=True)
    c_stays_fresh = _make_candidate("v_stays_fresh", as_of_day1 - timedelta(days=5), with_audio=True)
    fx = tmp_path / "i1.jsonl"
    fx.write_text("\n".join(json.dumps(c, ensure_ascii=False) for c in (c_borderline, c_stays_fresh)) + "\n", encoding="utf-8")

    out_dir = tmp_path / "i1_out"
    collector = BoundedIncrementalCollector(
        provider=OfflineFixtureCollectorProvider(fx),
        audio_converter=OfflineFixtureAudioConverter(),
        bounds=CollectorBounds(),
        sleep_fn=lambda _: None,
    )
    m1 = collector.run(output_dir=out_dir, as_of_utc=as_of_day1, historical_video_ids=set(), resume=False)
    assert m1.persisted_records_count == 2

    # Advance as_of by 3 days so v_expires_later falls outside 120d window on resume=True
    as_of_day4 = as_of_day1 + timedelta(days=3)
    m2 = collector.run(output_dir=out_dir, as_of_utc=as_of_day4, historical_video_ids=set(), resume=True)
    assert m2.persisted_records_count == 1
    assert m2.converted_audio_count == 1
    by_id = {i.video_id: i for i in m2.items}
    assert by_id["v_expires_later"].status == "skipped"
    assert by_id["v_expires_later"].reason == "outside_120d_rolling_window"
    assert by_id["v_stays_fresh"].status == "skipped"
    assert by_id["v_stays_fresh"].reason == "already_succeeded_in_checkpoint"
    assert by_id["v_stays_fresh"].comment_count == 1

    persisted_ids = [
        json.loads(line)["video_id"]
        for line in (out_dir / "videos_4m.jsonl").read_text(encoding="utf-8").splitlines()
        if line.strip()
    ]
    assert persisted_ids == ["v_stays_fresh"]


def test_i3_cli_live_provider_fails_closed_when_base_corpus_missing_protected_ids(
    tmp_path: Path,
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    from pipelines.crawl_incremental.__main__ import main as crawl_main

    monkeypatch.setenv("MS_TOKEN", "dummy_ms_tok_for_gate_test")
    monkeypatch.setattr(
        "sys.argv",
        [
            "crawl_incremental",
            "--source",
            "live_provider",
            "--allow-live-network",
            "--base-corpus",
            str(tmp_path / "nonexistent_corpus"),
            "--output-dir",
            str(tmp_path / "live_out"),
        ],
    )
    with pytest.raises(LiveNetworkDisabledError, match="historical|base_corpus|protected"):
        crawl_main()


def test_mappers_preserve_21khdl_item_struct_poi_ec_ad_and_unstripped_comments() -> None:
    from pipelines.crawl_incremental.mappers import (
        map_tiktok_comment_to_input,
        map_tiktok_item_struct_to_detail,
        map_ytdlp_json_to_detail,
    )

    raw_item = {
        "id": "7480001112223334445",
        "createTime": 1763500000,
        "desc": "Review phở bò Quận 1 #ancungtiktok #phobo",
        "isAd": True,
        "isECVideo": "1",
        "isPinnedItem": False,
        "playlistId": "pl_fnb_01",
        "author": {"id": "u_01", "uniqueId": "spicykim9386", "nickname": "Spicy Kim"},
        "authorStats": {"followerCount": 820000},
        "video": {"duration": 48, "VQScore": 72.5},
        "statsV2": {
            "playCount": "150000",
            "diggCount": "9200",
            "commentCount": "140",
            "shareCount": "310",
            "collectCount": "1200",
        },
        "challenges": [{"title": "ancungtiktok"}, {"title": "#saigonfood"}],
        "poi": {
            "id": "poi_999",
            "name": "Phở Hòa Pasteur",
            "address": "260C Pasteur, Quận 3",
            "city": "Ho Chi Minh City",
            "ttTypeNameTiny": "Noodle House",
        },
    }
    detail = map_tiktok_item_struct_to_detail(raw_item, collected_at_utc="2026-11-23T04:00:00+00:00")
    assert detail["video_id"] == "7480001112223334445"
    assert detail["author_handle"] == "spicykim9386"
    assert detail["follower_count"] == 820000
    assert detail["collect_count"] == 1200
    assert detail["is_ad"] is True
    assert detail["is_ec_video"] is True
    assert detail["playlist_id"] == "pl_fnb_01"
    assert detail["poi_name"] == "Phở Hòa Pasteur"
    assert detail["poi_category_tiny"] == "Noodle House"
    assert detail["hashtags"] == ["ancungtiktok", "saigonfood"]

    # Unstripped leading/trailing spaces preserved for M5.2 NFC offsets; blank rejected
    c_ok = map_tiktok_comment_to_input(
        {
            "cid": "c_901",
            "text": "  Nước dùng đậm đà nhưng giá hơi cao  ",
            "digg_count": 17,
            "reply_comment_total": 4,
            "user": {"uid": "u9", "unique_id": "diner_vn"},
        },
        canonical_vid="7480001112223334445",
        idx=0,
    )
    assert c_ok is not None
    assert c_ok["text"] == "  Nước dùng đậm đà nhưng giá hơi cao  "
    assert c_ok["like_count"] == 17
    assert c_ok["reply_count"] == 4
    assert (
        map_tiktok_comment_to_input({"cid": "c_blank", "text": "   "}, canonical_vid="7480001112223334445", idx=1)
        is None
    )

    # yt-dlp mapping rolls flat child replies into parent reply_count and extracts collect_count
    yt_detail, yt_comments = map_ytdlp_json_to_detail(
        {
            "id": "748000999",
            "timestamp": 1763500000,
            "uploader": "haidangrevieww",
            "uploader_id": "uid_hd",
            "description": "Bún bò Huế ngon",
            "duration": 35,
            "view_count": 60000,
            "like_count": 3000,
            "repost_count": 80,
            "collect_count": 450,
            "comments": [
                {"id": "root_1", "parent": "root", "author": "a1", "text": "  Ngon xuất sắc ", "like_count": 5},
                {"id": "rep_1", "parent": "root_1", "author": "a2", "text": "Đồng ý luôn", "like_count": 1},
            ],
        },
        candidate={"video_id": "748000999", "author_handle": "haidangrevieww"},
    )
    assert yt_detail["collect_count"] == 450
    assert yt_detail["share_count"] == 80
    by_cid = {c["comment_id"]: c for c in yt_comments}
    assert by_cid["root_1"]["reply_count"] == 1
    assert by_cid["root_1"]["text"] == "  Ngon xuất sắc "


def test_dotenv_bridge_curated_creators_and_authenticated_mp3_download(
    tmp_path: Path, monkeypatch: pytest.MonkeyPatch
) -> None:
    from pipelines.crawl_incremental import crawler_service

    # 1. .env bridges lowercase ms_token -> MS_TOKEN without overwriting existing env
    dotenv_file = tmp_path / ".env"
    dotenv_file.write_text("ms_token = 'tok_from_legacy_env'\nTIKTOK_BROWSER=webkit\n", encoding="utf-8")
    env_box: dict[str, str] = {}
    crawler_service.load_dotenv_if_present(dotenv_file, target_env=env_box)
    assert env_box["MS_TOKEN"] == "tok_from_legacy_env"
    assert env_box["TIKTOK_BROWSER"] == "webkit"

    env_existing = {"MS_TOKEN": "already_set_tok"}
    crawler_service.load_dotenv_if_present(dotenv_file, target_env=env_existing)
    assert env_existing["MS_TOKEN"] == "already_set_tok"

    # 2. Curated F&B creators prioritize author_unique_ids.txt present in dim_creators, then Chapter 3 thresholds
    corpus_dir = tmp_path / "gold"
    corpus_dir.mkdir()
    pd.DataFrame(
        [
            {"unique_id": "low_views_user", "median_play_count": 5000.0, "median_engagement_rate": 0.08, "avg_videos_per_week": 9.0, "sample_video_count": 100, "follower_count": 90000},
            {"unique_id": "ch3_qualified_b", "median_play_count": 65000.0, "median_engagement_rate": 0.045, "avg_videos_per_week": 3.5, "sample_video_count": 120, "follower_count": 300000},
            {"unique_id": "haidangrevieww", "median_play_count": 80000.0, "median_engagement_rate": 0.05, "avg_videos_per_week": 2.1, "sample_video_count": 255, "follower_count": 500000},
            {"unique_id": "spicykim9386", "median_play_count": 95000.0, "median_engagement_rate": 0.06, "avg_videos_per_week": 2.8, "sample_video_count": 298, "follower_count": 900000},
        ]
    ).to_parquet(corpus_dir / "dim_creators.parquet", index=False)
    filt = tmp_path / "author_unique_ids.txt"
    filt.write_text("spicykim9386\nhaidangrevieww\nmissing_from_corpus\n", encoding="utf-8")

    picked = crawler_service.select_curated_fnb_creators(corpus_dir, top_k=3, filter_file=filt)
    assert picked == ["spicykim9386", "haidangrevieww", "ch3_qualified_b"]

    # 3. download_audio_mp3_64k forwards msToken header, --cookies file, and UTF-8 subprocess kwargs
    captured_call: dict[str, Any] = {}
    cookies_txt = tmp_path / "cookies.txt"
    cookies_txt.write_text("# Netscape HTTP Cookie File\n", encoding="utf-8")
    out_mp3 = tmp_path / "audio_64k" / "v1.mp3"

    def _fake_run(cmd: list[str], **kwargs: Any) -> Any:
        captured_call["cmd"] = cmd
        captured_call["kwargs"] = kwargs
        out_mp3.parent.mkdir(parents=True, exist_ok=True)
        out_mp3.write_bytes(b"ID3-64K")

        class _Res:
            returncode = 0

        return _Res()

    monkeypatch.setattr(crawler_service.subprocess, "run", _fake_run)
    ok = crawler_service.download_audio_mp3_64k(
        "https://www.tiktok.com/@spicykim9386/video/123",
        out_mp3,
        ms_token="secret_ms_tok",
        cookies_file=cookies_txt,
    )
    assert ok is True
    assert "Cookie: msToken=secret_ms_tok" in captured_call["cmd"]
    assert "--cookies" in captured_call["cmd"]
    assert str(cookies_txt) in captured_call["cmd"]
    assert captured_call["kwargs"]["encoding"] == "utf-8"
    assert captured_call["kwargs"]["env"]["PYTHONUTF8"] == "1"
