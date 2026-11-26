from __future__ import annotations

import argparse
import hashlib
import json
import os
import time
from collections.abc import Mapping
from datetime import UTC, datetime
from pathlib import Path
from urllib.parse import urlparse

from playwright.sync_api import sync_playwright

from packages.analytics import load_verified_corpus
from pipelines.crawl_incremental.crawler_service import load_dotenv_if_present
from pipelines.crawl_incremental.providers import _load_tiktok_session_cookies

from .capture import (
    apply_session_cookies,
    capture_comments_on_page,
    ensure_new_capture_paths,
    run_batch_comment_capture,
    select_remaining_pilot_urls,
    validate_known_video_url,
    validate_loaded_video_identity,
    write_normalized_jsonl,
)


def resolve_capture_credentials(
    cookies_file: Path | None,
    *,
    dotenv_path: Path = Path(".env"),
    environ: Mapping[str, str] | None = None,
) -> tuple[Path, str]:
    env = load_dotenv_if_present(
        dotenv_path,
        target_env=dict(os.environ if environ is None else environ),
    )
    ms_token = env.get("MS_TOKEN", "").strip()
    raw_cookie = env.get("TIKTOK_COOKIES_FILE", "").strip()
    resolved_cookie = cookies_file or (Path(raw_cookie) if raw_cookie else None)
    if resolved_cookie is None or not resolved_cookie.is_file() or not ms_token:
        raise ValueError("A configured Netscape cookie file and MS_TOKEN are required")
    return resolved_cookie, ms_token


def main() -> None:
    parser = argparse.ArgumentParser(description="Capture visible comments from verified TikTok video URLs.")
    target_group = parser.add_mutually_exclusive_group(required=True)
    target_group.add_argument("--url")
    target_group.add_argument("--remaining-pilot", action="store_true")
    parser.add_argument("--base-corpus", type=Path, default=Path("data/corpus/m3_3_pilot_snapshot_v1"))
    parser.add_argument("--output-jsonl", type=Path, required=True)
    parser.add_argument("--cookies-file", type=Path)
    parser.add_argument("--as-of", default=None)
    parser.add_argument("--limit", type=int, default=50)
    parser.add_argument("--max-total-comments", type=int, default=1000)
    parser.add_argument("--manual-wait-seconds", type=int, default=300)
    parser.add_argument("--cooldown-seconds", type=float, default=10.0)
    parser.add_argument("--jitter-seconds", type=float, default=4.0)
    parser.add_argument("--scroll-rounds", type=int, default=None)
    parser.add_argument("--resume", action="store_true")
    parser.add_argument("--allow-live-network", action="store_true")
    args = parser.parse_args()
    if not args.allow_live_network:
        parser.error("--allow-live-network is required for browser capture")
    if not 1 <= args.limit <= 50:
        parser.error("--limit must be from 1 to 50")
    if not 1 <= args.max_total_comments <= 5000:
        parser.error("--max-total-comments must be from 1 to 5000")
    if not 1 <= args.manual_wait_seconds <= 300:
        parser.error("--manual-wait-seconds must be from 1 to 300")
    if not 0.0 <= args.cooldown_seconds <= 120.0:
        parser.error("--cooldown-seconds must be from 0 to 120")
    if not 0.0 <= args.jitter_seconds <= 60.0:
        parser.error("--jitter-seconds must be from 0 to 60")
    scroll_rounds = (4 if args.remaining_pilot else 0) if args.scroll_rounds is None else args.scroll_rounds
    if not 0 <= scroll_rounds <= 6:
        parser.error("--scroll-rounds must be from 0 to 6")
    if args.output_jsonl.suffix.lower() != ".jsonl":
        parser.error("Capture output path must have a .jsonl suffix")
    try:
        as_of = datetime.fromisoformat(args.as_of.replace("Z", "+00:00")) if args.as_of else datetime.now(UTC)
    except ValueError:
        parser.error("--as-of must be an ISO-8601 datetime")
    if args.url is not None:
        if args.resume:
            parser.error("--resume is only supported with --remaining-pilot")
        receipt_path = ensure_new_capture_paths(args.output_jsonl)
    elif not args.resume and (
        args.output_jsonl.exists()
        or args.output_jsonl.with_suffix(".state.json").exists()
        or args.output_jsonl.with_suffix(".receipt.json").exists()
    ):
        raise FileExistsError("Batch JSONL, state, and receipt paths must all be new unless --resume is set")

    try:
        cookie_file, ms_token = resolve_capture_credentials(args.cookies_file)
    except ValueError as exc:
        parser.error(str(exc))
    session_cookies = _load_tiktok_session_cookies(cookie_file, ms_token)

    if args.remaining_pilot:
        manifest, _, _ = load_verified_corpus(args.base_corpus)
        targets = select_remaining_pilot_urls(args.base_corpus, as_of_utc=as_of)
        if not targets:
            print(json.dumps({"status": "NOTHING_REMAINING", "base_snapshot_id": manifest.snapshot_id}, indent=2))
            return
        with sync_playwright() as playwright:
            browser = playwright.chromium.launch(headless=False)
            try:
                context = browser.new_context(locale="vi-VN")
                apply_session_cookies(context, session_cookies)
                page = context.new_page()
                batch_receipt = run_batch_comment_capture(
                    page,
                    targets,
                    args.output_jsonl,
                    base_snapshot_id=manifest.snapshot_id,
                    limit_per_video=args.limit,
                    max_total_comments=args.max_total_comments,
                    manual_wait_seconds=args.manual_wait_seconds,
                    scroll_rounds=scroll_rounds,
                    cooldown_seconds=args.cooldown_seconds,
                    jitter_seconds=args.jitter_seconds,
                    resume=args.resume,
                )
                context.close()
            finally:
                browser.close()
        print(json.dumps(batch_receipt, ensure_ascii=False, indent=2))
        return

    manifest, _, videos = load_verified_corpus(args.base_corpus)
    known = dict(zip(videos["video_id"].astype(str), videos["create_time"].astype(str)))
    video_id = validate_known_video_url(args.url, known, as_of)

    start = time.monotonic()
    with sync_playwright() as playwright:
        browser = playwright.chromium.launch(headless=False)
        try:
            context = browser.new_context(locale="vi-VN")
            apply_session_cookies(context, session_cookies)
            page = context.new_page()
            response = page.goto(args.url, wait_until="domcontentloaded", timeout=45000)
            if response is None or response.status != 200 or urlparse(page.url).netloc != "www.tiktok.com":
                raise ValueError("Video page did not load normally")
            validate_loaded_video_identity(page.url, video_id)
            rows, manual_challenge_seen = capture_comments_on_page(
                page,
                video_id,
                limit=args.limit,
                manual_wait_seconds=args.manual_wait_seconds,
                scroll_rounds=scroll_rounds,
            )
            validate_loaded_video_identity(page.url, video_id)
            context.close()
        finally:
            browser.close()

    write_normalized_jsonl(rows, args.output_jsonl)
    receipt = {
        "source": "playwright_rendered_video_page",
        "base_snapshot_id": manifest.snapshot_id,
        "video_id": video_id,
        "url": args.url,
        "comment_count": len(rows),
        "comment_id_scheme": "dom_derived_sha256_not_tiktok_native",
        "manual_challenge_seen": manual_challenge_seen,
        "elapsed_seconds": round(time.monotonic() - start, 3),
        "source_sha256": hashlib.sha256(args.output_jsonl.read_bytes()).hexdigest(),
    }
    with receipt_path.open("x", encoding="utf-8", newline="\n") as fp:
        fp.write(json.dumps(receipt, indent=2) + "\n")
    print(json.dumps(receipt, ensure_ascii=False, indent=2))


if __name__ == "__main__":
    main()
