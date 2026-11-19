from __future__ import annotations

import json
import os
import subprocess
from datetime import UTC, datetime, timedelta
from pathlib import Path
from typing import Any

from packages.data_contracts.multimodal import RawIncrementalVideoRecord


def compute_cutoff_utc(reference_now: datetime | None = None, window_days: int = 120) -> datetime:
    now = reference_now or datetime.now(UTC)
    if now.tzinfo is None:
        now = now.replace(tzinfo=UTC)
    return now - timedelta(days=max(1, window_days))


def is_within_rolling_window(
    create_time_iso: str | int | float,
    cutoff_utc: datetime,
) -> bool:
    """Return True strictly when video create_time >= 4-month rolling cutoff."""
    if isinstance(create_time_iso, bool):
        return False
    try:
        if isinstance(create_time_iso, int | float) or str(create_time_iso).isdigit():
            dt = datetime.fromtimestamp(float(create_time_iso), tz=UTC)
        else:
            dt = datetime.fromisoformat(str(create_time_iso).replace("Z", "+00:00"))
            if dt.tzinfo is None:
                dt = dt.replace(tzinfo=UTC)
        return dt >= cutoff_utc
    except Exception:
        return False


def filter_fresh_candidates(
    raw_items: list[dict[str, Any]],
    existing_video_ids: set[str],
    cutoff_utc: datetime,
) -> list[dict[str, Any]]:
    """Filter out historical (>4 months) and already-ingested videos so historical corpus is never re-crawled."""
    accepted: list[dict[str, Any]] = []
    seen: set[str] = set()
    for item in raw_items:
        vid = str(item.get("video_id") or item.get("id") or "").strip()
        if not vid or vid in existing_video_ids or vid in seen:
            continue
        ct = item.get("create_time") or item.get("createTime")
        if ct is None or not is_within_rolling_window(ct, cutoff_utc):
            continue
        seen.add(vid)
        accepted.append(item)
    return accepted


def download_audio_mp3_64k(tiktok_url: str, output_mp3: Path) -> bool:
    """Download lightweight 64kbps .mp3 (~500KB) via yt-dlp when installed."""
    output_mp3.parent.mkdir(parents=True, exist_ok=True)
    cmd = [
        "yt-dlp",
        "--force-overwrites",
        "-f",
        "bestaudio/best",
        "--extract-audio",
        "--audio-format",
        "mp3",
        "--audio-quality",
        "64K",
        "--no-playlist",
        "-o",
        str(output_mp3),
        tiktok_url,
    ]
    try:
        res = subprocess.run(cmd, capture_output=True, text=True, timeout=45, check=False)
        return res.returncode == 0 and output_mp3.is_file()
    except FileNotFoundError:
        return False
    except Exception:
        return False


def write_incremental_batch(
    records: list[RawIncrementalVideoRecord],
    batch_dir: Path,
) -> Path:
    batch_dir.mkdir(parents=True, exist_ok=True)
    out_jsonl = batch_dir / "videos_4m.jsonl"
    tmp_jsonl = batch_dir / "videos_4m.jsonl.tmp"
    with tmp_jsonl.open("w", encoding="utf-8") as fp:
        for rec in records:
            fp.write(json.dumps(rec.model_dump(), ensure_ascii=False) + "\n")
    os.replace(tmp_jsonl, out_jsonl)
    return out_jsonl
