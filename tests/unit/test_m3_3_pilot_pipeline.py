from __future__ import annotations

import hashlib
import json
from datetime import UTC, datetime, timedelta
from pathlib import Path
from typing import Any

import pandas as pd
import pyarrow as pa
import pyarrow.parquet as pq
import pytest

from packages.common.exceptions import IndexNotReadyError
from packages.data_contracts.corpus import CorpusFileChecksum, CorpusManifest
from packages.data_contracts.multimodal import RawIncrementalVideoRecord, RawWhisperSegment
from pipelines.pilot_m3_3.asr import BoundedCpuAsrRunner, FasterWhisperCpuAsrEngine
from pipelines.pilot_m3_3.models import M33PilotConfig
from pipelines.pilot_m3_3.runner import run_m3_3_pilot


class _StubCpuAsrEngine:
    model_id = "stub_cpu_whisper_int8"

    def __init__(self) -> None:
        self.called_paths: list[Path] = []

    def transcribe_file(self, audio_path: Path) -> tuple[str, list[RawWhisperSegment]]:
        self.called_paths.append(audio_path)
        stem = audio_path.stem
        segs = [
            RawWhisperSegment(
                start_sec=0.0,
                end_sec=4.5,
                text=f"Món đặc sản tươi ngon {stem} giá bình dân ở Sài Gòn.",
            ),
            RawWhisperSegment(
                start_sec=4.5,
                end_sec=9.0,
                text=f"Nước dùng đậm đà phục vụ nhanh tại {stem}.",
            ),
        ]
        full_text = " ".join(s.text for s in segs)
        return full_text, segs


def _write_minimal_gold_base(corpus_dir: Path, n_rows: int = 4) -> dict[str, str]:
    corpus_dir.mkdir(parents=True, exist_ok=True)
    creators_df = pd.DataFrame(
        [
            {
                "author_id": "auth_hist_1",
                "unique_id": "hist_creator",
                "nickname": "Hist",
                "verified": False,
                "commerce_user": False,
                "tt_seller": False,
                "follower_count": 50000,
                "follower_tier": "micro",
                "heart_count": 100000,
                "lifetime_video_count": n_rows,
                "sample_video_count": n_rows,
                "median_play_count": 25000.0,
                "median_engagement_rate": 0.04,
                "median_duration_sec": 40.0,
                "avg_videos_per_week": 2.0,
            }
        ]
    )
    rows = []
    for idx in range(n_rows):
        rows.append(
            {
                "video_id": f"hist_vid_{idx}",
                "author_id": "auth_hist_1",
                "author_handle": "hist_creator",
                "author_nickname": "Hist",
                "follower_count": 50000,
                "follower_tier": "micro",
                "create_time": "2025-02-01T10:00:00+00:00",
                "caption": "Phở bò truyền thống Sài Gòn",
                "hashtags": ["phobo"],
                "duration_sec": 40,
                "duration_bucket": "short_15_45s",
                "play_count": 25000,
                "digg_count": 900,
                "comment_count": 20,
                "share_count": 10,
                "collect_count": 30,
                "engagement_rate": 0.0384,
                "viral_multiplier": 1.0,
                "is_ad": False,
                "is_ec_video": False,
                "poi_id": "",
                "poi_name": "",
                "poi_address": "",
                "poi_city": "",
                "poi_category_tiny": "",
                "city_norm": "hồ chí minh",
                "district_norm": "quận 1",
                "region": "south",
                "video_format": "Review quán ăn",
                "food_category": "Món nước & Sợi",
                "dishes": ["phở bò"],
                "occasions": [],
                "price_tier": "budget",
                "has_transcript": True,
                "transcript": "Phở bò truyền thống nước dùng đậm đà ở Quận 1 Sài Gòn.",
                "transcript_char_len": 56,
                "word_count": 12,
                "word_per_second": 2.5,
                "hook_text": "Phở bò truyền thống",
                "body_beats": ["Nước dùng đậm đà ở Quận 1."],
                "cta_text": "Ghé thử nhé.",
                "hook_word_count": 4,
                "hook_has_price": False,
                "hook_has_location": False,
                "hook_has_question": False,
                "cta_type": "visit",
                "rag_document": "Phở bò truyền thống Sài Gòn. Nước dùng đậm đà ở Quận 1.",
                "source_platform": "tiktok",
                "snapshot_date": "2026-11-18",
            }
        )
    videos_df = pd.DataFrame(rows)
    creators_path = corpus_dir / "dim_creators.parquet"
    videos_path = corpus_dir / "fact_videos.parquet"
    pq.write_table(pa.Table.from_pandas(creators_df, preserve_index=False), creators_path)
    pq.write_table(pa.Table.from_pandas(videos_df, preserve_index=False), videos_path)

    files_meta = []
    hashes: dict[str, str] = {}
    for fname, df_cur in (("dim_creators.parquet", creators_df), ("fact_videos.parquet", videos_df)):
        p = corpus_dir / fname
        sha = hashlib.sha256(p.read_bytes()).hexdigest()
        hashes[fname] = sha
        files_meta.append(
            CorpusFileChecksum(
                filename=fname,
                rows=len(df_cur),
                columns=len(df_cur.columns),
                sha256=sha,
                size_bytes=p.stat().st_size,
            )
        )
    manifest = CorpusManifest(
        snapshot_id="base_hist_test_v1",
        created_at=datetime.now(UTC).isoformat(),
        date_window_start="2025-02-01",
        date_window_end="2025-03-01",
        total_creators=1,
        total_videos=n_rows,
        transcribed_videos=n_rows,
        poi_tagged_videos=0,
        ec_tagged_videos=0,
        files=files_meta,
        caveats=["Minimal synthetic test base corpus."],
    )
    m_path = corpus_dir / "manifest.json"
    m_path.write_text(json.dumps(manifest.model_dump(), ensure_ascii=False, indent=2), encoding="utf-8")
    hashes["manifest.json"] = hashlib.sha256(m_path.read_bytes()).hexdigest()
    return hashes


def test_bounded_asr_enforces_10_videos_20_minutes_and_skips_missing_audio(tmp_path: Path) -> None:
    batch_dir = tmp_path / "batch"
    audio_dir = batch_dir / "audio_64k"
    audio_dir.mkdir(parents=True)

    records: list[RawIncrementalVideoRecord] = []
    # 12 records: v0 missing audio; v1..v11 have audio (each 150s = 2.5m => 8 fit in 20m, cap 10 or 20m)
    for idx in range(12):
        vid = f"fresh_{idx:02d}"
        rel_audio: str | None = None
        if idx > 0:
            rel_audio = f"audio_64k/{vid}.mp3"
            (batch_dir / rel_audio).write_bytes(b"FAKE-64K-MP3-BYTES")
        records.append(
            RawIncrementalVideoRecord(
                video_id=vid,
                author_id="a1",
                author_handle="creator_fresh",
                create_time="2026-11-15T10:00:00+00:00",
                caption=f"Món ngon {vid}",
                duration_sec=150,  # 2.5 min each -> max 8 fit within 20.0 min
                play_count=1000,
                audio_path=rel_audio,
            )
        )

    engine = _StubCpuAsrEngine()
    runner = BoundedCpuAsrRunner(engine=engine, max_videos=10, max_audio_minutes=20.0)
    updated_records, receipt = runner.run(records=records, batch_dir=batch_dir)

    # 8 * 2.5 = 20.0 min exact ceiling; 9th would be 22.5 > 20.0
    assert receipt.transcribed_count == 8
    assert receipt.transcribed_count <= 10
    assert receipt.accumulated_audio_minutes <= 20.0
    assert receipt.skipped_no_audio_count == 1
    assert receipt.skipped_asr_ceiling_count == 3
    assert receipt.real_time_factor >= 0.0
    assert receipt.peak_rss_mib > 0.0
    # Missing audio keeps transcript empty
    assert updated_records[0].transcript == ""
    assert updated_records[0].whisper_segments == []
    # Transcribed items have valid segments
    for rec in updated_records[1:9]:
        assert rec.transcript != ""
        assert len(rec.whisper_segments) == 2
        for seg in rec.whisper_segments:
            assert 0.0 <= seg.start_sec < seg.end_sec


def test_faster_whisper_engine_fails_closed_when_missing(monkeypatch: pytest.MonkeyPatch) -> None:
    import builtins

    real_import = builtins.__import__

    def _blocked_import(name: str, *args: Any, **kwargs: Any) -> Any:
        if name == "faster_whisper":
            raise ImportError("No module named 'faster_whisper'")
        return real_import(name, *args, **kwargs)

    monkeypatch.setattr(builtins, "__import__", _blocked_import)
    with pytest.raises(IndexNotReadyError, match="faster-whisper"):
        FasterWhisperCpuAsrEngine()


def test_dry_run_fixture_pilot_end_to_end_collect_asr_ingest_search_and_50_50_split(
    tmp_path: Path,
) -> None:
    base_corpus = tmp_path / "base_gold"
    before_hashes = _write_minimal_gold_base(base_corpus, n_rows=4)

    now = datetime(2026, 11, 20, 9, 0, 0, tzinfo=UTC)
    dishes = [
        "bánh xèo giòn rụm miền Tây Quận 4",
        "hủ tiếu sa tế nai cay nồng Quận 5",
        "tàu hũ nóng đường gừng Gò Vấp",
        "gà nướng cơm lam Tây Nguyên Thủ Đức",
        "bún riêu cua đồng tóp mỡ Hà Nội",
        "lẩu mắm miền Tây cá linh Bình Thạnh",
    ]
    fixture_rows: list[dict[str, Any]] = []
    # Include 1 historical protected video that must be skipped, plus 6 fresh videos
    fixture_rows.append(
        {
            "video_id": "hist_vid_0",
            "author_id": "auth_hist_1",
            "author_handle": "hist_creator",
            "create_time": (now - timedelta(days=2)).isoformat(),
            "duration_sec": 45,
            "caption": "Historical must skip",
            "audio_fixture_payload": "MP3-HIST",
            "comments": [],
        }
    )
    for idx, dish in enumerate(dishes):
        vid = f"fresh_live_{idx + 1:02d}"
        fixture_rows.append(
            {
                "video_id": vid,
                "author_id": f"auth_new_{idx}",
                "author_handle": f"creator_new_{idx}",
                "author_nickname": f"Creator {idx}",
                "follower_count": 20000,
                "create_time": (now - timedelta(days=3 + idx)).isoformat(),
                "caption": f"Review {dish} #ancungtiktok",
                "hashtags": ["ancungtiktok"],
                "duration_sec": 42,
                "play_count": 30000 + idx * 1000,
                "digg_count": 1200,
                "comment_count": 1,
                "share_count": 40,
                "collect_count": 80,
                "audio_fixture_payload": f"FAKE-MP3-{vid}",
                "transcript": "",  # Initially empty; ASR stage must transcribe from audio
                "comments": [
                    {
                        "comment_id": f"{vid}_c1",
                        "author_handle": "diner_1",
                        "text": f"Quán {dish} ngon và giá hợp lý",
                        "like_count": 4,
                    }
                ],
            }
        )

    fixture_path = tmp_path / "m3_3_fixture.jsonl"
    fixture_path.write_text(
        "\n".join(json.dumps(r, ensure_ascii=False) for r in fixture_rows) + "\n",
        encoding="utf-8",
    )

    work_dir = tmp_path / "m3_3_run"
    cfg = M33PilotConfig(
        mode="dry_run_fixture",
        base_corpus_dir=base_corpus,
        batch_dir=work_dir / "raw_batch",
        output_gold_dir=work_dir / "gold_m3_3_pilot",
        output_bm25_dir=work_dir / "bm25_m3_3_pilot",
        receipt_path=work_dir / "m3_3_pilot_receipt.json",
        inspection_sheet_path=work_dir / "sample_inspection_sheet.jsonl",
        fixture_path=fixture_path,
        as_of_utc=now,
    )
    receipt = run_m3_3_pilot(cfg, asr_engine=_StubCpuAsrEngine())

    # Base historical corpus bytes preserved 100%
    for fname, sha in before_hashes.items():
        assert hashlib.sha256((base_corpus / fname).read_bytes()).hexdigest() == sha

    assert receipt.pilot_status == "FIXTURE_DRY_RUN_ONLY"
    assert receipt.is_synthetic_fixture is True
    assert receipt.collection.succeeded_count == 6
    assert receipt.collection.skipped_count == 1
    assert receipt.asr is not None
    assert receipt.asr.transcribed_count == 6
    assert receipt.asr.transcribed_count <= 10
    assert receipt.searchability.searchable_fresh_transcribed_count >= 5
    assert set(receipt.searchability.matched_fresh_video_ids).issubset(
        {f"fresh_live_{i:02d}" for i in range(1, 7)}
    )
    assert receipt.resources.total_disk_bytes > 0
    assert receipt.resources.peak_rss_mib > 0.0

    # Verify 50/50 equal inspection assignment for K and N
    sheet = [
        json.loads(line)
        for line in cfg.inspection_sheet_path.read_text(encoding="utf-8").splitlines()
        if line.strip()
    ]
    assert len(sheet) == 6
    k_rows = [r for r in sheet if r["assigned_reviewer"] == "K"]
    n_rows = [r for r in sheet if r["assigned_reviewer"] == "N"]
    assert len(k_rows) == 3 and len(n_rows) == 3
    assert all(r["human_verified"] is False for r in sheet)


def test_live_pilot_fails_closed_blocked_when_tools_or_token_missing(
    tmp_path: Path,
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    base_corpus = tmp_path / "base_gold"
    _write_minimal_gold_base(base_corpus, n_rows=2)

    monkeypatch.delenv("MS_TOKEN", raising=False)
    monkeypatch.setattr("shutil.which", lambda _cmd: None)

    work_dir = tmp_path / "m3_3_live_blocked"
    cfg = M33PilotConfig(
        mode="live_pilot",
        allow_live_network=True,
        creators=["ansapsaigon"],
        base_corpus_dir=base_corpus,
        batch_dir=work_dir / "raw_batch",
        output_gold_dir=work_dir / "gold_m3_3_pilot",
        output_bm25_dir=work_dir / "bm25_m3_3_pilot",
        receipt_path=work_dir / "m3_3_pilot_receipt.json",
        inspection_sheet_path=work_dir / "sample_inspection_sheet.jsonl",
    )
    receipt = run_m3_3_pilot(cfg)

    assert receipt.pilot_status == "BLOCKED"
    assert receipt.is_synthetic_fixture is False
    assert receipt.blocker_reasons
    assert any("MS_TOKEN" in r or "yt-dlp" in r for r in receipt.blocker_reasons)
    assert cfg.receipt_path.is_file()
