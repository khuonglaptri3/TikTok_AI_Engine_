from __future__ import annotations

import argparse
import json
import time
from collections.abc import Callable
from datetime import UTC, datetime
from pathlib import Path
from typing import Any

import numpy as np
import pandas as pd

from packages.common.resources import get_peak_rss_mib
from packages.prosody import (
    PROSODY_DESCRIPTIVE_NOTE,
    TOKENIZATION_SPEC,
    audit_temporal_invariants,
    build_m4_1_reference_pool,
    decode_audio_pcm_16k,
    evaluate_m4_1_reference_set,
    extract_prosody_features,
    normalize_timestamp_source,
)

MAX_PILOT_AUDIO_MINUTES = 60.0
MAX_CPU_WALL_SECONDS = 14_400.0  # 4 CPU hours
MAX_PEAK_RSS_MIB = 8_192.0  # 8 GiB


def run_m4_1_pilot_audit(
    *,
    corpus_dir: Path,
    audio_dir: Path,
    output_receipt: Path,
    output_sheet: Path,
    m3_3_receipt_path: Path | None = None,
    target_utterances: int = 60,
    overlap_utterances: int = 16,
    max_sampled_audio_minutes: float = 20.0,
    seed: int = 42,
    decode_fn: Callable[[Path], tuple[np.ndarray, float]] = decode_audio_pcm_16k,
) -> dict[str, Any]:
    """Process <=60m pilot MP3 audio on CPU, audit temporal invariants, and export >=50-utterance sheet."""
    if output_receipt.exists():
        raise FileExistsError(f"Output receipt already exists: {output_receipt}")
    if output_sheet.exists():
        raise FileExistsError(f"Output review sheet already exists: {output_sheet}")

    t0 = time.perf_counter()
    fact_videos = pd.read_parquet(corpus_dir / "fact_videos.parquet", columns=["video_id", "has_transcript"])
    known_vids = set(fact_videos["video_id"].astype(str).tolist())

    fvs_path = corpus_dir / "fact_voice_segments.parquet"
    fvs_df = pd.read_parquet(fvs_path) if fvs_path.is_file() else pd.DataFrame()
    seg_records = fvs_df.to_dict("records") if not fvs_df.empty else []

    segs_by_vid: dict[str, list[dict[str, Any]]] = {}
    for seg in seg_records:
        vid = str(seg.get("video_id") or "").strip()
        if vid:
            segs_by_vid.setdefault(vid, []).append(seg)

    mp3_files = sorted(audio_dir.glob("*.mp3"))
    if not mp3_files:
        raise FileNotFoundError(f"No .mp3 files found under {audio_dir}")

    media_durations: dict[str, float] = {}
    video_prosody_rows: list[dict[str, Any]] = []
    segment_prosody_computed = 0
    segment_pitch_non_null = 0
    segment_energy_non_null = 0
    total_audio_bytes = 0
    accumulated_audio_sec = 0.0

    for mp3_path in mp3_files:
        vid = mp3_path.stem.strip()
        total_audio_bytes += mp3_path.stat().st_size
        samples, dur_sec = decode_fn(mp3_path)
        if (accumulated_audio_sec + dur_sec) / 60.0 > MAX_PILOT_AUDIO_MINUTES + 1e-9:
            raise ValueError(
                f"Accumulated pilot audio exceeds {MAX_PILOT_AUDIO_MINUTES}-minute budget at {mp3_path.name}"
            )
        accumulated_audio_sec += dur_sec
        media_durations[vid] = dur_sec

        v_feats = extract_prosody_features(samples, sample_rate=16000)
        video_prosody_rows.append(
            {
                "video_id": vid,
                "audio_bytes": int(mp3_path.stat().st_size),
                "decoded_duration_sec": dur_sec,
                "voiced_frame_count": v_feats.voiced_frame_count,
                "active_frame_count": v_feats.active_frame_count,
                "pitch_std": v_feats.pitch_std,
                "energy_cv": v_feats.energy_cv,
            }
        )

        for seg in segs_by_vid.get(vid, []):
            s_idx = max(0, int(round(float(seg.get("start_sec") or 0.0) * 16000)))
            e_idx = min(len(samples), int(round(float(seg.get("end_sec") or 0.0) * 16000)))
            if e_idx > s_idx:
                s_feats = extract_prosody_features(samples[s_idx:e_idx], sample_rate=16000)
                segment_prosody_computed += 1
                if s_feats.pitch_std is not None:
                    segment_pitch_non_null += 1
                if s_feats.energy_cv is not None:
                    segment_energy_non_null += 1

        if (time.perf_counter() - t0) > MAX_CPU_WALL_SECONDS:
            raise RuntimeError("M4.1 pilot wall-time exceeded 4 CPU hours ceiling")

    invariant_audit = audit_temporal_invariants(
        seg_records,
        media_duration_by_video=media_durations,
        known_video_ids=known_vids,
    )

    pool_rows = build_m4_1_reference_pool(
        seg_records,
        media_duration_by_video=media_durations,
        target_utterances=target_utterances,
        overlap_utterances=overlap_utterances,
        max_pilot_audio_minutes=MAX_PILOT_AUDIO_MINUTES,
        max_sampled_audio_minutes=max_sampled_audio_minutes,
        seed=seed,
    )

    # Current pre-annotation evaluation cleanly abstains (0 human_verified rows)
    current_ref_eval = evaluate_m4_1_reference_set(
        pool_rows,
        is_real_human_verified=False,
        invariant_pass_rate=float(invariant_audit["invariant_pass_rate"]),
    )

    wall_seconds = round(time.perf_counter() - t0, 3)
    peak_rss_mib = round(float(get_peak_rss_mib()), 2)
    if peak_rss_mib > MAX_PEAK_RSS_MIB:
        raise MemoryError(
            f"Peak RSS {peak_rss_mib} MiB exceeded {MAX_PEAK_RSS_MIB} MiB pilot ceiling"
        )

    m3_3_asr_info: dict[str, Any] = {}
    if m3_3_receipt_path is not None and m3_3_receipt_path.is_file():
        m3_3_data = json.loads(m3_3_receipt_path.read_text(encoding="utf-8"))
        m3_3_asr_info = dict(m3_3_data.get("asr") or {})

    total_audio_min = round(accumulated_audio_sec / 60.0, 3)
    prosody_rtf = (
        round(wall_seconds / accumulated_audio_sec, 4) if accumulated_audio_sec > 0.0 else 0.0
    )

    valid_video_pitch = [float(r["pitch_std"]) for r in video_prosody_rows if r["pitch_std"] is not None]
    valid_video_energy = [float(r["energy_cv"]) for r in video_prosody_rows if r["energy_cv"] is not None]

    provenance_labels = sorted(
        {normalize_timestamp_source(str(s.get("timestamp_source") or "")) for s in seg_records}
    )
    sampled_vids = sorted({str(r["video_id"]) for r in pool_rows})
    sampled_min = round(sum(media_durations[v] for v in sampled_vids) / 60.0, 3)

    receipt: dict[str, Any] = {
        "task_id": "M4.1",
        "status": "IN_PROGRESS",
        "executed_at_utc": datetime.now(UTC).isoformat(),
        "descriptive_prosody_note": PROSODY_DESCRIPTIVE_NOTE,
        "tokenization_spec": TOKENIZATION_SPEC,
        "timestamp_provenance_labels_observed": provenance_labels,
        "audio_scope": {
            "processed_mp3_count": len(video_prosody_rows),
            "total_audio_seconds": round(accumulated_audio_sec, 2),
            "total_audio_minutes": total_audio_min,
            "max_pilot_audio_minutes_cap": MAX_PILOT_AUDIO_MINUTES,
            "within_60m_cap": total_audio_min <= MAX_PILOT_AUDIO_MINUTES,
            "audio_disk_bytes": total_audio_bytes,
        },
        "prosody_extraction_summary": {
            "videos_with_pitch_std": len(valid_video_pitch),
            "videos_with_energy_cv": len(valid_video_energy),
            "median_video_pitch_std_hz": round(float(np.median(valid_video_pitch)), 4)
            if valid_video_pitch
            else None,
            "median_video_energy_cv": round(float(np.median(valid_video_energy)), 4)
            if valid_video_energy
            else None,
            "utterances_processed": segment_prosody_computed,
            "utterances_with_pitch_std": segment_pitch_non_null,
            "utterances_with_energy_cv": segment_energy_non_null,
        },
        "temporal_invariant_audit": invariant_audit,
        "reference_review_pool": {
            "sheet_path": (
                output_sheet.name if output_sheet.is_absolute() else output_sheet.as_posix()
            ),
            "utterance_count": len(pool_rows),
            "unique_video_count": len(sampled_vids),
            "sampled_audio_minutes": sampled_min,
            "within_20m_cap": sampled_min <= max_sampled_audio_minutes + 1e-9,
            "assignment_counts": {
                k: sum(1 for r in pool_rows if r["review_assignment"] == k)
                for k in ("double_review_N_K", "N_only", "K_only")
            },
            "human_verified_count": sum(1 for r in pool_rows if r.get("human_verified") is True),
        },
        "reference_evaluation_status": current_ref_eval,
        "resources": {
            "prosody_wall_seconds": wall_seconds,
            "prosody_real_time_factor": prosody_rtf,
            "m3_3_asr_engine": m3_3_asr_info.get("engine_model_id", "faster-whisper/small-cpu-int8"),
            "m3_3_asr_wall_seconds": m3_3_asr_info.get("wall_seconds"),
            "m3_3_asr_real_time_factor": m3_3_asr_info.get("real_time_factor"),
            "peak_rss_mib": peak_rss_mib,
            "within_4h_cpu_budget": wall_seconds <= MAX_CPU_WALL_SECONDS,
            "within_8gib_ram_budget": peak_rss_mib <= MAX_PEAK_RSS_MIB,
        },
        "per_video_prosody": video_prosody_rows,
    }

    output_sheet.parent.mkdir(parents=True, exist_ok=True)
    output_receipt.parent.mkdir(parents=True, exist_ok=True)
    with output_sheet.open("x", encoding="utf-8") as fp_sheet:
        for row in pool_rows:
            fp_sheet.write(json.dumps(row, ensure_ascii=False) + "\n")
    with output_receipt.open("x", encoding="utf-8") as fp_rec:
        fp_rec.write(json.dumps(receipt, ensure_ascii=False, indent=2) + "\n")
    return receipt


def main() -> None:
    parser = argparse.ArgumentParser(description="Run M4.1 CPU prosody & temporal invariant audit.")
    parser.add_argument(
        "--corpus-dir",
        type=Path,
        default=Path("data/corpus/m3_3_pilot_snapshot_v1"),
    )
    parser.add_argument(
        "--audio-dir",
        type=Path,
        default=Path("data/raw_incremental/m3_3_pilot_run/batch/audio_64k"),
    )
    parser.add_argument(
        "--m3-3-receipt",
        type=Path,
        default=Path("docs/reports/milestones/M3.3/evidence/m3_3_pilot_receipt.json"),
    )
    parser.add_argument(
        "--output-receipt",
        type=Path,
        default=Path("docs/reports/milestones/M4.1/evidence/m4_1_audio_pilot_receipt.json"),
    )
    parser.add_argument(
        "--output-sheet",
        type=Path,
        default=Path("docs/reports/milestones/M4.1/evidence/m4_1_utterance_review_sheet.jsonl"),
    )
    parser.add_argument("--target-utterances", type=int, default=60)
    parser.add_argument("--overlap-utterances", type=int, default=16)
    parser.add_argument("--seed", type=int, default=42)
    args = parser.parse_args()

    res = run_m4_1_pilot_audit(
        corpus_dir=args.corpus_dir,
        audio_dir=args.audio_dir,
        output_receipt=args.output_receipt,
        output_sheet=args.output_sheet,
        m3_3_receipt_path=args.m3_3_receipt,
        target_utterances=args.target_utterances,
        overlap_utterances=args.overlap_utterances,
        seed=args.seed,
    )
    inv = res["temporal_invariant_audit"]
    pool = res["reference_review_pool"]
    print(
        f"PASS: wrote {args.output_receipt} & {args.output_sheet} ("
        f"mp3s={res['audio_scope']['processed_mp3_count']}, "
        f"audio_min={res['audio_scope']['total_audio_minutes']}, "
        f"inv_rate={inv['invariant_pass_rate']}, "
        f"pool_utts={pool['utterance_count']}, "
        f"precise_playback_allowed={res['reference_evaluation_status']['precise_playback_allowed']})"
    )


if __name__ == "__main__":
    main()
