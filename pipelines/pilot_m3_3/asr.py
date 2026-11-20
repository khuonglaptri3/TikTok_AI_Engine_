from __future__ import annotations

import time
from pathlib import Path
from typing import Protocol, runtime_checkable

from packages.common.exceptions import IndexNotReadyError
from packages.common.resources import get_peak_rss_mib
from packages.data_contracts.multimodal import RawIncrementalVideoRecord, RawWhisperSegment
from pipelines.pilot_m3_3.models import AsrPilotReceipt


@runtime_checkable
class CpuAsrEngine(Protocol):
    model_id: str

    def transcribe_file(self, audio_path: Path) -> tuple[str, list[RawWhisperSegment]]: ...


class FasterWhisperCpuAsrEngine:
    """Lazy-loading CPU int8 faster-whisper ASR wrapper; fails closed if absent."""

    def __init__(self, model_size: str = "small", language: str = "vi") -> None:
        try:
            from faster_whisper import WhisperModel  # type: ignore[import-not-found]
        except ImportError as exc:
            raise IndexNotReadyError(
                "faster-whisper is required for CPU ASR execution in M3.3 live_pilot. Install faster-whisper first."
            ) from exc
        self._model = WhisperModel(model_size, device="cpu", compute_type="int8")
        self.model_id = f"faster-whisper/{model_size}-cpu-int8"
        self._language = language

    def transcribe_file(self, audio_path: Path) -> tuple[str, list[RawWhisperSegment]]:
        segments_iter, _ = self._model.transcribe(
            str(audio_path),
            language=self._language,
            beam_size=1,
            vad_filter=True,
        )
        segments: list[RawWhisperSegment] = []
        texts: list[str] = []
        for raw_seg in segments_iter:
            txt = str(getattr(raw_seg, "text", "") or "").strip()
            start_s = max(0.0, float(getattr(raw_seg, "start", 0.0)))
            end_s = float(getattr(raw_seg, "end", start_s))
            if not txt or end_s <= start_s:
                continue
            segments.append(
                RawWhisperSegment(
                    start_sec=round(start_s, 3),
                    end_sec=round(end_s, 3),
                    text=txt,
                )
            )
            texts.append(txt)
        return " ".join(texts).strip(), segments


class BoundedCpuAsrRunner:
    """Bounded CPU ASR pilot stage capped at <= 10 videos and <= 20.0 audio minutes."""

    def __init__(
        self,
        engine: CpuAsrEngine,
        *,
        max_videos: int = 10,
        max_audio_minutes: float = 20.0,
    ) -> None:
        if max_videos < 1 or max_videos > 10:
            raise ValueError("M3.3 limits CPU ASR pilot to <= 10 videos")
        if max_audio_minutes <= 0.0 or max_audio_minutes > 20.0:
            raise ValueError("M3.3 limits CPU ASR pilot to <= 20.0 audio minutes")
        self.engine = engine
        self.max_videos = max_videos
        self.max_audio_minutes = max_audio_minutes

    def run(
        self,
        records: list[RawIncrementalVideoRecord],
        batch_dir: Path,
    ) -> tuple[list[RawIncrementalVideoRecord], AsrPilotReceipt]:
        t0 = time.perf_counter()
        transcribed = 0
        skipped_no_audio = 0
        skipped_ceiling = 0
        failed = 0
        acc_audio_sec = 0.0

        updated: list[RawIncrementalVideoRecord] = []
        for rec in records:
            if not rec.audio_path:
                skipped_no_audio += 1
                updated.append(rec)
                continue
            audio_file = batch_dir / rec.audio_path
            if not audio_file.is_file() or audio_file.stat().st_size <= 0:
                skipped_no_audio += 1
                updated.append(rec.model_copy(update={"audio_path": None}))
                continue

            dur_sec = float(max(0, rec.duration_sec))
            item_min = dur_sec / 60.0
            if transcribed >= self.max_videos or (
                dur_sec > 0 and ((acc_audio_sec / 60.0) + item_min) > (self.max_audio_minutes + 1e-9)
            ):
                skipped_ceiling += 1
                updated.append(rec)
                continue

            try:
                transcript_text, segments = self.engine.transcribe_file(audio_file)
            except Exception:
                failed += 1
                updated.append(rec)
                continue

            transcribed += 1
            acc_audio_sec += dur_sec
            if transcript_text:
                updated.append(
                    rec.model_copy(
                        update={
                            "transcript": transcript_text,
                            "whisper_segments": segments,
                        }
                    )
                )
            else:
                updated.append(rec)

        wall_sec = round(max(0.0, time.perf_counter() - t0), 3)
        rtf = round(wall_sec / acc_audio_sec, 4) if acc_audio_sec > 0.0 else 0.0
        receipt = AsrPilotReceipt(
            engine_model_id=self.engine.model_id,
            max_videos_cap=self.max_videos,
            max_audio_minutes_cap=self.max_audio_minutes,
            transcribed_count=transcribed,
            skipped_no_audio_count=skipped_no_audio,
            skipped_asr_ceiling_count=skipped_ceiling,
            failed_count=failed,
            accumulated_audio_minutes=round(acc_audio_sec / 60.0, 3),
            wall_seconds=wall_sec,
            real_time_factor=rtf,
            peak_rss_mib=round(float(get_peak_rss_mib()), 2),
        )
        return updated, receipt
