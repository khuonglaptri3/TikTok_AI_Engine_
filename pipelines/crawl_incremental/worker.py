from __future__ import annotations

import hashlib
import json
import math
import os
import re
import time
from collections.abc import Callable
from datetime import UTC, datetime
from pathlib import Path
from typing import Any

from packages.common.logging import StageTimer, redact_secrets
from packages.data_contracts.multimodal import RawCommentInput, RawIncrementalVideoRecord
from pipelines.crawl_incremental.crawler_service import (
    compute_cutoff_utc,
    is_within_rolling_window,
    write_incremental_batch,
)
from pipelines.crawl_incremental.models import (
    AudioConversionReceipt,
    CollectorBounds,
    CollectorCheckpoint,
    CollectorItemReceipt,
    CrawlManifest,
)
from pipelines.crawl_incremental.providers import (
    AntiBotChallengeError,
    AudioConverter,
    CollectorProvider,
    TransientCollectorError,
)

_COLLECTOR_SECRET_NAMES = (
    r"ms[_-]?token|mstoken|cookie|sessionid(?:_ss)?|sid_tt|sid_guard|"
    r"uid_tt(?:_ss)?|ttwid|odin_tt|passport_csrf_token|csrf[_-]?token"
)
_HTTP_COOKIE_HEADER_RE = re.compile(
    r"(?i)(\bcookie\s*:\s*)(?:[A-Za-z0-9_.-]+=[^\s;\"',]+(?:;\s*)?)+"
)
_COLLECTOR_QUOTED_KV_SECRET_RE = re.compile(
    rf"(?i)(['\"]?)\b({_COLLECTOR_SECRET_NAMES})\b\1(\s*[=:]\s*)(['\"]).*?\4"
)
_COLLECTOR_KV_SECRET_RE = re.compile(
    rf"(?i)(['\"]?)\b({_COLLECTOR_SECRET_NAMES})\b\1(\s*[=:]\s*)([^\s&\"'`,;\]\}}]+)"
)
_COOKIES_FILE_ARG_RE = re.compile(
    r"(--cookies(?:\s+|=))(?:'[^']*'|\"[^\"]*\"|[^\s,;]+)"
)


class _PostDetailSkip(Exception):
    """Internal control-flow signal when detail inspection reveals a skip condition."""

    def __init__(self, reason: str, iso_ct: str | None = None) -> None:
        super().__init__(reason)
        self.reason = reason
        self.iso_ct = iso_ct


class _PostDetailPermanentFail(Exception):
    """Internal control-flow signal for non-retryable post-detail timestamp failures."""

    def __init__(self, reason: str) -> None:
        super().__init__(reason)
        self.reason = reason


def _sanitize_text_preserve_length(text: str) -> str:
    out = _COOKIES_FILE_ARG_RE.sub(r"\1[REDACTED]", text)
    out = _HTTP_COOKIE_HEADER_RE.sub(r"\1[REDACTED]", out)
    out = _COLLECTOR_QUOTED_KV_SECRET_RE.sub(r"\1\2\1\3\4[REDACTED]\4", out)
    out = _COLLECTOR_KV_SECRET_RE.sub(r"\1\2\1\3[REDACTED]", out)
    return redact_secrets(out)


def _sanitize_reason(text: str) -> str:
    # Apply collector-specific quoted, unquoted, multi-cookie, and --cookies path redaction BEFORE generic redact_secrets
    return _sanitize_text_preserve_length(text)[:280]


_RAW_PAYLOAD_DROP_KEYS = frozenset({"formats", "requested_downloads", "requested_formats"})
_RAW_PAYLOAD_REDACT_KEYS = frozenset(
    {
        "cookie",
        "cookies",
        "ms_token",
        "mstoken",
        "sessionid",
        "sessionid_ss",
        "sid_tt",
        "sid_guard",
        "uid_tt",
        "uid_tt_ss",
        "ttwid",
        "odin_tt",
        "passport_csrf_token",
        "csrf_token",
        "authorization",
        "cookies_file",
    }
)


def _sanitize_raw_payload(obj: Any) -> Any:
    if isinstance(obj, dict):
        cleaned: dict[str, Any] = {}
        for raw_k, raw_v in obj.items():
            key_str = str(raw_k)
            key_low = key_str.lower()
            if key_low in _RAW_PAYLOAD_DROP_KEYS:
                continue
            if key_low in _RAW_PAYLOAD_REDACT_KEYS:
                cleaned[key_str] = "[REDACTED]"
            else:
                cleaned[key_str] = _sanitize_raw_payload(raw_v)
        return cleaned
    if isinstance(obj, list):
        return [_sanitize_raw_payload(item) for item in obj]
    if isinstance(obj, str):
        return _sanitize_text_preserve_length(obj)
    return obj


def _atomic_write_json(path: Path, payload: dict[str, Any]) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    tmp_path = path.with_suffix(path.suffix + ".tmp")
    tmp_path.write_text(
        json.dumps(payload, ensure_ascii=False, indent=2) + "\n",
        encoding="utf-8",
    )
    os.replace(tmp_path, path)


def _write_raw_payload_archive(
    raw_by_id: dict[str, dict[str, Any]],
    output_dir: Path,
) -> None:
    if not raw_by_id:
        return
    output_dir.mkdir(parents=True, exist_ok=True)
    target = output_dir / "raw_provider_payloads.jsonl"
    tmp_target = output_dir / "raw_provider_payloads.jsonl.tmp"
    with tmp_target.open("w", encoding="utf-8") as fp:
        for entry in raw_by_id.values():
            fp.write(json.dumps(entry, ensure_ascii=False) + "\n")
    os.replace(tmp_target, target)


def _load_existing_raw_payload_archive(path: Path, allowed_ids: set[str]) -> dict[str, dict[str, Any]]:
    out: dict[str, dict[str, Any]] = {}
    if not path.is_file():
        return out
    for line in path.read_text(encoding="utf-8").splitlines():
        if not line.strip():
            continue
        try:
            obj = json.loads(line)
        except json.JSONDecodeError:
            continue
        vid = str(obj.get("video_id") or "").strip()
        if vid and vid in allowed_ids:
            out[vid] = obj
    return out


def _interleave_candidates_by_creator(candidates: list[dict[str, Any]]) -> list[dict[str, Any]]:
    """Round-robin interleave candidates across creators so creator #1 never starves creators #2..#5."""
    if len(candidates) <= 1:
        return list(candidates)
    buckets: dict[str, list[dict[str, Any]]] = {}
    order: list[str] = []
    for cand in candidates:
        key = str(cand.get("author_handle") or "").lstrip("@").strip().lower()
        if key not in buckets:
            buckets[key] = []
            order.append(key)
        buckets[key].append(cand)
    if len(order) <= 1:
        return list(candidates)
    interleaved: list[dict[str, Any]] = []
    max_len = max(len(b) for b in buckets.values())
    for idx in range(max_len):
        for key in order:
            bucket = buckets[key]
            if idx < len(bucket):
                interleaved.append(bucket[idx])
    return interleaved


def _has_non_empty_timestamp_value(raw_ct: Any) -> bool:
    if raw_ct is None:
        return False
    if isinstance(raw_ct, bool):
        return True
    return str(raw_ct).strip() != ""


def _parse_iso_create_time(raw_ct: Any) -> str | None:
    if raw_ct is None or isinstance(raw_ct, bool):
        return None
    try:
        if isinstance(raw_ct, int | float):
            fval = float(raw_ct)
            if not math.isfinite(fval):
                return None
            return datetime.fromtimestamp(fval, tz=UTC).isoformat()
        text = str(raw_ct).strip()
        if not text:
            return None
        if text.isdigit():
            return datetime.fromtimestamp(float(text), tz=UTC).isoformat()
        dt = datetime.fromisoformat(text.replace("Z", "+00:00"))
        if dt.tzinfo is None:
            dt = dt.replace(tzinfo=UTC)
        return dt.isoformat()
    except (ValueError, OSError, OverflowError):
        return None


class BoundedIncrementalCollector:
    """Invoked bounded collector enforcing 120d cutoff, historical skip, retries, audio receipts, and resume."""

    def __init__(
        self,
        provider: CollectorProvider,
        audio_converter: AudioConverter,
        bounds: CollectorBounds | None = None,
        sleep_fn: Callable[[float], None] = time.sleep,
    ) -> None:
        self.provider = provider
        self.audio_converter = audio_converter
        self.bounds = bounds or CollectorBounds()
        self.sleep_fn = sleep_fn

    @staticmethod
    def _load_existing_batch_records(jsonl_path: Path) -> dict[str, RawIncrementalVideoRecord]:
        records: dict[str, RawIncrementalVideoRecord] = {}
        if not jsonl_path.is_file():
            return records
        for line in jsonl_path.read_text(encoding="utf-8").splitlines():
            if not line.strip():
                continue
            try:
                rec = RawIncrementalVideoRecord.model_validate(json.loads(line))
            except Exception:
                continue
            records[rec.video_id] = rec
        return records

    def _convert_audio_with_bounds(
        self,
        vid: str,
        detail: dict[str, Any],
        output_dir: Path,
        accumulated_audio_min: float,
    ) -> tuple[AudioConversionReceipt, str | None, float]:
        dur_sec = max(0, int(detail.get("duration_sec") or 0))
        item_min = dur_sec / 60.0
        if self.bounds.max_audio_minutes <= 0.0 or (
            dur_sec > 0 and (accumulated_audio_min + item_min) > self.bounds.max_audio_minutes + 1e-9
        ):
            return (
                AudioConversionReceipt(
                    status="skipped_audio_ceiling",
                    reason="max_audio_minutes_ceiling_reached",
                ),
                None,
                0.0,
            )

        rel_audio = f"audio_64k/{vid}.mp3"
        target_mp3 = output_dir / rel_audio
        if target_mp3.exists():
            target_mp3.unlink()
        try:
            ok = self.audio_converter.extract_mp3_64k(detail, target_mp3)
        except (TransientCollectorError, AntiBotChallengeError):
            if target_mp3.exists():
                target_mp3.unlink()
            raise
        except Exception as exc:
            if target_mp3.exists():
                target_mp3.unlink()
            return (
                AudioConversionReceipt(
                    status="failed",
                    reason=_sanitize_reason(str(exc)),
                ),
                None,
                0.0,
            )

        if ok and target_mp3.is_file() and target_mp3.stat().st_size > 0:
            raw_bytes = target_mp3.read_bytes()
            return (
                AudioConversionReceipt(
                    status="converted_64k_mp3",
                    target_bitrate_kbps=64,
                    audio_path=rel_audio,
                    audio_bytes=len(raw_bytes),
                    audio_sha256=hashlib.sha256(raw_bytes).hexdigest(),
                ),
                rel_audio,
                item_min,
            )

        if target_mp3.exists():
            target_mp3.unlink()
        return (
            AudioConversionReceipt(
                status="unavailable",
                reason="audio_source_or_extractor_unavailable",
            ),
            None,
            0.0,
        )

    def run(
        self,
        output_dir: Path,
        as_of_utc: datetime | None = None,
        historical_video_ids: set[str] | None = None,
        base_corpus_snapshot_id: str = "20261118_taxonomy_fix_v1",
        creators: list[str] | None = None,
        resume: bool = False,
    ) -> CrawlManifest:
        try:
            return self._run_inner(
                output_dir=output_dir,
                as_of_utc=as_of_utc,
                historical_video_ids=historical_video_ids,
                base_corpus_snapshot_id=base_corpus_snapshot_id,
                creators=creators,
                resume=resume,
            )
        finally:
            close_fn = getattr(self.provider, "close", None)
            if callable(close_fn):
                close_fn()

    def _run_inner(
        self,
        output_dir: Path,
        as_of_utc: datetime | None = None,
        historical_video_ids: set[str] | None = None,
        base_corpus_snapshot_id: str = "20261118_taxonomy_fix_v1",
        creators: list[str] | None = None,
        resume: bool = False,
    ) -> CrawlManifest:
        timer = StageTimer()
        session_t0 = time.monotonic()
        effective_as_of = as_of_utc or datetime.now(UTC)
        if effective_as_of.tzinfo is None:
            effective_as_of = effective_as_of.replace(tzinfo=UTC)
        cutoff_utc = compute_cutoff_utc(effective_as_of, window_days=self.bounds.window_days)
        protected_ids = historical_video_ids or set()

        output_dir.mkdir(parents=True, exist_ok=True)
        checkpoint_path = output_dir / "collector_checkpoint.json"
        jsonl_path = output_dir / "videos_4m.jsonl"
        raw_archive_path = output_dir / "raw_provider_payloads.jsonl"

        prior_records_by_id: dict[str, RawIncrementalVideoRecord] = {}
        prior_audio_receipts: dict[str, AudioConversionReceipt] = {}
        if resume and checkpoint_path.is_file():
            cp_prev = CollectorCheckpoint.model_validate(
                json.loads(checkpoint_path.read_text(encoding="utf-8"))
            )
            cp_prev_set = set(cp_prev.succeeded_ids)
            loaded_records = self._load_existing_batch_records(jsonl_path)
            for vid_k, rec_v in loaded_records.items():
                if vid_k not in cp_prev_set or vid_k in protected_ids:
                    continue
                if not is_within_rolling_window(rec_v.create_time, cutoff_utc):
                    continue
                if rec_v.audio_path and not (output_dir / rec_v.audio_path).is_file():
                    rec_v = rec_v.model_copy(update={"audio_path": None})
                prior_records_by_id[vid_k] = rec_v
                if vid_k in cp_prev.audio_receipts:
                    prior_audio_receipts[vid_k] = cp_prev.audio_receipts[vid_k]

        prior_succeeded_set = set(prior_records_by_id.keys())
        raw_archive_by_id = (
            _load_existing_raw_payload_archive(raw_archive_path, prior_succeeded_set)
            if resume
            else {}
        )
        checkpoint = CollectorCheckpoint(
            source_mode=self.provider.source_mode,
            as_of_utc=effective_as_of.isoformat(),
            cutoff_utc=cutoff_utc.isoformat(),
            succeeded_ids=list(prior_records_by_id.keys()),
            audio_receipts=prior_audio_receipts,
        )
        merged_records_by_id: dict[str, RawIncrementalVideoRecord] = dict(prior_records_by_id)

        # Persist clean initial state immediately so resume=False or empty runs never leave stale state
        write_incremental_batch(list(merged_records_by_id.values()), output_dir)
        if not raw_archive_by_id and raw_archive_path.exists():
            raw_archive_path.unlink()
        elif raw_archive_by_id:
            _write_raw_payload_archive(raw_archive_by_id, output_dir)
        _atomic_write_json(checkpoint_path, checkpoint.model_dump())

        bounded_creators = (
            [c.strip() for c in creators if c.strip()][: self.bounds.max_creators]
            if creators
            else None
        )
        per_creator_cap = (
            min(
                self.bounds.max_candidate_videos,
                max(10, math.ceil(self.bounds.max_candidate_videos / len(bounded_creators)) * 2),
            )
            if bounded_creators and len(bounded_creators) > 1
            else self.bounds.max_candidate_videos
        )

        stopped_reason: str | None = None
        discovery_error: str | None = None
        raw_candidates: list[dict[str, Any]] = []
        with timer.measure("discovery_ms"):
            try:
                raw_candidates = self.provider.discover_candidates(
                    creators=bounded_creators,
                    max_per_creator=per_creator_cap,
                )
            except AntiBotChallengeError as anti_disc:
                stopped_reason = "anti_bot_challenge_blocked"
                discovery_error = _sanitize_reason(f"anti_bot_challenge_blocked: {anti_disc}")
            except TransientCollectorError as trans_disc:
                stopped_reason = "discovery_failed"
                discovery_error = _sanitize_reason(f"discovery_failed: {trans_disc}")

        balanced_candidates = _interleave_candidates_by_creator(raw_candidates)
        unique_candidates: list[dict[str, Any]] = []
        seen_ids: set[str] = set()
        duplicate_ignored = 0
        for cand in balanced_candidates:
            vid = str(cand.get("video_id") or cand.get("id") or "").strip()
            if not vid:
                continue
            if vid in seen_ids:
                duplicate_ignored += 1
                continue
            if len(unique_candidates) >= self.bounds.max_candidate_videos:
                break
            seen_ids.add(vid)
            unique_candidates.append(cand)

        item_receipts: list[CollectorItemReceipt] = []
        collected_comments_total = sum(len(r.comments) for r in merged_records_by_id.values())
        accumulated_audio_min = sum(
            (r.duration_sec / 60.0) for r in merged_records_by_id.values() if r.audio_path
        )
        max_attempts = 1 + self.bounds.max_retries

        with timer.measure("collection_ms"):
            for cand in unique_candidates:
                vid = str(cand.get("video_id") or cand.get("id") or "").strip()
                handle = str(cand.get("author_handle") or "").strip()
                raw_ct = cand.get("create_time") if "create_time" in cand else cand.get("createTime")
                has_raw_ct = _has_non_empty_timestamp_value(raw_ct)
                iso_ct = _parse_iso_create_time(raw_ct) if has_raw_ct else None

                if stopped_reason == "anti_bot_challenge_blocked":
                    checkpoint.skipped_reasons[vid] = "anti_bot_challenge_blocked"
                    item_receipts.append(
                        CollectorItemReceipt(
                            video_id=vid,
                            author_handle=handle,
                            create_time=iso_ct,
                            status="skipped",
                            attempts=0,
                            reason="anti_bot_challenge_blocked",
                        )
                    )
                    _atomic_write_json(checkpoint_path, checkpoint.model_dump())
                    continue

                if (time.monotonic() - session_t0) > self.bounds.session_deadline_seconds:
                    stopped_reason = "session_deadline_exceeded"
                    checkpoint.skipped_reasons[vid] = "session_deadline_exceeded"
                    item_receipts.append(
                        CollectorItemReceipt(
                            video_id=vid,
                            author_handle=handle,
                            create_time=iso_ct,
                            status="skipped",
                            attempts=0,
                            reason="session_deadline_exceeded",
                        )
                    )
                    _atomic_write_json(checkpoint_path, checkpoint.model_dump())
                    continue

                if vid in protected_ids:
                    checkpoint.skipped_reasons[vid] = "historical_protected_id"
                    item_receipts.append(
                        CollectorItemReceipt(
                            video_id=vid,
                            author_handle=handle,
                            create_time=iso_ct,
                            status="skipped",
                            attempts=0,
                            reason="historical_protected_id",
                        )
                    )
                    _atomic_write_json(checkpoint_path, checkpoint.model_dump())
                    continue

                if vid in prior_succeeded_set:
                    prior_rec = prior_records_by_id[vid]
                    checkpoint.skipped_reasons[vid] = "already_succeeded_in_checkpoint"
                    item_receipts.append(
                        CollectorItemReceipt(
                            video_id=vid,
                            author_handle=prior_rec.author_handle or handle,
                            create_time=prior_rec.create_time,
                            status="skipped",
                            attempts=0,
                            reason="already_succeeded_in_checkpoint",
                            comment_count=len(prior_rec.comments),
                            audio_receipt=checkpoint.audio_receipts.get(vid),
                        )
                    )
                    _atomic_write_json(checkpoint_path, checkpoint.model_dump())
                    continue

                if has_raw_ct and iso_ct is None:
                    checkpoint.failed_reasons[vid] = "invalid_create_time"
                    item_receipts.append(
                        CollectorItemReceipt(
                            video_id=vid,
                            author_handle=handle,
                            create_time=None,
                            status="failed",
                            attempts=0,
                            reason="invalid_create_time",
                        )
                    )
                    _atomic_write_json(checkpoint_path, checkpoint.model_dump())
                    continue

                if iso_ct is not None and not is_within_rolling_window(iso_ct, cutoff_utc):
                    checkpoint.skipped_reasons[vid] = "outside_120d_rolling_window"
                    item_receipts.append(
                        CollectorItemReceipt(
                            video_id=vid,
                            author_handle=handle,
                            create_time=iso_ct,
                            status="skipped",
                            attempts=0,
                            reason="outside_120d_rolling_window",
                        )
                    )
                    _atomic_write_json(checkpoint_path, checkpoint.model_dump())
                    continue

                if len(merged_records_by_id) >= self.bounds.max_succeeded_videos:
                    stopped_reason = "max_succeeded_ceiling"
                    checkpoint.skipped_reasons[vid] = "max_succeeded_ceiling"
                    item_receipts.append(
                        CollectorItemReceipt(
                            video_id=vid,
                            author_handle=handle,
                            create_time=iso_ct,
                            status="skipped",
                            attempts=0,
                            reason="max_succeeded_ceiling",
                        )
                    )
                    _atomic_write_json(checkpoint_path, checkpoint.model_dump())
                    continue

                attempts_used = 0
                last_error = ""
                post_detail_skip: _PostDetailSkip | None = None
                item_rec: RawIncrementalVideoRecord | None = None
                item_comments_count = 0
                item_audio_receipt: AudioConversionReceipt | None = None
                added_audio_min = 0.0
                item_raw_payload_entry: dict[str, Any] | None = None

                for attempt in range(1, max_attempts + 1):
                    attempts_used = attempt
                    created_mp3_this_attempt: Path | None = None
                    try:
                        detail = dict(self.provider.fetch_video_detail(cand))
                        raw_payload = detail.pop("_raw_provider_payload", None)
                        provider_backend_tag = str(detail.pop("_provider_backend", "") or "")
                        collected_at = str(detail.pop("collected_at_utc", "") or effective_as_of.isoformat())

                        detail_vid = str(detail.get("video_id") or detail.get("id") or vid).strip()
                        if detail_vid in protected_ids:
                            raise _PostDetailSkip("historical_protected_id", iso_ct=iso_ct)

                        raw_detail_ct = (
                            detail.get("create_time")
                            if "create_time" in detail
                            else detail.get("createTime")
                        )
                        detail_ct = (
                            _parse_iso_create_time(raw_detail_ct)
                            if _has_non_empty_timestamp_value(raw_detail_ct)
                            else iso_ct
                        )
                        if detail_ct is None:
                            raise _PostDetailPermanentFail("invalid_create_time")
                        if not is_within_rolling_window(detail_ct, cutoff_utc):
                            raise _PostDetailSkip("outside_120d_rolling_window", iso_ct=detail_ct)

                        remaining_comment_budget = max(
                            0, self.bounds.max_comments_total - collected_comments_total
                        )
                        per_vid_cap = min(self.bounds.max_comments_per_video, remaining_comment_budget)
                        raw_comments = (
                            self.provider.fetch_comments(detail_vid, max_comments=per_vid_cap)[:per_vid_cap]
                            if per_vid_cap > 0
                            else []
                        )
                        parsed_comments = [RawCommentInput.model_validate(c) for c in raw_comments]

                        audio_receipt, rel_audio_path, added_min = self._convert_audio_with_bounds(
                            vid=detail_vid,
                            detail=detail,
                            output_dir=output_dir,
                            accumulated_audio_min=accumulated_audio_min,
                        )
                        if rel_audio_path:
                            created_mp3_this_attempt = output_dir / rel_audio_path

                        rec_payload = {
                            **detail,
                            "video_id": detail_vid,
                            "author_id": str(detail.get("author_id") or f"author_{detail_vid}"),
                            "author_handle": str(detail.get("author_handle") or handle or "unknown"),
                            "create_time": detail_ct,
                            "audio_path": rel_audio_path,
                            "comments": [c.model_dump() for c in parsed_comments],
                        }
                        item_rec = RawIncrementalVideoRecord.model_validate(rec_payload)
                        item_comments_count = len(parsed_comments)
                        item_audio_receipt = audio_receipt
                        added_audio_min = added_min
                        if isinstance(raw_payload, dict):
                            item_raw_payload_entry = {
                                "video_id": item_rec.video_id,
                                "collected_at_utc": collected_at,
                                "backend": provider_backend_tag
                                or str(getattr(self.provider, "backend_name", self.provider.source_mode)),
                                "raw_payload": _sanitize_raw_payload(raw_payload),
                            }
                        break
                    except _PostDetailSkip as skip_exc:
                        if created_mp3_this_attempt and created_mp3_this_attempt.exists():
                            created_mp3_this_attempt.unlink()
                        post_detail_skip = skip_exc
                        break
                    except _PostDetailPermanentFail as perm_exc:
                        if created_mp3_this_attempt and created_mp3_this_attempt.exists():
                            created_mp3_this_attempt.unlink()
                        last_error = perm_exc.reason
                        break
                    except AntiBotChallengeError as anti_exc:
                        if created_mp3_this_attempt and created_mp3_this_attempt.exists():
                            created_mp3_this_attempt.unlink()
                        last_error = _sanitize_reason(f"anti_bot_challenge_blocked: {anti_exc}")
                        stopped_reason = "anti_bot_challenge_blocked"
                        break
                    except TransientCollectorError as exc:
                        if created_mp3_this_attempt and created_mp3_this_attempt.exists():
                            created_mp3_this_attempt.unlink()
                        last_error = _sanitize_reason(f"transient_error: {exc}")
                        if attempt < max_attempts:
                            self.sleep_fn(0.5 * attempt)
                    except Exception as exc:
                        if created_mp3_this_attempt and created_mp3_this_attempt.exists():
                            created_mp3_this_attempt.unlink()
                        last_error = _sanitize_reason(f"validation_or_permanent_error: {exc}")
                        break

                if post_detail_skip is not None:
                    checkpoint.skipped_reasons[vid] = post_detail_skip.reason
                    item_receipts.append(
                        CollectorItemReceipt(
                            video_id=vid,
                            author_handle=handle,
                            create_time=post_detail_skip.iso_ct,
                            status="skipped",
                            attempts=attempts_used,
                            reason=post_detail_skip.reason,
                        )
                    )
                elif item_rec is not None:
                    merged_records_by_id[item_rec.video_id] = item_rec
                    collected_comments_total += item_comments_count
                    accumulated_audio_min += added_audio_min
                    if item_raw_payload_entry is not None:
                        raw_archive_by_id[item_rec.video_id] = item_raw_payload_entry
                        _write_raw_payload_archive(raw_archive_by_id, output_dir)
                    if item_rec.video_id not in checkpoint.succeeded_ids:
                        checkpoint.succeeded_ids.append(item_rec.video_id)
                    if item_audio_receipt is not None:
                        checkpoint.audio_receipts[item_rec.video_id] = item_audio_receipt
                    checkpoint.failed_reasons.pop(vid, None)
                    checkpoint.failed_reasons.pop(item_rec.video_id, None)
                    # Atomically persist videos_4m.jsonl BEFORE checkpoint so mid-run crash never loses items
                    write_incremental_batch(list(merged_records_by_id.values()), output_dir)
                    item_receipts.append(
                        CollectorItemReceipt(
                            video_id=vid,
                            author_handle=item_rec.author_handle,
                            create_time=item_rec.create_time,
                            status="succeeded",
                            attempts=attempts_used,
                            reason="ok",
                            comment_count=item_comments_count,
                            audio_receipt=item_audio_receipt,
                        )
                    )
                else:
                    checkpoint.failed_reasons[vid] = last_error or "unknown_failure"
                    item_receipts.append(
                        CollectorItemReceipt(
                            video_id=vid,
                            author_handle=handle,
                            create_time=iso_ct,
                            status="failed",
                            attempts=attempts_used,
                            reason=last_error or "unknown_failure",
                        )
                    )
                _atomic_write_json(checkpoint_path, checkpoint.model_dump())

        with timer.measure("persist_ms"):
            final_records = list(merged_records_by_id.values())
            out_jsonl = write_incremental_batch(final_records, output_dir)
            if raw_archive_by_id:
                _write_raw_payload_archive(raw_archive_by_id, output_dir)
            succeeded_count = sum(1 for r in item_receipts if r.status == "succeeded")
            failed_count = sum(1 for r in item_receipts if r.status == "failed")
            skipped_count = sum(1 for r in item_receipts if r.status == "skipped")
            final_audio_count = sum(1 for r in final_records if r.audio_path)
            final_comments_count = sum(len(r.comments) for r in final_records)
            final_audio_minutes = round(
                sum((r.duration_sec / 60.0) for r in final_records if r.audio_path), 3
            )
            req_backend = str(
                getattr(self.provider, "requested_backend", self.provider.source_mode)
            )
            used_backends = list(getattr(self.provider, "backends_used", []))

            manifest = CrawlManifest(
                source_mode=self.provider.source_mode,
                is_synthetic_fixture=self.provider.is_synthetic_fixture,
                collector_backend_requested=req_backend,
                collector_backends_used=used_backends,
                as_of_utc=effective_as_of.isoformat(),
                cutoff_utc=cutoff_utc.isoformat(),
                base_corpus_snapshot_id=base_corpus_snapshot_id,
                historical_protected_count=len(protected_ids),
                creators_queried=bounded_creators or [],
                bounds=self.bounds,
                requested_count=len(unique_candidates),
                succeeded_count=succeeded_count,
                failed_count=failed_count,
                skipped_count=skipped_count,
                persisted_records_count=len(final_records),
                duplicate_candidates_ignored=duplicate_ignored,
                converted_audio_count=final_audio_count,
                collected_comments_count=final_comments_count,
                accumulated_audio_minutes=final_audio_minutes,
                stopped_reason=stopped_reason,
                discovery_error=discovery_error,
                output_jsonl=out_jsonl.name,
                items=item_receipts,
                timings_ms=timer.finalize(),
            )
            _atomic_write_json(output_dir / "crawl_manifest.json", manifest.model_dump())

        return manifest
