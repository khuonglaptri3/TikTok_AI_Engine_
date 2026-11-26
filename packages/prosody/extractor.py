from __future__ import annotations

import math
import shutil
import subprocess
import sys
from collections.abc import Iterable, Mapping, Sequence
from dataclasses import dataclass
from pathlib import Path
from typing import Any, Literal

import numpy as np

TimestampProvenance = Literal["audio_derived", "wps_estimated"]

PROSODY_DESCRIPTIVE_NOTE = (
    "Descriptive acoustic variation metrics (pitch_std, energy_cv, words_per_sec); "
    "never proof of speaker intent, emotion certainty, or undisclosed sponsorship."
)


@dataclass(frozen=True)
class ProsodyFeatures:
    """Finite descriptive prosody summary for a decoded mono 16kHz audio slice."""

    duration_sec: float
    voiced_frame_count: int
    active_frame_count: int
    pitch_std: float | None
    energy_cv: float | None


def _resolve_ffmpeg_bin() -> str:
    venv_ffmpeg = Path(sys.executable).parent / "ffmpeg"
    if venv_ffmpeg.is_file():
        return str(venv_ffmpeg)
    found = shutil.which("ffmpeg")
    if found:
        return found
    raise FileNotFoundError("ffmpeg binary is required for 16kHz PCM audio decoding")


def decode_audio_pcm_16k(audio_path: Path, *, sample_rate: int = 16000) -> tuple[np.ndarray, float]:
    """Decode compressed audio (.mp3/.m4a) to mono float32 PCM and exact decoded duration in seconds."""
    if not audio_path.is_file():
        raise FileNotFoundError(f"Audio file not found: {audio_path}")
    ffmpeg_bin = _resolve_ffmpeg_bin()
    cmd = [
        ffmpeg_bin,
        "-nostdin",
        "-v",
        "error",
        "-i",
        str(audio_path),
        "-f",
        "f32le",
        "-acodec",
        "pcm_f32le",
        "-ac",
        "1",
        "-ar",
        str(sample_rate),
        "-",
    ]
    res = subprocess.run(cmd, capture_output=True, check=False)
    if res.returncode != 0:
        err = (res.stderr or b"").decode("utf-8", errors="replace").strip()
        raise RuntimeError(f"ffmpeg decode failed for {audio_path.name}: {err[:240]}")
    samples = np.frombuffer(res.stdout, dtype=np.float32)
    duration_sec = round(float(len(samples) / float(sample_rate)), 4)
    return samples, duration_sec


def extract_prosody_features(
    samples: np.ndarray,
    *,
    sample_rate: int = 16000,
    min_f0_hz: float = 70.0,
    max_f0_hz: float = 380.0,
) -> ProsodyFeatures:
    """Compute bounded descriptive energy_cv and autocorrelation F0 pitch_std over mono audio."""
    if sample_rate <= 0:
        raise ValueError("sample_rate must be positive")
    clean = np.asarray(samples, dtype=np.float32)
    duration_sec = round(float(len(clean) / float(sample_rate)), 4)
    if clean.size == 0 or duration_sec <= 0.0:
        return ProsodyFeatures(
            duration_sec=0.0,
            voiced_frame_count=0,
            active_frame_count=0,
            pitch_std=None,
            energy_cv=None,
        )

    frame_len = max(160, int(round(0.030 * sample_rate)))
    hop_len = max(80, int(round(0.010 * sample_rate)))
    if len(clean) < frame_len:
        rms = float(np.sqrt(np.mean(np.square(clean))))
        return ProsodyFeatures(
            duration_sec=duration_sec,
            voiced_frame_count=0,
            active_frame_count=1 if rms > 1e-4 else 0,
            pitch_std=None,
            energy_cv=None,
        )

    frames = np.lib.stride_tricks.sliding_window_view(clean, frame_len)[::hop_len]
    rms_vals = np.sqrt(np.mean(np.square(frames), axis=1))
    peak_rms = float(np.max(rms_vals)) if rms_vals.size > 0 else 0.0
    if peak_rms <= 1e-4 or not math.isfinite(peak_rms):
        return ProsodyFeatures(
            duration_sec=duration_sec,
            voiced_frame_count=0,
            active_frame_count=0,
            pitch_std=None,
            energy_cv=None,
        )

    noise_floor = max(1e-4, peak_rms * 0.08)
    active_mask = rms_vals >= noise_floor
    active_rms = rms_vals[active_mask]
    active_count = int(active_rms.size)

    energy_cv: float | None = None
    if active_count >= 3:
        mean_e = float(np.mean(active_rms))
        if mean_e > 0.0:
            raw_cv = float(np.std(active_rms) / mean_e)
            if math.isfinite(raw_cv):
                energy_cv = round(raw_cv, 4)

    min_lag = max(2, int(math.floor(sample_rate / max_f0_hz)))
    max_lag = min(frame_len // 2, int(math.ceil(sample_rate / min_f0_hz)))
    voiced_f0: list[float] = []
    if max_lag > min_lag:
        for idx, is_active in enumerate(active_mask):
            if not is_active:
                continue
            frame = frames[idx] - float(np.mean(frames[idx]))
            energy = float(np.dot(frame, frame))
            if energy <= 1e-9:
                continue
            corr = np.correlate(frame, frame, mode="full")[frame_len - 1 :]
            seg = corr[min_lag : max_lag + 1] / energy
            if seg.size == 0:
                continue
            best_idx = int(np.argmax(seg))
            if float(seg[best_idx]) >= 0.35:
                lag = min_lag + best_idx
                f0 = float(sample_rate) / float(lag)
                if math.isfinite(f0):
                    voiced_f0.append(f0)

    pitch_std: float | None = None
    if len(voiced_f0) >= 5:
        raw_std = float(np.std(np.asarray(voiced_f0, dtype=np.float64)))
        if math.isfinite(raw_std):
            pitch_std = round(raw_std, 4)

    return ProsodyFeatures(
        duration_sec=duration_sec,
        voiced_frame_count=len(voiced_f0),
        active_frame_count=active_count,
        pitch_std=pitch_std,
        energy_cv=energy_cv,
    )


def normalize_timestamp_source(raw_source: str) -> TimestampProvenance:
    """Map ASR timestamps ('whisper_exact' / 'audio_derived') strictly to 'audio_derived' estimates."""
    clean = str(raw_source or "").strip().lower()
    if clean in {"audio_derived", "whisper_exact"}:
        return "audio_derived"
    if clean == "wps_estimated":
        return "wps_estimated"
    raise ValueError(
        f"Unsupported timestamp_source {raw_source!r}; expected 'audio_derived', 'whisper_exact', or 'wps_estimated'"
    )


def audit_temporal_invariants(
    segments: Sequence[Mapping[str, Any]],
    *,
    media_duration_by_video: Mapping[str, float],
    known_video_ids: Iterable[str] | None = None,
) -> dict[str, Any]:
    """Enforce 0 <= start < end <= media_duration and 100% source resolvability across utterances."""
    known_set = (
        {str(v).strip() for v in known_video_ids if str(v).strip()}
        if known_video_ids is not None
        else set(media_duration_by_video.keys())
    )
    total = len(segments)
    valid = 0
    violations: list[dict[str, Any]] = []
    source_counts: dict[str, int] = {"audio_derived": 0, "wps_estimated": 0}

    for seg in segments:
        vid = str(seg.get("video_id") or "").strip()
        sid = str(seg.get("segment_id") or "").strip()
        txt = str(seg.get("text") or "").strip()
        raw_src = str(seg.get("timestamp_source") or "").strip()
        reason: str | None = None

        try:
            norm_src = normalize_timestamp_source(raw_src)
            source_counts[norm_src] = source_counts.get(norm_src, 0) + 1
        except ValueError:
            reason = "invalid_timestamp_source"

        start_val = seg.get("start_sec")
        end_val = seg.get("end_sec")
        if reason is None:
            if not vid or vid not in known_set:
                reason = "unresolvable_video_id"
            elif not sid or not txt:
                reason = "blank_segment_id_or_text"
            elif vid not in media_duration_by_video:
                reason = "missing_media_duration"
            elif start_val is None or end_val is None:
                reason = "missing_timestamp_bounds"
            else:
                s = float(start_val)
                e = float(end_val)
                dur = float(media_duration_by_video[vid])
                if not (math.isfinite(s) and math.isfinite(e) and math.isfinite(dur)):
                    reason = "nonfinite_timestamp"
                elif s < 0.0:
                    reason = "negative_start_sec"
                elif e <= s:
                    reason = "non_positive_segment_duration"
                elif e > dur:
                    reason = "end_exceeds_media_duration"

        if reason is None:
            valid += 1
        else:
            violations.append(
                {
                    "segment_id": sid,
                    "video_id": vid,
                    "start_sec": start_val,
                    "end_sec": end_val,
                    "media_duration_sec": media_duration_by_video.get(vid),
                    "reason": reason,
                }
            )

    pass_rate = round(valid / total, 4) if total > 0 else 0.0
    return {
        "total_segments": total,
        "valid_segments": valid,
        "invariant_violation_count": total - valid,
        "invariant_pass_rate": pass_rate,
        "meets_100pct_invariant_gate": (total > 0 and valid == total),
        "timestamp_source_counts": source_counts,
        "violations_sample": violations[:20],
    }
