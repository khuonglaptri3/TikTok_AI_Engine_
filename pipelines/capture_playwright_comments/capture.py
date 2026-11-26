from __future__ import annotations

import hashlib
import json
import os
import random
import re
import time
from collections.abc import Callable, Mapping
from datetime import UTC, datetime, timedelta
from html.parser import HTMLParser
from pathlib import Path
from typing import Any, cast
from urllib.parse import unquote, urlparse

import pandas as pd
from playwright.sync_api import BrowserContext, Page

from packages.analytics import load_verified_corpus
from pipelines.crawl_incremental.providers import AntiBotChallengeError

_VOID_TAGS = frozenset({
    "area",
    "base",
    "br",
    "col",
    "embed",
    "hr",
    "img",
    "input",
    "link",
    "meta",
    "param",
    "source",
    "track",
    "wbr",
})


def _extract_author_handle(href: str) -> str:
    parsed = urlparse(href)
    if parsed.scheme and (parsed.scheme not in {"http", "https"} or parsed.netloc != "www.tiktok.com"):
        return ""
    if not parsed.scheme and parsed.netloc:
        return ""
    if not parsed.path.startswith("/@"):
        return ""
    return unquote(parsed.path[2:]).split("/", 1)[0].strip()


class _CommentCardParser(HTMLParser):
    def __init__(self) -> None:
        super().__init__(convert_charrefs=True)
        self.author_handle = ""
        self._capture_stack: list[bool] = []
        self._text_parts: list[str] = []

    def handle_starttag(self, tag: str, attrs: list[tuple[str, str | None]]) -> None:
        values = dict(attrs)
        capturing = bool(self._capture_stack and self._capture_stack[-1])
        if values.get("data-e2e") == "comment-level-1":
            capturing = True
        if not self.author_handle and not capturing and tag == "a":
            self.author_handle = _extract_author_handle(values.get("href") or "")
        if tag == "img" and capturing:
            self._text_parts.append(values.get("alt") or "")
        if tag == "br" and capturing:
            self._text_parts.append("\n")
        if tag not in _VOID_TAGS:
            self._capture_stack.append(capturing)

    def handle_endtag(self, tag: str) -> None:
        if tag not in _VOID_TAGS and self._capture_stack:
            self._capture_stack.pop()

    def handle_data(self, data: str) -> None:
        if self._capture_stack and self._capture_stack[-1]:
            self._text_parts.append(data)

    @property
    def text(self) -> str:
        return "".join(self._text_parts)


def normalize_rendered_cards(cards_html: list[str], video_id: str, *, limit: int = 50) -> list[dict[str, str]]:
    """Normalize rendered comment cards; IDs are local DOM hashes, not TikTok IDs."""
    if not video_id.strip() or not 1 <= limit <= 50:
        raise ValueError("A video ID and a limit from 1 to 50 are required")
    rows: list[dict[str, str]] = []
    for position, html in enumerate(cards_html):
        parser = _CommentCardParser()
        parser.feed(html)
        if not parser.text.strip():
            continue
        digest = hashlib.sha256(
            f"{video_id}\0{parser.author_handle}\0{parser.text}\0{position}".encode()
        ).hexdigest()[:24]
        rows.append({
            "video_id": video_id,
            "comment_id": f"dom_{digest}",
            "text": parser.text,
            "author_handle": parser.author_handle,
        })
        if len(rows) >= limit:
            break
    if not rows:
        raise ValueError("No visible comments were found in the rendered cards")
    return rows


def validate_known_video_url(url: str, videos: Mapping[str, str], as_of_utc: datetime) -> str:
    parsed = urlparse(url)
    match = re.fullmatch(r"/@[^/]+/video/(\d+)", parsed.path)
    if parsed.scheme != "https" or parsed.netloc != "www.tiktok.com" or parsed.query or parsed.fragment or not match:
        raise ValueError("Expected a canonical www.tiktok.com video URL")
    video_id = match.group(1)
    created_raw = videos.get(video_id)
    if created_raw is None:
        raise ValueError("Video ID is absent from the verified Gold snapshot")
    created = datetime.fromisoformat(created_raw.replace("Z", "+00:00"))
    if created.tzinfo is None:
        created = created.replace(tzinfo=UTC)
    if as_of_utc.tzinfo is None:
        as_of_utc = as_of_utc.replace(tzinfo=UTC)
    as_of_utc = as_of_utc.astimezone(UTC)
    if not as_of_utc - timedelta(days=120) <= created.astimezone(UTC) <= as_of_utc:
        raise ValueError("Video is outside the 120-day rolling window")
    return video_id


def select_remaining_pilot_urls(corpus_dir: Path, *, as_of_utc: datetime) -> list[tuple[str, str]]:
    """Return canonical URLs for fresh Gold videos not yet present in fact_comments.parquet."""
    manifest, _, videos = load_verified_corpus(corpus_dir)
    if as_of_utc.tzinfo is None:
        as_of_utc = as_of_utc.replace(tzinfo=UTC)
    as_of_utc = as_of_utc.astimezone(UTC)
    cutoff = as_of_utc - timedelta(days=120)
    commented_ids: set[str] = set()
    if "fact_comments.parquet" in {entry.filename for entry in manifest.files}:
        prior_comments = pd.read_parquet(corpus_dir / "fact_comments.parquet", columns=["video_id"])
        commented_ids = set(prior_comments["video_id"].astype(str))

    selected: list[tuple[datetime, str, str]] = []
    for row in videos.to_dict(orient="records"):
        vid = str(row.get("video_id") or "").strip()
        handle = str(row.get("author_handle") or "").strip().lstrip("@")
        created_raw = str(row.get("create_time") or "").strip()
        if not vid or not handle or not created_raw or vid in commented_ids:
            continue
        created = datetime.fromisoformat(created_raw.replace("Z", "+00:00"))
        if created.tzinfo is None:
            created = created.replace(tzinfo=UTC)
        created_utc = created.astimezone(UTC)
        if cutoff <= created_utc <= as_of_utc:
            selected.append((created_utc, vid, f"https://www.tiktok.com/@{handle}/video/{vid}"))
    selected.sort(key=lambda item: (-item[0].timestamp(), item[1]))
    return [(vid, url) for _, vid, url in selected]


def validate_loaded_video_identity(loaded_url: str, expected_video_id: str) -> str:
    parsed = urlparse(loaded_url)
    match = re.fullmatch(r"/@[^/]+/video/(\d+)", parsed.path)
    if parsed.scheme != "https" or parsed.netloc != "www.tiktok.com" or not match:
        raise ValueError("Loaded page is not a canonical TikTok video")
    if match.group(1) != expected_video_id:
        raise ValueError("Loaded page video ID differs from the requested Gold video")
    return expected_video_id


def visible_comment_cards(page: Page, *, limit: int) -> list[str]:
    if not 1 <= limit <= 50:
        raise ValueError("Comment limit must be from 1 to 50")
    return cast(list[str], page.locator('[class*="DivCommentItemWrapper"]').evaluate_all(
        """(els, cap) => els.filter(e => {
            const body = e.querySelector('[data-e2e="comment-level-1"]');
            if (!body) return false;
            if ((body.textContent || '').trim()) return true;
            return Array.from(body.querySelectorAll('img[alt]')).some(
                img => (img.getAttribute('alt') || '').trim()
            );
        }).slice(0, cap).map(e => e.outerHTML)""",
        limit,
    ))


def write_normalized_jsonl(rows: list[dict[str, str]], output_path: Path) -> None:
    if not rows:
        raise ValueError("No visible comments were captured")
    output_path.parent.mkdir(parents=True, exist_ok=True)
    with output_path.open("x", encoding="utf-8", newline="\n") as fp:
        for row in rows:
            fp.write(json.dumps(row, ensure_ascii=False) + "\n")


def ensure_new_capture_paths(output_path: Path) -> Path:
    if output_path.suffix.lower() != ".jsonl":
        raise ValueError("Capture output path must have a .jsonl suffix")
    receipt_path = output_path.with_suffix(".receipt.json")
    if output_path.exists() or receipt_path.exists():
        raise FileExistsError("Capture JSONL and receipt paths must both be new")
    return receipt_path


def apply_session_cookies(context: BrowserContext, session_cookies: Mapping[str, str]) -> None:
    try:
        context.add_cookies([
            {"name": name, "value": value, "url": "https://www.tiktok.com"}
            for name, value in session_cookies.items()
        ])
    except Exception:
        raise ValueError("Configured TikTok cookies could not be applied to browser session") from None


def _challenge_overlay_visible(page: Page) -> bool:
    return cast(bool, page.locator("body *").evaluate_all("""els => {
        const contentSel = '[class*="DivCommentItemWrapper"], [data-e2e="comment-level-1"], ' +
                           '[data-e2e="comment-level-2"], [data-e2e="browse-video-desc"], [data-e2e="video-desc"]';
        const verifyMarkers = ['verify-bar', 'verify_bar', 'verifycenter', 'sliver_verify',
                               'tiktok-verify', 'verify.tiktok.com'];
        return els.some(e => {
            if (e.closest(contentSel)) return false;
            const rect = e.getBoundingClientRect();
            if (rect.width <= 0 || rect.height <= 0) return false;
            for (let cur = e; cur; cur = cur.parentElement) {
                if (cur.getAttribute('aria-hidden') === 'true') return false;
                const st = getComputedStyle(cur);
                if (st.display === 'none' || st.visibility === 'hidden' || Number(st.opacity) === 0) {
                    return false;
                }
            }
            const cls = typeof e.className === 'string' ? e.className : '';
            const identity = (cls + ' ' + (e.id || '') + ' ' + (e.getAttribute('src') || '')).toLowerCase();
            if (identity.includes('captcha') || identity.includes('secsdk') ||
                verifyMarkers.some(m => identity.includes(m))) {
                return true;
            }
            if (e.querySelector(contentSel)) return false;
            const label = (e.textContent || '').toLowerCase();
            return label.includes('kéo thanh trượt') || label.includes('verify you are human') ||
                   label.includes('security verification') || label.includes('drag the slider');
        });
    }"""))


def _empty_comments_state_visible(page: Page) -> bool:
    return cast(bool, page.locator("body *").evaluate_all("""els => {
        const contentSel = '[class*="DivCommentItemWrapper"], [data-e2e="browse-video-desc"], [data-e2e="video-desc"]';
        const emptyMarkers = [
            'hãy là người đầu tiên bình luận',
            'chưa có bình luận',
            'be the first to comment',
            'no comments yet',
            'tính năng bình luận đã được tắt',
            'comments are turned off'
        ];
        return els.some(e => {
            if (e.closest(contentSel) || e.querySelector(contentSel)) return false;
            const rect = e.getBoundingClientRect();
            if (rect.width <= 0 || rect.height <= 0) return false;
            const label = (e.textContent || '').toLowerCase();
            return emptyMarkers.some(m => label.includes(m));
        });
    }"""))


def _scroll_comment_panel_once(page: Page) -> None:
    wrappers = page.locator('[class*="DivCommentItemWrapper"]')
    if not wrappers.count():
        return
    wrappers.last.evaluate("""el => {
        el.scrollIntoView({ block: 'end' });
        let cur = el.parentElement;
        while (cur) {
            if (cur.scrollHeight > cur.clientHeight + 10) {
                cur.scrollTop = cur.scrollHeight;
            }
            cur = cur.parentElement;
        }
        window.scrollBy(0, 600);
    }""")


def _write_json_atomic(path: Path, payload: Mapping[str, Any]) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    tmp = path.with_name(path.name + ".tmp")
    tmp.write_text(json.dumps(payload, ensure_ascii=False, indent=2) + "\n", encoding="utf-8", newline="\n")
    os.replace(tmp, path)


def capture_comments_on_page(
    page: Page,
    video_id: str,
    *,
    limit: int = 50,
    manual_wait_seconds: int = 300,
    no_comment_wait_seconds: int = 45,
    scroll_rounds: int = 0,
    scroll_pause_ms: int = 1500,
    allow_zero_comments: bool = False,
) -> tuple[list[dict[str, str]], bool]:
    """Open comments normally and wait for visible cards or manual slider completion."""
    if (
        not 1 <= limit <= 50
        or not 1 <= manual_wait_seconds <= 300
        or not 1 <= no_comment_wait_seconds <= 120
        or not 0 <= scroll_rounds <= 6
        or not 0 <= scroll_pause_ms <= 5000
    ):
        raise ValueError("Invalid capture bounds")
    icon = page.locator('[data-e2e="comment-icon"]')
    if not icon.count():
        try:
            icon.first.wait_for(state="attached", timeout=min(5000, no_comment_wait_seconds * 1000))
        except Exception:
            pass
    if not icon.count():
        raise ValueError("Video page has no visible comments action")
    icon.first.locator("..").click(timeout=5000)
    challenge_start: float | None = None
    clear_start: float | None = None
    challenge_seen = False
    while True:
        if "/login" in page.url:
            raise ValueError("TikTok redirected to a login gate")
        if page.url != "about:blank":
            validate_loaded_video_identity(page.url, video_id)
        now = time.monotonic()
        gated = _challenge_overlay_visible(page)
        if gated:
            challenge_seen = True
            clear_start = None
            if challenge_start is None:
                challenge_start = now
            if now - challenge_start >= manual_wait_seconds:
                raise AntiBotChallengeError("Manual CAPTCHA window expired; no comments captured")
        else:
            if clear_start is None:
                clear_start = now
            cards = visible_comment_cards(page, limit=limit)
            if cards:
                page.wait_for_timeout(1500)
                if not _challenge_overlay_visible(page):
                    if page.url != "about:blank":
                        validate_loaded_video_identity(page.url, video_id)
                    settled_cards = visible_comment_cards(page, limit=limit)
                    challenge_mid_scroll = False
                    for _ in range(scroll_rounds):
                        if len(settled_cards) >= limit:
                            break
                        _scroll_comment_panel_once(page)
                        if scroll_pause_ms > 0:
                            page.wait_for_timeout(scroll_pause_ms)
                        if _challenge_overlay_visible(page):
                            challenge_mid_scroll = True
                            break
                        if page.url != "about:blank":
                            validate_loaded_video_identity(page.url, video_id)
                        next_cards = visible_comment_cards(page, limit=limit)
                        if len(next_cards) <= len(settled_cards):
                            settled_cards = next_cards
                            break
                        settled_cards = next_cards
                    if not challenge_mid_scroll and settled_cards:
                        return normalize_rendered_cards(settled_cards, video_id, limit=limit), challenge_seen
            elif allow_zero_comments and _empty_comments_state_visible(page) and now - clear_start >= 0.4:
                return [], challenge_seen
            if now - clear_start >= no_comment_wait_seconds:
                if allow_zero_comments:
                    return [], challenge_seen
                raise ValueError("No visible comment cards loaded within the bounded wait")
        page.wait_for_timeout(250)


def run_batch_comment_capture(
    page: Page,
    targets: list[tuple[str, str]],
    output_path: Path,
    *,
    base_snapshot_id: str = "",
    limit_per_video: int = 50,
    max_total_comments: int = 1000,
    manual_wait_seconds: int = 300,
    no_comment_wait_seconds: int = 10,
    scroll_rounds: int = 4,
    cooldown_seconds: float = 10.0,
    jitter_seconds: float = 4.0,
    resume: bool = False,
    sleep_fn: Callable[[float], None] = time.sleep,
    rng_fn: Callable[[float, float], float] = random.uniform,
) -> dict[str, Any]:
    """Capture comments across multiple verified URLs in one browser session with checkpointing."""
    if output_path.suffix.lower() != ".jsonl":
        raise ValueError("Capture output path must have a .jsonl suffix")
    if (
        not 1 <= limit_per_video <= 50
        or not 1 <= max_total_comments <= 5000
        or not 0.0 <= cooldown_seconds <= 120.0
        or not 0.0 <= jitter_seconds <= 60.0
        or not 0 <= scroll_rounds <= 6
    ):
        raise ValueError("Invalid batch capture bounds")

    state_path = output_path.with_suffix(".state.json")
    receipt_path = output_path.with_suffix(".receipt.json")
    if not resume and (output_path.exists() or state_path.exists() or receipt_path.exists()):
        raise FileExistsError("Batch JSONL, state, and receipt paths must all be new unless --resume is set")

    completed_map: dict[str, dict[str, Any]] = {}
    if resume and state_path.is_file():
        loaded_state = json.loads(state_path.read_text(encoding="utf-8"))
        if isinstance(loaded_state, dict) and isinstance(loaded_state.get("completed"), dict):
            completed_map = dict(loaded_state["completed"])

    total_rows = 0
    if resume and output_path.is_file():
        for raw_line in output_path.read_text(encoding="utf-8").splitlines():
            if not raw_line.strip():
                continue
            obj = json.loads(raw_line)
            total_rows += 1
            vid_existing = str(obj.get("video_id") or "")
            if vid_existing and vid_existing not in completed_map:
                completed_map[vid_existing] = {"status": "captured", "comment_count": 1}

    start = time.monotonic()
    visited_this_run = 0
    manual_challenge_count = 0
    stopped_reason = "completed"
    challenge_exc: AntiBotChallengeError | None = None

    for idx, (video_id, url) in enumerate(targets, start=1):
        if video_id in completed_map:
            continue
        remaining_budget = max_total_comments - total_rows
        if remaining_budget <= 0:
            stopped_reason = "max_total_comments_reached"
            break
        if visited_this_run > 0:
            delay = round(
                cooldown_seconds + (rng_fn(0.0, jitter_seconds) if jitter_seconds > 0 else 0.0),
                3,
            )
            if delay > 0:
                print(f"  -> cooldown {delay:.1f}s before next video...", flush=True)
                sleep_fn(delay)
        visited_this_run += 1
        print(f"[{idx}/{len(targets)}] Navigating {url} ...", flush=True)
        response = page.goto(url, wait_until="domcontentloaded", timeout=45000)
        if "/login" in page.url:
            stopped_reason = "login_gate_blocked"
            break
        if response is None or response.status != 200 or urlparse(page.url).netloc != "www.tiktok.com":
            completed_map[video_id] = {"status": "unavailable_skipped", "comment_count": 0}
            _write_json_atomic(state_path, {"completed": completed_map})
            print("  -> page unavailable, skipped", flush=True)
            continue
        try:
            validate_loaded_video_identity(page.url, video_id)
            rows, challenge_seen = capture_comments_on_page(
                page,
                video_id,
                limit=min(limit_per_video, remaining_budget),
                manual_wait_seconds=manual_wait_seconds,
                no_comment_wait_seconds=no_comment_wait_seconds,
                scroll_rounds=scroll_rounds,
                allow_zero_comments=True,
            )
        except AntiBotChallengeError as exc:
            stopped_reason = "anti_bot_challenge_blocked"
            challenge_exc = exc
            break
        except ValueError as exc:
            if "login gate" in str(exc).lower():
                stopped_reason = "login_gate_blocked"
                break
            completed_map[video_id] = {"status": "unavailable_skipped", "comment_count": 0}
            _write_json_atomic(state_path, {"completed": completed_map})
            print(f"  -> skipped ({exc})", flush=True)
            continue

        if challenge_seen:
            manual_challenge_count += 1
        if rows:
            output_path.parent.mkdir(parents=True, exist_ok=True)
            with output_path.open("a", encoding="utf-8", newline="\n") as fp:
                for row in rows:
                    fp.write(json.dumps(row, ensure_ascii=False) + "\n")
            total_rows += len(rows)
            completed_map[video_id] = {"status": "captured", "comment_count": len(rows)}
            print(f"  -> captured {len(rows)} comments (batch total: {total_rows})", flush=True)
        else:
            completed_map[video_id] = {"status": "zero_comments", "comment_count": 0}
            print("  -> 0 visible comments", flush=True)
        _write_json_atomic(state_path, {"completed": completed_map})

    captured_videos = sum(1 for v in completed_map.values() if v.get("status") == "captured")
    zero_comment_videos = sum(1 for v in completed_map.values() if v.get("status") == "zero_comments")
    unavailable_videos = sum(1 for v in completed_map.values() if v.get("status") == "unavailable_skipped")
    source_sha256 = (
        hashlib.sha256(output_path.read_bytes()).hexdigest() if output_path.is_file() else None
    )
    receipt: dict[str, Any] = {
        "source": "playwright_rendered_video_batch",
        "base_snapshot_id": base_snapshot_id,
        "requested_videos": len(targets),
        "captured_videos": captured_videos,
        "zero_comment_videos": zero_comment_videos,
        "unavailable_videos": unavailable_videos,
        "comment_count": total_rows,
        "comment_id_scheme": "dom_derived_sha256_not_tiktok_native",
        "manual_challenge_count": manual_challenge_count,
        "cooldown_seconds": cooldown_seconds,
        "jitter_seconds": jitter_seconds,
        "scroll_rounds": scroll_rounds,
        "stopped_reason": stopped_reason,
        "elapsed_seconds": round(time.monotonic() - start, 3),
        "source_sha256": source_sha256,
    }
    _write_json_atomic(receipt_path, receipt)
    if challenge_exc is not None:
        raise challenge_exc
    if stopped_reason == "login_gate_blocked":
        raise ValueError("TikTok redirected to a login gate")
    return receipt
