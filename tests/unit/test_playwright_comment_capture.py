from __future__ import annotations

import subprocess
import sys
from datetime import UTC, datetime
from pathlib import Path
from typing import Any, cast

import pytest


def _sync_playwright() -> Any:
    pw_mod = pytest.importorskip("playwright.sync_api")
    return pw_mod.sync_playwright


def _launch_headless_chromium(pw: Any) -> Any:
    try:
        return pw.chromium.launch(headless=True)
    except Exception as exc:
        msg = str(exc).lower()
        if "executable doesn't exist" in msg or "executable does not exist" in msg or "playwright install" in msg:
            pytest.skip("Playwright Chromium browser binary is not installed on this host")
        raise


def test_normalize_rendered_cards_preserves_text_and_bounds_rows() -> None:
    from pipelines.capture_playwright_comments.capture import normalize_rendered_cards

    first = (
        '<div class="DivCommentItemWrapper"><a href="/@viewer_one">Profile</a>'
        '<div data-e2e="comment-username-1">Viewer One</div>'
        '<span data-e2e="comment-level-1">  Gia <b>hợp lý</b><img alt="😀">  </span></div>'
    )
    second = (
        '<div class="DivCommentItemWrapper"><a href="/@viewer_two">Profile</a>'
        '<span data-e2e="comment-level-1">Món ngon</span></div>'
    )
    rows = normalize_rendered_cards([first, second], "7710927418533399815", limit=1)

    assert len(rows) == 1
    assert rows[0]["video_id"] == "7710927418533399815"
    assert rows[0]["author_handle"] == "viewer_one"
    assert rows[0]["text"] == "  Gia hợp lý😀  "
    assert rows[0]["comment_id"].startswith("dom_")


def test_normalize_rendered_cards_rejects_missing_comment_text() -> None:
    from pipelines.capture_playwright_comments.capture import normalize_rendered_cards

    with pytest.raises(ValueError, match="No visible comments"):
        normalize_rendered_cards(
            ['<div class="DivCommentItemWrapper"><span data-e2e="comment-level-1">  </span></div>'],
            "7710927418533399815", limit=50,
        )


def test_validate_known_video_url_rejects_host_and_old_or_unknown_ids() -> None:
    from pipelines.capture_playwright_comments.capture import validate_known_video_url

    videos = {"7710927418533399815": "2026-11-22T09:36:43+00:00"}
    as_of = datetime(2026, 11, 25, tzinfo=UTC)
    good = "https://www.tiktok.com/@tinhtungtangvn/video/7710927418533399815"
    assert validate_known_video_url(good, videos, as_of) == "7710927418533399815"
    with pytest.raises(ValueError):
        validate_known_video_url(good.replace("www.tiktok.com", "example.org"), videos, as_of)
    with pytest.raises(ValueError):
        validate_known_video_url(good.replace("7710927418533399815", "999"), videos, as_of)
    with pytest.raises(ValueError):
        validate_known_video_url(good, videos, datetime(2027, 5, 1, tzinfo=UTC))


def test_write_normalized_jsonl_requires_rows_and_new_path(tmp_path: Path) -> None:
    from pipelines.capture_playwright_comments.capture import write_normalized_jsonl

    output = tmp_path / "captured.jsonl"
    with pytest.raises(ValueError):
        write_normalized_jsonl([], output)
    assert not output.exists()
    write_normalized_jsonl([{"video_id": "1", "comment_id": "dom_1", "text": "Good"}], output)
    assert output.read_text(encoding="utf-8").count("\n") == 1
    with pytest.raises(FileExistsError):
        write_normalized_jsonl([{"video_id": "1", "comment_id": "dom_2", "text": "More"}], output)


def test_visible_comment_cards_reads_observed_dom_wrapper() -> None:
    from pipelines.capture_playwright_comments.capture import visible_comment_cards

    sync_playwright = _sync_playwright()
    with sync_playwright() as pw:
        browser = _launch_headless_chromium(pw)
        try:
            page = browser.new_page()
            page.set_content('<div class="DivCommentItemWrapper"><span data-e2e="comment-level-1">Good</span></div>')
            cards = visible_comment_cards(page, limit=50)
            assert len(cards) == 1
            assert "Good" in cards[0]
        finally:
            browser.close()


def test_capture_comments_on_page_opens_visible_panel() -> None:
    from pipelines.capture_playwright_comments.capture import capture_comments_on_page

    sync_playwright = _sync_playwright()
    with sync_playwright() as pw:
        browser = _launch_headless_chromium(pw)
        try:
            page = browser.new_page()
            page.set_content('<section><div data-e2e="comment-icon">Comments</div></section><div id="target"></div>')
            page.locator("section").evaluate(
                "(e) => e.addEventListener('click', () => {"
                "document.getElementById('target').innerHTML = "
                "'<div class=\"DivCommentItemWrapper\"><a href=\"/@viewer\">Viewer</a>"
                "<span data-e2e=\"comment-level-1\">Good</span></div>';})"
            )
            rows, challenge_seen = capture_comments_on_page(
                page, "123", limit=50, manual_wait_seconds=1, no_comment_wait_seconds=1,
            )
            assert len(rows) == 1 and rows[0]["text"] == "Good"
            assert not challenge_seen
        finally:
            browser.close()


def test_capture_comments_on_page_stops_at_unsolved_slider() -> None:
    from pipelines.capture_playwright_comments.capture import capture_comments_on_page
    from pipelines.crawl_incremental.providers import AntiBotChallengeError

    sync_playwright = _sync_playwright()
    with sync_playwright() as pw:
        browser = _launch_headless_chromium(pw)
        try:
            page = browser.new_page()
            page.set_content(
                '<section><div data-e2e="comment-icon">Comments</div></section>'
                '<div role="dialog" class="CaptchaVerifyPanel">Kéo thanh trượt để ghép hình</div>'
            )
            with pytest.raises(AntiBotChallengeError):
                capture_comments_on_page(
                    page, "123", limit=50, manual_wait_seconds=1, no_comment_wait_seconds=1,
                )
        finally:
            browser.close()


def test_capture_comments_on_page_waits_for_visible_list_to_settle() -> None:
    from pipelines.capture_playwright_comments.capture import capture_comments_on_page

    sync_playwright = _sync_playwright()
    with sync_playwright() as pw:
        browser = _launch_headless_chromium(pw)
        try:
            page = browser.new_page()
            page.set_content(
                '<section><div data-e2e="comment-icon">Comments</div></section>'
                '<div class="DivCommentItemWrapper"><span data-e2e="comment-level-1">First</span></div>'
                '<div id="target"></div>'
            )
            page.evaluate(
                "setTimeout(() => {document.getElementById('target').innerHTML = "
                "'<div class=\"DivCommentItemWrapper\"><span data-e2e=\"comment-level-1\">Second</span></div>';}, 1200)"
            )
            rows, _ = capture_comments_on_page(
                page, "123", limit=50, manual_wait_seconds=1, no_comment_wait_seconds=2,
            )
            assert [row["text"] for row in rows] == ["First", "Second"]
        finally:
            browser.close()


def test_capture_cli_requires_live_network_opt_in(tmp_path: Path) -> None:
    output = tmp_path / "comments.jsonl"
    result = subprocess.run(
        [sys.executable, "-m", "pipelines.capture_playwright_comments",
         "--url", "https://www.tiktok.com/@creator/video/123", "--output-jsonl", str(output)],
        capture_output=True, text=True, check=False,
    )
    assert result.returncode == 2
    assert "--allow-live-network" in result.stderr
    assert not output.exists()


def test_capture_paths_reject_existing_receipt_before_capture(tmp_path: Path) -> None:
    from pipelines.capture_playwright_comments.capture import ensure_new_capture_paths

    output = tmp_path / "video.jsonl"
    receipt = output.with_suffix(".receipt.json")
    receipt.write_text("previous receipt", encoding="utf-8")
    with pytest.raises(FileExistsError):
        ensure_new_capture_paths(output)
    assert receipt.read_text(encoding="utf-8") == "previous receipt"
    assert not output.exists()


def test_capture_comments_ignores_captcha_word_inside_real_comment() -> None:
    from pipelines.capture_playwright_comments.capture import capture_comments_on_page

    sync_playwright = _sync_playwright()
    with sync_playwright() as pw:
        browser = _launch_headless_chromium(pw)
        try:
            page = browser.new_page()
            page.set_content(
                '<div id="app"><section><div data-e2e="comment-icon">Comments</div></section>'
                '<div class="DivCommentItemWrapper">'
                '<span data-e2e="comment-level-1">This comment mentions captcha and Kéo thanh trượt</span></div></div>'
            )
            rows, challenge_seen = capture_comments_on_page(
                page, "123", limit=50, manual_wait_seconds=1, no_comment_wait_seconds=2,
            )
            assert len(rows) == 1 and not challenge_seen
        finally:
            browser.close()


def test_validate_loaded_video_identity_rejects_same_host_redirect() -> None:
    from pipelines.capture_playwright_comments.capture import validate_loaded_video_identity

    with pytest.raises(ValueError):
        validate_loaded_video_identity("https://www.tiktok.com/@other/video/999", "123")
    assert validate_loaded_video_identity("https://www.tiktok.com/@creator/video/123?lang=vi", "123") == "123"


def test_capture_comments_detects_visible_slider_without_named_class() -> None:
    from pipelines.capture_playwright_comments.capture import capture_comments_on_page
    from pipelines.crawl_incremental.providers import AntiBotChallengeError

    sync_playwright = _sync_playwright()
    with sync_playwright() as pw:
        browser = _launch_headless_chromium(pw)
        try:
            page = browser.new_page()
            page.set_content(
                '<section><div data-e2e="comment-icon">Comments</div></section>'
                '<div style="position:fixed">Kéo thanh trượt để ghép hình</div>'
            )
            with pytest.raises(AntiBotChallengeError):
                capture_comments_on_page(page, "123", manual_wait_seconds=1, no_comment_wait_seconds=1)
        finally:
            browser.close()


def test_capture_comments_rejects_manual_wait_above_five_minutes() -> None:
    from pipelines.capture_playwright_comments.capture import capture_comments_on_page

    with pytest.raises(ValueError, match="bounds"):
        capture_comments_on_page(cast(Any, object()), "123", manual_wait_seconds=301)


def test_capture_cli_validates_bounds_and_env_precedence_before_browser_launch(tmp_path: Path) -> None:
    output = tmp_path / "comments.jsonl"
    for bad_args in (["--limit", "0"], ["--limit", "51"], ["--manual-wait-seconds", "301"]):
        res = subprocess.run(
            [
                sys.executable,
                "-m",
                "pipelines.capture_playwright_comments",
                "--allow-live-network",
                "--url",
                "https://www.tiktok.com/@creator/video/123",
                "--output-jsonl",
                str(output),
                *bad_args,
            ],
            capture_output=True,
            text=True,
            check=False,
        )
        assert res.returncode == 2
        assert not output.exists()

    from pipelines.capture_playwright_comments.__main__ import resolve_capture_credentials

    env_cookie = tmp_path / "env_cookies.txt"
    env_cookie.write_text("# Netscape HTTP Cookie File\n", encoding="utf-8")
    dotenv_cookie = tmp_path / "dotenv_cookies.txt"
    dotenv_cookie.write_text("# Netscape HTTP Cookie File\n", encoding="utf-8")
    dotenv_file = tmp_path / ".env"
    dotenv_file.write_text(
        f"MS_TOKEN=dotenv_tok\nTIKTOK_COOKIES_FILE={dotenv_cookie}\n",
        encoding="utf-8",
    )

    cookie_path, token = resolve_capture_credentials(
        None,
        dotenv_path=dotenv_file,
        environ={"MS_TOKEN": "  env_tok  ", "TIKTOK_COOKIES_FILE": f"  {env_cookie}  "},
    )
    assert cookie_path == env_cookie
    assert token == "env_tok"

    with pytest.raises(ValueError, match="MS_TOKEN"):
        resolve_capture_credentials(
            env_cookie,
            dotenv_path=tmp_path / "missing.env",
            environ={"MS_TOKEN": "   "},
        )


def test_ensure_new_capture_paths_requires_jsonl_suffix_and_sanitizes_cookie_apply_error(
    tmp_path: Path,
) -> None:
    from pipelines.capture_playwright_comments.capture import (
        apply_session_cookies,
        ensure_new_capture_paths,
    )

    with pytest.raises(ValueError, match=r"\.jsonl"):
        ensure_new_capture_paths(tmp_path / "comments.txt")

    class _FailingContext:
        def add_cookies(self, cookies: list[dict[str, str]]) -> None:
            raise RuntimeError(f"Chromium rejected {cookies[0]['value']}")

    with pytest.raises(ValueError, match="cookies") as exc_info:
        apply_session_cookies(_FailingContext(), {"msToken": "SUPER_SECRET_COOKIE_123"})  # type: ignore[arg-type]
    assert "SUPER_SECRET_COOKIE_123" not in str(exc_info.value)


def test_normalize_rendered_cards_handles_void_tags_and_ignores_in_body_mentions() -> None:
    from pipelines.capture_playwright_comments.capture import normalize_rendered_cards

    with_wbr_and_query_author = (
        '<div class="DivCommentItemWrapper">'
        '<a href="https://www.tiktok.com/@real_author?lang=vi#profile">Profile</a>'
        '<span data-e2e="comment-level-1">Check <wbr>'
        '<a href="/@mentioned_friend">@mentioned_friend</a> ngon</span>'
        '<div class="DivReplyAction">Trả lời · 2h</div></div>'
    )
    without_header_author = (
        '<div class="DivCommentItemWrapper">'
        '<span data-e2e="comment-level-1">Tag <a href="/@mentioned_only">@mentioned_only</a></span>'
        "</div>"
    )

    rows = normalize_rendered_cards(
        [with_wbr_and_query_author, without_header_author],
        "7710927418533399815",
        limit=10,
    )
    assert rows[0]["author_handle"] == "real_author"
    assert rows[0]["text"] == "Check @mentioned_friend ngon"
    assert rows[1]["author_handle"] == ""
    assert rows[1]["text"] == "Tag @mentioned_only"


def test_challenge_overlay_ignores_zero_size_hidden_parent_and_verified_creator_badge() -> None:
    from pipelines.capture_playwright_comments.capture import capture_comments_on_page

    sync_playwright = _sync_playwright()
    with sync_playwright() as pw:
        browser = _launch_headless_chromium(pw)
        try:
            page = browser.new_page()
            page.set_content(
                '<section><div data-e2e="comment-icon">Comments</div></section>'
                '<div id="captcha-verify-container-main-page" style="display:block;width:300px;height:0"></div>'
                '<div style="opacity:0"><div class="secsdk-captcha-wrapper" style="width:200px;height:200px">'
                "Kéo thanh trượt</div></div>"
                '<div aria-hidden="true"><div class="CaptchaModal" style="width:200px;height:200px">'
                "Security verification</div></div>"
                '<div class="DivUserVerify"><span class="SpanVerifyWrapper">Creator Verified</span></div>'
                '<div class="DivCommentItemWrapper"><span data-e2e="comment-level-1">Ngon quá</span></div>'
            )
            rows, challenge_seen = capture_comments_on_page(
                page, "123", manual_wait_seconds=1, no_comment_wait_seconds=2,
            )
            assert len(rows) == 1
            assert rows[0]["text"] == "Ngon quá"
            assert not challenge_seen
        finally:
            browser.close()


def test_capture_comments_waits_for_hydrated_icon_skips_skeleton_cards_and_guards_loop_redirect() -> None:
    from pipelines.capture_playwright_comments.capture import (
        capture_comments_on_page,
        validate_known_video_url,
        validate_loaded_video_identity,
    )

    videos = {"7710927418533399815": "2026-11-22T09:36:43+00:00"}
    as_of = datetime(2026, 11, 25, tzinfo=UTC)
    with pytest.raises(ValueError):
        validate_known_video_url(
            "https://www.tiktok.com:8443/@tinhtungtangvn/video/7710927418533399815",
            videos,
            as_of,
        )
    with pytest.raises(ValueError):
        validate_loaded_video_identity("https://www.tiktok.com:8443/@creator/video/123", "123")

    sync_playwright = _sync_playwright()
    with sync_playwright() as pw:
        browser = _launch_headless_chromium(pw)
        try:
            page = browser.new_page()
            page.set_content(
                '<div id="header"></div>'
                '<div class="DivCommentItemWrapper"><div class="SkeletonLine"></div></div>'
                '<div id="real"></div>'
            )
            page.evaluate(
                """() => {
                    setTimeout(() => {
                        const header = document.getElementById('header');
                        header.innerHTML = '<section><div data-e2e="comment-icon">Comments</div></section>';
                        header.querySelector('section').addEventListener('click', () => {
                            setTimeout(() => {
                                document.getElementById('real').innerHTML =
                                    '<div class="DivCommentItemWrapper">' +
                                    '<span data-e2e="comment-level-1"><img alt="🍜"></span></div>';
                            }, 300);
                        });
                    }, 300);
                }"""
            )
            rows, _ = capture_comments_on_page(
                page, "123", limit=1, manual_wait_seconds=1, no_comment_wait_seconds=4,
            )
            assert len(rows) == 1
            assert rows[0]["text"] == "🍜"

            redirected_page = browser.new_page()

            def _fulfill_video(route: Any) -> None:
                route.fulfill(
                    status=200,
                    content_type="text/html",
                    body=(
                        '<section onclick="history.pushState({}, \'\', \'/@other/video/999\')">'
                        '<div data-e2e="comment-icon">Comments</div></section>'
                        '<div class="DivCommentItemWrapper">'
                        '<span data-e2e="comment-level-1">Wrong video comment</span></div>'
                    ),
                )

            redirected_page.route("https://www.tiktok.com/@creator/video/123", _fulfill_video)
            redirected_page.goto("https://www.tiktok.com/@creator/video/123")
            with pytest.raises(ValueError, match="video ID differs"):
                capture_comments_on_page(
                    redirected_page, "123", manual_wait_seconds=1, no_comment_wait_seconds=2,
                )
        finally:
            browser.close()


def test_select_remaining_pilot_urls_excludes_old_and_already_commented_videos(tmp_path: Path) -> None:
    import hashlib
    import json

    import pandas as pd

    from pipelines.capture_playwright_comments.capture import select_remaining_pilot_urls

    corpus = tmp_path / "gold_v2"
    corpus.mkdir()
    pd.DataFrame([{"creator_id": "c1", "unique_id": "saigonmap"}]).to_parquet(
        corpus / "dim_creators.parquet", index=False,
    )
    pd.DataFrame(
        [
            {
                "video_id": "100",
                "author_id": "c1",
                "author_handle": "saigonmap",
                "create_time": "2024-05-01T00:00:00+00:00",
            },
            {
                "video_id": "200",
                "author_id": "c1",
                "author_handle": "saigonmap",
                "create_time": "2026-11-22T10:00:00+00:00",
            },
            {
                "video_id": "300",
                "author_id": "c1",
                "author_handle": "ansapsaigon",
                "create_time": "2026-11-21T10:00:00+00:00",
            },
            {
                "video_id": "400",
                "author_id": "c1",
                "author_handle": "dicungphuc",
                "create_time": "2026-11-23T10:00:00+00:00",
            },
        ]
    ).to_parquet(corpus / "fact_videos.parquet", index=False)
    pd.DataFrame(
        [{"video_id": "200", "comment_id": "dom_1", "text": "Ngon", "original_text": "Ngon"}]
    ).to_parquet(corpus / "fact_comments.parquet", index=False)

    files_meta = []
    for fname, rows, cols in (
        ("dim_creators.parquet", 1, 2),
        ("fact_videos.parquet", 4, 4),
        ("fact_comments.parquet", 1, 4),
    ):
        fpath = corpus / fname
        files_meta.append(
            {
                "filename": fname,
                "rows": rows,
                "columns": cols,
                "sha256": hashlib.sha256(fpath.read_bytes()).hexdigest(),
                "size_bytes": fpath.stat().st_size,
            }
        )
    (corpus / "manifest.json").write_text(
        json.dumps(
            {
                "snapshot_id": "gold_v2",
                "created_at": "2026-11-25T00:00:00+00:00",
                "date_window_start": "2024-05-01",
                "date_window_end": "2026-11-23",
                "total_creators": 1,
                "total_videos": 4,
                "transcribed_videos": 0,
                "poi_tagged_videos": 0,
                "ec_tagged_videos": 0,
                "files": files_meta,
                "caveats": [],
            }
        ),
        encoding="utf-8",
    )

    targets = select_remaining_pilot_urls(corpus, as_of_utc=datetime(2026, 11, 25, tzinfo=UTC))
    assert targets == [
        ("400", "https://www.tiktok.com/@dicungphuc/video/400"),
        ("300", "https://www.tiktok.com/@ansapsaigon/video/300"),
    ]


def test_capture_comments_on_page_scrolls_up_to_limit_and_allows_zero_comments() -> None:
    from pipelines.capture_playwright_comments.capture import capture_comments_on_page

    sync_playwright = _sync_playwright()
    with sync_playwright() as pw:
        browser = _launch_headless_chromium(pw)
        try:
            page = browser.new_page()
            page.set_content(
                '<section><div data-e2e="comment-icon">Comments</div></section>'
                '<div id="panel" style="height:100px;overflow-y:auto">'
                '<div style="height:300px">'
                '<div class="DivCommentItemWrapper"><span data-e2e="comment-level-1">First</span></div>'
                '<div id="more"></div></div></div>'
            )
            page.locator("#panel").evaluate(
                """el => el.addEventListener('scroll', () => {
                    document.getElementById('more').innerHTML =
                        '<div class="DivCommentItemWrapper"><span data-e2e="comment-level-1">Second</span></div>' +
                        '<div class="DivCommentItemWrapper"><span data-e2e="comment-level-1">Third</span></div>';
                }, { once: true })"""
            )
            rows, _ = capture_comments_on_page(
                page,
                "123",
                limit=2,
                manual_wait_seconds=1,
                no_comment_wait_seconds=2,
                scroll_rounds=3,
                scroll_pause_ms=200,
            )
            assert [r["text"] for r in rows] == ["First", "Second"]

            empty_page = browser.new_page()
            empty_page.set_content(
                '<section><div data-e2e="comment-icon">0</div></section>'
                "<div>Hãy là người đầu tiên bình luận</div>"
            )
            zero_rows, zero_chal = capture_comments_on_page(
                empty_page,
                "456",
                manual_wait_seconds=1,
                no_comment_wait_seconds=1,
                allow_zero_comments=True,
            )
            assert zero_rows == []
            assert not zero_chal
        finally:
            browser.close()


def test_run_batch_comment_capture_reuses_page_applies_cooldown_checkpoints_and_resumes(
    tmp_path: Path,
) -> None:
    import json

    from pipelines.capture_playwright_comments.capture import run_batch_comment_capture
    from pipelines.crawl_incremental.providers import AntiBotChallengeError

    sleeps: list[float] = []
    block_third = True

    def _router(route: Any) -> None:
        url = route.request.url
        if url.endswith("/video/111"):
            body = (
                '<section><div data-e2e="comment-icon">2</div></section>'
                '<div class="DivCommentItemWrapper"><a href="/@u1">u1</a>'
                '<span data-e2e="comment-level-1">Ngon 1</span></div>'
                '<div class="DivCommentItemWrapper"><a href="/@u2">u2</a>'
                '<span data-e2e="comment-level-1">Ngon 2</span></div>'
            )
        elif url.endswith("/video/222"):
            body = (
                '<section><div data-e2e="comment-icon">0</div></section>'
                "<div>Chưa có bình luận nào</div>"
            )
        else:
            if block_third:
                body = (
                    '<section><div data-e2e="comment-icon">5</div></section>'
                    '<div class="CaptchaVerifyPanel">Kéo thanh trượt để ghép hình</div>'
                )
            else:
                body = (
                    '<section><div data-e2e="comment-icon">1</div></section>'
                    '<div class="DivCommentItemWrapper"><a href="/@u3">u3</a>'
                    '<span data-e2e="comment-level-1">Ngon 3</span></div>'
                )
        route.fulfill(status=200, content_type="text/html", body=body)

    targets = [
        ("111", "https://www.tiktok.com/@c1/video/111"),
        ("222", "https://www.tiktok.com/@c2/video/222"),
        ("333", "https://www.tiktok.com/@c3/video/333"),
    ]
    out_jsonl = tmp_path / "batch_comments.jsonl"

    sync_playwright = _sync_playwright()
    with sync_playwright() as pw:
        browser = _launch_headless_chromium(pw)
        try:
            page = browser.new_page()
            page.route("https://www.tiktok.com/**", _router)
            with pytest.raises(AntiBotChallengeError):
                run_batch_comment_capture(
                    page,
                    targets,
                    out_jsonl,
                    limit_per_video=50,
                    manual_wait_seconds=1,
                    no_comment_wait_seconds=1,
                    scroll_rounds=1,
                    cooldown_seconds=10.0,
                    jitter_seconds=4.0,
                    sleep_fn=sleeps.append,
                    rng_fn=lambda a, b: 2.5,
                )
            assert sleeps == [12.5, 12.5]
            partial_lines = [json.loads(x) for x in out_jsonl.read_text(encoding="utf-8").splitlines()]
            assert [r["text"] for r in partial_lines] == ["Ngon 1", "Ngon 2"]

            block_third = False
            sleeps.clear()
            receipt = run_batch_comment_capture(
                page,
                targets,
                out_jsonl,
                limit_per_video=50,
                manual_wait_seconds=1,
                no_comment_wait_seconds=1,
                scroll_rounds=1,
                cooldown_seconds=10.0,
                jitter_seconds=4.0,
                resume=True,
                sleep_fn=sleeps.append,
                rng_fn=lambda a, b: 1.5,
            )
            assert sleeps == []
            assert receipt["stopped_reason"] == "completed"
            assert receipt["captured_videos"] == 2
            assert receipt["zero_comment_videos"] == 1
            assert receipt["comment_count"] == 3
            final_lines = [json.loads(x) for x in out_jsonl.read_text(encoding="utf-8").splitlines()]
            assert [r["text"] for r in final_lines] == ["Ngon 1", "Ngon 2", "Ngon 3"]
        finally:
            browser.close()


def test_capture_cli_validates_mutually_exclusive_target_and_cooldown_bounds(tmp_path: Path) -> None:
    out = tmp_path / "out.jsonl"
    for bad, expected_msg in (
        (["--allow-live-network", "--output-jsonl", str(out)], "--remaining-pilot"),
        (
            [
                "--allow-live-network",
                "--url",
                "https://www.tiktok.com/@c/video/1",
                "--remaining-pilot",
                "--output-jsonl",
                str(out),
            ],
            "not allowed with argument",
        ),
        (
            [
                "--allow-live-network",
                "--remaining-pilot",
                "--cooldown-seconds",
                "-1",
                "--output-jsonl",
                str(out),
            ],
            "--cooldown-seconds must be",
        ),
    ):
        res = subprocess.run(
            [sys.executable, "-m", "pipelines.capture_playwright_comments", *bad],
            capture_output=True,
            text=True,
            check=False,
        )
        assert res.returncode == 2
        assert expected_msg in res.stderr
        assert not out.exists()


def test_batch_capture_and_importer_support_explicit_5000_comment_ceiling(tmp_path: Path) -> None:
    import json

    from pipelines.import_authorized_comments.importer import _read_rows

    big_jsonl = tmp_path / "big.jsonl"
    lines = [
        json.dumps(
            {
                "video_id": str(1000 + (i // 50)),
                "comment_id": f"dom_{i}",
                "text": f"Bình luận {i}",
            },
            ensure_ascii=False,
        )
        for i in range(1005)
    ]
    big_jsonl.write_text("\n".join(lines) + "\n", encoding="utf-8")

    with pytest.raises(ValueError, match="1000"):
        _read_rows(big_jsonl)

    rows = _read_rows(big_jsonl, max_rows=5000)
    assert len(rows) == 1005

    with pytest.raises(ValueError, match="5000"):
        _read_rows(big_jsonl, max_rows=5001)

    res = subprocess.run(
        [
            sys.executable,
            "-m",
            "pipelines.capture_playwright_comments",
            "--allow-live-network",
            "--remaining-pilot",
            "--max-total-comments",
            "5001",
            "--output-jsonl",
            str(tmp_path / "out.jsonl"),
        ],
        capture_output=True,
        text=True,
        check=False,
    )
    assert res.returncode == 2
    assert "--max-total-comments" in res.stderr
