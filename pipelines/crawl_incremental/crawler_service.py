from __future__ import annotations

import json
import os
import subprocess
from datetime import UTC, datetime, timedelta
from pathlib import Path
from typing import Any

import pandas as pd

from packages.data_contracts.multimodal import RawIncrementalVideoRecord


def utf8_subprocess_env(base_env: dict[str, str] | None = None) -> dict[str, str]:
    """Ensure child processes (yt-dlp/ffmpeg) emit UTF-8 on both Linux and Windows (21KHDL run_crawler pattern)."""
    env = dict(base_env) if base_env is not None else os.environ.copy()
    env["PYTHONIOENCODING"] = "utf-8"
    env["PYTHONUTF8"] = "1"
    return env


def load_dotenv_if_present(
    dotenv_path: Path = Path(".env"),
    *,
    target_env: dict[str, str] | None = None,
) -> dict[str, str]:
    """Load unset KEY=VALUE entries from gitignored .env and bridge legacy lowercase ms_token -> MS_TOKEN."""
    env_store: Any = target_env if target_env is not None else os.environ
    if dotenv_path.is_file():
        for raw_line in dotenv_path.read_text(encoding="utf-8").splitlines():
            line = raw_line.strip()
            if not line or line.startswith("#"):
                continue
            if line.startswith("export "):
                line = line[len("export ") :].strip()
            if "=" not in line:
                continue
            key, val = line.split("=", 1)
            clean_key = key.strip()
            if not clean_key:
                continue
            clean_val = val.strip()
            if len(clean_val) >= 2 and clean_val[0] == clean_val[-1] and clean_val[0] in {"'", '"'}:
                clean_val = clean_val[1:-1]
            if not str(env_store.get(clean_key, "")).strip() and clean_val:
                env_store[clean_key] = clean_val

    # Bridge 21KHDL-TikTok-Analytics legacy lowercase ms_token -> canonical MS_TOKEN
    if not str(env_store.get("MS_TOKEN", "")).strip():
        legacy_tok = str(env_store.get("ms_token", "")).strip()
        if legacy_tok:
            env_store["MS_TOKEN"] = legacy_tok
    return dict(env_store)


def select_curated_fnb_creators(
    base_corpus_dir: Path,
    *,
    top_k: int = 5,
    filter_file: Path = Path("data/filters/author_unique_ids.txt"),
) -> list[str]:
    """Select curated Vietnamese F&B handles prioritizing 21KHDL author_unique_ids.txt + Chapter 3 thresholds."""
    if top_k <= 0:
        return []
    dim_path = base_corpus_dir / "dim_creators.parquet"
    if not dim_path.is_file():
        return []
    df = pd.read_parquet(dim_path)
    if df.empty or "unique_id" not in df.columns:
        return []

    records = df.to_dict(orient="records")
    by_handle: dict[str, dict[str, Any]] = {}
    for row in records:
        uid = str(row.get("unique_id") or "").lstrip("@").strip()
        if uid and uid.lower() not in {"none", "nan", "null"}:
            by_handle[uid] = row

    selected: list[str] = []
    seen: set[str] = set()

    # Tier 1: Hand-curated flagship F&B handles from 21KHDL-TikTok-Analytics (02_DEP_03-Filter_users)
    if filter_file.is_file():
        for raw_h in filter_file.read_text(encoding="utf-8").splitlines():
            h = raw_h.lstrip("@").strip()
            if h and h in by_handle and h not in seen:
                seen.add(h)
                selected.append(h)
                if len(selected) >= top_k:
                    return selected

    def _rank_key(item: tuple[str, dict[str, Any]]) -> tuple[float, int, int, str]:
        handle_name, r = item
        return (
            -float(r.get("avg_videos_per_week") or 0.0),
            -int(r.get("sample_video_count") or 0),
            -int(r.get("follower_count") or 0),
            handle_name,
        )

    # Tier 2: Chapter 3 quantitative thresholds (median_play_count >= 40,000 & median_engagement_rate >= 0.03)
    ch3_candidates = sorted(
        [
            (h, r)
            for h, r in by_handle.items()
            if h not in seen
            and float(r.get("median_play_count") or 0.0) >= 40_000.0
            and float(r.get("median_engagement_rate") or 0.0) >= 0.03
        ],
        key=_rank_key,
    )
    for h, _ in ch3_candidates:
        seen.add(h)
        selected.append(h)
        if len(selected) >= top_k:
            return selected

    # Tier 3: Remaining active creators in dim_creators if still below top_k
    remaining = sorted(
        [(h, r) for h, r in by_handle.items() if h not in seen],
        key=_rank_key,
    )
    for h, _ in remaining:
        seen.add(h)
        selected.append(h)
        if len(selected) >= top_k:
            break
    return selected


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


def download_audio_mp3_64k(
    tiktok_url: str,
    output_mp3: Path,
    *,
    ms_token: str = "",
    cookies_file: Path | None = None,
    timeout_sec: int = 45,
) -> bool:
    """Download lightweight 64kbps .mp3 (~500KB) via yt-dlp with msToken/cookies auth and UTF-8 safety."""
    output_mp3.parent.mkdir(parents=True, exist_ok=True)
    auth_args: list[str] = []
    if ms_token.strip():
        auth_args.extend(["--add-header", f"Cookie: msToken={ms_token.strip()}"])
    if cookies_file is not None and cookies_file.is_file():
        auth_args.extend(["--cookies", str(cookies_file)])

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
        *auth_args,
        "-o",
        str(output_mp3),
        tiktok_url,
    ]
    try:
        res = subprocess.run(
            cmd,
            capture_output=True,
            text=True,
            encoding="utf-8",
            errors="replace",
            env=utf8_subprocess_env(),
            timeout=max(5, int(timeout_sec)),
            check=False,
        )
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
