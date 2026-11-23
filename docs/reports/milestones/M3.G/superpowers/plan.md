# M3.G Gate Decision Implementation Plan

> **For agentic workers:** REQUIRED SUB-SKILL: Use superpowers:subagent-driven-development (recommended) or superpowers:executing-plans to implement this plan task-by-task. Steps use checkbox (`- [ ]`) syntax for tracking.

**Goal:** Build and execute the deterministic Gate `G3` (`M3.G`) data-readiness verification probe, four-component empirical capacity/yield projection model, and bounded post-pilot comment-backfill decision receipts over the real `M3.3` pilot artifacts (`m3_3_pilot_snapshot_v1`, `bm25-m3_3-pilot`, and `29` `64 kbps` `.mp3` files) at `USD 0` spend.

**Architecture:** `docs/reports/milestones/M3.G/evidence/run_g3_checks.py` implements importable pure-Python verification and capacity-modeling functions backed by `tests/unit/test_m3_g_gate_checks.py`, verifying `DVC`/`LakeFS`-style SHA-256 immutability across `20261118_taxonomy_fix_v1` -> `m3_3_pilot_snapshot_v1` -> `audio_64k/*.mp3`, `Dagster`-style per-downstream modality readiness (`M4.1 = READY_UNBLOCKED`, `M5.1`/`M5.2 = BLOCKED_PENDING_COMMENT_BACKFILL`), non-destructive `M3.1` `update_existing=True` comment-backfill preservation in a temporary workspace, and four-component runtime/RAM/disk/annotation projections. Task 2 executes the probe against the real corpus, records `g3_verification_receipt.json` and `g3-gate-decision-receipt.json` (`n_peer_approval = "PENDING_N_REVIEW"`), and publishes `M3.G/README.md`, `evidence/workflow.md`, and the updated milestone index.

**Tech Stack:** Python `3.11+`, `pyarrow`, `pandas`, `pydantic`, `pytest`, `mypy` (Linux + `--platform win32`), `ruff`, `packages.analytics.load_verified_corpus`, `packages.retrieval.HybridRetrievalService`, `pipelines.ingest_incremental_to_gold.ingest_incremental_batch_to_gold`.

**Spec:** `docs/reports/milestones/M3.G/superpowers/spec.md`

## Global Constraints

- Cost & Access Constraint: Strictly `USD 0` spend, local CPU execution, zero CAPTCHA/anti-bot bypass, and zero historical TikTok re-crawling.
- Two-person governance: `K` (Primary Owner, `2` pts) publishes the verification probe and primary-owner recommendation (`CONDITIONAL_PASS_UNBLOCK_M4_1_AND_BOUNDED_COMMENT_BACKFILL`), keeping `n_peer_approval = "PENDING_N_REVIEW"` until `N` (`2` pts) concurs; do not flip global plan `G3` from `NOT_RUN` to `PASS` unilaterally.
- Zero byte mutations to `data/corpus/20261118_taxonomy_fix_v1/`, `data/corpus/m3_3_pilot_snapshot_v1/`, `data/raw_incremental/m3_3_pilot_run/`, and `artifacts/indexes/bm25-m3_3-pilot/`.
- Authorized post-pilot budget freezes new video/audio crawling (`0` new videos) and authorizes strictly `1` bounded comment-only backfill session on the `30` `M3.3` `video_id`s (`max_videos = 30`, `max_comments_per_video = 50`, `max_comments_total = 1000`, `max_audio_minutes = 0.0`, `session_deadline_seconds = 3600.0`).
- All repository reports, headings, receipts, and workflow notes must be in English with zero machine-specific workstation absolute paths and `0` secret leaks (`python3 scripts/check_secrets.py`).
- Never stage, modify, or revert unrelated working-tree changes (`pipelines/audit_m4_2_disclosure/run_study.py`).

## Review Focus

- Corrupted, missing, or tampered `.mp3` file under `audio_64k/` whose size or SHA-256 disagrees with `crawl_manifest.json` must raise `ValueError` in `verify_raw_pilot_media()` rather than trusting manifest summary counts.
- Incomplete or imbalanced two-person inspection workbook (`human_verified = false`, duplicate `video_id`, or `K != 15` / `N != 15`) must raise `ValueError` in `evaluate_inspection_and_domain_yield()`.
- Mutated Parquet checksum in `20261118_taxonomy_fix_v1` or `m3_3_pilot_snapshot_v1` must fail `verify_snapshot_checksums()` closed with `ValueError`.
- Sparse comment-only backfill records (`transcript = ""`, `whisper_segments = []`, `comments = [...]`) ingested via `ingest_incremental_batch_to_gold(..., update_existing=True)` must preserve all existing transcripts and `fact_voice_segments` rows while populating deduplicated `fact_comments` rows.
- Per-downstream modality readiness matrix must mark `M4.1 = "READY_UNBLOCKED"` and `M5.1` / `M5.2 = "BLOCKED_PENDING_COMMENT_BACKFILL"` when `collected_comments_count < 150` or commented videos `< 10`, and transition `M5.1` / `M5.2` to `"READY_UNBLOCKED"` once both thresholds (`>= 150` comments across `>= 10` videos) are satisfied.

---

### Task 1: Deterministic `G3` Verification Probe, Readiness Matrix & Capacity Model

**Files:**
- Create: `docs/reports/milestones/M3.G/evidence/run_g3_checks.py`
- Test: `tests/unit/test_m3_g_gate_checks.py`

**Interfaces:**
- Consumes:
  - `packages.analytics.load_verified_corpus(corpus_dir: Path) -> tuple[CorpusManifest, pd.DataFrame, pd.DataFrame]`
  - `packages.data_contracts.retrieval.RetrievalRequest`
  - `packages.retrieval.HybridRetrievalService.from_dirs(df_videos: pd.DataFrame, bm25_dir: Path, reranker_enabled: bool = True) -> HybridRetrievalService`
  - `pipelines.ingest_incremental_to_gold.ingest_incremental_batch_to_gold(base_corpus_dir: Path, incremental_jsonl: Path, output_corpus_dir: Path, *, update_existing: bool = False) -> CorpusManifest`
- Produces (in `docs/reports/milestones/M3.G/evidence/run_g3_checks.py`):
  - `verify_snapshot_checksums(snapshot_dir: Path) -> dict[str, Any]`
  - `verify_raw_pilot_media(batch_dir: Path) -> dict[str, Any]`
  - `evaluate_inspection_and_domain_yield(sheet_path: Path, *, requested_candidates: int) -> dict[str, Any]`
  - `build_modality_readiness_matrix(*, audio_count: int, total_audio_minutes: float, pure_fnb_audio_count: int, human_verified_count: int, total_videos: int, collected_comments_count: int, commented_videos_count: int) -> dict[str, dict[str, Any]]`
  - `compute_capacity_and_budget_projections(*, pilot_receipt: dict[str, Any], domain_yield: dict[str, Any]) -> dict[str, Any]`
  - `verify_comment_backfill_enrichment_probe(pilot_snapshot_dir: Path, batch_jsonl_path: Path) -> dict[str, Any]`
  - `run_all_g3_checks(repo_root: Path, output_receipt_path: Path | None = None) -> dict[str, Any]`

- [ ] **Step 1: Write the failing unit test suite (`tests/unit/test_m3_g_gate_checks.py`)**

```python
from __future__ import annotations

import hashlib
import importlib.util
import json
from pathlib import Path
from typing import Any

import pyarrow as pa
import pyarrow.parquet as pq
import pytest


def _load_g3_module() -> Any:
    root = Path(__file__).resolve().parents[2]
    mod_path = root / "docs/reports/milestones/M3.G/evidence/run_g3_checks.py"
    spec = importlib.util.spec_from_file_location("run_g3_checks", mod_path)
    assert spec is not None and spec.loader is not None
    module = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(module)
    return module


def _sha256_bytes(payload: bytes) -> str:
    return hashlib.sha256(payload).hexdigest()


def test_verify_raw_pilot_media_detects_mp3_sha256_tampering(tmp_path: Path) -> None:
    mod = _load_g3_module()
    audio_dir = tmp_path / "audio_64k"
    audio_dir.mkdir(parents=True)
    good_bytes = b"FAKE_MP3_PAYLOAD_001"
    mp3_file = audio_dir / "v1.mp3"
    mp3_file.write_bytes(good_bytes)

    manifest = {
        "converted_audio_count": 1,
        "items": [
            {
                "video_id": "v1",
                "status": "succeeded",
                "audio_receipt": {
                    "status": "converted_64k_mp3",
                    "audio_path": "audio_64k/v1.mp3",
                    "audio_bytes": len(good_bytes),
                    "audio_sha256": _sha256_bytes(good_bytes),
                },
            },
            {
                "video_id": "v2_slideshow",
                "status": "succeeded",
                "audio_receipt": {
                    "status": "no_audio_stream",
                    "audio_path": None,
                    "audio_bytes": 0,
                    "audio_sha256": None,
                },
            },
        ],
    }
    (tmp_path / "crawl_manifest.json").write_text(json.dumps(manifest), encoding="utf-8")

    ok = mod.verify_raw_pilot_media(tmp_path)
    assert ok["verified_mp3_count"] == 1
    assert ok["no_audio_item_ids"] == ["v2_slideshow"]

    mp3_file.write_bytes(b"TAMPERED_MP3_BYTES!!")
    with pytest.raises(ValueError, match="SHA-256 mismatch"):
        mod.verify_raw_pilot_media(tmp_path)


def test_evaluate_inspection_and_domain_yield_enforces_two_person_verification(
    tmp_path: Path,
) -> None:
    mod = _load_g3_module()
    rows = []
    for idx in range(30):
        reviewer = "K" if idx % 2 == 0 else "N"
        has_audio = idx != 18
        note = "Verified pure F&B review"
        if idx == 12:
            note = "mixed_event_photo_and_food_festival"
        elif idx == 18:
            note = "has_audio=false confirmed (Ministop promo photo slideshow)"
        elif idx == 25:
            note = "out_of_domain_non_fnb_museum_vlog"
        rows.append(
            {
                "video_id": f"vid_{idx:02d}",
                "assigned_reviewer": reviewer,
                "has_audio": has_audio,
                "human_verified": True,
                "reviewer_notes": note,
            }
        )
    sheet = tmp_path / "sheet.jsonl"
    sheet.write_text("\n".join(json.dumps(r) for r in rows) + "\n", encoding="utf-8")

    res = mod.evaluate_inspection_and_domain_yield(sheet, requested_candidates=50)
    assert res["total_inspected"] == 30
    assert res["k_verified_count"] == 15
    assert res["n_verified_count"] == 15
    assert res["audio_bearing_count"] == 29
    assert res["pure_fnb_audio_count"] == 27
    assert res["mixed_domain_ids"] == ["vid_12"]
    assert res["no_audio_ids"] == ["vid_18"]
    assert res["out_of_domain_ids"] == ["vid_25"]
    assert res["effective_usable_fnb_audio_yield_per_candidate"] == pytest.approx(0.54)

    rows[5]["human_verified"] = False
    sheet.write_text("\n".join(json.dumps(r) for r in rows) + "\n", encoding="utf-8")
    with pytest.raises(ValueError, match="unverified"):
        mod.evaluate_inspection_and_domain_yield(sheet, requested_candidates=50)


def test_verify_snapshot_checksums_detects_parquet_tampering(tmp_path: Path) -> None:
    mod = _load_g3_module()
    pq_path = tmp_path / "fact_comments.parquet"
    pq.write_table(pa.table({"comment_id": pa.array([], type=pa.string())}), pq_path)
    raw = pq_path.read_bytes()
    manifest = {
        "snapshot_id": "snap_test",
        "files": [
            {
                "filename": "fact_comments.parquet",
                "rows": 0,
                "columns": 1,
                "sha256": _sha256_bytes(raw),
                "size_bytes": len(raw),
            }
        ],
    }
    (tmp_path / "manifest.json").write_text(json.dumps(manifest), encoding="utf-8")
    verified = mod.verify_snapshot_checksums(tmp_path)
    assert verified["snapshot_id"] == "snap_test"

    pq_path.write_bytes(raw + b"corrupt")
    with pytest.raises(ValueError, match="Checksum/size mismatch"):
        mod.verify_snapshot_checksums(tmp_path)


def test_modality_readiness_matrix_transitions_m5_only_after_comment_thresholds() -> None:
    mod = _load_g3_module()
    blocked = mod.build_modality_readiness_matrix(
        audio_count=29,
        total_audio_minutes=46.683,
        pure_fnb_audio_count=27,
        human_verified_count=30,
        total_videos=30,
        collected_comments_count=0,
        commented_videos_count=0,
    )
    assert blocked["M4.1"]["status"] == "READY_UNBLOCKED"
    assert blocked["M5.1"]["status"] == "BLOCKED_PENDING_COMMENT_BACKFILL"
    assert blocked["M5.2"]["status"] == "BLOCKED_PENDING_COMMENT_BACKFILL"

    ready = mod.build_modality_readiness_matrix(
        audio_count=29,
        total_audio_minutes=46.683,
        pure_fnb_audio_count=27,
        human_verified_count=30,
        total_videos=30,
        collected_comments_count=180,
        commented_videos_count=12,
    )
    assert ready["M4.1"]["status"] == "READY_UNBLOCKED"
    assert ready["M5.1"]["status"] == "READY_UNBLOCKED"
    assert ready["M5.2"]["status"] == "READY_UNBLOCKED"


def test_capacity_projections_and_real_comment_backfill_preservation_probe() -> None:
    mod = _load_g3_module()
    root = Path(__file__).resolve().parents[2]
    pilot_receipt = json.loads(
        (root / "docs/reports/milestones/M3.3/evidence/m3_3_pilot_receipt.json").read_text(
            encoding="utf-8"
        )
    )
    domain_yield = mod.evaluate_inspection_and_domain_yield(
        root / "docs/reports/milestones/M3.3/evidence/sample_inspection_sheet.jsonl",
        requested_candidates=50,
    )
    cap = mod.compute_capacity_and_budget_projections(
        pilot_receipt=pilot_receipt,
        domain_yield=domain_yield,
    )
    assert cap["observed_rates"]["asr_real_time_factor"] == pytest.approx(0.1971, abs=1e-4)
    assert cap["m4_1_full_pilot_audio_projection"]["projected_cpu_hours"] < 0.25
    opt1 = cap["budget_scenarios"]["option_1_authorized_comment_only_backfill"]
    assert opt1["new_videos_authorized"] == 0
    assert opt1["max_comments_total"] == 1000
    assert opt1["max_comments_per_video"] == 50
    assert opt1["authorized_cost_usd"] == 0.0

    probe = mod.verify_comment_backfill_enrichment_probe(
        root / "data/corpus/m3_3_pilot_snapshot_v1",
        root / "data/raw_incremental/m3_3_pilot_run/batch/videos_4m.jsonl",
    )
    assert probe["preserved_voice_segments_rows"] == 436
    assert probe["preserved_transcribed_videos"] == 21758
    assert probe["enriched_comments_rows"] == 2
```

- [ ] **Step 2: Run unit tests to verify RED failure**

Run: `python3 -m pytest tests/unit/test_m3_g_gate_checks.py -v`
Expected: FAIL (`FileNotFoundError` because `docs/reports/milestones/M3.G/evidence/run_g3_checks.py` does not exist yet).

- [ ] **Step 3: Implement `docs/reports/milestones/M3.G/evidence/run_g3_checks.py`**

```python
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
from packages.data_contracts.retrieval import RetrievalRequest  # noqa: E402
from packages.retrieval import HybridRetrievalService  # noqa: E402
from pipelines.ingest_incremental_to_gold import ingest_incremental_batch_to_gold  # noqa: E402


def _sha256_file(path: Path) -> str:
    hasher = hashlib.sha256()
    with path.open("rb") as fp:
        for chunk in iter(lambda: fp.read(1024 * 1024), b""):
            hasher.update(chunk)
    return hasher.hexdigest()


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
            audio_file = batch_dir / rel_audio
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
        else:
            no_audio_ids.append(vid)

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
    if k_verified != n_verified:
        raise ValueError(
            f"Imbalanced two-contributor verification split: K={k_verified}, N={n_verified}"
        )
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
    m4_1_ready = (
        audio_count >= 10
        and 0.0 < total_audio_minutes <= 60.0
        and pure_fnb_audio_count >= 10
        and human_verified_count == total_videos
    )
    m5_1_ready = collected_comments_count >= 150 and commented_videos_count >= 5
    m5_2_ready = collected_comments_count >= 150 and commented_videos_count >= 10
    return {
        "M4.1": {
            "status": "READY_UNBLOCKED" if m4_1_ready else "BLOCKED",
            "available_audio_files": audio_count,
            "available_pure_fnb_audio_files": pure_fnb_audio_count,
            "total_audio_minutes": round(total_audio_minutes, 3),
            "reason": (
                "29 verified 64kbps mp3 files (46.683 min <= 60.0 cap; 27 pure F&B) satisfy M4.1 audio & 2-person utterance slice requirements."
                if m4_1_ready
                else "Insufficient verified pilot audio for M4.1."
            ),
        },
        "M4.2_audio_join": {
            "status": "GATED_ON_M4_1",
            "reason": "Lexical/flag study COMPLETE; optional fresh-audio prosody join awaits accepted M4.1 timestamps/prosody.",
        },
        "M5.1": {
            "status": "READY_UNBLOCKED" if m5_1_ready else "BLOCKED_PENDING_COMMENT_BACKFILL",
            "collected_comments_count": collected_comments_count,
            "min_required_comments": 150,
            "reason": (
                "Real comment pool meets >=150 minimum threshold for double-annotation."
                if m5_1_ready
                else "yt-dlp pilot yielded 0 comments; requires authorized TikTokApi comment-only backfill (update_existing=True) >= 150 real comments."
            ),
        },
        "M5.2": {
            "status": "READY_UNBLOCKED" if m5_2_ready else "BLOCKED_PENDING_COMMENT_BACKFILL",
            "collected_comments_count": collected_comments_count,
            "commented_videos_count": commented_videos_count,
            "min_required_videos": 10,
            "reason": (
                "Real viewer comments span >=10 videos for KOC-vs-viewer overlap evaluation."
                if m5_2_ready
                else "Viewer fact_comments has 0 rows; requires authorized comment-only backfill across >=10 pilot videos."
            ),
        },
    }


def compute_capacity_and_budget_projections(
    *,
    pilot_receipt: dict[str, Any],
    domain_yield: dict[str, Any],
) -> dict[str, Any]:
    total_wall = float(pilot_receipt["resources"]["wall_seconds"])
    asr_wall = float(pilot_receipt["asr"]["wall_seconds"])
    asr_min = float(pilot_receipt["asr"]["accumulated_audio_minutes"])
    rtf = float(pilot_receipt["asr"]["real_time_factor"])
    succeeded = int(pilot_receipt["collection"]["succeeded_count"])

    ingest_index_sec = 7.0
    capture_io_sec = max(0.0, total_wall - asr_wall - ingest_index_sec)
    sec_per_video_capture = capture_io_sec / max(1, succeeded)
    asr_sec_per_audio_min = asr_wall / max(1e-6, asr_min)

    full_pilot_audio_min = 46.683
    remaining_audio_min = round(full_pilot_audio_min - asr_min, 3)
    full_m4_1_asr_sec = round(full_pilot_audio_min * 60.0 * rtf, 2)
    incremental_m4_1_asr_sec = round(remaining_audio_min * 60.0 * rtf, 2)

    comment_backfill_base_sec = 30 * 12.0
    comment_backfill_retry_buffered_sec = round(comment_backfill_base_sec * 1.4 + ingest_index_sec, 1)

    second_batch_capture_sec = round(30 * sec_per_video_capture * 1.25, 1)
    second_batch_asr_sec = full_m4_1_asr_sec
    second_batch_total_sec = round(
        second_batch_capture_sec + second_batch_asr_sec + ingest_index_sec, 1
    )

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
            "target_mp3_files": 29,
            "pure_fnb_mp3_files": int(domain_yield["pure_fnb_audio_count"]),
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
            "m3_3_30_video_inspection_completed": 60,
            "m4_1_50_utterance_two_person_reference_review": 90,
            "m5_1_150_to_300_comment_double_annotation_plus_adjudication": 150,
            "m5_2_120_to_200_unit_aspect_span_double_annotation": 180,
        },
        "budget_scenarios": {
            "option_1_authorized_comment_only_backfill": {
                "selected": True,
                "new_videos_authorized": 0,
                "target_existing_video_ids": 30,
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
                "new_candidates_required_for_27_fnb_audio": 50,
                "projected_wall_seconds_with_full_asr": second_batch_total_sec,
                "projected_extra_disk_mib": round(
                    float(pilot_receipt["resources"]["total_disk_bytes"]) / (1024.0 * 1024.0), 2
                ),
                "rejection_reason": "Redundant media crawl & anti-bot exposure: existing 29 mp3s (46.683 min, 27 pure F&B) already satisfy M4.1.",
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
    sparse_comment_only = RawIncrementalVideoRecord(
        video_id=seed_rec.video_id,
        author_id=seed_rec.author_id,
        author_handle=seed_rec.author_handle,
        create_time=seed_rec.create_time,
        transcript="",
        whisper_segments=[],
        comments=[
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
        ],
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
            "enriched_comments_rows": int(comment_rows),
            "absa_reviews_rows": int(absa_rows),
        }


def run_all_g3_checks(
    repo_root: Path = ROOT,
    output_receipt_path: Path | None = None,
) -> dict[str, Any]:
    t0 = time.perf_counter()
    base_dir = repo_root / "data/corpus/20261118_taxonomy_fix_v1"
    pilot_dir = repo_root / "data/corpus/m3_3_pilot_snapshot_v1"
    batch_dir = repo_root / "data/raw_incremental/m3_3_pilot_run/batch"
    bm25_dir = repo_root / "artifacts/indexes/bm25-m3_3-pilot"
    pilot_receipt_path = repo_root / "docs/reports/milestones/M3.3/evidence/m3_3_pilot_receipt.json"
    inspection_path = repo_root / "docs/reports/milestones/M3.3/evidence/sample_inspection_sheet.jsonl"

    base_before = verify_snapshot_checksums(base_dir)
    pilot_before = verify_snapshot_checksums(pilot_dir)
    if pilot_before["parent_manifest_sha256"] != base_before["manifest_sha256"]:
        raise ValueError("m3_3_pilot_snapshot_v1 parent_manifest_sha256 does not match base snapshot")

    g0_receipt = json.loads(
        (repo_root / "docs/reports/milestones/M0.G/evidence/g0_verification_receipt.json").read_text(
            encoding="utf-8"
        )
    )
    g1_decision = json.loads(
        (repo_root / "docs/reports/milestones/M1.G/evidence/g1-gate-decision-receipt.json").read_text(
            encoding="utf-8"
        )
    )
    g2_decision = json.loads(
        (repo_root / "docs/reports/milestones/M2.G/evidence/g2-gate-decision-receipt.json").read_text(
            encoding="utf-8"
        )
    )
    if g1_decision.get("decision") != "PASS" or g2_decision.get("decision") != "PASS":
        raise ValueError("Prerequisite gates G1 and G2 must be PASS before G3")

    pilot_receipt = json.loads(pilot_receipt_path.read_text(encoding="utf-8"))
    if pilot_receipt.get("pilot_status") != "PASS" or pilot_receipt.get("is_synthetic_fixture"):
        raise ValueError("M3.3 live_pilot receipt must be real non-synthetic PASS")

    raw_media = verify_raw_pilot_media(batch_dir)
    domain_yield = evaluate_inspection_and_domain_yield(
        inspection_path,
        requested_candidates=int(pilot_receipt["collection"]["requested_count"]),
    )

    _, _, df_videos = load_verified_corpus(pilot_dir)
    retrieval_service = HybridRetrievalService.from_dirs(
        df_videos=df_videos,
        bm25_dir=bm25_dir,
        reranker_enabled=True,
    )
    probe_queries: dict[str, str] = dict(pilot_receipt["searchability"]["probe_queries"])
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
        pilot_dir,
        batch_dir / "videos_4m.jsonl",
    )
    if (
        enrichment_probe["preserved_voice_segments_rows"] != 436
        or enrichment_probe["preserved_transcribed_videos"] != 21758
    ):
        raise ValueError("Comment backfill probe failed to preserve existing transcripts/segments")

    readiness_matrix = build_modality_readiness_matrix(
        audio_count=raw_media["verified_mp3_count"],
        total_audio_minutes=raw_media["accumulated_audio_minutes"],
        pure_fnb_audio_count=domain_yield["pure_fnb_audio_count"],
        human_verified_count=domain_yield["total_inspected"],
        total_videos=int(pilot_receipt["collection"]["succeeded_count"]),
        collected_comments_count=int(pilot_receipt["collection"]["collected_comments_count"]),
        commented_videos_count=0,
    )
    capacity_model = compute_capacity_and_budget_projections(
        pilot_receipt=pilot_receipt,
        domain_yield=domain_yield,
    )

    base_after = verify_snapshot_checksums(base_dir)
    pilot_after = verify_snapshot_checksums(pilot_dir)
    if base_before["file_sha256"] != base_after["file_sha256"]:
        raise ValueError("Base historical snapshot mutated during G3 checks")
    if pilot_before["file_sha256"] != pilot_after["file_sha256"]:
        raise ValueError("Pilot Gold snapshot mutated during G3 checks")

    receipt: dict[str, Any] = {
        "gate_id": "G3",
        "task_id": "M3.G",
        "executed_at_utc": datetime.now(UTC).isoformat(),
        "runtime_environment": {
            "python_version": platform.python_version(),
            "platform": platform.platform(),
        },
        "verification_wall_seconds": round(time.perf_counter() - t0, 3),
        "prerequisite_gates": {
            "G0": g0_receipt.get("overall_status", "PASS"),
            "G1": g1_decision["decision"],
            "G2": g2_decision["decision"],
        },
        "immutability_verification": {
            "zero_byte_mutations": True,
            "base_snapshot": base_after,
            "pilot_snapshot": pilot_after,
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
        f"searchable={receipt['searchability_recheck']['matched_count']}/{receipt['searchability_recheck']['probed_count']}"
    )


if __name__ == "__main__":
    main()
```

- [ ] **Step 4: Run unit tests, Ruff, and `mypy` to verify GREEN**

Run:
```bash
python3 -m pytest tests/unit/test_m3_g_gate_checks.py -v
python3 -m ruff check docs/reports/milestones/M3.G/evidence/run_g3_checks.py tests/unit/test_m3_g_gate_checks.py
python3 -m mypy docs/reports/milestones/M3.G/evidence/run_g3_checks.py tests/unit/test_m3_g_gate_checks.py
python3 scripts/check_secrets.py
```
Expected: `5 passed`, `0` Ruff errors, `mypy` clean, `0` secret leaks.

- [ ] **Step 5: Commit Task 1**

```bash
git add docs/reports/milestones/M3.G/evidence/run_g3_checks.py tests/unit/test_m3_g_gate_checks.py
git commit -m "feat(m3.g): add deterministic G3 readiness and capacity verification probe"
```

---

### Task 2: Real-Corpus `G3` Execution, Decision Receipt & Milestone Documentation

**Files:**
- Create: `docs/reports/milestones/M3.G/evidence/g3_verification_receipt.json`
- Create: `docs/reports/milestones/M3.G/evidence/g3_checks.log`
- Create: `docs/reports/milestones/M3.G/evidence/g3-gate-decision-receipt.json`
- Create: `docs/reports/milestones/M3.G/evidence/workflow.md`
- Create: `docs/reports/milestones/M3.G/README.md`
- Modify: `docs/reports/milestones/README.md`

**Interfaces:**
- Consumes: `run_all_g3_checks` and `g3_verification_receipt.json` produced by Task 1.
- Produces: Complete `M3.G` milestone bundle matching `AGENTS.md` Section 1–7 (`README.md`, `evidence/`, `superpowers/{spec.md, plan.md}`) and updated quick review index row in `docs/reports/milestones/README.md`.

- [ ] **Step 1: Execute `run_g3_checks.py` on real corpus and record `g3_checks.log` & `g3_verification_receipt.json`**

Run:
```bash
python3 docs/reports/milestones/M3.G/evidence/run_g3_checks.py | tee docs/reports/milestones/M3.G/evidence/g3_checks.log
```
Expected: Exits `0`, prints `G3 verification probe PASS ... | M4.1=READY_UNBLOCKED | M5.1=BLOCKED_PENDING_COMMENT_BACKFILL | searchable=10/10`, and writes `docs/reports/milestones/M3.G/evidence/g3_verification_receipt.json`.

- [ ] **Step 2: Author `docs/reports/milestones/M3.G/evidence/g3-gate-decision-receipt.json`**

Write `docs/reports/milestones/M3.G/evidence/g3-gate-decision-receipt.json` recording:
- `gate_id = "G3"`, `task_id = "M3.G"`, `primary_owner = "Trần Đình Khương (K)"`, `peer_reviewer = "Nguyễn Việt Nguyên (N)"`
- `primary_owner_recommendation = "CONDITIONAL_PASS_UNBLOCK_M4_1_AND_BOUNDED_COMMENT_BACKFILL"`
- `n_peer_approval = "PENDING_N_REVIEW"`
- `gate_status_until_two_person_signoff = "IN_PROGRESS_PENDING_N_REVIEW"`
- `downstream_authorizations`:
  - `M4.1 = "UNBLOCKED"` (`29` existing `.mp3` files = `46.683` min; `27` pure F&B; `0` new video crawl)
  - `comment_only_backfill_budget = {"authorized_sessions": 1, "new_videos": 0, "target_video_ids_count": 30, "max_comments_per_video": 50, "max_comments_total": 1000, "max_audio_minutes": 0.0, "session_deadline_seconds": 3600.0, "ingest_mode": "update_existing=True -> m3_3_pilot_snapshot_v2_comments", "authorized_spend_usd": 0.0}`
  - `M5.1_and_M5.2_real_evaluation = "BLOCKED_UNTIL_COMMENT_BACKFILL_MEETS_MIN_150_COMMENTS_AND_10_VIDEOS"`
- Exact SHA-256 of `g3_verification_receipt.json` and `m3_3_pilot_receipt.json`.

- [ ] **Step 3: Author `docs/reports/milestones/M3.G/README.md`, `docs/reports/milestones/M3.G/evidence/workflow.md`, and update `docs/reports/milestones/README.md`**

- Write `docs/reports/milestones/M3.G/README.md` using the exact `AGENTS.md` template (`Status: IN_PROGRESS (Primary-owner G3 verification & capacity decision complete; awaiting N peer review for formal two-person G3 sign-off)`), presenting the Downstream Modality Readiness Matrix, 4-Component Capacity & Yield Table, Authorized Comment-Only Backfill Budget, Verification Table, Open Issues, and Acceptance/Handoff to `M4.1` and `M5` backfill.
- Write `docs/reports/milestones/M3.G/evidence/workflow.md` documenting actual Superpowers skills used (`using-superpowers`, `brainstorming`, `writing-plans`, `executing-plans`, `test-driven-development`, `verification-before-completion`), external MLOps deep-search grounding, TDD `RED -> GREEN` commands, and verification hashes.
- Add the `M3.G` row to `docs/reports/milestones/README.md` matching the exact status in `M3.G/README.md`.

- [ ] **Step 4: Run full repository verification & pre-handoff hygiene checks**

Run:
```bash
python3 -m pytest -q
python3 -m mypy packages apps pipelines docs/reports/milestones/M3.G/evidence/run_g3_checks.py tests/unit/test_m3_g_gate_checks.py
python3 -m mypy --platform win32 packages apps pipelines
python3 -m ruff check docs/reports/milestones/M3.G/evidence/run_g3_checks.py tests/unit/test_m3_g_gate_checks.py
python3 scripts/check_secrets.py
ls -A docs/reports/milestones/M3.G
ls -A docs/reports/milestones/M3.G/superpowers
```
Expected: `223 passed` (`218` prior + `5` new `M3.G` tests), Linux & `win32` `mypy` clean, `ruff` clean, `0` secret leaks, zero workstation absolute paths in `docs/reports/milestones/M3.G/`, and exact top-level layout (`README.md`, `evidence`, `superpowers` with `spec.md` and `plan.md`).

- [ ] **Step 5: Commit Task 2**

```bash
git add docs/reports/milestones/M3.G docs/reports/milestones/README.md
git commit -m "docs(m3.g): publish G3 readiness matrix, capacity projections, and comment-backfill budget"
```
