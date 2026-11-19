"""Independent M3.1 peer reproduction by Trần Đình Khương (K) on real Gold snapshot 20261118_taxonomy_fix_v1."""
from __future__ import annotations

import hashlib
import json
import os
import platform
import subprocess
import sys
import tempfile
import time
from datetime import UTC, datetime
from pathlib import Path

import pandas as pd
import pyarrow.parquet as pq

from packages.analytics import load_verified_corpus
from packages.data_contracts.multimodal import (
    RawCommentInput,
    RawIncrementalVideoRecord,
    RawWhisperSegment,
)
from pipelines.ingest_incremental_to_gold import ingest_incremental_batch_to_gold

ROOT = Path(__file__).resolve().parents[5]
OUT = Path(__file__).resolve().parent


def _dir_hashes(folder: Path) -> dict[str, str]:
    return {
        p.name: hashlib.sha256(p.read_bytes()).hexdigest()
        for p in sorted(folder.iterdir())
        if p.is_file()
    }


def _write_jsonl(path: Path, records: list[RawIncrementalVideoRecord]) -> Path:
    lines = [rec.model_dump_json() for rec in records]
    path.write_text("\n".join(lines) + ("\n" if lines else ""), encoding="utf-8")
    return path


def main() -> int:
    t0 = time.perf_counter()
    base_dir = ROOT / "data/corpus/20261118_taxonomy_fix_v1"
    base_before = _dir_hashes(base_dir)

    # Pick one real historical video row that has NaN nullable fields (e.g. poi_name is null) and ndarray hashtags
    _, base_creators, base_videos = load_verified_corpus(base_dir)
    nan_candidates = base_videos[base_videos["poi_name"].isna() & (base_videos["has_transcript"] == False)]  # noqa: E712
    assert len(nan_candidates) > 0
    sample_hist = nan_candidates.iloc[0]
    hist_vid = str(sample_hist["video_id"])
    hist_aid = str(sample_hist["author_id"])
    hist_handle = str(sample_hist["author_handle"])
    hist_play_count = int(sample_hist["play_count"])

    steps_summary: dict[str, object] = {}

    with tempfile.TemporaryDirectory(prefix="m3_1_khuong_repro_") as tmp:
        tmp_root = Path(tmp)

        # 1. Batch A: 1 new creator + 1 new video with whisper + comments
        batch_a = _write_jsonl(
            tmp_root / "batch_a.jsonl",
            [
                RawIncrementalVideoRecord(
                    video_id="inc_k_v1",
                    author_id="inc_k_author_1",
                    author_handle="khuong_fnb_test",
                    author_nickname="Khương Review",
                    follower_count=15000,
                    create_time="2026-10-05T11:30:00+00:00",
                    caption="Phở bò tái lăn Quận 3 nước dùng đậm đà #phobo #quan3",
                    hashtags=["#phobo", "#quan3"],
                    duration_sec=35,
                    play_count=25000,
                    digg_count=1800,
                    comment_count=45,
                    share_count=30,
                    collect_count=120,
                    poi_name="Phở Bò Quận 3",
                    poi_city="Ho Chi Minh City",
                    poi_address="Quận 3, TP.HCM",
                    transcript="Nước dùng phở bò rất thơm ngọt, giá 55 cành hơi cao nhưng quán sạch sẽ.",
                    whisper_segments=[
                        RawWhisperSegment(
                            start_sec=0.0,
                            end_sec=4.5,
                            text="Nước dùng phở bò rất thơm ngọt, giá 55 cành hơi cao nhưng quán sạch sẽ.",
                        )
                    ],
                    pitch_std=24.5,
                    energy_cv=0.31,
                    comments=[
                        RawCommentInput(
                            comment_id="c_k_1",
                            video_id="inc_k_v1",
                            text="Phở ngon lắm ạ, nước lèo đậm đà giá hợp lý!",
                            author_id="viewer_1",
                            digg_count=12,
                            reply_count=1,
                            create_time="2026-10-05T12:00:00+00:00",
                        )
                    ],
                )
            ],
        )
        snap_a = tmp_root / "snap_a"
        m_a = ingest_incremental_batch_to_gold(base_dir, batch_a, snap_a)
        assert m_a.total_videos == 70997 and m_a.total_creators == 265
        assert m_a.date_window_end == "2026-10-05"
        snap_a_hashes = _dir_hashes(snap_a)
        steps_summary["batch_a"] = {
            "total_videos": m_a.total_videos,
            "total_creators": m_a.total_creators,
            "date_window_end": m_a.date_window_end,
        }

        # 2. Batch B (missing modalities: metadata-only new video, 0 whisper, 0 transcript, 0 comments)
        batch_b = _write_jsonl(
            tmp_root / "batch_b_missing_modalities.jsonl",
            [
                RawIncrementalVideoRecord(
                    video_id="inc_k_v2_meta_only",
                    author_id=hist_aid,
                    author_handle=hist_handle,
                    create_time="2026-10-12T08:00:00+00:00",
                    caption="Cà phê muối buổi sáng Hà Nội",
                    duration_sec=22,
                    play_count=8400,
                )
            ],
        )
        snap_b = tmp_root / "snap_b"
        m_b = ingest_incremental_batch_to_gold(snap_a, batch_b, snap_b)
        assert m_b.total_videos == 70998 and m_b.total_creators == 265
        assert m_b.date_window_end == "2026-10-12"
        assert _dir_hashes(snap_a) == snap_a_hashes, "snap_a mutated during Batch B!"

        # Also test missing-modality batch & empty batch directly on base_dir to verify 0-row typed Arrow schemas
        empty_jsonl = tmp_root / "empty.jsonl"
        empty_jsonl.write_text("", encoding="utf-8")

        snap_zero_mm = tmp_root / "snap_zero_multimodal"
        ingest_incremental_batch_to_gold(base_dir, batch_b, snap_zero_mm)
        expected_mm_rows = {
            "fact_voice_segments.parquet": 0,
            "fact_comments.parquet": 0,
            "fact_absa_reviews.parquet": 1,
        }
        zero_mm_schemas: dict[str, object] = {}
        for mm_name, exp_rows in expected_mm_rows.items():
            tbl = pq.read_table(snap_zero_mm / mm_name)
            assert tbl.num_rows == exp_rows, (mm_name, tbl.num_rows, exp_rows)
            null_typed = [f.name for f in tbl.schema if str(f.type) == "null"]
            assert not null_typed, (mm_name, null_typed)
            zero_mm_schemas[mm_name] = {"rows": tbl.num_rows, "schema": {f.name: str(f.type) for f in tbl.schema}}

        snap_zero_all = tmp_root / "snap_zero_all_three"
        ingest_incremental_batch_to_gold(base_dir, empty_jsonl, snap_zero_all)
        for mm_name in ("fact_voice_segments.parquet", "fact_comments.parquet", "fact_absa_reviews.parquet"):
            tbl0 = pq.read_table(snap_zero_all / mm_name)
            assert tbl0.num_rows == 0, (mm_name, tbl0.num_rows)
            null_typed0 = [f.name for f in tbl0.schema if str(f.type) == "null"]
            assert not null_typed0, (mm_name, null_typed0)
        steps_summary["missing_modalities_zero_row_schemas"] = zero_mm_schemas

        # 3. Replay Batch B with update_existing=False -> exact deduplication, window unchanged
        snap_replay = tmp_root / "snap_replay"
        m_replay = ingest_incremental_batch_to_gold(snap_b, batch_b, snap_replay, update_existing=False)
        assert m_replay.total_videos == 70998 and m_replay.total_creators == 265
        assert m_replay.date_window_end == "2026-10-12"
        steps_summary["replay_b"] = {
            "total_videos": m_replay.total_videos,
            "date_window_end": m_replay.date_window_end,
        }

        # 4. Empty batch -> preserves date_window_end ("2026-10-12"), does NOT advance to today (2026-11-18)
        snap_empty = tmp_root / "snap_empty"
        m_empty = ingest_incremental_batch_to_gold(snap_replay, empty_jsonl, snap_empty)
        assert m_empty.total_videos == 70998
        assert m_empty.date_window_end == "2026-10-12", m_empty.date_window_end
        steps_summary["empty_batch"] = {
            "total_videos": m_empty.total_videos,
            "date_window_end": m_empty.date_window_end,
        }

        # 5. Enrichment (update_existing=True) on BOTH real historical NaN/ndarray row AND inc_k_v1
        enrich_jsonl = _write_jsonl(
            tmp_root / "enrich.jsonl",
            [
                RawIncrementalVideoRecord(
                    video_id=hist_vid,
                    author_id=hist_aid,
                    author_handle=hist_handle,
                    create_time="2024-06-01T00:00:00+00:00",
                    transcript="Bổ sung transcript mới cho video lịch sử có trường NaN và ndarray.",
                    whisper_segments=[
                        RawWhisperSegment(
                            start_sec=0.0,
                            end_sec=3.2,
                            text="Bổ sung transcript mới cho video lịch sử có trường NaN và ndarray.",
                        )
                    ],
                    comments=[
                        RawCommentInput(
                            comment_id="c_hist_enrich_1",
                            video_id=hist_vid,
                            text="Quán phục vụ nhiệt tình, đồ ăn ngon sạch sẽ.",
                            author_id="viewer_hist_1",
                        )
                    ],
                ),
                RawIncrementalVideoRecord(
                    video_id="inc_k_v1",
                    author_id="inc_k_author_1",
                    author_handle="khuong_fnb_test",
                    create_time="2026-10-05T11:30:00+00:00",
                    comments=[
                        RawCommentInput(
                            comment_id="c_k_2",
                            video_id="inc_k_v1",
                            text="Giá hơi đắt nhưng nước phở ngon.",
                            author_id="viewer_2",
                        )
                    ],
                ),
            ],
        )
        snap_enrich = tmp_root / "snap_enrich"
        m_enrich = ingest_incremental_batch_to_gold(snap_empty, enrich_jsonl, snap_enrich, update_existing=True)
        assert m_enrich.total_videos == 70998
        assert m_enrich.transcribed_videos == m_empty.transcribed_videos + 1
        _, _, v_enrich = load_verified_corpus(snap_enrich)
        enriched_hist_row = v_enrich[v_enrich["video_id"] == hist_vid].iloc[0]
        assert int(enriched_hist_row["play_count"]) == hist_play_count
        assert bool(enriched_hist_row["has_transcript"]) is True
        comments_df = pd.read_parquet(snap_enrich / "fact_comments.parquet")
        assert set(comments_df[comments_df["video_id"] == "inc_k_v1"]["comment_id"]) == {"c_k_1", "c_k_2"}
        steps_summary["enrichment_real_nan_row"] = {
            "historical_video_id": hist_vid,
            "preserved_play_count": int(enriched_hist_row["play_count"]),
            "transcribed_videos_delta": m_enrich.transcribed_videos - m_empty.transcribed_videos,
            "merged_inc_k_v1_comments": sorted(comments_df[comments_df["video_id"] == "inc_k_v1"]["comment_id"].tolist()),
        }

        # 6. Collision rejection -> FileExistsError, zero byte mutation on snap_enrich
        enrich_hashes_before = _dir_hashes(snap_enrich)
        collision_raised = False
        try:
            ingest_incremental_batch_to_gold(snap_empty, empty_jsonl, snap_enrich)
        except FileExistsError:
            collision_raised = True
        assert collision_raised, "Expected FileExistsError on existing snapshot directory!"
        assert _dir_hashes(snap_enrich) == enrich_hashes_before

        # 7. Interrupted / corrupt mid-batch JSONL -> zero partial target, no leftover staging/lock, clean retry
        bad_jsonl = tmp_root / "interrupted.jsonl"
        bad_jsonl.write_text(
            RawIncrementalVideoRecord(
                video_id="inc_k_v3",
                author_id=hist_aid,
                author_handle=hist_handle,
                create_time="2026-10-15T09:00:00+00:00",
                caption="Valid first line",
                duration_sec=25,
                play_count=3000,
            ).model_dump_json()
            + "\n{corrupt_second_line_json\n",
            encoding="utf-8",
        )
        snap_retry = tmp_root / "snap_retry"
        failed_cleanly = False
        try:
            ingest_incremental_batch_to_gold(snap_enrich, bad_jsonl, snap_retry)
        except Exception:
            failed_cleanly = True
        assert failed_cleanly
        assert not snap_retry.exists(), "Partial output directory must not exist after failed ingest!"
        leftovers = [p.name for p in tmp_root.iterdir() if ".staging" in p.name or ".lock" in p.name]
        assert not leftovers, leftovers

        # Fix JSONL and retry into same target path snap_retry
        good_retry_jsonl = _write_jsonl(
            tmp_root / "good_retry.jsonl",
            [
                RawIncrementalVideoRecord(
                    video_id="inc_k_v3",
                    author_id=hist_aid,
                    author_handle=hist_handle,
                    create_time="2026-10-15T09:00:00+00:00",
                    caption="Valid retry line",
                    duration_sec=25,
                    play_count=3000,
                )
            ],
        )
        m_retry = ingest_incremental_batch_to_gold(snap_enrich, good_retry_jsonl, snap_retry)
        assert m_retry.total_videos == 70999
        assert m_retry.date_window_end == "2026-10-15"
        steps_summary["interrupted_and_retried"] = {
            "partial_target_after_abort": False,
            "leftover_staging_or_locks": [],
            "retried_total_videos": m_retry.total_videos,
            "retried_date_window_end": m_retry.date_window_end,
        }

    # Verify 100% byte preservation of real base snapshot 20261118_taxonomy_fix_v1
    base_after = _dir_hashes(base_dir)
    assert base_before == base_after, "Base Gold snapshot 20261118_taxonomy_fix_v1 bytes changed!"

    receipt = {
        "task_id": "M3.1",
        "reviewer": "Trần Đình Khương (K)",
        "primary_owner": "Nguyễn Việt Nguyên (N)",
        "verdict": "APPROVED — M3.1 COMPLETE",
        "checked_at": datetime.now(UTC).isoformat(),
        "head": subprocess.check_output(["git", "rev-parse", "HEAD"], cwd=ROOT, text=True).strip(),
        "platform": platform.platform(),
        "python": sys.version,
        "cpu_count": os.cpu_count(),
        "elapsed_seconds": round(time.perf_counter() - t0, 3),
        "base_snapshot_id": "20261118_taxonomy_fix_v1",
        "base_hashes_before": base_before,
        "base_hashes_after": base_after,
        "base_bytes_100_percent_identical": base_before == base_after,
        "steps_verified": steps_summary,
    }
    out_path = OUT / "khuong_m3_1_reproduction.json"
    out_path.write_text(json.dumps(receipt, indent=2, ensure_ascii=False) + "\n", encoding="utf-8")
    print(f"PASS: M3.1 independent K reproduction succeeded in {receipt['elapsed_seconds']}s -> {out_path.name}")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
