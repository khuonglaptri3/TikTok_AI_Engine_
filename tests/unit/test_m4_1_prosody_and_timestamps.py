from __future__ import annotations

import math
from pathlib import Path

import numpy as np
import pytest


def test_prosody_feature_extraction_and_silence_abstention() -> None:
    from packages.prosody import PROSODY_DESCRIPTIVE_NOTE, extract_prosody_features

    sr = 16000
    # First 0.6s at ~130 Hz amplitude 0.2, next 0.6s at ~210 Hz amplitude 0.7 -> non-zero pitch_std & energy_cv
    t1 = np.arange(int(0.6 * sr), dtype=np.float32) / sr
    t2 = np.arange(int(0.6 * sr), dtype=np.float32) / sr
    sig1 = 0.2 * (np.sin(2 * np.pi * 130.0 * t1) + 0.4 * np.sin(2 * np.pi * 260.0 * t1))
    sig2 = 0.7 * (np.sin(2 * np.pi * 210.0 * t2) + 0.4 * np.sin(2 * np.pi * 420.0 * t2))
    audio = np.concatenate([sig1, sig2]).astype(np.float32)

    feats = extract_prosody_features(audio, sample_rate=sr)
    assert feats.duration_sec == pytest.approx(1.2, abs=0.01)
    assert feats.pitch_std is not None and math.isfinite(feats.pitch_std) and feats.pitch_std > 10.0
    assert feats.energy_cv is not None and math.isfinite(feats.energy_cv) and feats.energy_cv > 0.1
    assert feats.voiced_frame_count >= 10
    assert "descriptive" in PROSODY_DESCRIPTIVE_NOTE.lower()
    assert "intent" in PROSODY_DESCRIPTIVE_NOTE.lower()

    silence = np.zeros(int(0.5 * sr), dtype=np.float32)
    silent_feats = extract_prosody_features(silence, sample_rate=sr)
    assert silent_feats.pitch_std is None
    assert silent_feats.energy_cv is None
    assert silent_feats.voiced_frame_count == 0


def test_temporal_invariants_and_audio_derived_normalization() -> None:
    from packages.data_contracts.multimodal import VoiceSegmentRecord
    from packages.prosody import audit_temporal_invariants, normalize_timestamp_source

    assert normalize_timestamp_source("whisper_exact") == "audio_derived"
    assert normalize_timestamp_source("audio_derived") == "audio_derived"
    assert normalize_timestamp_source("wps_estimated") == "wps_estimated"
    with pytest.raises(ValueError):
        normalize_timestamp_source("exact_ground_truth")

    # VoiceSegmentRecord accepts both audio_derived and legacy whisper_exact
    seg_ok = VoiceSegmentRecord(
        segment_id="v1_s000",
        video_id="v1",
        seq_no=0,
        start_sec=0.5,
        end_sec=4.0,
        timestamp_source="audio_derived",
        text="Nước dùng đậm đà",
        words_per_sec=1.14,
    )
    assert seg_ok.timestamp_source == "audio_derived"

    segs = [
        {"segment_id": "v1_s000", "video_id": "v1", "start_sec": 0.0, "end_sec": 5.0, "timestamp_source": "whisper_exact", "text": "Câu một"},
        {"segment_id": "v1_s001", "video_id": "v1", "start_sec": 5.0, "end_sec": 10.4, "timestamp_source": "whisper_exact", "text": "Câu quá thời lượng"},
        {"segment_id": "v2_s000", "video_id": "v_missing", "start_sec": 0.0, "end_sec": 2.0, "timestamp_source": "wps_estimated", "text": "Thiếu video"},
        {"segment_id": "v1_s002", "video_id": "v1", "start_sec": 4.0, "end_sec": 4.0, "timestamp_source": "audio_derived", "text": "Độ dài bằng 0"},
    ]
    audit = audit_temporal_invariants(
        segs,
        media_duration_by_video={"v1": 10.0},
        known_video_ids={"v1"},
    )
    assert audit["total_segments"] == 4
    assert audit["valid_segments"] == 1
    assert audit["invariant_violation_count"] == 3
    assert audit["invariant_pass_rate"] == 0.25
    assert audit["meets_100pct_invariant_gate"] is False
    assert audit["timestamp_source_counts"] == {"audio_derived": 3, "wps_estimated": 1}


def test_cer_wer_boundary_evaluator_and_abstention_gate() -> None:
    from packages.prosody import (
        TOKENIZATION_SPEC,
        compute_levenshtein_distance,
        evaluate_m4_1_reference_set,
        tokenize_vi_chars,
        tokenize_vi_words,
    )

    assert "NFC" in TOKENIZATION_SPEC
    assert tokenize_vi_words("Nước dùng, rất NGON!!") == ["nước", "dùng", "rất", "ngon"]
    assert tokenize_vi_chars("Á, b!") == ["á", "b"]
    # Hand check: "nước dùng ngon" vs "nước lèo ngon lắm" -> 1 sub + 1 ins = 2 edits / 3 ref words = 0.6667
    edits, subs, dels, ins = compute_levenshtein_distance(
        tokenize_vi_words("Nước dùng ngon"),
        tokenize_vi_words("Nước lèo ngon lắm"),
    )
    assert (edits, subs, dels, ins) == (2, 1, 0, 1)

    passing_rows = [
        {
            "segment_id": f"v{i // 5}_s{i:03d}",
            "video_id": f"v{i // 5}",
            "audio_duration_sec": 18.0,
            "pred_start_sec": 1.0,
            "pred_end_sec": 4.0,
            "ref_start_sec": 1.2 if i % 2 == 0 else 1.5,
            "ref_end_sec": 4.1 if i % 2 == 0 else 4.4,
            "pred_text": "Phở bò tái nạm ngon lắm",
            "ref_text": "Phở bò tái nạm ngon lắm" if i < 45 else "Phở bò tái gân ngon lắm",
            "timestamp_source": "whisper_exact",
            "human_verified": True,
        }
        for i in range(50)
    ]
    res_pass = evaluate_m4_1_reference_set(
        passing_rows,
        is_real_human_verified=True,
        invariant_pass_rate=1.0,
    )
    assert res_pass["evaluated_utterance_count"] == 50
    assert res_pass["total_sampled_audio_minutes"] == pytest.approx(3.0, abs=0.01)
    assert res_pass["wer"] == pytest.approx(5.0 / 300.0, abs=1e-4)
    assert res_pass["boundary_median_abs_err_sec"] <= 1.0
    assert res_pass["boundary_p95_abs_err_sec"] <= 3.0
    assert res_pass["precise_playback_allowed"] is True
    assert res_pass["abstain_precise_playback"] is False

    # Fail closed if p95 > 3.0s (>= 6 out of 100 boundary errors > 3s) or fewer than 50 utterances
    failing_boundary = [dict(r) for r in passing_rows]
    for idx in range(6):
        failing_boundary[idx]["ref_end_sec"] = 9.5
    res_fail_p95 = evaluate_m4_1_reference_set(
        failing_boundary,
        is_real_human_verified=True,
        invariant_pass_rate=1.0,
    )
    assert res_fail_p95["boundary_p95_abs_err_sec"] > 3.0
    assert res_fail_p95["precise_playback_allowed"] is False
    assert res_fail_p95["abstain_precise_playback"] is True

    res_small = evaluate_m4_1_reference_set(
        passing_rows[:49],
        is_real_human_verified=True,
        invariant_pass_rate=1.0,
    )
    assert res_small["precise_playback_allowed"] is False
    assert res_small["abstain_precise_playback"] is True


def test_build_m4_1_reference_pool_enforces_20m_and_50utt_bounds() -> None:
    from packages.prosody import build_m4_1_reference_pool

    seg_rows = [
        {
            "segment_id": f"v{i // 10}_s{i:03d}",
            "video_id": f"v{i // 10}",
            "seq_no": i % 10,
            "start_sec": float((i % 10) * 8),
            "end_sec": float((i % 10) * 8 + 7),
            "timestamp_source": "whisper_exact",
            "text": f"Đoạn thoại review món số {i}",
        }
        for i in range(100)
    ]
    media_durations = {f"v{v}": 100.0 for v in range(10)}  # 10 videos * 100s = 16.67 min <= 20 min

    pool = build_m4_1_reference_pool(
        seg_rows,
        media_duration_by_video=media_durations,
        target_utterances=60,
        overlap_utterances=16,
        max_sampled_audio_minutes=20.0,
        seed=42,
    )
    assert len(pool) == 60
    sampled_vids = {r["video_id"] for r in pool}
    total_sampled_min = sum(media_durations[v] for v in sampled_vids) / 60.0
    assert total_sampled_min <= 20.0
    assert all(r["timestamp_provenance"] == "audio_derived" for r in pool)
    assert all(r["human_verified"] is False for r in pool)
    assert {r["review_assignment"] for r in pool} == {"double_review_N_K", "N_only", "K_only"}
    assert sum(1 for r in pool if r["review_assignment"] == "double_review_N_K") == 16

    # Reject pilot audio exceeding 60.0 min ceiling
    too_big = {f"v{v}": 400.0 for v in range(10)}  # 4000s = 66.67 min > 60 min
    with pytest.raises(ValueError, match="60"):
        build_m4_1_reference_pool(seg_rows, media_duration_by_video=too_big)


def test_run_m4_1_pilot_audit_fail_closed_and_receipt(tmp_path: Path) -> None:
    import json

    import pandas as pd

    from pipelines.audit_m4_1_audio import run_m4_1_pilot_audit

    corpus_dir = tmp_path / "gold"
    corpus_dir.mkdir()
    audio_dir = tmp_path / "audio_64k"
    audio_dir.mkdir()

    vids = [f"v{i}" for i in range(6)]
    pd.DataFrame([{"video_id": v, "has_transcript": True} for v in vids]).to_parquet(
        corpus_dir / "fact_videos.parquet", index=False
    )
    segs = [
        {
            "segment_id": f"{v}_s{s:03d}",
            "video_id": v,
            "seq_no": s,
            "start_sec": float(s * 6),
            "end_sec": float(s * 6 + 5),
            "timestamp_source": "whisper_exact",
            "text": f"Món ngon phần {s}",
        }
        for v in vids
        for s in range(10)
    ]
    pd.DataFrame(segs).to_parquet(corpus_dir / "fact_voice_segments.parquet", index=False)
    for v in vids:
        (audio_dir / f"{v}.mp3").write_bytes(b"fake-mp3-placeholder")

    def fake_decode(_p: Path) -> tuple[np.ndarray, float]:
        sr = 16000
        t = np.arange(sr * 65, dtype=np.float32) / sr
        wav = 0.4 * (np.sin(2 * np.pi * 160.0 * t) + 0.3 * np.sin(2 * np.pi * 320.0 * t))
        return wav.astype(np.float32), 65.0

    rec_path = tmp_path / "m4_1_rec.json"
    sheet_path = tmp_path / "m4_1_sheet.jsonl"
    receipt = run_m4_1_pilot_audit(
        corpus_dir=corpus_dir,
        audio_dir=audio_dir,
        output_receipt=rec_path,
        output_sheet=sheet_path,
        target_utterances=52,
        overlap_utterances=12,
        decode_fn=fake_decode,
    )
    assert receipt["audio_scope"]["processed_mp3_count"] == 6
    assert receipt["temporal_invariant_audit"]["meets_100pct_invariant_gate"] is True
    assert receipt["timestamp_provenance_labels_observed"] == ["audio_derived"]
    assert receipt["reference_review_pool"]["utterance_count"] == 52
    assert receipt["reference_evaluation_status"]["precise_playback_allowed"] is False
    assert receipt["reference_evaluation_status"]["abstain_precise_playback"] is True
    assert len([json.loads(line) for line in sheet_path.read_text(encoding="utf-8").splitlines() if line.strip()]) == 52

    with pytest.raises(FileExistsError):
        run_m4_1_pilot_audit(
            corpus_dir=corpus_dir,
            audio_dir=audio_dir,
            output_receipt=rec_path,
            output_sheet=tmp_path / "other.jsonl",
            decode_fn=fake_decode,
        )


def test_m4_1_k_review_strict_verified_bounds_pool_cap_and_iaa() -> None:
    from packages.prosody import compute_m4_1_annotator_agreement, evaluate_m4_1_reference_set

    base_rows = [
        {
            "segment_id": f"v{i // 10}_s{i:03d}",
            "video_id": f"v{i // 10}",
            "audio_duration_sec": 60.0,
            "pred_start_sec": 1.0,
            "pred_end_sec": 3.5,
            "ref_start_sec": 1.1,
            "ref_end_sec": 3.4,
            "pred_text": "Bánh xèo giòn rụm",
            "ref_text": "Bánh xèo giòn rụm",
            "human_verified": True,
        }
        for i in range(50)
    ]

    # 1. Incomplete or out-of-bounds human_verified row MUST fail closed
    missing_bounds = [dict(r) for r in base_rows]
    missing_bounds[0]["ref_start_sec"] = None
    res_missing = evaluate_m4_1_reference_set(
        missing_bounds,
        is_real_human_verified=True,
        invariant_pass_rate=1.0,
    )
    assert res_missing["invalid_verified_row_count"] == 1
    assert res_missing["evaluated_utterance_count"] == 49
    assert res_missing["precise_playback_allowed"] is False

    bad_end = [dict(r) for r in base_rows]
    bad_end[0]["ref_end_sec"] = 61.5  # exceeds audio_duration_sec=60.0
    res_bad_end = evaluate_m4_1_reference_set(
        bad_end,
        is_real_human_verified=True,
        invariant_pass_rate=1.0,
    )
    assert res_bad_end["invalid_verified_row_count"] == 1
    assert res_bad_end["precise_playback_allowed"] is False

    # 2. Unverified videos in an >20m sampled pool MUST NOT bypass max_sampled_audio_minutes
    oversized_pool = [dict(r) for r in base_rows] + [
        {
            "segment_id": "v_extra_s000",
            "video_id": "v_extra",
            "audio_duration_sec": 1000.0,  # +16.67 min -> total 21.67 min > 20.0 min
            "pred_start_sec": 0.0,
            "pred_end_sec": 2.0,
            "ref_start_sec": None,
            "ref_end_sec": None,
            "pred_text": "Chưa chấm",
            "ref_text": "",
            "human_verified": False,
        }
    ]
    res_oversized = evaluate_m4_1_reference_set(
        oversized_pool,
        is_real_human_verified=True,
        invariant_pass_rate=1.0,
    )
    assert res_oversized["total_sampled_audio_minutes"] > 20.0
    assert res_oversized["precise_playback_allowed"] is False

    # 3. Inter-annotator agreement over double_review_N_K rows
    overlap_rows = [
        {
            "segment_id": "u1",
            "review_assignment": "double_review_N_K",
            "N_verified": True,
            "N_ref_start_sec": 1.00,
            "N_ref_end_sec": 2.50,
            "N_ref_text": "Kẹp chả!",
            "K_verified": True,
            "K_ref_start_sec": 1.04,
            "K_ref_end_sec": 2.48,
            "K_ref_text": "kẹp chả",
        },
        {
            "segment_id": "u2",
            "review_assignment": "double_review_N_K",
            "N_verified": True,
            "N_ref_start_sec": 3.00,
            "N_ref_end_sec": 4.80,
            "N_ref_text": "trending Hà Nội trên Đà Lạt",
            "K_verified": True,
            "K_ref_start_sec": 3.12,
            "K_ref_end_sec": 4.66,
            "K_ref_text": "trending họ nói trên Đà Lạt",
        },
    ]
    iaa = compute_m4_1_annotator_agreement(overlap_rows)
    assert iaa["double_review_total"] == 2
    assert iaa["both_verified_count"] == 2
    assert iaa["exact_normalized_text_match_count"] == 1
    assert iaa["exact_normalized_text_match_rate"] == 0.5
    assert iaa["inter_annotator_wer"] == pytest.approx(2.0 / 8.0, abs=1e-4)
    assert iaa["boundary_median_abs_diff_sec"] == pytest.approx(0.08, abs=1e-4)
    assert len(iaa["text_disagreements"]) == 1
    assert iaa["text_disagreements"][0]["segment_id"] == "u2"


