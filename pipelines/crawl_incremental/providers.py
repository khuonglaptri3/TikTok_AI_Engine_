from __future__ import annotations

import json
import subprocess
from datetime import UTC, datetime
from pathlib import Path
from typing import Any, Protocol

from pipelines.crawl_incremental.crawler_service import download_audio_mp3_64k
from pipelines.crawl_incremental.models import SourceMode


class TransientCollectorError(RuntimeError):
    """Raised on retryable network, rate-limit, or temporary media extraction failures."""


class LiveNetworkDisabledError(PermissionError):
    """Raised when LiveTikTokCollectorProvider is invoked without explicit live-network authorization."""


class CollectorProvider(Protocol):
    @property
    def source_mode(self) -> SourceMode: ...

    @property
    def is_synthetic_fixture(self) -> bool: ...

    def discover_candidates(
        self,
        creators: list[str] | None,
        max_per_creator: int,
    ) -> list[dict[str, Any]]: ...

    def fetch_video_detail(self, candidate: dict[str, Any]) -> dict[str, Any]: ...

    def fetch_comments(self, video_id: str, max_comments: int) -> list[dict[str, Any]]: ...


class AudioConverter(Protocol):
    def extract_mp3_64k(self, detail: dict[str, Any], output_mp3: Path) -> bool: ...


class OfflineFixtureCollectorProvider:
    """Deterministic offline fixture provider (0 network calls, visibly marked synthetic)."""

    def __init__(self, fixture_path: Path) -> None:
        self.fixture_path = fixture_path
        self.detail_called_ids: list[str] = []
        self.comments_called_ids: list[str] = []
        self._items = self._load_fixture(fixture_path)
        self._by_id: dict[str, dict[str, Any]] = {}
        for item in self._items:
            vid = str(item.get("video_id") or item.get("id") or "").strip()
            if vid and vid not in self._by_id:
                self._by_id[vid] = item

    @staticmethod
    def _load_fixture(path: Path) -> list[dict[str, Any]]:
        if not path.is_file():
            raise FileNotFoundError(f"Offline fixture file not found: {path}")
        raw_text = path.read_text(encoding="utf-8").strip()
        if not raw_text:
            return []
        if path.suffix.lower() == ".json":
            parsed = json.loads(raw_text)
            if isinstance(parsed, list):
                return [dict(x) for x in parsed if isinstance(x, dict)]
            raise ValueError("JSON fixture must contain a list of candidate objects")
        return [
            dict(json.loads(line))
            for line in raw_text.splitlines()
            if line.strip()
        ]

    @property
    def source_mode(self) -> SourceMode:
        return "offline_fixture"

    @property
    def is_synthetic_fixture(self) -> bool:
        return True

    def discover_candidates(
        self,
        creators: list[str] | None,
        max_per_creator: int,
    ) -> list[dict[str, Any]]:
        allowed_creators = {c.lstrip("@").strip().lower() for c in creators} if creators else None
        per_creator_counts: dict[str, int] = {}
        discovered: list[dict[str, Any]] = []
        for item in self._items:
            handle = str(item.get("author_handle") or "").lstrip("@").strip().lower()
            if allowed_creators is not None and handle not in allowed_creators:
                continue
            cur = per_creator_counts.get(handle, 0)
            if cur >= max_per_creator:
                continue
            per_creator_counts[handle] = cur + 1
            discovered.append(
                {
                    "video_id": item.get("video_id") or item.get("id"),
                    "author_handle": item.get("author_handle") or "",
                    "create_time": item.get("create_time") or item.get("createTime"),
                }
            )
        return discovered

    def fetch_video_detail(self, candidate: dict[str, Any]) -> dict[str, Any]:
        vid = str(candidate.get("video_id") or "").strip()
        self.detail_called_ids.append(vid)
        return dict(self._by_id.get(vid) or candidate)

    def fetch_comments(self, video_id: str, max_comments: int) -> list[dict[str, Any]]:
        self.comments_called_ids.append(video_id)
        if max_comments <= 0:
            return []
        full = self._by_id.get(video_id) or {}
        raw_comments = full.get("comments") or []
        return [dict(c) for c in raw_comments[:max_comments] if isinstance(c, dict)]


class OfflineFixtureAudioConverter:
    """Offline 64 kbps .mp3 converter backed by fixture payload bytes (0 subprocess calls)."""

    def extract_mp3_64k(self, detail: dict[str, Any], output_mp3: Path) -> bool:
        payload = detail.get("audio_fixture_payload")
        if not payload:
            return False
        output_mp3.parent.mkdir(parents=True, exist_ok=True)
        output_mp3.write_bytes(str(payload).encode("utf-8"))
        return True


class LiveTikTokCollectorProvider:
    """Bounded host-network TikTok provider gated behind allow_live_network and MS_TOKEN."""

    def __init__(
        self,
        *,
        allow_live_network: bool = False,
        ms_token: str = "",
        timeout_sec: int = 45,
    ) -> None:
        if not allow_live_network:
            raise LiveNetworkDisabledError(
                "Live network collection is disabled unless allow_live_network=True (--allow-live-network) is explicitly passed."
            )
        if not ms_token.strip():
            raise LiveNetworkDisabledError(
                "Live TikTok collection requires a non-empty MS_TOKEN environment credential."
            )
        self._ms_token = ms_token.strip()
        self._timeout_sec = max(5, int(timeout_sec))
        self._cached_comments: dict[str, list[dict[str, Any]]] = {}

    @property
    def source_mode(self) -> SourceMode:
        return "live_provider"

    @property
    def is_synthetic_fixture(self) -> bool:
        return False

    def _cookie_header_arg(self) -> list[str]:
        return ["--add-header", f"Cookie: msToken={self._ms_token}"]

    def discover_candidates(
        self,
        creators: list[str] | None,
        max_per_creator: int,
    ) -> list[dict[str, Any]]:
        if not creators:
            return []
        cap = max(1, int(max_per_creator))
        discovered: list[dict[str, Any]] = []
        for raw_handle in creators:
            handle = raw_handle.lstrip("@").strip()
            if not handle:
                continue
            profile_url = f"https://www.tiktok.com/@{handle}"
            cmd = [
                "yt-dlp",
                "--flat-playlist",
                "--dump-json",
                "--playlist-end",
                str(cap),
                *self._cookie_header_arg(),
                profile_url,
            ]
            try:
                res = subprocess.run(
                    cmd,
                    capture_output=True,
                    text=True,
                    timeout=self._timeout_sec,
                    check=False,
                )
            except subprocess.TimeoutExpired:
                raise TransientCollectorError("discovery subprocess timed out") from None
            except OSError as exc:
                raise TransientCollectorError(f"discovery subprocess os error: {exc.errno}") from None
            if res.returncode != 0:
                raise TransientCollectorError(f"discovery exited with code {res.returncode}")
            for line in res.stdout.splitlines():
                if not line.strip():
                    continue
                try:
                    obj = json.loads(line)
                except json.JSONDecodeError:
                    continue
                ts = obj.get("timestamp")
                iso_ct = (
                    datetime.fromtimestamp(float(ts), tz=UTC).isoformat()
                    if ts is not None
                    else obj.get("create_time")
                )
                vid = str(obj.get("id") or "").strip()
                if vid:
                    discovered.append(
                        {
                            "video_id": vid,
                            "author_handle": handle,
                            "create_time": iso_ct,
                            "tiktok_url": obj.get("webpage_url")
                            or f"https://www.tiktok.com/@{handle}/video/{vid}",
                        }
                    )
        return discovered

    def fetch_video_detail(self, candidate: dict[str, Any]) -> dict[str, Any]:
        vid = str(candidate.get("video_id") or "").strip()
        handle = str(candidate.get("author_handle") or "").lstrip("@").strip()
        url = str(
            candidate.get("tiktok_url") or f"https://www.tiktok.com/@{handle}/video/{vid}"
        )
        cmd = [
            "yt-dlp",
            "--dump-single-json",
            "--no-playlist",
            "--write-comments",
            *self._cookie_header_arg(),
            url,
        ]
        try:
            res = subprocess.run(
                cmd,
                capture_output=True,
                text=True,
                timeout=self._timeout_sec,
                check=False,
            )
        except subprocess.TimeoutExpired:
            raise TransientCollectorError("detail subprocess timed out") from None
        except OSError as exc:
            raise TransientCollectorError(f"detail subprocess os error: {exc.errno}") from None
        if res.returncode != 0 or not res.stdout.strip():
            raise TransientCollectorError(f"detail fetch failed with code {res.returncode}")

        try:
            raw = json.loads(res.stdout)
        except json.JSONDecodeError:
            raise TransientCollectorError("detail fetch returned invalid json") from None
        canonical_vid = str(raw.get("id") or vid).strip()
        ts = raw.get("timestamp")
        iso_ct = (
            datetime.fromtimestamp(float(ts), tz=UTC).isoformat()
            if ts is not None
            else str(candidate.get("create_time") or "")
        )
        raw_comments = raw.get("comments") or []
        mapped_comments: list[dict[str, Any]] = []
        for idx, c in enumerate(raw_comments):
            if not isinstance(c, dict) or not str(c.get("text") or "").strip():
                continue
            mapped_comments.append(
                {
                    "comment_id": str(c.get("id") or f"{canonical_vid}_c{idx}"),
                    "author_handle": str(c.get("author") or ""),
                    "text": str(c.get("text") or ""),
                    "like_count": max(0, int(c.get("like_count") or 0)),
                    "reply_count": 0,
                }
            )
        self._cached_comments[canonical_vid] = mapped_comments
        self._cached_comments[vid] = mapped_comments
        tags = [str(t).lstrip("#") for t in (raw.get("tags") or []) if str(t).strip()]
        return {
            "video_id": canonical_vid,
            "author_id": str(raw.get("uploader_id") or raw.get("channel_id") or f"author_{vid}"),
            "author_handle": str(raw.get("uploader") or handle or "unknown"),
            "author_nickname": str(raw.get("creator") or raw.get("uploader") or ""),
            "follower_count": max(0, int(raw.get("channel_follower_count") or 0)),
            "create_time": iso_ct,
            "caption": str(raw.get("description") or raw.get("title") or ""),
            "hashtags": tags,
            "duration_sec": max(0, int(round(float(raw.get("duration") or 0)))),
            "play_count": max(0, int(raw.get("view_count") or 0)),
            "digg_count": max(0, int(raw.get("like_count") or 0)),
            "comment_count": max(0, int(raw.get("comment_count") or len(mapped_comments))),
            "share_count": max(0, int(raw.get("repost_count") or 0)),
            "collect_count": 0,
            "tiktok_url": url,
            "transcript": "",
        }

    def fetch_comments(self, video_id: str, max_comments: int) -> list[dict[str, Any]]:
        if max_comments <= 0:
            return []
        return list((self._cached_comments.get(video_id) or [])[:max_comments])


class YtDlpAudioConverter64k:
    """Live 64 kbps .mp3 extractor gated behind allow_live_network."""

    def __init__(self, *, allow_live_network: bool = False) -> None:
        if not allow_live_network:
            raise LiveNetworkDisabledError(
                "Live audio extraction is disabled unless allow_live_network=True."
            )

    def extract_mp3_64k(self, detail: dict[str, Any], output_mp3: Path) -> bool:
        vid = str(detail.get("video_id") or "").strip()
        handle = str(detail.get("author_handle") or "").lstrip("@").strip()
        url = str(detail.get("tiktok_url") or f"https://www.tiktok.com/@{handle}/video/{vid}")
        return download_audio_mp3_64k(url, output_mp3)
