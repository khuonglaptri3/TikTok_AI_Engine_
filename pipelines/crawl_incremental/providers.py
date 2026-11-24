from __future__ import annotations

import asyncio
import importlib.util
import json
import subprocess
import threading
from collections.abc import Callable
from datetime import datetime
from pathlib import Path
from typing import Any, Protocol

from pipelines.crawl_incremental.crawler_service import (
    download_audio_mp3_64k,
    is_within_rolling_window,
    utf8_subprocess_env,
    yt_dlp_impersonate_args,
)
from pipelines.crawl_incremental.mappers import (
    map_tiktok_comment_to_input,
    map_tiktok_item_struct_to_detail,
    map_ytdlp_json_to_detail,
    parse_timestamp_to_iso_utc,
)
from pipelines.crawl_incremental.models import CollectorBackend, SourceMode


class TransientCollectorError(RuntimeError):
    """Raised on retryable network, rate-limit, or temporary media extraction failures."""


class AntiBotChallengeError(RuntimeError):
    """Raised on CAPTCHA / human-verification gates; MUST fail closed with zero retry or bypass."""


class LiveNetworkDisabledError(PermissionError):
    """Raised when a live TikTok provider is invoked without explicit live-network authorization."""


_ANTI_BOT_MARKERS = (
    "captcha",
    "verify you are human",
    "not a bot",
    "detecting you're a bot",
    "detecting you are a bot",
    "security verification",
    "sliver_verify",
)

_BROWSER_UNAVAILABLE_MARKERS = (
    "executable doesn't exist",
    "executable does not exist",
    "browsertype.launch",
    "playwright install",
    "failed to launch",
)


def _is_anti_bot_challenge(text_or_exc: Any) -> bool:
    if isinstance(text_or_exc, AntiBotChallengeError):
        return True
    cls_name = type(text_or_exc).__name__.lower()
    if "captcha" in cls_name or "emptyresponse" in cls_name:
        return True
    msg = str(text_or_exc or "").lower()
    return any(marker in msg for marker in _ANTI_BOT_MARKERS)


def _is_browser_launch_unavailable(exc: Exception) -> bool:
    msg = str(exc or "").lower()
    return any(marker in msg for marker in _BROWSER_UNAVAILABLE_MARKERS)


def is_tiktokapi_available() -> bool:
    """Return True when the official TikTokApi package is importable in this Python runtime."""
    try:
        return importlib.util.find_spec("TikTokApi") is not None
    except Exception:
        return False


class _PersistentAsyncLoop:
    """Dedicated background asyncio loop keeping a single Playwright/TikTokApi session alive across sync calls."""

    def __init__(self) -> None:
        self._loop: asyncio.AbstractEventLoop | None = None
        self._thread: threading.Thread | None = None
        self._lock = threading.Lock()
        self._fallback_sync_mode = False

    def run(self, coro: Any) -> Any:
        with self._lock:
            if not self._fallback_sync_mode and (self._loop is None or self._loop.is_closed()):
                ready = threading.Event()
                loop_holder: list[asyncio.AbstractEventLoop] = []
                err_holder: list[BaseException] = []

                def _worker() -> None:
                    try:
                        loop = asyncio.new_event_loop()
                        asyncio.set_event_loop(loop)
                        loop_holder.append(loop)
                        loop.call_soon(ready.set)
                        loop.run_forever()
                    except BaseException as exc:
                        err_holder.append(exc)
                        ready.set()

                thread = threading.Thread(target=_worker, name="tiktokapi-loop", daemon=True)
                thread.start()
                ready.wait(timeout=2.0)
                if loop_holder and not err_holder:
                    self._loop = loop_holder[0]
                    self._thread = thread
                else:
                    # Windows restricted sandbox without local loopback socket falls back to direct coroutine execution
                    self._fallback_sync_mode = True
            active_loop = self._loop

        if self._fallback_sync_mode or active_loop is None:
            return self._drive_sync_without_socket(coro)
        fut = asyncio.run_coroutine_threadsafe(coro, active_loop)
        return fut.result(timeout=60.0)

    @staticmethod
    def _drive_sync_without_socket(coro: Any) -> Any:
        try:
            while True:
                coro.send(None)
        except StopIteration as stop:
            return stop.value

    def close(self) -> None:
        with self._lock:
            loop = self._loop
            thread = self._thread
            self._loop = None
            self._thread = None
        if loop is not None and not loop.is_closed():
            try:
                loop.call_soon_threadsafe(loop.stop)
            except Exception:
                pass
            if thread is not None and thread.is_alive():
                thread.join(timeout=2.0)
            if thread is None or not thread.is_alive():
                try:
                    loop.close()
                except RuntimeError:
                    pass


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

    requested_backend = "offline_fixture"
    backend_name = "offline_fixture"

    def __init__(self, fixture_path: Path) -> None:
        self.fixture_path = fixture_path
        self.detail_called_ids: list[str] = []
        self.comments_called_ids: list[str] = []
        self.backends_used: list[str] = ["offline_fixture"]
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


def _validate_live_auth(allow_live_network: bool, ms_token: str) -> str:
    if not allow_live_network:
        raise LiveNetworkDisabledError(
            "Live network collection is disabled unless allow_live_network=True (--allow-live-network) is explicitly passed."
        )
    cleaned = ms_token.strip()
    if not cleaned:
        raise LiveNetworkDisabledError(
            "Live TikTok collection requires a non-empty MS_TOKEN (or ms_token) environment credential."
        )
    return cleaned


class TikTokApiCollectorProvider:
    """Official TikTokApi provider adapting 21KHDL-TikTok-Analytics itemStruct, pinned-post, & single-session mechanics."""

    requested_backend = "tiktokapi"
    backend_name = "tiktokapi"

    def __init__(
        self,
        *,
        allow_live_network: bool = False,
        ms_token: str = "",
        cookies_file: Path | None = None,
        browser: str = "chromium",
        headless: bool = True,
        cutoff_utc: datetime | None = None,
        timeout_sec: int = 45,
        api_factory: Callable[[], Any] | None = None,
    ) -> None:
        self._ms_token = _validate_live_auth(allow_live_network, ms_token)
        if api_factory is None and not is_tiktokapi_available():
            raise LiveNetworkDisabledError(
                "TikTokApi package is not installed; install TikTokApi + playwright or use --backend auto / --backend ytdlp."
            )
        self._api_factory = api_factory
        self._cookies_file = cookies_file
        self._browser = browser.strip().lower() or "chromium"
        if self._browser not in {"chromium", "webkit", "firefox"}:
            raise ValueError(f"Unsupported TikTok browser {browser!r}; expected chromium, webkit, or firefox.")
        self._headless = bool(headless)
        self._cutoff_utc = cutoff_utc
        self._timeout_sec = max(5, int(timeout_sec))
        self._cached_details: dict[str, dict[str, Any]] = {}
        self._loop_runner = _PersistentAsyncLoop()
        self._api_instance: Any | None = None
        self.backends_used: list[str] = []

    @property
    def source_mode(self) -> SourceMode:
        return "live_provider"

    @property
    def is_synthetic_fixture(self) -> bool:
        return False

    def _mark_used(self) -> None:
        if self.backend_name not in self.backends_used:
            self.backends_used.append(self.backend_name)

    def _instantiate_api(self) -> Any:
        if self._api_factory is not None:
            return self._api_factory()
        from TikTokApi import TikTokApi  # type: ignore[import-not-found]

        return TikTokApi()

    async def _ensure_session_async(self) -> Any:
        if self._api_instance is not None:
            return self._api_instance
        api = await self._instantiate_api().__aenter__()
        try:
            await api.create_sessions(
                num_sessions=1,
                ms_tokens=[self._ms_token],
                headless=self._headless,
                browser=self._browser,
                sleep_after=2,
                timeout=self._timeout_sec * 1000,
            )
        except Exception:
            try:
                await api.__aexit__(None, None, None)
            except Exception:
                pass
            raise
        self._api_instance = api
        return api

    def close(self) -> None:
        api = self._api_instance
        self._api_instance = None
        if api is not None:
            try:
                self._loop_runner.run(api.__aexit__(None, None, None))
            except Exception:
                pass
        self._loop_runner.close()

    def _classify_exception(self, exc: Exception, stage: str) -> Exception:
        if isinstance(exc, (AntiBotChallengeError, LiveNetworkDisabledError)):
            return exc
        if _is_anti_bot_challenge(exc):
            hint = (
                " (tip: try --no-tiktok-headless on desktop or refresh MS_TOKEN)"
                if "emptyresponse" in type(exc).__name__.lower()
                else ""
            )
            return AntiBotChallengeError(f"{stage} blocked by anti-bot/captcha challenge{hint}: {exc}")
        return TransientCollectorError(f"{stage} tiktokapi error: {exc}")

    def discover_candidates(
        self,
        creators: list[str] | None,
        max_per_creator: int,
    ) -> list[dict[str, Any]]:
        if not creators:
            return []
        cap = max(1, int(max_per_creator))

        async def _discover_async() -> list[dict[str, Any]]:
            discovered: list[dict[str, Any]] = []
            api = await self._ensure_session_async()
            for raw_handle in creators:
                handle = raw_handle.lstrip("@").strip()
                if not handle:
                    continue
                collected_for_user = 0
                # Allow headroom for up to 5 pinned videos at the top of a creator profile
                scan_limit = max(cap + 5, 35)
                user_obj = api.user(username=handle)
                async for video in user_obj.videos(count=scan_limit):
                    raw_dict = dict(getattr(video, "as_dict", None) or {})
                    vid_hint = str(getattr(video, "id", None) or raw_dict.get("id") or "").strip()
                    detail = map_tiktok_item_struct_to_detail(
                        raw_dict,
                        fallback_vid=vid_hint,
                        fallback_handle=handle,
                    )
                    vid = str(detail.get("video_id") or "").strip()
                    if not vid:
                        continue
                    iso_ct = str(detail.get("create_time") or "")
                    is_pinned = bool(detail.get("is_pinned_item"))

                    # 21KHDL-TikTok-Analytics crawler.py:99-118 chronological + isPinnedItem rule
                    if self._cutoff_utc is not None and iso_ct:
                        if not is_within_rolling_window(iso_ct, self._cutoff_utc):
                            if is_pinned:
                                continue
                            break

                    detail["_provider_backend"] = self.backend_name
                    self._cached_details[vid] = detail
                    discovered.append(
                        {
                            "video_id": vid,
                            "author_handle": detail["author_handle"],
                            "create_time": iso_ct or None,
                            "tiktok_url": detail["tiktok_url"],
                        }
                    )
                    collected_for_user += 1
                    if collected_for_user >= cap:
                        break
            return discovered

        try:
            items: list[dict[str, Any]] = self._loop_runner.run(_discover_async())
            self._mark_used()
            return items
        except Exception as exc:
            raise self._classify_exception(exc, "discovery") from None

    def fetch_video_detail(self, candidate: dict[str, Any]) -> dict[str, Any]:
        vid = str(candidate.get("video_id") or "").strip()
        if vid and vid in self._cached_details:
            self._mark_used()
            return dict(self._cached_details[vid])

        handle = str(candidate.get("author_handle") or "").lstrip("@").strip()
        url = str(
            candidate.get("tiktok_url") or f"https://www.tiktok.com/@{handle}/video/{vid}"
        )

        async def _detail_async() -> dict[str, Any]:
            api = await self._ensure_session_async()
            video_obj = api.video(url=url)
            raw_info = await video_obj.info()
            raw_dict = dict(raw_info if isinstance(raw_info, dict) else (getattr(video_obj, "as_dict", None) or {}))
            mapped = map_tiktok_item_struct_to_detail(
                raw_dict,
                fallback_vid=vid,
                fallback_handle=handle,
            )
            mapped["_provider_backend"] = self.backend_name
            return mapped

        try:
            detail: dict[str, Any] = self._loop_runner.run(_detail_async())
            canonical_vid = str(detail.get("video_id") or vid).strip()
            if canonical_vid:
                self._cached_details[canonical_vid] = detail
            self._mark_used()
            return dict(detail)
        except Exception as exc:
            raise self._classify_exception(exc, "detail") from None

    def fetch_comments(self, video_id: str, max_comments: int) -> list[dict[str, Any]]:
        clean_vid = video_id.strip()
        if max_comments <= 0 or not clean_vid:
            return []
        cached = self._cached_details.get(clean_vid)
        if cached is not None and int(cached.get("comment_count") or 0) == 0:
            self._mark_used()
            return []
        cap = int(max_comments)

        async def _comments_async() -> list[dict[str, Any]]:
            collected: list[dict[str, Any]] = []
            api = await self._ensure_session_async()
            sessions = getattr(api, "sessions", None)
            saved_params: list[tuple[Any, Any]] = []
            if isinstance(sessions, list):
                get_cookies_fn = getattr(api, "get_session_cookies", None)
                for sess in sessions:
                    old_p = getattr(sess, "params", None)
                    saved_params.append((sess, old_p))
                    if callable(get_cookies_fn):
                        try:
                            cookie_map = await get_cookies_fn(sess)
                            if isinstance(cookie_map, dict) and cookie_map.get("msToken"):
                                sess.ms_token = str(cookie_map["msToken"])
                        except Exception:
                            pass
                    # TikTokApi 7.3.5 populates synthetic session.params (region='US', from_page='user', random device_id)
                    # that cause /api/comment/list/ X-Bogus signing to return an empty response body.
                    if isinstance(old_p, dict):
                        sess.params = {"aid": str(old_p.get("aid") or "1988")}
            try:
                video_obj = api.video(id=clean_vid)
                idx = 0
                try:
                    async for c_obj in video_obj.comments(count=cap):
                        raw_c = getattr(c_obj, "as_dict", None)
                        if isinstance(raw_c, dict):
                            norm = map_tiktok_comment_to_input(raw_c, canonical_vid=clean_vid, idx=idx)
                            if norm is not None:
                                collected.append(norm)
                                if len(collected) >= cap:
                                    break
                        idx += 1
                except TypeError as te:
                    # TikTokApi Video.comments does `for video in resp.get("comments", [])` which raises
                    # TypeError("'NoneType' object is not iterable") when TikTok returns `{"comments": null, "has_more": 0}`.
                    if "nonetype" not in str(te).lower() or "iterable" not in str(te).lower():
                        raise
            finally:
                for sess, old_p in saved_params:
                    sess.params = old_p
            return collected

        try:
            out: list[dict[str, Any]] = self._loop_runner.run(_comments_async())
            self._mark_used()
            return out
        except Exception as exc:
            raise self._classify_exception(exc, "comments") from None


class LiveTikTokCollectorProvider:
    """Bounded host-network yt-dlp TikTok provider gated behind allow_live_network and MS_TOKEN."""

    requested_backend = "ytdlp"
    backend_name = "ytdlp"

    def __init__(
        self,
        *,
        allow_live_network: bool = False,
        ms_token: str = "",
        cookies_file: Path | None = None,
        timeout_sec: int = 45,
    ) -> None:
        self._ms_token = _validate_live_auth(allow_live_network, ms_token)
        self._cookies_file = cookies_file
        self._timeout_sec = max(5, int(timeout_sec))
        self._cached_comments: dict[str, list[dict[str, Any]]] = {}
        self.backends_used: list[str] = []

    @property
    def source_mode(self) -> SourceMode:
        return "live_provider"

    @property
    def is_synthetic_fixture(self) -> bool:
        return False

    def _mark_used(self) -> None:
        if self.backend_name not in self.backends_used:
            self.backends_used.append(self.backend_name)

    def _auth_args(self) -> list[str]:
        args = ["--add-header", f"Cookie: msToken={self._ms_token}"]
        if self._cookies_file is not None and self._cookies_file.is_file():
            args.extend(["--cookies", str(self._cookies_file)])
        return args

    def discover_candidates(
        self,
        creators: list[str] | None,
        max_per_creator: int,
    ) -> list[dict[str, Any]]:
        if not creators:
            return []
        handles = [h.lstrip("@").strip() for h in creators if h.lstrip("@").strip()]
        if not handles:
            return []
        cap = max(1, int(max_per_creator))
        per_creator_cap = max(1, (cap + len(handles) - 1) // len(handles))
        per_creator_items: list[list[dict[str, Any]]] = []
        for handle in handles:
            profile_url = f"https://www.tiktok.com/@{handle}"
            cmd = [
                "yt-dlp",
                *yt_dlp_impersonate_args(),
                "--flat-playlist",
                "--dump-json",
                "--playlist-end",
                str(per_creator_cap),
                *self._auth_args(),
                profile_url,
            ]
            try:
                res = subprocess.run(
                    cmd,
                    capture_output=True,
                    text=True,
                    encoding="utf-8",
                    errors="replace",
                    env=utf8_subprocess_env(),
                    timeout=self._timeout_sec,
                    check=False,
                )
            except subprocess.TimeoutExpired:
                raise TransientCollectorError("discovery subprocess timed out") from None
            except OSError as exc:
                raise TransientCollectorError(f"discovery subprocess os error: {exc.errno}") from None
            if res.returncode != 0:
                stderr_txt = (res.stderr or "").strip()
                if _is_anti_bot_challenge(stderr_txt):
                    raise AntiBotChallengeError(f"discovery blocked by anti-bot challenge: {stderr_txt}")
                raise TransientCollectorError(f"discovery exited with code {res.returncode}")
            creator_rows: list[dict[str, Any]] = []
            for line in res.stdout.splitlines():
                if not line.strip():
                    continue
                try:
                    obj = json.loads(line)
                except json.JSONDecodeError:
                    continue
                iso_ct = parse_timestamp_to_iso_utc(
                    obj.get("timestamp") if obj.get("timestamp") is not None else obj.get("create_time")
                )
                vid = str(obj.get("id") or "").strip()
                if vid:
                    creator_rows.append(
                        {
                            "video_id": vid,
                            "author_handle": handle,
                            "create_time": iso_ct or None,
                            "tiktok_url": obj.get("webpage_url")
                            or f"https://www.tiktok.com/@{handle}/video/{vid}",
                        }
                    )
            per_creator_items.append(creator_rows)

        # Interleave round-robin so bounded downstream collection/ASR samples every creator
        discovered: list[dict[str, Any]] = []
        max_rows = max((len(items) for items in per_creator_items), default=0)
        for idx in range(max_rows):
            for items in per_creator_items:
                if idx < len(items):
                    discovered.append(items[idx])
        self._mark_used()
        return discovered

    def fetch_video_detail(self, candidate: dict[str, Any]) -> dict[str, Any]:
        vid = str(candidate.get("video_id") or "").strip()
        handle = str(candidate.get("author_handle") or "").lstrip("@").strip()
        url = str(
            candidate.get("tiktok_url") or f"https://www.tiktok.com/@{handle}/video/{vid}"
        )
        cmd = [
            "yt-dlp",
            *yt_dlp_impersonate_args(),
            "--dump-single-json",
            "--no-playlist",
            "--write-comments",
            *self._auth_args(),
            url,
        ]
        try:
            res = subprocess.run(
                cmd,
                capture_output=True,
                text=True,
                encoding="utf-8",
                errors="replace",
                env=utf8_subprocess_env(),
                timeout=self._timeout_sec,
                check=False,
            )
        except subprocess.TimeoutExpired:
            raise TransientCollectorError("detail subprocess timed out") from None
        except OSError as exc:
            raise TransientCollectorError(f"detail subprocess os error: {exc.errno}") from None
        if res.returncode != 0 or not res.stdout.strip():
            stderr_txt = (res.stderr or "").strip()
            if _is_anti_bot_challenge(stderr_txt):
                raise AntiBotChallengeError(f"detail blocked by anti-bot challenge: {stderr_txt}")
            raise TransientCollectorError(f"detail fetch failed with code {res.returncode}")

        try:
            raw = json.loads(res.stdout)
        except json.JSONDecodeError:
            raise TransientCollectorError("detail fetch returned invalid json") from None

        detail, mapped_comments = map_ytdlp_json_to_detail(raw, candidate=candidate)
        canonical_vid = str(detail.get("video_id") or vid).strip()
        self._cached_comments[canonical_vid] = mapped_comments
        if vid:
            self._cached_comments[vid] = mapped_comments
        detail["_provider_backend"] = self.backend_name
        self._mark_used()
        return detail

    def fetch_comments(self, video_id: str, max_comments: int) -> list[dict[str, Any]]:
        if max_comments <= 0:
            return []
        self._mark_used()
        return list((self._cached_comments.get(video_id) or [])[:max_comments])


class AutoHybridTikTokCollectorProvider:
    """Automatic TikTokApi-first provider falling back to yt-dlp while never bypassing anti-bot challenges."""

    requested_backend = "auto"

    def __init__(
        self,
        *,
        allow_live_network: bool = False,
        ms_token: str = "",
        cookies_file: Path | None = None,
        browser: str = "chromium",
        headless: bool = True,
        cutoff_utc: datetime | None = None,
        timeout_sec: int = 45,
        primary: CollectorProvider | None = None,
        secondary: CollectorProvider | None = None,
    ) -> None:
        clean_tok = _validate_live_auth(allow_live_network, ms_token)
        if primary is not None:
            self._primary: CollectorProvider | None = primary
        elif is_tiktokapi_available():
            self._primary = TikTokApiCollectorProvider(
                allow_live_network=allow_live_network,
                ms_token=clean_tok,
                cookies_file=cookies_file,
                browser=browser,
                headless=headless,
                cutoff_utc=cutoff_utc,
                timeout_sec=timeout_sec,
            )
        else:
            self._primary = None

        self._secondary: CollectorProvider = secondary or LiveTikTokCollectorProvider(
            allow_live_network=allow_live_network,
            ms_token=clean_tok,
            cookies_file=cookies_file,
            timeout_sec=timeout_sec,
        )
        self._primary_disabled = False
        self._expected_comment_counts: dict[str, int] = {}
        self._unfetched_secondary_candidates: dict[str, dict[str, Any]] = {}
        self.backends_used: list[str] = []

    @property
    def source_mode(self) -> SourceMode:
        return "live_provider"

    @property
    def is_synthetic_fixture(self) -> bool:
        return False

    def _record_backend(self, provider_obj: Any) -> None:
        name = str(getattr(provider_obj, "backend_name", "live_provider"))
        if name not in self.backends_used:
            self.backends_used.append(name)

    def _handle_primary_transient_failure(self, exc: TransientCollectorError) -> None:
        if _is_browser_launch_unavailable(exc):
            self._primary_disabled = True
            close_fn = getattr(self._primary, "close", None)
            if callable(close_fn):
                close_fn()

    def close(self) -> None:
        for obj in (self._primary, self._secondary):
            close_fn = getattr(obj, "close", None)
            if callable(close_fn):
                close_fn()

    def discover_candidates(
        self,
        creators: list[str] | None,
        max_per_creator: int,
    ) -> list[dict[str, Any]]:
        if self._primary is not None and not self._primary_disabled:
            try:
                items = self._primary.discover_candidates(creators, max_per_creator)
                self._record_backend(self._primary)
                return items
            except AntiBotChallengeError:
                raise
            except TransientCollectorError as exc:
                self._handle_primary_transient_failure(exc)
        items = self._secondary.discover_candidates(creators, max_per_creator)
        self._record_backend(self._secondary)
        return items

    def fetch_video_detail(self, candidate: dict[str, Any]) -> dict[str, Any]:
        if self._primary is not None and not self._primary_disabled:
            try:
                detail = dict(self._primary.fetch_video_detail(candidate))
                detail.setdefault("_provider_backend", getattr(self._primary, "backend_name", "tiktokapi"))
                vid = str(detail.get("video_id") or candidate.get("video_id") or "").strip()
                if vid:
                    self._expected_comment_counts[vid] = int(detail.get("comment_count") or 0)
                    self._unfetched_secondary_candidates[vid] = dict(candidate)
                self._record_backend(self._primary)
                return detail
            except AntiBotChallengeError:
                raise
            except TransientCollectorError as exc:
                self._handle_primary_transient_failure(exc)

        detail = dict(self._secondary.fetch_video_detail(candidate))
        detail.setdefault("_provider_backend", getattr(self._secondary, "backend_name", "ytdlp"))
        vid = str(detail.get("video_id") or candidate.get("video_id") or "").strip()
        if vid:
            self._expected_comment_counts[vid] = int(detail.get("comment_count") or 0)
            self._unfetched_secondary_candidates.pop(vid, None)
        self._record_backend(self._secondary)
        return detail

    def fetch_comments(self, video_id: str, max_comments: int) -> list[dict[str, Any]]:
        if max_comments <= 0:
            return []
        if self._primary is not None and not self._primary_disabled:
            try:
                cmts = self._primary.fetch_comments(video_id, max_comments)
                if cmts:
                    self._record_backend(self._primary)
                    return cmts
                if self._expected_comment_counts.get(video_id, 0) == 0:
                    self._record_backend(self._primary)
                    return []
            except AntiBotChallengeError:
                raise
            except TransientCollectorError as exc:
                self._handle_primary_transient_failure(exc)

        sec_cmts = self._secondary.fetch_comments(video_id, max_comments)
        unfetched_cand = self._unfetched_secondary_candidates.pop(video_id, None)
        if not sec_cmts and self._expected_comment_counts.get(video_id, 0) > 0 and unfetched_cand is not None:
            try:
                self._secondary.fetch_video_detail(unfetched_cand)
                sec_cmts = self._secondary.fetch_comments(video_id, max_comments)
            except AntiBotChallengeError:
                raise
            except TransientCollectorError:
                return []
        if sec_cmts or self._primary is None or self._primary_disabled:
            self._record_backend(self._secondary)
        return sec_cmts


class YtDlpAudioConverter64k:
    """Live 64 kbps .mp3 extractor gated behind allow_live_network with msToken/cookies forwarding."""

    def __init__(
        self,
        *,
        allow_live_network: bool = False,
        ms_token: str = "",
        cookies_file: Path | None = None,
        timeout_sec: int = 45,
    ) -> None:
        if not allow_live_network:
            raise LiveNetworkDisabledError(
                "Live audio extraction is disabled unless allow_live_network=True."
            )
        self._ms_token = ms_token.strip()
        self._cookies_file = cookies_file
        self._timeout_sec = max(5, int(timeout_sec))

    def extract_mp3_64k(self, detail: dict[str, Any], output_mp3: Path) -> bool:
        vid = str(detail.get("video_id") or "").strip()
        handle = str(detail.get("author_handle") or "").lstrip("@").strip()
        url = str(detail.get("tiktok_url") or f"https://www.tiktok.com/@{handle}/video/{vid}")

        def _check_stderr(stderr_txt: str) -> None:
            if _is_anti_bot_challenge(stderr_txt):
                raise AntiBotChallengeError(
                    f"audio extraction blocked by anti-bot challenge: {stderr_txt}"
                )

        return download_audio_mp3_64k(
            url,
            output_mp3,
            ms_token=self._ms_token,
            cookies_file=self._cookies_file,
            timeout_sec=self._timeout_sec,
            on_stderr_error=_check_stderr,
        )


def build_live_collector_provider(
    *,
    backend: CollectorBackend = "auto",
    allow_live_network: bool = False,
    ms_token: str = "",
    cookies_file: Path | None = None,
    browser: str = "chromium",
    headless: bool = True,
    cutoff_utc: datetime | None = None,
    timeout_sec: int = 45,
) -> CollectorProvider:
    """Construct the requested live collector provider (auto, tiktokapi, or ytdlp)."""
    if backend == "tiktokapi":
        return TikTokApiCollectorProvider(
            allow_live_network=allow_live_network,
            ms_token=ms_token,
            cookies_file=cookies_file,
            browser=browser,
            headless=headless,
            cutoff_utc=cutoff_utc,
            timeout_sec=timeout_sec,
        )
    if backend == "ytdlp":
        return LiveTikTokCollectorProvider(
            allow_live_network=allow_live_network,
            ms_token=ms_token,
            cookies_file=cookies_file,
            timeout_sec=timeout_sec,
        )
    if backend == "auto":
        return AutoHybridTikTokCollectorProvider(
            allow_live_network=allow_live_network,
            ms_token=ms_token,
            cookies_file=cookies_file,
            browser=browser,
            headless=headless,
            cutoff_utc=cutoff_utc,
            timeout_sec=timeout_sec,
        )
    raise ValueError(f"Unsupported collector backend: {backend!r}")
