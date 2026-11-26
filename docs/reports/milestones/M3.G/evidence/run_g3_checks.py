"""Deterministic Gate G3 (M3.G) data-readiness, immutability, and capacity verification probe."""
from __future__ import annotations

import hashlib
import json
import platform
import sys
import tempfile
import time
from datetime import UTC, datetime
from pathlib import Path
from typing import Any

import pyarrow.parquet as pq

ROOT = Path(__file__).resolve().parents[5]
if str(ROOT) not in sys.path:
    sys.path.insert(0, str(ROOT))

from packages.analytics import load_verified_corpus  # noqa: E402
from packages.data_contracts.multimodal import (  # noqa: E402
    RawCommentInput,
    RawIncrementalVideoRecord,
)
from packages.data_contracts.query import RetrievalRequest  # noqa: E402
from packages.retrieval import HybridRetrievalService  # noqa: E402
from pipelines.ingest_incremental_to_gold import ingest_incremental_batch_to_gold  # noqa: E402


def _sha256_file(path: Path) -> str:
    hasher = hashlib.sha256()
    with path.open("rb") as fp:
        for chunk in iter(lambda: fp.read(1024 * 1024), b""):
            hasher.update(chunk)
    return hasher.hexdigest()


def verify_prerequisites_and_upstream_tasks(repo_root: Path) -> dict[str, Any]:
    gate_receipt_paths = {
        "G0": repo_root / "docs/reports/milestones/M0.G/evidence/owner-gate-decision-receipt.json",
        "G1": repo_root / "docs/reports/milestones/M1.G/evidence/g1-gate-decision-receipt.json",
        "G2": repo_root / "docs/reports/milestones/M2.G/evidence/g2-gate-decision-receipt.json",
    }
    prerequisite_gates: dict[str, str] = {}
    for gate_id, r_path in gate_receipt_paths.items():
        if not r_path.is_file():
            raise ValueError(f"Missing prerequisite gate receipt for {gate_id}: {r_path}")
        payload = json.loads(r_path.read_text(encoding="utf-8"))
        decision = str(payload.get("decision") or "")
        if decision != "PASS":
            raise ValueError(
                f"Prerequisite gate {gate_id} must have decision=='PASS', got {decision!r}"
            )
        prerequisite_gates[gate_id] = decision

    m3_1_signoff = repo_root / "docs/reports/milestones/M3.1/evidence/khuong_m3_1_reproduction.json"
    m3_2_signoff = repo_root / "docs/reports/milestones/M3.2/evidence/nguyen_signoff_receipt.json"
    if not m3_1_signoff.is_file() or not m3_2_signoff.is_file():
        raise ValueError("Missing M3.1 or M3.2 reciprocal sign-off receipt")
    m3_1_payload = json.loads(m3_1_signoff.read_text(encoding="utf-8"))
    m3_2_payload = json.loads(m3_2_signoff.read_text(encoding="utf-8"))
    if "APPROVED" not in str(m3_1_payload.get("verdict") or ""):
        raise ValueError(
            f"M3.1 peer reproduction receipt not APPROVED: {m3_1_payload.get('verdict')!r}"
        )
    if (
        str(m3_2_payload.get("verdict") or "") != "APPROVED"
        or int(m3_2_payload.get("blocking_issues", 1)) != 0
    ):
        raise ValueError("M3.2 peer sign-off receipt not APPROVED with 0 blocking issues")

    upstream_tasks: dict[str, str] = {}
    for task_id in ("M3.1", "M3.2", "M3.3"):
        readme_path = repo_root / f"docs/reports/milestones/{task_id}/README.md"
        if not readme_path.is_file():
            raise ValueError(f"Missing milestone report for {task_id}: {readme_path}")
        text = readme_path.read_text(encoding="utf-8")
        if "- Status: COMPLETE" not in text:
            raise ValueError(f"Upstream task {task_id} is not marked '- Status: COMPLETE'")
        upstream_tasks[task_id] = "COMPLETE"

    return {
        "prerequisite_gates": prerequisite_gates,
        "upstream_tasks": upstream_tasks,
    }


def verify_snapshot_checksums(snapshot_dir: Path) -> dict[str, Any]:
    manifest_path = snapshot_dir / "manifest.json"
    if not manifest_path.is_file():
        raise ValueError(f"Missing snapshot manifest: {manifest_path}")
    manifest = json.loads(manifest_path.read_text(encoding="utf-8"))
    file_hashes: dict[str, str] = {}
    row_counts: dict[str, int] = {}
    for entry in manifest.get("files", []):
        fname = str(entry["filename"])
        fpath = snapshot_dir / fname
        if not fpath.is_file():
            raise ValueError(f"Missing Parquet table {fname} in {snapshot_dir}")
        actual_size = fpath.stat().st_size
        actual_sha = _sha256_file(fpath)
        if actual_size != int(entry["size_bytes"]) or actual_sha != str(entry["sha256"]):
            raise ValueError(
                f"Checksum/size mismatch for {fname}: expected ({entry['size_bytes']}, {entry['sha256']}), "
                f"got ({actual_size}, {actual_sha})"
            )
        table_meta = pq.read_metadata(fpath)
        if table_meta.num_rows != int(entry["rows"]):
            raise ValueError(
                f"Row count mismatch for {fname}: expected {entry['rows']}, got {table_meta.num_rows}"
            )
        file_hashes[fname] = actual_sha
        row_counts[fname] = int(table_meta.num_rows)
    return {
        "snapshot_id": str(manifest["snapshot_id"]),
        "manifest_sha256": _sha256_file(manifest_path),
        "parent_snapshot_id": manifest.get("parent_snapshot_id"),
        "parent_manifest_sha256": manifest.get("parent_manifest_sha256"),
        "transcribed_videos": int(manifest.get("transcribed_videos", 0)),
        "file_sha256": file_hashes,
        "row_counts": row_counts,
    }


def verify_raw_pilot_media(batch_dir: Path) -> dict[str, Any]:
    manifest_path = batch_dir / "crawl_manifest.json"
    if not manifest_path.is_file():
        raise ValueError(f"Missing crawl_manifest.json in {batch_dir}")
    manifest = json.loads(manifest_path.read_text(encoding="utf-8"))
    verified_mp3_count = 0
    total_mp3_bytes = 0
    no_audio_ids: list[str] = []
    mp3_hashes: dict[str, str] = {}
    verified_paths: set[Path] = set()

    for item in manifest.get("items", []):
        if item.get("status") != "succeeded":
            continue
        vid = str(item["video_id"])
        receipt = item.get("audio_receipt") or {}
        r_status = str(receipt.get("status") or "")
        if r_status == "converted_64k_mp3":
            rel_audio = str(receipt.get("audio_path") or "")
            if not rel_audio:
                raise ValueError(f"Missing audio_path for converted item {vid}")
            audio_file = (batch_dir / rel_audio).resolve()
            if not audio_file.is_file() or audio_file.stat().st_size <= 0:
                raise ValueError(f"Missing or empty mp3 file for {vid}: {rel_audio}")
            actual_bytes = audio_file.stat().st_size
            actual_sha = _sha256_file(audio_file)
            if actual_bytes != int(receipt["audio_bytes"]):
                raise ValueError(
                    f"Byte size mismatch for {vid}: expected {receipt['audio_bytes']}, got {actual_bytes}"
                )
            if actual_sha != str(receipt["audio_sha256"]):
                raise ValueError(
                    f"SHA-256 mismatch for {vid}: expected {receipt['audio_sha256']}, got {actual_sha}"
                )
            verified_mp3_count += 1
            total_mp3_bytes += actual_bytes
            mp3_hashes[vid] = actual_sha
            verified_paths.add(audio_file)
        elif r_status in {"unavailable", "no_audio_stream"}:
            no_audio_ids.append(vid)
        else:
            raise ValueError(
                f"Unexpected audio_receipt status {r_status!r} on succeeded item {vid}"
            )

    audio_dir = batch_dir / "audio_64k"
    if audio_dir.is_dir():
        actual_mp3_files = {p.resolve() for p in audio_dir.glob("*.mp3") if p.is_file()}
        untracked = actual_mp3_files - verified_paths
        if untracked:
            raise ValueError(
                f"Untracked mp3 files in audio_64k: {sorted(p.name for p in untracked)}"
            )

    if verified_mp3_count != int(manifest.get("converted_audio_count", 0)):
        raise ValueError(
            f"Verified mp3 count {verified_mp3_count} != manifest converted_audio_count {manifest.get('converted_audio_count')}"
        )
    return {
        "crawl_manifest_sha256": _sha256_file(manifest_path),
        "verified_mp3_count": verified_mp3_count,
        "total_mp3_bytes": total_mp3_bytes,
        "no_audio_item_ids": no_audio_ids,
        "accumulated_audio_minutes": float(manifest.get("accumulated_audio_minutes", 0.0)),
        "mp3_sha256_by_video_id": mp3_hashes,
    }


def evaluate_inspection_and_domain_yield(
    sheet_path: Path,
    *,
    requested_candidates: int,
    expected_total: int | None = None,
    expected_video_ids: set[str] | None = None,
) -> dict[str, Any]:
    if not sheet_path.is_file():
        raise ValueError(f"Missing sample inspection sheet: {sheet_path}")
    lines = [ln for ln in sheet_path.read_text(encoding="utf-8").splitlines() if ln.strip()]
    if not lines:
        raise ValueError("Empty sample inspection sheet")

    seen_ids: set[str] = set()
    k_verified = 0
    n_verified = 0
    audio_bearing = 0
    pure_fnb_audio = 0
    mixed_ids: list[str] = []
    ood_ids: list[str] = []
    no_audio_ids: list[str] = []

    for ln in lines:
        row = json.loads(ln)
        vid = str(row["video_id"])
        if vid in seen_ids:
            raise ValueError(f"Duplicate video_id in inspection sheet: {vid}")
        seen_ids.add(vid)
        if not bool(row.get("human_verified")):
            raise ValueError(f"Inspection sheet contains unverified row: {vid}")
        rev = str(row.get("assigned_reviewer", ""))
        if rev == "K":
            k_verified += 1
        elif rev == "N":
            n_verified += 1
        else:
            raise ValueError(f"Unexpected assigned_reviewer {rev!r} on {vid}")

        has_audio = bool(row.get("has_audio"))
        notes_lower = str(row.get("reviewer_notes", "")).lower()
        if not has_audio:
            no_audio_ids.append(vid)
            continue

        audio_bearing += 1
        if "out_of_domain" in notes_lower:
            ood_ids.append(vid)
        elif "mixed_event" in notes_lower:
            mixed_ids.append(vid)
        else:
            pure_fnb_audio += 1

    total = len(lines)
    if expected_total is not None and total != expected_total:
        raise ValueError(
            f"Incomplete inspection sheet: got {total} rows, expected {expected_total}"
        )
    if k_verified != n_verified:
        raise ValueError(
            f"Imbalanced two-contributor verification split: K={k_verified}, N={n_verified}"
        )
    if expected_video_ids is not None and seen_ids != expected_video_ids:
        raise ValueError("Inspection sheet video_ids mismatch crawl_manifest succeeded IDs")
    capture_yield = round(total / requested_candidates, 4) if requested_candidates > 0 else 0.0
    audio_rate = round(audio_bearing / total, 4)
    pure_fnb_audio_rate = round(pure_fnb_audio / total, 4)
    effective_yield = (
        round(pure_fnb_audio / requested_candidates, 4) if requested_candidates > 0 else 0.0
    )
    return {
        "inspection_sheet_sha256": _sha256_file(sheet_path),
        "total_inspected": total,
        "k_verified_count": k_verified,
        "n_verified_count": n_verified,
        "audio_bearing_count": audio_bearing,
        "pure_fnb_audio_count": pure_fnb_audio,
        "mixed_domain_ids": mixed_ids,
        "no_audio_ids": no_audio_ids,
        "out_of_domain_ids": ood_ids,
        "capture_yield_rate": capture_yield,
        "audio_availability_rate": audio_rate,
        "pure_fnb_audio_rate_of_succeeded": pure_fnb_audio_rate,
        "pure_fnb_rate_of_audio_bearing": round(pure_fnb_audio / max(1, audio_bearing), 4),
        "effective_usable_fnb_audio_yield_per_candidate": effective_yield,
    }


def build_modality_readiness_matrix(
    *,
    audio_count: int,
    total_audio_minutes: float,
    pure_fnb_audio_count: int,
    human_verified_count: int,
    total_videos: int,
    collected_comments_count: int,
    commented_videos_count: int,
) -> dict[str, dict[str, Any]]:
    rounded_min = round(total_audio_minutes, 3)
    m4_1_ready = (
        audio_count >= 10
        and 0.0 < total_audio_minutes <= 60.0
        and pure_fnb_audio_count >= 10
        and human_verified_count == total_videos
    )
    m5_1_ready = collected_comments_count >= 150 and commented_videos_count >= 10
    m5_2_ready = collected_comments_count >= 150 and commented_videos_count >= 10
    return {
        "M4.1": {
            "status": "READY_UNBLOCKED" if m4_1_ready else "BLOCKED",
            "available_audio_files": audio_count,
            "available_pure_fnb_audio_files": pure_fnb_audio_count,
            "total_audio_minutes": rounded_min,
            "reason": (
                f"{audio_count} verified 64kbps mp3 files ({rounded_min} min <= 60.0 cap; {pure_fnb_audio_count} pure F&B) satisfy M4.1 audio & 2-person utterance slice requirements."
                if m4_1_ready
                else f"Insufficient verified pilot audio ({audio_count} files, {rounded_min} min) for M4.1."
            ),
        },
        "M4.2_audio_join": {
            "status": "GATED_ON_M4_1",
            "reason": "Lexical/flag study COMPLETE; optional fresh-audio prosody join awaits accepted M4.1 timestamps/prosody.",
        },
        "M5.1": {
            "status": "READY_UNBLOCKED" if m5_1_ready else "BLOCKED_PENDING_COMMENT_BACKFILL",
            "collected_comments_count": collected_comments_count,
            "commented_videos_count": commented_videos_count,
            "min_required_comments": 150,
            "min_required_videos": 10,
            "reason": (
                f"Real comment pool ({collected_comments_count} comments across {commented_videos_count} videos) meets >=150 comments & >=10 videos thresholds for video-disjoint evaluation."
                if m5_1_ready
                else f"Observed {collected_comments_count} comments across {commented_videos_count} videos; requires authorized TikTokApi comment-only backfill (update_existing=True) >= 150 real comments across >= 10 videos."
            ),
        },
        "M5.2": {
            "status": "READY_UNBLOCKED" if m5_2_ready else "BLOCKED_PENDING_COMMENT_BACKFILL",
            "collected_comments_count": collected_comments_count,
            "commented_videos_count": commented_videos_count,
            "min_required_comments": 150,
            "min_required_videos": 10,
            "reason": (
                f"Real viewer comments ({collected_comments_count} rows across {commented_videos_count} videos) satisfy >=10-video KOC-vs-viewer overlap evaluation."
                if m5_2_ready
                else f"Observed {collected_comments_count} viewer comments across {commented_videos_count} videos; requires authorized comment-only backfill (>=150 comments across >=10 pilot videos)."
            ),
        },
    }


def compute_capacity_and_budget_projections(
    *,
    pilot_receipt: dict[str, Any],
    domain_yield: dict[str, Any],
    verified_mp3_count: int | None = None,
    total_audio_minutes: float | None = None,
) -> dict[str, Any]:
    total_wall = float(pilot_receipt["resources"]["wall_seconds"])
    asr_wall = float(pilot_receipt["asr"]["wall_seconds"])
    asr_min = float(pilot_receipt["asr"]["accumulated_audio_minutes"])
    rtf = float(pilot_receipt["asr"]["real_time_factor"])
    succeeded = int(pilot_receipt["collection"]["succeeded_count"])
    target_mp3_files = (
        int(verified_mp3_count)
        if verified_mp3_count is not None
        else int(pilot_receipt["collection"]["converted_audio_count"])
    )
    full_pilot_audio_min = (
        round(float(total_audio_minutes), 3)
        if total_audio_minutes is not None
        else round(asr_min, 3)
    )

    ingest_index_sec = 7.0
    capture_io_sec = max(0.0, total_wall - asr_wall - ingest_index_sec)
    sec_per_video_capture = capture_io_sec / max(1, succeeded)
    asr_sec_per_audio_min = asr_wall / max(1e-6, asr_min)

    remaining_audio_min = round(max(0.0, full_pilot_audio_min - asr_min), 3)
    full_m4_1_asr_sec = round(full_pilot_audio_min * 60.0 * rtf, 2)
    incremental_m4_1_asr_sec = round(remaining_audio_min * 60.0 * rtf, 2)

    comment_backfill_base_sec = succeeded * 12.0
    comment_backfill_retry_buffered_sec = round(comment_backfill_base_sec * 1.4 + ingest_index_sec, 1)

    second_batch_capture_sec = round(succeeded * sec_per_video_capture * 1.25, 1)
    second_batch_asr_sec = full_m4_1_asr_sec
    second_batch_total_sec = round(
        second_batch_capture_sec + second_batch_asr_sec + ingest_index_sec, 1
    )
    pure_fnb_count = int(domain_yield["pure_fnb_audio_count"])

    return {
        "observed_rates": {
            "capture_io_seconds_total": round(capture_io_sec, 3),
            "capture_io_seconds_per_succeeded_video": round(sec_per_video_capture, 3),
            "asr_real_time_factor": rtf,
            "asr_wall_seconds_per_audio_minute": round(asr_sec_per_audio_min, 3),
            "fixed_dual_sink_and_bm25_seconds": ingest_index_sec,
            "batch_raw_bytes_per_video": round(
                float(pilot_receipt["resources"]["batch_disk_bytes"]) / max(1, succeeded), 1
            ),
            "snapshot_plus_bm25_bytes_per_publish": int(
                pilot_receipt["resources"]["gold_snapshot_disk_bytes"]
                + pilot_receipt["resources"]["bm25_index_disk_bytes"]
            ),
            "effective_usable_fnb_audio_yield_per_candidate": domain_yield[
                "effective_usable_fnb_audio_yield_per_candidate"
            ],
        },
        "m4_1_full_pilot_audio_projection": {
            "target_mp3_files": target_mp3_files,
            "pure_fnb_mp3_files": pure_fnb_count,
            "total_audio_minutes": full_pilot_audio_min,
            "remaining_untranscribed_minutes": remaining_audio_min,
            "projected_total_asr_wall_seconds": full_m4_1_asr_sec,
            "projected_incremental_asr_wall_seconds": incremental_m4_1_asr_sec,
            "projected_cpu_hours": round(full_m4_1_asr_sec / 3600.0, 4),
            "m4_1_cpu_hour_ceiling": 4.0,
            "projected_peak_rss_mib": float(pilot_receipt["resources"]["peak_rss_mib"]),
            "m4_1_ram_ceiling_mib": 8192.0,
        },
        "annotation_effort_estimates_person_minutes": {
            "m3_3_n_15_videos_reported_minutes": 15.0,
            "m3_3_k_15_videos_reported_minutes": 18.0,
            "m3_3_30_video_inspection_completed": 33.0,
            "m4_1_60_utterance_two_person_reference_review": 90,
            "m5_1_300_comment_double_annotation_plus_adjudication": 150,
            "m5_2_180_unit_aspect_span_double_annotation": 180,
        },
        "budget_scenarios": {
            "option_1_authorized_comment_only_backfill": {
                "selected": True,
                "new_videos_authorized": 0,
                "target_existing_video_ids": succeeded,
                "max_comments_per_video": 50,
                "max_comments_total": 1000,
                "max_audio_minutes": 0.0,
                "session_deadline_seconds": 3600.0,
                "projected_wall_seconds_with_retry_buffer": comment_backfill_retry_buffered_sec,
                "projected_new_snapshot_disk_mib": 56.5,
                "authorized_cost_usd": 0.0,
            },
            "option_2_rejected_second_30_video_crawl_batch": {
                "selected": False,
                "new_candidates_required_for_27_fnb_audio": int(
                    pilot_receipt["collection"]["requested_count"]
                ),
                "projected_wall_seconds_with_full_asr": second_batch_total_sec,
                "projected_extra_disk_mib": round(
                    float(pilot_receipt["resources"]["total_disk_bytes"]) / (1024.0 * 1024.0), 2
                ),
                "rejection_reason": (
                    f"Redundant media crawl & anti-bot exposure: existing {target_mp3_files} mp3s "
                    f"({full_pilot_audio_min} min, {pure_fnb_count} pure F&B) already satisfy M4.1."
                ),
            },
            "option_3_contingency_if_comments_anti_bot_blocked": {
                "selected": False,
                "fallback_policy": (
                    "Never bypass CAPTCHA/anti-bot gates; retain G2=PASS historical core + M4.1 audio evaluation, "
                    "record M5 live comment capture BLOCKED, and keep comment filtering in diagnostic_only_unvalidated mode."
                ),
            },
        },
    }


def verify_comment_backfill_enrichment_probe(
    pilot_snapshot_dir: Path,
    batch_jsonl_path: Path,
) -> dict[str, Any]:
    first_line = next(
        ln for ln in batch_jsonl_path.read_text(encoding="utf-8").splitlines() if ln.strip()
    )
    seed_rec = RawIncrementalVideoRecord.model_validate_json(first_line)
    submitted_comments = [
        RawCommentInput(
            comment_id="g3_probe_c1",
            author_handle="viewer_one",
            text="Khoai tây trứng muối ngon nha giá hơi cao xíu",
            like_count=3,
            reply_count=0,
        ),
        RawCommentInput(
            comment_id="g3_probe_c2",
            author_handle="viewer_two",
            text="Đóng gói sạch sẽ nhân viên dễ thương",
            like_count=1,
            reply_count=0,
        ),
        RawCommentInput(
            comment_id="g3_probe_c1",
            author_handle="viewer_one",
            text="Khoai tây trứng muối ngon nha giá hơi cao xíu",
            like_count=5,
            reply_count=0,
        ),
    ]
    sparse_comment_only = RawIncrementalVideoRecord(
        video_id=seed_rec.video_id,
        author_id=seed_rec.author_id,
        author_handle=seed_rec.author_handle,
        create_time=seed_rec.create_time,
        transcript="",
        whisper_segments=[],
        comments=submitted_comments,
    )

    with tempfile.TemporaryDirectory(prefix="m3_g_enrichment_probe_") as tmp:
        tmp_dir = Path(tmp)
        enrichment_jsonl = tmp_dir / "comment_backfill_probe.jsonl"
        enrichment_jsonl.write_text(
            sparse_comment_only.model_dump_json() + "\n",
            encoding="utf-8",
        )
        out_snap = tmp_dir / "m3_3_pilot_snapshot_v2_probe"
        manifest = ingest_incremental_batch_to_gold(
            base_corpus_dir=pilot_snapshot_dir,
            incremental_jsonl=enrichment_jsonl,
            output_corpus_dir=out_snap,
            update_existing=True,
        )
        voice_rows = pq.read_metadata(out_snap / "fact_voice_segments.parquet").num_rows
        comment_rows = pq.read_metadata(out_snap / "fact_comments.parquet").num_rows
        absa_rows = pq.read_metadata(out_snap / "fact_absa_reviews.parquet").num_rows
        return {
            "probe_snapshot_id": manifest.snapshot_id,
            "total_videos": manifest.total_videos,
            "preserved_transcribed_videos": manifest.transcribed_videos,
            "preserved_voice_segments_rows": int(voice_rows),
            "submitted_comments_rows": len(submitted_comments),
            "enriched_comments_rows": int(comment_rows),
            "absa_reviews_rows": int(absa_rows),
        }


def run_all_g3_checks(
    repo_root: Path = ROOT,
    output_receipt_path: Path | None = None,
) -> dict[str, Any]:
    t0 = time.perf_counter()
    base_dir = repo_root / "data/corpus/20261118_taxonomy_fix_v1"
    pilot_v1_dir = repo_root / "data/corpus/m3_3_pilot_snapshot_v1"
    pilot_v2_dir = repo_root / "data/corpus/m3_3_pilot_snapshot_v2"
    playwright_v5_dir = repo_root / "data/corpus/m3_3_playwright_comments_20261125_v5"
    batch_dir = repo_root / "data/raw_incremental/m3_3_pilot_run/batch"
    bm25_dir = repo_root / "artifacts/indexes/bm25-m3_3-pilot"
    original_receipt_path = (
        repo_root / "docs/reports/milestones/M3.3/evidence/m3_3_original_pass_receipt.json"
    )
    enriched_receipt_path = (
        repo_root / "docs/reports/milestones/M3.3/evidence/m3_3_pilot_receipt.json"
    )
    inspection_path = (
        repo_root / "docs/reports/milestones/M3.3/evidence/sample_inspection_sheet.jsonl"
    )

    prereqs = verify_prerequisites_and_upstream_tasks(repo_root)

    base_before = verify_snapshot_checksums(base_dir)
    v1_before = verify_snapshot_checksums(pilot_v1_dir)
    v2_before = verify_snapshot_checksums(pilot_v2_dir)
    v5_before = verify_snapshot_checksums(playwright_v5_dir)
    if v1_before["parent_manifest_sha256"] != base_before["manifest_sha256"]:
        raise ValueError("m3_3_pilot_snapshot_v1 parent_manifest_sha256 does not match base snapshot")
    if v2_before["parent_manifest_sha256"] != base_before["manifest_sha256"]:
        raise ValueError("m3_3_pilot_snapshot_v2 parent_manifest_sha256 does not match base snapshot")

    original_receipt = json.loads(original_receipt_path.read_text(encoding="utf-8"))
    enriched_receipt = json.loads(enriched_receipt_path.read_text(encoding="utf-8"))
    for rec_name, rec_obj in (
        ("m3_3_original_pass_receipt", original_receipt),
        ("m3_3_pilot_receipt", enriched_receipt),
    ):
        if rec_obj.get("pilot_status") != "PASS" or rec_obj.get("is_synthetic_fixture"):
            raise ValueError(f"{rec_name} must be real non-synthetic PASS")

    raw_media = verify_raw_pilot_media(batch_dir)
    expected_succeeded_count = int(original_receipt["collection"]["succeeded_count"])
    expected_succeeded_ids = set(raw_media["mp3_sha256_by_video_id"]) | set(
        raw_media["no_audio_item_ids"]
    )
    domain_yield = evaluate_inspection_and_domain_yield(
        inspection_path,
        requested_candidates=int(original_receipt["collection"]["requested_count"]),
        expected_total=expected_succeeded_count,
        expected_video_ids=expected_succeeded_ids,
    )
    if sorted(domain_yield["no_audio_ids"]) != sorted(raw_media["no_audio_item_ids"]):
        raise ValueError("Inspection sheet no_audio_ids disagree with crawl_manifest.json")

    _, _, df_videos = load_verified_corpus(pilot_v2_dir)
    retrieval_service = HybridRetrievalService.from_dirs(
        df_videos=df_videos,
        bm25_dir=bm25_dir,
        reranker_enabled=True,
    )
    probe_queries: dict[str, str] = dict(enriched_receipt["searchability"]["probe_queries"])
    matched_fresh: list[str] = []
    for vid, query_text in probe_queries.items():
        resp = retrieval_service.search(
            RetrievalRequest(query=query_text, mode="bm25", top_k=10, rerank=True)
        )
        if vid in {item.citation.video_id for item in resp.items}:
            matched_fresh.append(vid)
    if len(matched_fresh) < 5:
        raise ValueError(f"Expected >= 5 searchable fresh videos, got {len(matched_fresh)}")

    enrichment_probe = verify_comment_backfill_enrichment_probe(
        pilot_v1_dir,
        batch_dir / "videos_4m.jsonl",
    )
    expected_voice_rows = int(v1_before["row_counts"]["fact_voice_segments.parquet"])
    expected_transcribed = int(v1_before["transcribed_videos"])
    if (
        enrichment_probe["preserved_voice_segments_rows"] != expected_voice_rows
        or enrichment_probe["preserved_transcribed_videos"] != expected_transcribed
        or enrichment_probe["enriched_comments_rows"] != 2
    ):
        raise ValueError("Comment backfill probe failed preservation or deduplication invariants")

    v2_comments_table = pq.read_table(pilot_v2_dir / "fact_comments.parquet", columns=["video_id"])
    v2_comment_rows = int(v2_comments_table.num_rows)
    v2_commented_videos = len(
        {str(v) for v in v2_comments_table.column("video_id").to_pylist() if v}
    )

    v5_comments_table = pq.read_table(
        playwright_v5_dir / "fact_comments.parquet", columns=["video_id"]
    )
    v5_comment_rows = int(v5_comments_table.num_rows)
    v5_commented_videos = len(
        {str(v) for v in v5_comments_table.column("video_id").to_pylist() if v}
    )

    readiness_matrix = build_modality_readiness_matrix(
        audio_count=raw_media["verified_mp3_count"],
        total_audio_minutes=raw_media["accumulated_audio_minutes"],
        pure_fnb_audio_count=domain_yield["pure_fnb_audio_count"],
        human_verified_count=domain_yield["total_inspected"],
        total_videos=expected_succeeded_count,
        collected_comments_count=v2_comment_rows,
        commented_videos_count=v2_commented_videos,
    )
    if readiness_matrix["M4.1"]["status"] != "READY_UNBLOCKED":
        raise ValueError(
            f"G3 requires M4.1 to be READY_UNBLOCKED, got {readiness_matrix['M4.1']}"
        )

    capacity_model = compute_capacity_and_budget_projections(
        pilot_receipt=original_receipt,
        domain_yield=domain_yield,
        verified_mp3_count=raw_media["verified_mp3_count"],
        total_audio_minutes=raw_media["accumulated_audio_minutes"],
    )
    capacity_model["executed_comment_enrichments"] = {
        "m3_3_pilot_snapshot_v2_tiktokapi_native": {
            "wall_seconds": float(enriched_receipt["resources"]["wall_seconds"]),
            "fact_comments_rows": v2_comment_rows,
            "commented_videos_count": v2_commented_videos,
        },
        "m3_3_playwright_comments_20261125_v5_expansion": {
            "total_fresh_videos": 130,
            "fact_comments_rows": v5_comment_rows,
            "commented_videos_count": v5_commented_videos,
        },
    }

    base_after = verify_snapshot_checksums(base_dir)
    v1_after = verify_snapshot_checksums(pilot_v1_dir)
    v2_after = verify_snapshot_checksums(pilot_v2_dir)
    v5_after = verify_snapshot_checksums(playwright_v5_dir)
    for label, before_s, after_s in (
        ("base", base_before, base_after),
        ("pilot_v1", v1_before, v1_after),
        ("pilot_v2", v2_before, v2_after),
        ("playwright_v5", v5_before, v5_after),
    ):
        if before_s["file_sha256"] != after_s["file_sha256"]:
            raise ValueError(f"Snapshot {label} mutated during G3 checks")

    receipt: dict[str, Any] = {
        "gate_id": "G3",
        "task_id": "M3.G",
        "executed_at_utc": datetime.now(UTC).isoformat(),
        "runtime_environment": {
            "python_version": platform.python_version(),
            "platform": platform.platform(),
        },
        "verification_wall_seconds": round(time.perf_counter() - t0, 3),
        "prerequisite_gates": prereqs["prerequisite_gates"],
        "upstream_tasks": prereqs["upstream_tasks"],
        "immutability_verification": {
            "zero_byte_mutations": True,
            "base_snapshot": base_after,
            "pilot_snapshot_v1": v1_after,
            "pilot_snapshot_v2": v2_after,
            "playwright_snapshot_v5": v5_after,
            "raw_pilot_media": {
                "crawl_manifest_sha256": raw_media["crawl_manifest_sha256"],
                "verified_mp3_count": raw_media["verified_mp3_count"],
                "total_mp3_bytes": raw_media["total_mp3_bytes"],
                "no_audio_item_ids": raw_media["no_audio_item_ids"],
                "accumulated_audio_minutes": raw_media["accumulated_audio_minutes"],
            },
        },
        "searchability_recheck": {
            "bm25_receipt_sha256": _sha256_file(bm25_dir / "bm25-receipt.json"),
            "probed_count": len(probe_queries),
            "matched_count": len(matched_fresh),
            "matched_video_ids": matched_fresh,
        },
        "inspection_and_domain_yield": domain_yield,
        "m3_1_comment_enrichment_preservation_probe": enrichment_probe,
        "downstream_modality_readiness_matrix": readiness_matrix,
        "capacity_and_budget_model": capacity_model,
    }
    if output_receipt_path is not None:
        output_receipt_path.parent.mkdir(parents=True, exist_ok=True)
        output_receipt_path.write_text(
            json.dumps(receipt, indent=2, ensure_ascii=False) + "\n",
            encoding="utf-8",
        )
    return receipt


def main() -> None:
    out_path = Path(__file__).resolve().parent / "g3_verification_receipt.json"
    receipt = run_all_g3_checks(ROOT, output_receipt_path=out_path)
    print(
        f"G3 verification probe PASS in {receipt['verification_wall_seconds']}s | "
        f"M4.1={receipt['downstream_modality_readiness_matrix']['M4.1']['status']} | "
        f"M5.1={receipt['downstream_modality_readiness_matrix']['M5.1']['status']} | "
        f"M5.2={receipt['downstream_modality_readiness_matrix']['M5.2']['status']} | "
        f"searchable={receipt['searchability_recheck']['matched_count']}/{receipt['searchability_recheck']['probed_count']}"
    )


if __name__ == "__main__":
    main()
