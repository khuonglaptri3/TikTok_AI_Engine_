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
