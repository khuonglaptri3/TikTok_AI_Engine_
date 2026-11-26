# M3.3 Hybrid Legacy-Grounded Collector & Home Pilot Execution Implementation Plan

> **For agentic workers:** REQUIRED SUB-SKILL: Use superpowers:subagent-driven-development (recommended) or superpowers:executing-plans to implement this plan task-by-task. Steps use checkbox (`- [ ]`) syntax for tracking.

**Goal:** Integrate the verified `TrggTin/21KHDL-TikTok-Analytics` crawling mechanics (`itemStruct` POI/EC/Ad/statsV2 mapping, `isPinnedItem` chronological loop, zero-extra-HTTP `video.as_dict` caching, `TikTokApi` comment pagination, Chapter 3 + `author_unique_ids.txt` F&B creator selection, and UTF-8 subprocess safety) with an automatic `TikTokApi -> yt-dlp` fallback (`--backend auto`), authenticated `64 kbps` `.mp3` extraction, `--resume`, and `--preflight-only` so contributor `K` can run live `M3.3` crawling reliably at home.

**Architecture:** Pure schema-mapping and creator-selection helpers live in `pipelines/crawl_incremental/mappers.py` and `crawler_service.py`, feeding pluggable live providers (`TikTokApiCollectorProvider`, `LiveTikTokCollectorProvider`, `AutoHybridTikTokCollectorProvider`) in `providers.py` and fail-closed `AntiBotChallengeError` handling + `raw_provider_payloads.jsonl` archiving in `worker.py`. `pipelines/pilot_m3_3/` wires `.env` auto-loading, `--backend`, `--auto-creators`, `--resume`, and `--preflight-only` directly into the bounded `M3.3` capture -> CPU ASR -> Dual-Sink Gold -> BM25 -> searchability pipeline.

**Tech Stack:** Python 3.11+, Pydantic v2 (`ConfigDict(frozen=True, allow_inf_nan=False)`), Pandas, `yt-dlp`, optional `TikTokApi` + `playwright`, `faster-whisper`, `pytest`, `mypy` (Linux & `--platform win32`).

**Spec:** [spec.md](spec.md)

## Global Constraints

- Authorized provider/GPU/hosting spend is **`USD 0`**; all unit/integration tests run 100% offline with zero live TikTok requests unless `--allow-live-network` and a non-empty `MS_TOKEN` (or `ms_token`) are explicitly provided at runtime.
- Preserve Dual-Tier Data discipline: never re-crawl or mutate any of the `70,996` historical `video_id`s in `data/corpus/20261118_taxonomy_fix_v1` or historical `data/` files, and keep `CollectorBounds` ceilings (`max_creators <= 5`, `max_candidate_videos <= 50`, `max_succeeded_videos <= 30`, `max_audio_minutes <= 60.0`, `max_comments_total <= 1000`, `session_deadline_seconds <= 7200.0`).
- Never bundle frozen legacy `stealth/js` scripts and never solve, click through, retry around, or switch backends to bypass a CAPTCHA or "verify you are human" gate (`AntiBotChallengeError` halts with `attempts=1` and `stopped_reason="anti_bot_challenge_blocked"`).
- Preserve raw unstripped comment `text` (leading/trailing whitespace intact when non-blank) so downstream `CommentRecord.original_text` and `M5.2` Unicode `NFC` character offsets remain 1-to-1 exact.
- Enforce `encoding="utf-8", errors="replace"` plus `PYTHONIOENCODING="utf-8"` and `PYTHONUTF8="1"` on every `yt-dlp` subprocess for cross-platform Linux/Windows safety, and redact `ms_token`, `msToken`, `sessionid`, `Cookie`, and `--cookies <path>` from all logs, manifests, and receipts.
- All repository reports, docstrings, logs, and guidelines must be in **English** (preserving Vietnamese F&B source examples for evidence integrity) with zero machine-specific absolute user-home paths in Markdown reports and `python3 scripts/check_secrets.py` exiting `0` before every commit.

## Review Focus

1. **Pinned old videos (`isPinnedItem=True` from 2024) at the top of a creator profile (`crawler.py:97-118`):** Discovery in `TikTokApiCollectorProvider` must `continue` past pinned out-of-window items to reach fresh 2026 posts below them, and `break` immediately once the first **unpinned** item is older than `cutoff_utc` (pinned in Task 2).
2. **CAPTCHA / `EmptyResponseException` raised during `AutoHybridTikTokCollectorProvider` (`--backend auto`) or `discover_candidates`:** `AutoHybridTikTokCollectorProvider` must re-raise `AntiBotChallengeError` immediately without falling back to `yt-dlp`, and `BoundedIncrementalCollector.run` must catch `AntiBotChallengeError` in both discovery and per-item collection (`attempts=1`, `stopped_reason="anti_bot_challenge_blocked"`) without crashing (pinned in Task 2).
3. **Unauthenticated `HTTP 403` on `.mp3` extraction & `--cookies <secret_path>` leakage:** `YtDlpAudioConverter64k` / `download_audio_mp3_64k` must pass `Cookie: msToken=...` and `--cookies <path>` to `yt-dlp`, while `_sanitize_reason` strips both cookie values and `--cookies /secret/path/cookies.txt` from failure receipts (pinned in Tasks 1 & 2).
4. **Leading whitespace on Vietnamese comments (`"  Nước dùng đậm đà  "`) & flat `yt-dlp` comment replies (`parent != "root"`):** `map_tiktok_comment_to_input` must reject whitespace-only strings (`"   "`) while keeping `"  Nước dùng đậm đà  "` unstripped, and `map_ytdlp_json_to_detail` must roll child comment counts (`parent == top_id`) into top-level `reply_count` without duplicating child replies as root comments if desired or preserving accurate `reply_count` (pinned in Task 1).
5. **Windows `cp1252` `subprocess.run` crash & missing `source .env` at home:** All subprocesses must pass `encoding="utf-8", errors="replace"` with `PYTHONIOENCODING="utf-8"` / `PYTHONUTF8="1"`, and `load_dotenv_if_present` must bridge lowercase `ms_token=...` in `.env` to `MS_TOKEN` without overwriting already-exported environment variables (pinned in Tasks 1 & 3).

---

### Task 1: `21KHDL-TikTok-Analytics` Schema Mappers, `.env` Bridge, Curated F&B Creator Selector & Authenticated `64 kbps` Audio

**Files:**
- Create: `pipelines/crawl_incremental/mappers.py`
- Modify: `pipelines/crawl_incremental/models.py`
- Modify: `pipelines/crawl_incremental/crawler_service.py`
- Modify: `tests/unit/test_bounded_collector_worker.py`

**Interfaces:**
- Consumes: `RawIncrementalVideoRecord`, `RawCommentInput` (`packages/data_contracts/multimodal.py`), `data/filters/author_unique_ids.txt`, `dim_creators.parquet`
- Produces:
  - `CollectorBackend = Literal["auto", "tiktokapi", "ytdlp"]` and additive fields `collector_backend_requested: str = "auto"`, `collector_backends_used: list[str] = Field(default_factory=list)` on `CrawlManifest` (`pipelines/crawl_incremental/models.py`)
  - `map_tiktok_item_struct_to_detail(raw: dict[str, Any], *, fallback_vid: str = "", fallback_handle: str = "", collected_at_utc: str | None = None) -> dict[str, Any]` (`pipelines/crawl_incremental/mappers.py`)
  - `map_tiktok_comment_to_input(raw: dict[str, Any], *, canonical_vid: str, idx: int) -> dict[str, Any] | None` (`pipelines/crawl_incremental/mappers.py`)
  - `map_ytdlp_json_to_detail(raw: dict[str, Any], *, candidate: dict[str, Any], collected_at_utc: str | None = None) -> tuple[dict[str, Any], list[dict[str, Any]]]` (`pipelines/crawl_incremental/mappers.py`)
  - `utf8_subprocess_env(base_env: dict[str, str] | None = None) -> dict[str, str]` (`pipelines/crawl_incremental/crawler_service.py`)
  - `load_dotenv_if_present(dotenv_path: Path = Path(".env"), *, target_env: dict[str, str] | None = None) -> dict[str, str]` (`pipelines/crawl_incremental/crawler_service.py`)
  - `select_curated_fnb_creators(base_corpus_dir: Path, *, top_k: int = 5, filter_file: Path = Path("data/filters/author_unique_ids.txt")) -> list[str]` (`pipelines/crawl_incremental/crawler_service.py`)
  - `download_audio_mp3_64k(tiktok_url: str, output_mp3: Path, *, ms_token: str = "", cookies_file: Path | None = None, timeout_sec: int = 45) -> bool` (`pipelines/crawl_incremental/crawler_service.py`)

- [ ] **Step 1: Write failing unit tests in `tests/unit/test_bounded_collector_worker.py`**

Append tests verifying:
```python
def test_mappers_preserve_21khdl_item_struct_poi_ec_ad_and_unstripped_comments() -> None:
    from pipelines.crawl_incremental.mappers import (
        map_tiktok_comment_to_input,
        map_tiktok_item_struct_to_detail,
        map_ytdlp_json_to_detail,
    )

    raw_item = {
        "id": "7480001112223334445",
        "createTime": 1763500000,
        "desc": "Review phở bò Quận 1 #ancungtiktok #phobo",
        "isAd": True,
        "isECVideo": "1",
        "isPinnedItem": False,
        "playlistId": "pl_fnb_01",
        "author": {"id": "u_01", "uniqueId": "spicykim9386", "nickname": "Spicy Kim"},
        "authorStats": {"followerCount": 820000},
        "video": {"duration": 48, "VQScore": 72.5},
        "statsV2": {
            "playCount": "150000",
            "diggCount": "9200",
            "commentCount": "140",
            "shareCount": "310",
            "collectCount": "1200",
        },
        "challenges": [{"title": "ancungtiktok"}, {"title": "#saigonfood"}],
        "poi": {
            "id": "poi_999",
            "name": "Phở Hòa Pasteur",
            "address": "260C Pasteur, Quận 3",
            "city": "Ho Chi Minh City",
            "ttTypeNameTiny": "Noodle House",
        },
    }
    detail = map_tiktok_item_struct_to_detail(raw_item, collected_at_utc="2026-11-23T04:00:00+00:00")
    assert detail["video_id"] == "7480001112223334445"
    assert detail["author_handle"] == "spicykim9386"
    assert detail["follower_count"] == 820000
    assert detail["collect_count"] == 1200
    assert detail["is_ad"] is True
    assert detail["is_ec_video"] is True
    assert detail["playlist_id"] == "pl_fnb_01"
    assert detail["poi_name"] == "Phở Hòa Pasteur"
    assert detail["poi_category_tiny"] == "Noodle House"
    assert detail["hashtags"] == ["ancungtiktok", "saigonfood"]

    # Unstripped leading/trailing spaces preserved for M5.2 NFC offsets; blank rejected
    c_ok = map_tiktok_comment_to_input(
        {
            "cid": "c_901",
            "text": "  Nước dùng đậm đà nhưng giá hơi cao  ",
            "digg_count": 17,
            "reply_comment_total": 4,
            "user": {"uid": "u9", "unique_id": "diner_vn"},
        },
        canonical_vid="7480001112223334445",
        idx=0,
    )
    assert c_ok is not None
    assert c_ok["text"] == "  Nước dùng đậm đà nhưng giá hơi cao  "
    assert c_ok["like_count"] == 17
    assert c_ok["reply_count"] == 4
    assert (
        map_tiktok_comment_to_input({"cid": "c_blank", "text": "   "}, canonical_vid="7480001112223334445", idx=1)
        is None
    )

    # yt-dlp mapping rolls flat child replies into parent reply_count and extracts collect_count
    yt_detail, yt_comments = map_ytdlp_json_to_detail(
        {
            "id": "748000999",
            "timestamp": 1763500000,
            "uploader": "haidangrevieww",
            "uploader_id": "uid_hd",
            "description": "Bún bò Huế ngon",
            "duration": 35,
            "view_count": 60000,
            "like_count": 3000,
            "repost_count": 80,
            "collect_count": 450,
            "comments": [
                {"id": "root_1", "parent": "root", "author": "a1", "text": "  Ngon xuất sắc ", "like_count": 5},
                {"id": "rep_1", "parent": "root_1", "author": "a2", "text": "Đồng ý luôn", "like_count": 1},
            ],
        },
        candidate={"video_id": "748000999", "author_handle": "haidangrevieww"},
    )
    assert yt_detail["collect_count"] == 450
    assert yt_detail["share_count"] == 80
    by_cid = {c["comment_id"]: c for c in yt_comments}
    assert by_cid["root_1"]["reply_count"] == 1
    assert by_cid["root_1"]["text"] == "  Ngon xuất sắc "


def test_dotenv_bridge_curated_creators_and_authenticated_mp3_download(
    tmp_path: Path, monkeypatch: pytest.MonkeyPatch
) -> None:
    from pipelines.crawl_incremental import crawler_service

    # 1. .env bridges lowercase ms_token -> MS_TOKEN without overwriting existing env
    dotenv_file = tmp_path / ".env"
    dotenv_file.write_text("ms_token = 'tok_from_legacy_env'\nTIKTOK_BROWSER=webkit\n", encoding="utf-8")
    env_box: dict[str, str] = {}
    crawler_service.load_dotenv_if_present(dotenv_file, target_env=env_box)
    assert env_box["MS_TOKEN"] == "tok_from_legacy_env"
    assert env_box["TIKTOK_BROWSER"] == "webkit"

    env_existing = {"MS_TOKEN": "already_set_tok"}
    crawler_service.load_dotenv_if_present(dotenv_file, target_env=env_existing)
    assert env_existing["MS_TOKEN"] == "already_set_tok"

    # 2. Curated F&B creators prioritize author_unique_ids.txt present in dim_creators, then Chapter 3 thresholds
    corpus_dir = tmp_path / "gold"
    corpus_dir.mkdir()
    pd.DataFrame(
        [
            {"unique_id": "low_views_user", "median_play_count": 5000.0, "median_engagement_rate": 0.08, "avg_videos_per_week": 9.0, "sample_video_count": 100, "follower_count": 90000},
            {"unique_id": "ch3_qualified_b", "median_play_count": 65000.0, "median_engagement_rate": 0.045, "avg_videos_per_week": 3.5, "sample_video_count": 120, "follower_count": 300000},
            {"unique_id": "haidangrevieww", "median_play_count": 80000.0, "median_engagement_rate": 0.05, "avg_videos_per_week": 2.1, "sample_video_count": 255, "follower_count": 500000},
            {"unique_id": "spicykim9386", "median_play_count": 95000.0, "median_engagement_rate": 0.06, "avg_videos_per_week": 2.8, "sample_video_count": 298, "follower_count": 900000},
        ]
    ).to_parquet(corpus_dir / "dim_creators.parquet", index=False)
    filt = tmp_path / "author_unique_ids.txt"
    filt.write_text("spicykim9386\nhaidangrevieww\nmissing_from_corpus\n", encoding="utf-8")

    picked = crawler_service.select_curated_fnb_creators(corpus_dir, top_k=3, filter_file=filt)
    assert picked == ["spicykim9386", "haidangrevieww", "ch3_qualified_b"]

    # 3. download_audio_mp3_64k forwards msToken header, --cookies file, and UTF-8 subprocess kwargs
    captured_call: dict[str, Any] = {}
    cookies_txt = tmp_path / "cookies.txt"
    cookies_txt.write_text("# Netscape HTTP Cookie File\n", encoding="utf-8")
    out_mp3 = tmp_path / "audio_64k" / "v1.mp3"

    def _fake_run(cmd: list[str], **kwargs: Any) -> Any:
        captured_call["cmd"] = cmd
        captured_call["kwargs"] = kwargs
        out_mp3.parent.mkdir(parents=True, exist_ok=True)
        out_mp3.write_bytes(b"ID3-64K")

        class _Res:
            returncode = 0

        return _Res()

    monkeypatch.setattr(crawler_service.subprocess, "run", _fake_run)
    ok = crawler_service.download_audio_mp3_64k(
        "https://www.tiktok.com/@spicykim9386/video/123",
        out_mp3,
        ms_token="secret_ms_tok",
        cookies_file=cookies_txt,
    )
    assert ok is True
    assert "Cookie: msToken=secret_ms_tok" in captured_call["cmd"]
    assert "--cookies" in captured_call["cmd"]
    assert str(cookies_txt) in captured_call["cmd"]
    assert captured_call["kwargs"]["encoding"] == "utf-8"
    assert captured_call["kwargs"]["env"]["PYTHONUTF8"] == "1"
```

- [ ] **Step 2: Run test to verify it fails**

Run: `python3 -m pytest tests/unit/test_bounded_collector_worker.py -k "mappers_preserve_21khdl or dotenv_bridge_curated_creators" -v`
Expected: FAIL with `ModuleNotFoundError: No module named 'pipelines.crawl_incremental.mappers'`

- [ ] **Step 3: Implement `mappers.py`, `models.py` fields, and `crawler_service.py` helpers**

1. Create `pipelines/crawl_incremental/mappers.py` implementing `map_tiktok_item_struct_to_detail`, `map_tiktok_comment_to_input`, and `map_ytdlp_json_to_detail` (cleaning `"others"`/`"null"`/`"nan"`/`""` POI/playlist strings to `None`, parsing `"true"`/`"1"`/`True` booleans for `isAd`/`isECVideo`/`isPinnedItem`, preserving unstripped non-blank comment `text`, and rolling child `parent` replies into `reply_count` for `yt-dlp` comments).
2. Add `CollectorBackend = Literal["auto", "tiktokapi", "ytdlp"]` and defaulted `collector_backend_requested: str = "auto"`, `collector_backends_used: list[str] = Field(default_factory=list)` on `CrawlManifest` in `pipelines/crawl_incremental/models.py`.
3. Update `pipelines/crawl_incremental/crawler_service.py` with `utf8_subprocess_env`, `load_dotenv_if_present` (bridging `ms_token` -> `MS_TOKEN` when `MS_TOKEN` is unset), `select_curated_fnb_creators` (`author_unique_ids.txt` priority + Chapter 3 `median_play_count >= 40_000` and `median_engagement_rate >= 0.03` ranking with fallback to remaining `dim_creators` if `< top_k`), and authenticated UTF-8 `download_audio_mp3_64k`.

- [ ] **Step 4: Run tests & `mypy` to verify Task 1 passes**

Run:
- `python3 -m pytest tests/unit/test_bounded_collector_worker.py -v`
- `python3 -m mypy pipelines/crawl_incremental`
Expected: All collector worker tests PASS and `mypy` reports `0` issues.

- [ ] **Step 5: Commit Task 1**

```bash
python3 scripts/check_secrets.py
git add pipelines/crawl_incremental/mappers.py pipelines/crawl_incremental/models.py pipelines/crawl_incremental/crawler_service.py tests/unit/test_bounded_collector_worker.py
git commit -m "feat(m3.3): add 21KHDL itemStruct mappers, curated creator selector, and authenticated mp3 helper"
```

---

### Task 2: Pluggable `TikTokApi` / `yt-dlp` / `auto` Providers, `isPinnedItem` Chronological Loop, Raw Payload Archive & Fail-Closed `AntiBotChallengeError`

**Files:**
- Modify: `pipelines/crawl_incremental/providers.py`
- Modify: `pipelines/crawl_incremental/worker.py`
- Modify: `pipelines/crawl_incremental/__main__.py`
- Modify: `tests/unit/test_bounded_collector_worker.py`

**Interfaces:**
- Consumes: `CollectorBackend`, `map_tiktok_item_struct_to_detail`, `map_tiktok_comment_to_input`, `map_ytdlp_json_to_detail`, `utf8_subprocess_env`, `download_audio_mp3_64k`, `load_dotenv_if_present`, `select_curated_fnb_creators`
- Produces:
  - `AntiBotChallengeError(RuntimeError)` (`pipelines/crawl_incremental/providers.py`)
  - `TikTokApiCollectorProvider(*, allow_live_network: bool = False, ms_token: str = "", cookies_file: Path | None = None, browser: str = "chromium", headless: bool = True, cutoff_utc: datetime | None = None, timeout_sec: int = 45, api_factory: Callable[[], Any] | None = None)` (`pipelines/crawl_incremental/providers.py`)
  - `LiveTikTokCollectorProvider(*, allow_live_network: bool = False, ms_token: str = "", cookies_file: Path | None = None, timeout_sec: int = 45)` (`pipelines/crawl_incremental/providers.py`)
  - `AutoHybridTikTokCollectorProvider(*, allow_live_network: bool = False, ms_token: str = "", cookies_file: Path | None = None, browser: str = "chromium", headless: bool = True, cutoff_utc: datetime | None = None, timeout_sec: int = 45, primary: CollectorProvider | None = None, secondary: CollectorProvider | None = None)` (`pipelines/crawl_incremental/providers.py`)
  - `YtDlpAudioConverter64k(*, allow_live_network: bool = False, ms_token: str = "", cookies_file: Path | None = None, timeout_sec: int = 45)` (`pipelines/crawl_incremental/providers.py`)
  - `build_live_collector_provider(*, backend: CollectorBackend = "auto", allow_live_network: bool = False, ms_token: str = "", cookies_file: Path | None = None, browser: str = "chromium", headless: bool = True, cutoff_utc: datetime | None = None, timeout_sec: int = 45) -> CollectorProvider` (`pipelines/crawl_incremental/providers.py`)

- [ ] **Step 1: Write failing unit tests in `tests/unit/test_bounded_collector_worker.py`**

Append tests verifying:
```python
def test_tiktokapi_provider_skips_pinned_old_items_breaks_chronologically_and_caches_as_dict() -> None:
    from pipelines.crawl_incremental.providers import TikTokApiCollectorProvider

    as_of = datetime(2026, 11, 23, 12, 0, 0, tzinfo=UTC)
    cutoff = as_of - timedelta(days=120)
    video_info_calls: list[str] = []
    yielded_ids_seen: list[str] = []

    class _FakeComment:
        def __init__(self, data: dict[str, Any]) -> None:
            self.as_dict = data

    class _FakeVideo:
        def __init__(self, data: dict[str, Any]) -> None:
            self.id = data["id"]
            self.as_dict = data

        async def info(self) -> dict[str, Any]:
            video_info_calls.append(self.id)
            return self.as_dict

        async def comments(self, count: int = 20):
            for idx in range(min(count, 2)):
                yield _FakeComment(
                    {
                        "cid": f"{self.id}_c{idx}",
                        "text": f"  Món này ngon quá {idx} ",
                        "digg_count": 10 + idx,
                        "reply_comment_total": idx,
                        "user": {"uid": f"u{idx}", "unique_id": f"viewer_{idx}"},
                    }
                )

    class _FakeUser:
        async def videos(self, count: int = 30):
            stream = [
                # #0: Pinned 2024 video -> MUST skip without breaking!
                {
                    "id": "pinned_2024_vid",
                    "createTime": int((cutoff - timedelta(days=300)).timestamp()),
                    "isPinnedItem": True,
                    "desc": "Video ghim từ 2024",
                    "author": {"id": "a1", "uniqueId": "spicykim9386", "nickname": "Kim"},
                    "statsV2": {"playCount": 900000, "commentCount": 50},
                    "video": {"duration": 30},
                },
                # #1: Fresh unpinned video -> MUST collect & cache!
                {
                    "id": "fresh_2026_vid_1",
                    "createTime": int((as_of - timedelta(days=5)).timestamp()),
                    "isPinnedItem": False,
                    "desc": "Phở mới mở Quận 1 #ancungtiktok",
                    "isECVideo": True,
                    "author": {"id": "a1", "uniqueId": "spicykim9386", "nickname": "Kim"},
                    "statsV2": {"playCount": 120000, "commentCount": 12, "collectCount": 300},
                    "poi": {"id": "p1", "name": "Phở Q1", "city": "Ho Chi Minh City"},
                    "video": {"duration": 42, "VQScore": 75.0},
                },
                # #2: Unpinned old video (< cutoff) -> MUST trigger chronological break!
                {
                    "id": "unpinned_old_break",
                    "createTime": int((cutoff - timedelta(days=10)).timestamp()),
                    "isPinnedItem": False,
                    "desc": "Video cũ hết hạn",
                    "author": {"id": "a1", "uniqueId": "spicykim9386"},
                    "video": {"duration": 25},
                },
                # #3: Should NEVER even be inspected because #2 broke the loop!
                {
                    "id": "unreachable_after_break",
                    "createTime": int((as_of - timedelta(days=1)).timestamp()),
                    "isPinnedItem": False,
                    "desc": "Unreachable",
                    "author": {"id": "a1", "uniqueId": "spicykim9386"},
                    "video": {"duration": 20},
                },
            ]
            for item in stream:
                yielded_ids_seen.append(item["id"])
                yield _FakeVideo(item)

    class _FakeApi:
        async def __aenter__(self) -> _FakeApi:
            return self

        async def __aexit__(self, exc_type: Any, exc: Any, tb: Any) -> None:
            return None

        async def create_sessions(self, **kwargs: Any) -> None:
            return None

        def user(self, username: str) -> _FakeUser:
            return _FakeUser()

        def video(self, id: str | None = None, url: str | None = None) -> _FakeVideo:
            return _FakeVideo({"id": id or "unknown", "createTime": int(as_of.timestamp())})

    prov = TikTokApiCollectorProvider(
        allow_live_network=True,
        ms_token="tok_valid",
        cutoff_utc=cutoff,
        api_factory=_FakeApi,
    )
    discovered = prov.discover_candidates(["@spicykim9386"], max_per_creator=10)
    assert [d["video_id"] for d in discovered] == ["fresh_2026_vid_1"]
    assert "unreachable_after_break" not in yielded_ids_seen

    detail = prov.fetch_video_detail(discovered[0])
    assert video_info_calls == []  # zero slow HTML scraping calls; served from cached video.as_dict
    assert detail["is_ec_video"] is True
    assert detail["poi_name"] == "Phở Q1"
    assert "_raw_provider_payload" in detail

    cmts = prov.fetch_comments("fresh_2026_vid_1", max_comments=5)
    assert len(cmts) == 2
    assert cmts[0]["text"].startswith("  Món này")


def test_auto_hybrid_fallback_raw_payload_archive_and_fail_closed_anti_bot_gate(tmp_path: Path) -> None:
    from pipelines.crawl_incremental.providers import (
        AntiBotChallengeError,
        AutoHybridTikTokCollectorProvider,
        OfflineFixtureAudioConverter,
        TransientCollectorError,
    )

    as_of = datetime(2026, 11, 23, 12, 0, 0, tzinfo=UTC)

    class _FlakyPrimary:
        source_mode: Any = "live_provider"
        is_synthetic_fixture = False
        backend_name = "tiktokapi"

        def discover_candidates(self, creators: list[str] | None, max_per_creator: int) -> list[dict[str, Any]]:
            raise TransientCollectorError("Playwright chromium executable doesn't exist")

        def fetch_video_detail(self, candidate: dict[str, Any]) -> dict[str, Any]:
            raise TransientCollectorError("Playwright unavailable")

        def fetch_comments(self, video_id: str, max_comments: int) -> list[dict[str, Any]]:
            return []

    class _WorkingSecondary:
        source_mode: Any = "live_provider"
        is_synthetic_fixture = False
        backend_name = "ytdlp"

        def discover_candidates(self, creators: list[str] | None, max_per_creator: int) -> list[dict[str, Any]]:
            return [{"video_id": "v_hyb_1", "author_handle": "putaangi", "create_time": (as_of - timedelta(days=3)).isoformat()}]

        def fetch_video_detail(self, candidate: dict[str, Any]) -> dict[str, Any]:
            return {
                "video_id": "v_hyb_1",
                "author_id": "aid_puta",
                "author_handle": "putaangi",
                "create_time": (as_of - timedelta(days=3)).isoformat(),
                "caption": "Review bún đậu",
                "duration_sec": 30,
                "comment_count": 3,
                "_raw_provider_payload": {"id": "v_hyb_1", "video": {"VQScore": 80.1}, "collectTime": 1763800000},
            }

        def fetch_comments(self, video_id: str, max_comments: int) -> list[dict[str, Any]]:
            return [{"comment_id": "c1", "author_handle": "u1", "text": "Ngon lắm", "like_count": 2, "reply_count": 0}]

    hybrid = AutoHybridTikTokCollectorProvider(
        allow_live_network=True,
        ms_token="secret_tok_999",
        primary=_FlakyPrimary(),
        secondary=_WorkingSecondary(),
    )
    collector = BoundedIncrementalCollector(
        provider=hybrid,
        audio_converter=OfflineFixtureAudioConverter(),
        bounds=CollectorBounds(max_retries=2),
        sleep_fn=lambda _: None,
    )
    out_dir = tmp_path / "hyb_batch"
    manifest = collector.run(
        output_dir=out_dir,
        as_of_utc=as_of,
        historical_video_ids={"hist_1"},
        creators=["putaangi"],
    )
    assert manifest.succeeded_count == 1
    assert manifest.collector_backends_used == ["ytdlp"]
    raw_archive = out_dir / "raw_provider_payloads.jsonl"
    assert raw_archive.is_file()
    archived_obj = json.loads(raw_archive.read_text(encoding="utf-8").splitlines()[0])
    assert archived_obj["video_id"] == "v_hyb_1"
    assert archived_obj["raw_payload"]["video"]["VQScore"] == 80.1

    # Fail-closed CAPTCHA check: MUST NOT fallback to secondary and MUST halt at attempts=1 with redacted secrets!
    class _CaptchaPrimary(_FlakyPrimary):
        def fetch_video_detail(self, candidate: dict[str, Any]) -> dict[str, Any]:
            raise AntiBotChallengeError(
                "TikTok CaptchaException with Cookie: msToken=secret_tok_999 --cookies /priv/cookies.txt"
            )

    class _SpySecondary(_WorkingSecondary):
        detail_calls = 0

        def fetch_video_detail(self, candidate: dict[str, Any]) -> dict[str, Any]:
            self.detail_calls += 1
            return super().fetch_video_detail(candidate)

    spy_sec = _SpySecondary()
    captcha_hybrid = AutoHybridTikTokCollectorProvider(
        allow_live_network=True,
        ms_token="secret_tok_999",
        primary=_CaptchaPrimary(),
        secondary=spy_sec,
    )
    captcha_collector = BoundedIncrementalCollector(
        provider=captcha_hybrid,
        audio_converter=OfflineFixtureAudioConverter(),
        bounds=CollectorBounds(max_retries=2),
        sleep_fn=lambda _: None,
    )
    cap_manifest = captcha_collector.run(
        output_dir=tmp_path / "captcha_batch",
        as_of_utc=as_of,
        historical_video_ids={"hist_1"},
        creators=["putaangi"],
    )
    assert spy_sec.detail_calls == 0  # zero fallback bypass on CAPTCHA
    assert cap_manifest.failed_count == 1
    assert cap_manifest.stopped_reason == "anti_bot_challenge_blocked"
    assert cap_manifest.items[0].attempts == 1
    assert "secret_tok_999" not in cap_manifest.items[0].reason
    assert "/priv/cookies.txt" not in cap_manifest.items[0].reason
```

- [ ] **Step 2: Run test to verify it fails**

Run: `python3 -m pytest tests/unit/test_bounded_collector_worker.py -k "tiktokapi_provider_skips_pinned or auto_hybrid_fallback" -v`
Expected: FAIL with `ImportError: cannot import name 'TikTokApiCollectorProvider'`

- [ ] **Step 3: Implement `providers.py`, `worker.py`, and `crawl_incremental/__main__.py` upgrades**

1. In `pipelines/crawl_incremental/providers.py`:
   - Add `AntiBotChallengeError(RuntimeError)` and helper `_is_anti_bot_challenge(text_or_exc)` detecting `CaptchaException`, `EmptyResponseException` bot-detection messages (`"detecting you're a bot"`, `"captcha"`, `"verify you are human"`), and `yt-dlp` CAPTCHA challenges without subclassing `TransientCollectorError`.
   - Implement `TikTokApiCollectorProvider` (lazy-importing `TikTokApi`, running async `create_sessions(num_sessions=1, ms_tokens=[ms_token], headless=headless, browser=browser, sleep_after=2, timeout=timeout_sec * 1000)`, enforcing `isPinnedItem` skip + unpinned `cutoff_utc` `break`, caching `video.as_dict` in `_cached_details`, and fetching top-level `video.comments(count=max_comments)`).
   - Upgrade `LiveTikTokCollectorProvider` (`ytdlp`) and `YtDlpAudioConverter64k` to accept `cookies_file: Path | None = None`, run `subprocess.run` with `encoding="utf-8", errors="replace", env=utf8_subprocess_env()`, detect `_is_anti_bot_challenge(res.stderr)`, and use `map_ytdlp_json_to_detail`.
   - Implement `AutoHybridTikTokCollectorProvider` and `build_live_collector_provider`.
2. In `pipelines/crawl_incremental/worker.py`:
   - Extend `_sanitize_reason` to redact `--cookies <path>` (`--cookies [REDACTED]`).
   - Catch `AntiBotChallengeError` in `discover_candidates` and in the per-item loop (`attempts=1`, `stopped_reason="anti_bot_challenge_blocked"`, marking any remaining queued candidates as `skipped` with `reason="anti_bot_challenge_blocked"`), and catch `TransientCollectorError` in `discover_candidates` (`stopped_reason="discovery_failed"`).
   - Strip `_raw_provider_payload` before `RawIncrementalVideoRecord.model_validate` and persist sanitized raw payloads in `output_dir / "raw_provider_payloads.jsonl"` (`video_id`, `collected_at_utc`, `backend`, `raw_payload`).
   - Populate `collector_backend_requested` and `collector_backends_used` on `CrawlManifest`.
3. Update `pipelines/crawl_incremental/__main__.py` to call `load_dotenv_if_present()`, accept `--backend`, `--cookies-file`, `--tiktok-browser`, `--tiktok-headless` / `--no-tiktok-headless`, and `--auto-creators`, and construct the provider via `build_live_collector_provider`.

- [ ] **Step 4: Run tests & `mypy` to verify Task 2 passes**

Run:
- `python3 -m pytest tests/unit/test_bounded_collector_worker.py -v`
- `python3 -m mypy pipelines/crawl_incremental`
Expected: All `16` collector worker tests PASS and `mypy` reports `0` issues.

- [ ] **Step 5: Commit Task 2**

```bash
python3 scripts/check_secrets.py
git add pipelines/crawl_incremental/providers.py pipelines/crawl_incremental/worker.py pipelines/crawl_incremental/__main__.py tests/unit/test_bounded_collector_worker.py
git commit -m "feat(m3.3): add hybrid TikTokApi/yt-dlp auto provider, pinned-item loop, and fail-closed anti-bot gate"
```

---

### Task 3: Turnkey Home Execution in `M3.3` (`--backend`, `--auto-creators`, `--resume`, `--preflight-only`), `.env.example` & Run-at-Home Guide

**Files:**
- Modify: `pipelines/pilot_m3_3/models.py`
- Modify: `pipelines/pilot_m3_3/runner.py`
- Modify: `pipelines/pilot_m3_3/__main__.py`
- Modify: `.env.example`
- Modify: `docs/reports/milestones/M3.3/README.md`
- Modify: `docs/reports/milestones/M3.3/evidence/workflow.md`
- Modify: `docs/reports/milestones/README.md`
- Modify: `tests/unit/test_m3_3_pilot_pipeline.py`

**Interfaces:**
- Consumes: `CollectorBackend`, `build_live_collector_provider`, `YtDlpAudioConverter64k`, `load_dotenv_if_present`, `select_curated_fnb_creators`
- Produces:
  - Extended `M33PilotConfig` (`backend: CollectorBackend = "auto"`, `cookies_file: Path | None = None`, `tiktok_browser: str = "chromium"`, `tiktok_headless: bool = True`, `auto_creators: int = Field(default=0, ge=0, le=5)`, `resume: bool = False`), extended `CollectionSummaryReceipt` (`collector_backend_requested`, `collector_backends_used`), and `M33PreflightReport` (`pipelines/pilot_m3_3/models.py`)
  - `run_m3_3_preflight(config: M33PilotConfig) -> M33PreflightReport` (`pipelines/pilot_m3_3/runner.py`)
  - CLI flags `--backend`, `--cookies-file`, `--tiktok-browser`, `--tiktok-headless` / `--no-tiktok-headless`, `--auto-creators`, `--resume`, and `--preflight-only` (`pipelines/pilot_m3_3/__main__.py`)

- [ ] **Step 1: Write failing unit tests in `tests/unit/test_m3_3_pilot_pipeline.py`**

Append tests verifying:
```python
def test_m3_3_preflight_auto_creators_dotenv_and_resume_forwarding(
    tmp_path: Path, monkeypatch: pytest.MonkeyPatch
) -> None:
    from pipelines.pilot_m3_3.models import M33PilotConfig
    from pipelines.pilot_m3_3.runner import run_m3_3_pilot, run_m3_3_preflight

    base_dir = tmp_path / "gold_base"
    _write_minimal_gold_base(base_dir, n_rows=4)
    filt_file = tmp_path / "author_unique_ids.txt"
    filt_file.write_text("hist_creator\n", encoding="utf-8")

    dotenv_path = tmp_path / ".env"
    dotenv_path.write_text("ms_token=home_cookie_token_abc\n", encoding="utf-8")
    monkeypatch.delenv("MS_TOKEN", raising=False)
    monkeypatch.delenv("ms_token", raising=False)
    monkeypatch.setattr("shutil.which", lambda name, path=None: f"/usr/bin/{name}")

    cfg = M33PilotConfig(
        mode="live_pilot",
        allow_live_network=True,
        backend="auto",
        base_corpus_dir=base_dir,
        batch_dir=tmp_path / "batch",
        output_gold_dir=tmp_path / "gold_out",
        output_bm25_dir=tmp_path / "bm25_out",
        receipt_path=tmp_path / "receipt.json",
        inspection_sheet_path=tmp_path / "inspect.jsonl",
        auto_creators=3,
        resume=True,
    )
    preflight = run_m3_3_preflight(
        cfg,
        dotenv_path=dotenv_path,
        creator_filter_file=filt_file,
        has_injected_asr=True,
    )
    assert preflight.ready_for_live_pilot is True
    assert preflight.ms_token_present is True
    assert preflight.selected_creators == ["hist_creator"]
    assert preflight.historical_protected_count == 4
    assert preflight.resolved_backend in {"tiktokapi_with_ytdlp_fallback", "ytdlp_only"}

    # Verify dry_run_fixture forwards resume=True so pre-existing checkpoint records are retained
    as_of = datetime(2026, 11, 23, 12, 0, 0, tzinfo=UTC)
    fx1 = tmp_path / "fx1.jsonl"
    fx2 = tmp_path / "fx2.jsonl"
    rec1 = {
        "video_id": "fresh_r1",
        "author_id": "a1",
        "author_handle": "c1",
        "create_time": (as_of - timedelta(days=4)).isoformat(),
        "caption": "Phở bò tái lăn Hà Nội",
        "duration_sec": 30,
        "audio_fixture_payload": "FAKE-MP3-1",
        "comments": [],
    }
    rec2 = {
        "video_id": "fresh_r2",
        "author_id": "a2",
        "author_handle": "c2",
        "create_time": (as_of - timedelta(days=2)).isoformat(),
        "caption": "Bún chả nướng than hoa",
        "duration_sec": 30,
        "audio_fixture_payload": "FAKE-MP3-2",
        "comments": [],
    }
    fx1.write_text(json.dumps(rec1, ensure_ascii=False) + "\n", encoding="utf-8")
    fx2.write_text(
        "\n".join(json.dumps(r, ensure_ascii=False) for r in (rec1, rec2)) + "\n",
        encoding="utf-8",
    )

    stub_asr = _StubCpuAsrEngine()
    run1_cfg = M33PilotConfig(
        mode="dry_run_fixture",
        base_corpus_dir=base_dir,
        batch_dir=tmp_path / "resume_batch",
        output_gold_dir=tmp_path / "gold_r1",
        output_bm25_dir=tmp_path / "bm25_r1",
        receipt_path=tmp_path / "rec_r1.json",
        inspection_sheet_path=tmp_path / "ins_r1.jsonl",
        fixture_path=fx1,
        as_of_utc=as_of,
        resume=False,
    )
    r1 = run_m3_3_pilot(run1_cfg, asr_engine=stub_asr)
    assert r1.collection.succeeded_count == 1

    run2_cfg = run1_cfg.model_copy(
        update={
            "fixture_path": fx2,
            "output_gold_dir": tmp_path / "gold_r2",
            "output_bm25_dir": tmp_path / "bm25_r2",
            "receipt_path": tmp_path / "rec_r2.json",
            "inspection_sheet_path": tmp_path / "ins_r2.jsonl",
            "resume": True,
        }
    )
    r2 = run_m3_3_pilot(run2_cfg, asr_engine=stub_asr)
    assert r2.collection.skipped_count == 1  # fresh_r1 skipped from checkpoint!
    assert r2.collection.succeeded_count == 1  # only fresh_r2 newly fetched!
    assert (r2.inspection_k_count + r2.inspection_n_count) == 2  # both retained in merged batch!
```

- [ ] **Step 2: Run test to verify it fails**

Run: `python3 -m pytest tests/unit/test_m3_3_pilot_pipeline.py::test_m3_3_preflight_auto_creators_dotenv_and_resume_forwarding -v`
Expected: FAIL with `ImportError: cannot import name 'run_m3_3_preflight'`

- [ ] **Step 3: Implement `pilot_m3_3` upgrades, `.env.example`, and Run-at-Home documentation**

1. Extend `pipelines/pilot_m3_3/models.py` (`M33PilotConfig`, `CollectionSummaryReceipt`, `M33PreflightReport`).
2. Update `pipelines/pilot_m3_3/runner.py` & `__main__.py`:
   - Auto-load `.env` via `load_dotenv_if_present()` before preflight/execution, resolve creators by merging `config.creators` with `select_curated_fnb_creators(..., top_k=config.auto_creators)` up to `config.max_creators`, implement `run_m3_3_preflight`, build live providers via `build_live_collector_provider` + authenticated `YtDlpAudioConverter64k(..., ms_token=ms_token, cookies_file=cookies_file)`, and forward `resume=config.resume` into `collector.run(...)`.
   - Support `--preflight-only` in `__main__.py` (printing `M33PreflightReport` JSON and exiting `0` without mutating Gold/BM25 paths).
3. Update `.env.example` (`MS_TOKEN=`, optional `TIKTOK_COOKIES_FILE=`, `TIKTOK_BROWSER=chromium`, `TIKTOK_HEADLESS=true`) and update `docs/reports/milestones/M3.3/README.md`, `docs/reports/milestones/M3.3/evidence/workflow.md`, and `docs/reports/milestones/README.md` with clear, copy-pasteable home setup & execution commands (both quick `yt-dlp`-only mode and enriched `TikTokApi` + Playwright `--backend auto` mode, plus `--resume` recovery).

- [ ] **Step 4: Run full verification suite (`pytest`, Linux & Windows `mypy`, secret scan, layout & link check)**

Run:
- `python3 -m pytest -v`
- `python3 -m mypy packages apps pipelines`
- `python3 -m mypy --platform win32 packages apps pipelines`
- `python3 scripts/check_secrets.py`
Expected: Full test suite passes (`198+ passed`), `mypy` clean on both Linux and `--platform win32` (`101` source files), `0` secret leaks, `0` broken relative links, `0` machine-specific absolute user-home paths in Markdown reports.

- [ ] **Step 5: Commit Task 3**

```bash
python3 scripts/check_secrets.py
git add pipelines/pilot_m3_3/ .env.example docs/reports/milestones/M3.3/ docs/reports/milestones/README.md tests/unit/test_m3_3_pilot_pipeline.py
git commit -m "feat(m3.3): wire hybrid auto backend, auto-creators, resume, preflight, and home run guide"
```

---

### Task 4: Phase 3 Targeted Batch Comment Enrichment (`--enrich-comments-only`) & Dual-Sink `fact_comments.parquet` Publication

**Files:**
- Modify: `pipelines/crawl_incremental/worker.py`
- Modify: `pipelines/crawl_incremental/__main__.py`
- Modify: `pipelines/pilot_m3_3/models.py`
- Modify: `pipelines/pilot_m3_3/runner.py`
- Modify: `pipelines/pilot_m3_3/__main__.py`
- Modify: `tests/unit/test_m3_3_pilot_pipeline.py`

**Interfaces:**
- Consumes: Existing `batch_dir / "videos_4m.jsonl"`, `CollectorProvider.fetch_comments`, `ingest_incremental_batch_to_gold(..., update_existing=True)`
- Produces:
  - `BoundedIncrementalCollector.enrich_existing_comments(self, output_dir: Path, *, historical_video_ids: set[str] | None = None, base_corpus_snapshot_id: str = "20261118_taxonomy_fix_v1") -> CrawlManifest` (`pipelines/crawl_incremental/worker.py`)
  - `M33PilotConfig.enrich_comments_only: bool = False` (`pipelines/pilot_m3_3/models.py`)
  - `run_m3_3_comment_enrichment(config: M33PilotConfig, *, provider: CollectorProvider | None = None, dotenv_path: Path | None = None) -> M33PilotReceipt` (`pipelines/pilot_m3_3/runner.py`)
  - CLI flag `--enrich-comments-only` on `pipelines.pilot_m3_3` and `pipelines.crawl_incremental`

- [x] **Step 1: Write failing unit tests in `tests/unit/test_m3_3_pilot_pipeline.py`**
  - Verify `run_m3_3_comment_enrichment` (and `run_m3_3_pilot` with `enrich_comments_only=True`) enriches comments onto an existing `videos_4m.jsonl` batch without re-running discovery, audio extraction, or CPU ASR, preserves existing `transcript`, `whisper_segments`, `audio_path`, and `sample_inspection_sheet.jsonl` `human_verified=True` annotations, respects `max_comments_per_video` / `max_comments_total` and fail-closed `AntiBotChallengeError`, and publishes a new Gold snapshot with populated `fact_comments.parquet`.
- [x] **Step 2: Implement `enrich_existing_comments` and `run_m3_3_comment_enrichment`**
- [x] **Step 3: Run unit tests, `mypy`, `ruff`, and execute live comment enrichment on Windows desktop**

---

### Task 4B: Reconcile Local Browser Cookies and Measure One Bounded Live Rerun (2026-11-25)

**Files:**
- Update: `docs/reports/milestones/M3.3/superpowers/spec.md`
- Update: `docs/reports/milestones/M3.3/superpowers/plan.md`
- Update: `docs/reports/milestones/M3.3/evidence/workflow.md`
- Update: `docs/reports/milestones/M3.3/README.md`
- Create: distinct sanitized receipt under `docs/reports/milestones/M3.3/evidence/`
- Local only: gitignored `.env` and an external Netscape cookies file; preserve the source JSON.

**Interfaces:** Consumes the owner supplied local JSON cookie export and `pipelines.pilot_m3_3` CLI. Produces an aligned local `MS_TOKEN`/`TIKTOK_COOKIES_FILE` pair and a measured, honest live pilot receipt.

- [x] **Step 1:** Validate the JSON shape, unexpired `www.tiktok.com` `msToken`, and current configuration using counts and booleans only. Record the existing blocked receipt separately before running.
- [x] **Step 2:** Convert the JSON export to a Netscape file without printing cookie values; keep one matching `msToken` and validate the file with `MozillaCookieJar`.
- [x] **Step 3:** Update only the two `.env` auth keys, check effective loader output by equality/paths without echoing secrets, and run `--preflight-only` with new output paths.
- [x] **Step 4:** If preflight is ready, execute one bounded `--mode live_pilot --allow-live-network --backend auto --no-tiktok-headless --auto-creators 5` run using distinct output paths; honor fail-closed anti-bot handling.
- [x] **Step 5:** Check the resulting receipt/manifest, run `python scripts/check_secrets.py`, update this task's evidence/report with the observed result, and verify report links/layout/status consistency. Do not overwrite the prior successful M3.3 measurement.

### Task 5: Pass the Netscape Session Cookies to TikTokApi (2026-11-25)

**Files:**
- Modify: `pipelines/crawl_incremental/providers.py` (`TikTokApiCollectorProvider` and a focused cookie loader)
- Test: `tests/unit/test_bounded_collector_worker.py`
- Update: `docs/reports/milestones/M3.3/README.md`, `docs/reports/milestones/M3.3/evidence/workflow.md`, and `docs/reports/milestones/README.md`
- Create: distinct receipt/manifest evidence for one new live attempt if preflight permits it

**Interfaces:** Consume existing `cookies_file: Path | None` and `MS_TOKEN`; produce the TikTokApi `cookies=[dict[str, str]]` session argument only when a valid file is configured. No public CLI changes.

- [x] **Step 1:** Add offline failing tests with a fake TikTokApi session verifying a valid Netscape jar passes scoped session cookies, excludes host-only `tiktok.com`, chooses the specific `www.tiktok.com` duplicate, and overrides jar `msToken` with `MS_TOKEN`; verify the no-file path still omits `cookies` and malformed input does not expose secret content.
- [x] **Step 2:** Run the targeted tests and confirm RED for the missing cookie propagation behavior, not a test setup error.
- [x] **Step 3:** Implement a minimal cookie loader and pass its mapping to `create_sessions`; keep anti-bot exceptions fail-closed.
- [x] **Step 4:** Run targeted tests, then full `pytest`, type check, secret scan, and diff hygiene. Record actual outputs.
- [x] **Step 5:** If all local gates pass, run one preflight and one owner-authorized bounded live pilot with distinct work/Gold/BM25/receipt paths. Stop on anti-bot and preserve every prior attempt.
- [x] **Step 6:** Record the live result, evidence hashes, report/index status, and remaining source-access limitation. Review the diff and report truthfully whether fresh data was obtained.

### Task 6: Import Authorized Comment Files into a New Gold Snapshot (2026-11-25)

**Files:**
- Create: `pipelines/import_authorized_comments/{__init__.py,importer.py,__main__.py}`
- Test: `tests/unit/test_snapshot_continuity.py` (reuse its verified synthetic Gold fixture)
- Update: `docs/reports/milestones/M3.3/README.md`, `docs/reports/milestones/M3.3/evidence/workflow.md`, `docs/reports/milestones/README.md`
- Create: `docs/reports/milestones/M3.3/evidence/authorized_comments_template.csv`

**Interfaces:** `import_authorized_comments(comments_file: Path, base_corpus_dir: Path, work_dir: Path, output_corpus_dir: Path, *, source_label: str, as_of_utc: datetime, preflight_only: bool = False) -> AuthorizedCommentReceipt` validates a normalized CSV/JSONL file, returns a no-write `READY` receipt in preflight mode, or writes a bounded incremental batch and calls the verified dual-sink converter with `update_existing=True` into a new snapshot. The CLI supports `--preflight-only`, `--source-label`, `--as-of`, `--base-corpus`, `--comments-file`, `--work-dir`, and `--output-gold`.

- [x] **Step 1:** Write an end-to-end synthetic fixture test that imports two comments for an existing fresh video, verifies `fact_comments`/ABSA rows, original video/voice preservation, immutable base hashes, and provenance receipt. Watch RED before implementation.
- [x] **Step 2:** Write focused failing validation tests for unknown/old video IDs, duplicate IDs, blank text, invalid counts, and bound violations; verify preflight writes no batch or snapshot.
- [x] **Step 3:** Implement minimal CSV/JSONL parsing, source hashing, Gold membership/window checks, bounded comment grouping, atomic batch/receipt writes, and the `update_existing=True` call. Add a header-only CSV template.
- [x] **Step 4:** Run targeted tests, then full pytest, Linux/Windows mypy, Ruff, and secret scan. Check that no fixture is reported as live data.
- [x] **Step 5:** Inspect the workspace for a real authorized file. If none exists, run preflight on a controlled fixture only, document `REAL_INPUT_MISSING`, and do not create a production Gold snapshot. Update report/index/workflow and verify links/layout/hashes.

### Task 7: Capture Visible Comments from Known Video URLs with Playwright (2026-11-25)

**Files:** `pipelines/capture_playwright_comments/{__init__.py,__main__.py,capture.py}`, focused tests under `tests/unit/`, and this M3.3 task bundle/report/index. No change to creator discovery or historical corpus.

**Interfaces:** A bounded page capture accepts a verified Gold video URL, scoped Netscape cookies, and a new JSONL output path. It emits rows accepted by `pipelines.import_authorized_comments`; only a validated nonempty live output can feed the immutable Gold importer. Challenge/login/empty pages produce no output file.

- [x] **Step 1:** Probe one known accepted video URL in direct Playwright using the configured scoped cookies. Record elapsed time, final host, challenge/login state, and comment-card selector counts without printing cookies or comment text. The comments action exposed a slider CAPTCHA, so continue only through the owner's explicitly offered manual completion in one bounded visible-browser wait.
- [x] **Step 2:** From observed DOM structure, write offline tests first for valid URL/Gold membership, rendered-card text extraction, bounded count, missing native IDs, and challenge/empty no-write behavior; observe RED.
- [x] **Step 3:** Implement the minimal one-page Playwright capture CLI and normalized JSONL output. Preserve source text and provenance, close the browser, and fail closed on challenge or missing cards.
- [x] **Step 4:** Run targeted tests, full pytest, Linux/Windows mypy, Ruff, and secret scan. Review the implementation and correct concrete findings with TDD (`19/19` capture tests, `253` full `pytest`, `111`-file Windows/Linux `mypy`, `ruff`, and `check_secrets.py` all green after two independent review + TDD fix passes).
- [x] **Step 5:** Run one distinct bounded live capture, then preflight/import only if real comments were captured. Record receipt/Gold row counts, timing, blockers, hashes, report/index consistency, and actual remaining work. *(Verified both fail-closed no-write behavior when an unsolved background window expired at `300 s`, and live foreground execution of `pipelines.capture_playwright_comments` on `https://www.tiktok.com/@saigonmap/video/7710502428428356871`: `20` real comments captured in `17.656 s` after manual owner slider solve -> `READY` preflight -> `IMPORTED` into SHA256-verified `m3_3_playwright_comments_20261125_v2` with `39` total real comments across `2` videos and `39/39` nonblank `original_text`.)*

### Task 8: Single-Session Remaining-Pilot Batch Capture with Cooldown, Scroll & Checkpointing (2026-11-25)

**Files:** `pipelines/capture_playwright_comments/{capture.py,__main__.py}`, `tests/unit/test_playwright_comment_capture.py`, and M3.3 report/workflow records.

**Interfaces:** Adds `select_remaining_pilot_urls(corpus_dir, *, as_of_utc)`, optional `scroll_rounds` / `allow_zero_comments` on `capture_comments_on_page`, `run_batch_comment_capture(...)` with `.state.json` checkpointing + `cooldown_seconds`/`jitter_seconds` (`10–14`s default) + `1,000`-row ceiling, and CLI flags `--remaining-pilot`, `--cooldown-seconds`, `--jitter-seconds`, `--scroll-rounds`, and `--resume`.

- [x] **Step 1:** Write failing offline tests for remaining-pilot Gold selection, bounded comment-panel scrolling + zero-comment continuation, single-session batch cooldown/checkpointing/fail-closed CAPTCHA halt + `--resume`, and CLI flag validation; observe RED (`4/4` failed).
- [x] **Step 2:** Implement minimal batch selection, bounded scroll, zero-comment handling, checkpointed `run_batch_comment_capture`, and CLI flags without breaking single-URL mode.
- [x] **Step 3:** Run targeted tests (`23/23` passed), `ruff`, Windows/Linux `mypy` (`111` files clean), and `scripts/check_secrets.py` (`0` leaks).
- [x] **Step 4:** Execute live `--remaining-pilot` capture against `m3_3_playwright_comments_20261125_v2` with owner supervision, import captured rows into `m3_3_playwright_comments_20261125_v3`, and update M3.3 evidence/report (`28/28` visited in `666.938 s`, `manual_challenge_count=1`, `355` new comments -> `394` total real comments across `28` commented pilot videos in verified `v3`).

### Task 9: Bounded 100-Video Fresh Metadata + Comment Expansion (`<= 5,000` Comments) (2026-11-25)

**Files:** `pipelines/capture_playwright_comments/{capture.py,__main__.py}`, `pipelines/import_authorized_comments/{importer.py,__main__.py}`, `tests/unit/test_playwright_comment_capture.py`, and M3.3 report/workflow records.

**Interfaces:** Adds `max_total_comments` (`1..5000`, CLI `--max-total-comments`) on `capture_playwright_comments` and `max_rows: int = 1000` (`1..5000`, CLI `--max-rows`) on `import_authorized_comments`, preserving `1,000` defaults.

- [x] **Step 1:** Write a failing test verifying default `1,000`-row rejection, explicit `max_rows=5000` / `--max-total-comments 5000` acceptance over `1,005` rows, and rejection above `5,000`; observe RED.
- [x] **Step 2:** Implement `--max-total-comments` (`<= 5000`) and `max_rows` / `--max-rows` (`<= 5000`), and verify `pytest`, `ruff`, `mypy` (`111` files), and `check_secrets.py` (`0` leaks).
- [x] **Step 3:** Run bounded `pipelines.crawl_incremental` (`--backend ytdlp --max-succeeded 100 --max-audio-minutes 0`) over curated F&B creators protecting all `71,026` IDs in `v3`, and ingest the `100` fresh metadata records into `m3_3_playwright_comments_20261125_v4_meta` (`persisted=100`, `failed=0`, `V4_TOTAL_VIDEOS=71,126`).
- [x] **Step 4:** Run `--remaining-pilot` (`--max-total-comments 5000`, `8–12 s` cooldown) across the `100` new fresh videos, import into `m3_3_playwright_comments_20261125_v5`, and record verified hashes/counts (`100` new videos visited in `2,383.062 s`, `90` commented videos -> `2,429` new comments -> **`2,823` total real comments across `118` commented videos** in verified `v5`).
