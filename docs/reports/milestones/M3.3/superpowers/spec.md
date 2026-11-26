# M3.3 — Specification: Capped Capture-to-Transcript-to-Search Pilot & Hybrid Legacy-Grounded Collector Upgrade

- **Task ID:** `M3.3`
- **Primary Owners:** Nguyễn Việt Nguyên (`N`) & Trần Đình Khương (`K`) (shared integration & 50/50 sample inspection)
- **Prerequisite Gates / Tasks:** `G2 = PASS` (`M2.G`), `M3.1 = COMPLETE`, `M3.2 = COMPLETE`
- **Requirement Source:** [TikTok_AI_Engine_Milestone.md](../../../../planning/TikTok_AI_Engine_Milestone.md) (`M3.3`, lines 56, 99)
- **Upstream Crawler Grounding (`TrggTin/21KHDL-TikTok-Analytics` @ `f142e5656a220f94f8024de168b0832754b3bd9e`):**
  - Full line-by-line inspection completed across `src/crawler/crawler.py` (`156` lines), `src/crawler/run_crawler.py` (`87` lines), `src/crawler/crawler_readme.md`, `src/crawler/TikTokApi/tiktok.py`, `src/crawler/TikTokApi/api/{user.py, video.py, comment.py}`, `src/crawler/TikTokApi/exceptions.py`, `docs/TikTok_data_fields.md`, `reports/chapter03-data_collection/data_collection.tex`, `notebooks/02_DEP_03-Filter_users.ipynb`, and preserved `data/filters/author_unique_ids.txt`.
- **Revision History:**
  - `2026-11-20` (Phase 1): Bounded `M3.3` capture -> CPU ASR -> Dual-Sink Gold -> BM25 -> searchability orchestrator & host `.venv` `faster-whisper` verification.
  - `2026-11-23` (Phase 2, authored by `K`): Deep-grounded hybrid `TikTokApi` + `yt-dlp` collector upgrade adapting the exact `21KHDL-TikTok-Analytics` crawler mechanics (`isPinnedItem` chronological loop, zero-extra-HTTP `video.as_dict` caching, `TIKTOK_BROWSER`/headless session controls, UTF-8 Windows/Linux subprocess safety, Chapter 3 + `author_unique_ids.txt` F&B creator selection, `collectTime` + raw payload archiving, and authenticated `64 kbps` `.mp3` extraction).
  - `2026-11-24` (Phase 3, authored by `N` & `K`): Targeted Batch Comment Enrichment (`enrich_batch_comments` / `--enrich-comments-only`) keyed strictly on the `30` existing `M3.3` pilot `video_id`s in `videos_4m.jsonl` (`max_comments_per_video <= 50`, `max_comments_total <= 1000`), preserving 100% of existing `.mp3` audio, Whisper transcripts, and `30/30` human verification flags while publishing an updated Dual-Sink Gold snapshot (`update_existing=True`) with populated `fact_comments.parquet` and `fact_absa_reviews.parquet` for `M3.G`, `M5.1`, and `M5.2`.

---

## 1. Scope & Hard Ceilings (Preserved Baseline)

Prepare and execute (when live network tools and `MS_TOKEN` are available) the bounded end-to-end fresh-data pilot under a strict `USD 0` local CPU budget:

1. **Collection Bounds (`M3.2` worker):** Maximum `5` creators, `50` candidate fresh videos (`<= 120` days, excluding all `70,996` historical IDs), `30` successful videos, `60.0` audio minutes, `1,000` comments (`<= 50` comments per video), and `1` bounded session (`<= 7,200` seconds / `2` hours).
2. **Measured CPU ASR Pilot Cap:** Transcribe **at most `10` videos** and **at most `20.0` audio minutes** before searchability verification. Enforce `0.0 <= start_sec < end_sec` on `RawWhisperSegment` outputs and leave un-transcribed or audio-missing records untouched (`transcript=""`, `whisper_segments=[]`).
3. **Dual-Sink Gold Ingest (`M3.1`) & Searchability Probe:** Ingest the pilot batch atop `data/corpus/20261118_taxonomy_fix_v1` into a new versioned output snapshot (never mutating historical bytes), build a versioned BM25 index (`BM25Index.build`), and verify that freshly transcribed videos are retrievable via `HybridRetrievalService` with exact source `video_id` matching (`>= 5` real non-synthetic transcribed fresh videos required for pilot `PASS`).
4. **Honest Mode Separation & Fail-Closed Status:**
   - `--mode dry_run_fixture`: verifies wiring, caps, metrics, disk/RAM/RTF measurement, and 50/50 `K`/`N` inspection sheet generation using synthetic fixtures (`is_synthetic_fixture=True`, `pilot_status="FIXTURE_DRY_RUN_ONLY"`). Never counts as live `M3.3` acceptance.
   - `--mode live_pilot`: requires `--allow-live-network`, `MS_TOKEN` (or legacy `ms_token`), `yt-dlp`, `ffmpeg`, and `faster-whisper`. If host tools, credentials, anti-bot challenges, or TikTok network yield fail (`< 5` real fresh searchable transcribed videos), emit `pilot_status="BLOCKED"` honestly without fake replacement data.
5. **Equal Sample Inspection (`50% K / 50% N`):** Export `sample_inspection_sheet.jsonl` assigning half of succeeded videos to `K` and half to `N` with `human_verified=false` placeholders.

---

## 2. Phase 2 Architectural Upgrade (`2026-11-23`) — Grounded in `21KHDL-TikTok-Analytics` Source Inspection

### 2.1 Direct Mechanics Adapted from `21KHDL-TikTok-Analytics` (and Legacy Defects Avoided)

| Upstream File & Lines | Upstream Mechanism Found | How `TikTok_AI_Engine_` Adapts / Improves It |
| --- | --- | --- |
| `src/crawler/crawler.py:97-118` | Iterates `async for video in user.videos(...)`, checks `is_within_range(video_data["createTime"], ...)`, skips old pinned posts via `elif video_data.get("isPinnedItem"): continue`, and stops paging old history via `else: break`. | Preserve exact **`isPinnedItem` skip + unpinned reverse-chronological early `break`** against `cutoff_utc` (`120` days) so pinned 2023/2024 profile videos never prematurely abort discovery of 2026 posts and old history is never over-paged. |
| `src/crawler/crawler.py:98` & `TikTokApi/api/video.py:76-80` | `user.videos()` (`/api/post/item_list/`, `min(35, count-found)` per page) already populates full `video.as_dict` (`itemStruct`), whereas `video.info()` warns *"Note: This is slow since it requires an HTTP request, avoid using this if possible"*. | Cache `video.as_dict` inside `TikTokApiCollectorProvider` during `discover_candidates` so `fetch_video_detail` performs **zero redundant per-video HTML scraping requests**, calling `video.info()` only if a candidate was not cached. |
| `src/crawler/crawler.py:10,84` & `TikTokApi/tiktok.py:220-279,490` | Reads `ms_token` env var and calls `create_sessions(headless=False, ms_tokens=[ms_token], num_sessions=1, sleep_after=3, browser=os.getenv("TIKTOK_BROWSER", "chromium"))`. | Support both `MS_TOKEN` and legacy `ms_token` env keys, `TIKTOK_BROWSER` (`chromium` \| `webkit` \| `firefox`), and configurable `tiktok_headless: bool` (`--tiktok-headless` / `--no-tiktok-headless`, default `True` for CLI servers and toggleable to `False` on home desktop PCs). Do **not** vendor frozen `stealth/js` scripts or auto-bypass CAPTCHAs. |
| `TikTokApi/api/video.py:239-284` & `comment.py:43-63` | `video.comments(count=...)` paginates `/api/comment/list/` yielding `as_dict` (`cid`, `text`, `digg_count`, `reply_comment_total`, `user.{uid, unique_id, sec_uid}`), whereas `Comment.replies()` (`comment.py:61`) had an upstream bug passing `item_id=self.author.user_id`. | Consume top-level `video.comments(count=max_comments)` `as_dict` directly, mapping `reply_comment_total -> reply_count` without calling the broken `Comment.replies()` endpoint, and preserving unstripped `text` for exact `M5.2` `NFC` span offsets. |
| `src/crawler/run_crawler.py:16-31` & `crawler.py:54-65` | Enforces `PYTHONIOENCODING="utf-8"` and `PYTHONUTF8="1"` on `win32` subprocesses; `extract_video_contents` downloaded full `.mp4` files via `yt_dlp` without `ms_token`. | Enforce `encoding="utf-8", errors="replace"` plus `PYTHONIOENCODING="utf-8"` / `PYTHONUTF8="1"` on all `yt-dlp` subprocesses (preventing Windows `cp1252` crashes on Vietnamese text), keep lightweight `64 kbps` `.mp3` only (no `.mp4`), and pass `Cookie: msToken=...` + optional `--cookies` to `.mp3` extraction. |
| `data/filters/author_unique_ids.txt`, `02_DEP_03-Filter_users.ipynb`, & `data_collection.tex:14-33` | Curated 6 flagship Vietnamese F&B handles (`spicykim9386`, `haidangrevieww`, `khaikhampha`, `putaangi`, `trangtam2607`, `huynhanhtuan_dienvien`) and Chapter 3 thresholds (`total_views > 100k`, `avg_views > 40k`, `ER > 0.03`). | `--auto-creators <k>` prioritizes preserved `data/filters/author_unique_ids.txt` handles verified in `dim_creators.parquet`, then ranks remaining `dim_creators.parquet` creators meeting `median_play_count >= 40,000` and `median_engagement_rate >= 0.03` by `(-avg_videos_per_week, -sample_video_count, -follower_count, unique_id)`. |
| `src/crawler/crawler.py:106-127` & `docs/TikTok_data_fields.md` | Appends `collectTime` Unix timestamp and writes raw `videos_info.json` preserving audio/quality metadata (`video.VQScore`, `video.volumeInfo`, `video.claInfo.hasOriginalAudio`, `diversificationLabels`, `poi.*`, `isAd`, `isECVideo`). | Record `collect_time_unix` / `collected_at_utc` and append sanitized raw provider payloads (`raw_provider_payloads.jsonl`) alongside canonical `videos_4m.jsonl` inside `batch_dir` so rich `M4.1`/`M4.2` fields are preserved without bloating the canonical contract. |

---

### 2.2 Unified `itemStruct` & `yt-dlp` Schema Mapper (`pipelines/crawl_incremental/mappers.py`)

- **`map_tiktok_item_struct_to_detail(raw, *, fallback_vid="", fallback_handle="", collected_at_utc=None) -> dict[str, Any]`:**
  - Maps `id -> video_id`, `createTime -> create_time` (ISO-8601 UTC), `desc -> caption`, `author.{id, uniqueId, nickname}`, `authorStats.followerCount` (fallback `author.followerCount`), `video.duration -> duration_sec`, `statsV2.{playCount, diggCount, commentCount, shareCount, collectCount}` (fallback `stats.*`), and deduplicated hashtags from `challenges[*].title`, `contents[*].textExtra[*].hashtagName`, and `textExtra[*].hashtagName`.
  - Maps `isAd -> is_ad`, `isECVideo -> is_ec_video`, `playlistId -> playlist_id`, `isPinnedItem -> is_pinned_item`, and `poi.{id, name, address, city, ttTypeNameTiny} -> poi_{id, name, address, city, category_tiny}` (normalizing empty/`"others"`/`"null"`/`"nan"` strings to `None`).
- **`map_tiktok_comment_to_input(raw, *, canonical_vid, idx) -> dict[str, Any] | None`:**
  - Normalizes `TikTokApi` (`cid`, `user.{unique_id, uniqueId}`, `text`, `digg_count`, `reply_comment_total`) and `yt-dlp` (`id`, `author`, `text`, `like_count`, `reply_count`) comments, rejecting whitespace-only comments while **preserving raw unstripped `text`** so `CommentRecord.original_text` and `M5.2` `NFC` offsets match 1-to-1.
- **`map_ytdlp_json_to_detail(raw, *, candidate, collected_at_utc=None) -> tuple[dict[str, Any], list[dict[str, Any]]]`:**
  - Extracts `collect_count` (`collect_count` / `save_count`), `share_count` (`repost_count` / `share_count`), comment `reply_count` (including counting child replies via `parent` IDs when `yt-dlp` emits flat comment lists), `is_pinned` (`is_pinned` / `pinned`), and any `is_ad`, `is_ec_video`, `playlist_id`, or `poi` fields exposed by `yt-dlp`.

### 2.3 Pluggable `CollectorBackend` (`auto` | `tiktokapi` | `ytdlp`) & Fail-Closed Anti-Bot Gate (`providers.py`, `worker.py`)

- **`CollectorBackend = Literal["auto", "tiktokapi", "ytdlp"]` (default `"auto"`):**
  1. **`TikTokApiCollectorProvider` (`backend="tiktokapi"`):** Lazily imports the official `TikTokApi` package. Runs bounded async operations (`num_sessions=1`, `ms_tokens=[ms_token]`, `browser=tiktok_browser`, `headless=tiktok_headless`, `sleep_after=2`, `timeout=timeout_sec * 1000`). During `discover_candidates(creators, max_per_creator)`, applies the `crawler.py:97-118` loop (`isPinnedItem` skip + early `break` when an unpinned item has `cutoff_utc` > `createTime`) and caches `video.as_dict` by `video_id` so `fetch_video_detail` requires zero extra HTTP calls.
  2. **`LiveTikTokCollectorProvider` (`backend="ytdlp"`):** Runs `yt-dlp` with UTF-8 subprocess environment (`encoding="utf-8", errors="replace"`, `PYTHONIOENCODING="utf-8"`, `PYTHONUTF8="1"`), `--add-header "Cookie: msToken=<ms_token>"`, and optional `--cookies <cookies_file>`.
  3. **`AutoHybridTikTokCollectorProvider` (`backend="auto"`):** Uses `TikTokApiCollectorProvider` first when `TikTokApi` is importable on the host, falling back automatically per operation to `LiveTikTokCollectorProvider` (`ytdlp`) on `TransientCollectorError` or Playwright browser-launch unavailability; if primary detail/comments return `0` comments for a video reporting `comment_count > 0`, attempts secondary `fetch_comments` once. Routes directly to `ytdlp` when `TikTokApi` is not installed. Records `backends_used: list[str]`.
- **Strict Fail-Closed Anti-Bot / CAPTCHA Boundary (`AntiBotChallengeError`):**
  - Any `CaptchaException`, `EmptyResponseException` bot-detection block (`tiktok.py:490`), or `yt-dlp` CAPTCHA/human-verification gate raises `AntiBotChallengeError` (distinct from `TransientCollectorError`).
  - Neither `AutoHybridTikTokCollectorProvider` nor `BoundedIncrementalCollector` retries or switches backends to evade `AntiBotChallengeError`. `BoundedIncrementalCollector` records `status="failed"`, `attempts=1`, sanitized `reason="anti_bot_challenge_blocked: ..."`, and halts live collection (`stopped_reason="anti_bot_challenge_blocked"`).

### 2.4 Authenticated `64 kbps` Audio Extraction, Curated Auto-Creators & Home CLI Controls

- **Authenticated `64 kbps` `.mp3`:** `download_audio_mp3_64k(tiktok_url, output_mp3, *, ms_token="", cookies_file=None, timeout_sec=45)` and `YtDlpAudioConverter64k(allow_live_network=False, ms_token="", cookies_file=None)` forward `Cookie: msToken=<ms_token>`, optional `--cookies <cookies_file>`, and UTF-8 subprocess settings to `yt-dlp`. `_sanitize_reason` redacts `ms_token`, `msToken`, `sessionid`, `Cookie`, and `--cookies <path>` values.
- **`.env` Auto-Loader (`load_dotenv_if_present`):** Populates unset `MS_TOKEN` (accepting `MS_TOKEN` or legacy `ms_token` from `.env`), `TIKTOK_COOKIES_FILE`, `TIKTOK_BROWSER`, and `TIKTOK_HEADLESS` without overwriting existing environment variables or logging secret values.
- **Curated Creator Selection (`select_curated_fnb_creators`):** Uses `data/filters/author_unique_ids.txt` + Chapter 3 thresholds (`median_play_count >= 40,000`, `median_engagement_rate >= 0.03`) over `dim_creators.parquet` when `--auto-creators <k>` (`1..5`) is passed.
- **CLI & Orchestrator Controls (`pipelines.crawl_incremental` & `pipelines.pilot_m3_3`):**
  - `--backend {auto,tiktokapi,ytdlp}` (default `auto`), `--cookies-file <path>`, `--tiktok-browser {chromium,webkit,firefox}`, `--tiktok-headless` / `--no-tiktok-headless`, `--auto-creators <k>`, `--resume` (forwarded into `BoundedIncrementalCollector.run`), and `--preflight-only` (0 network calls; outputs JSON readiness check covering `MS_TOKEN`, `yt-dlp`, `ffmpeg`, `faster-whisper`, optional `TikTokApi`/Playwright, `70,996` protected IDs, and resolved creators).
  - Additive defaulted provenance fields `collector_backend_requested: str = "auto"` and `collector_backends_used: list[str] = Field(default_factory=list)` on `CrawlManifest` and `CollectionSummaryReceipt`.

### 2.5 Phase 3 Targeted Batch Comment Enrichment (`enrich_batch_comments` & `--enrich-comments-only`)

- **Why needed:** During the initial `yt-dlp` pilot capture, `30` fresh videos, `29` `.mp3` files, and `10` CPU Whisper transcripts were collected and `30/30` human-verified, but `collected_comments_count` was `0`. Under normal `--resume`, `BoundedIncrementalCollector` skips `already_succeeded_in_checkpoint` items without re-calling `fetch_comments()`.
- **Bounded Enrichment Mechanics (`BoundedIncrementalCollector.enrich_existing_comments` & `run_m3_3_comment_enrichment`):**
  1. Reads existing `videos_4m.jsonl` from `batch_dir` (failing closed if `videos_4m.jsonl` is absent or empty, or if any record violates `historical_video_ids`).
  2. For each record lacking comments (or when `refresh_all=False`, skipping records that already have non-empty `comments` or `comment_count == 0` when metadata explicitly says `0`), calls `provider.fetch_comments(video_id, max_comments=min(max_comments_per_video, remaining_budget))` with bounded retry (`<= 1 + max_retries`) and fail-closed `AntiBotChallengeError` halting (`stopped_reason="anti_bot_challenge_blocked"`).
  3. Preserves 100% of existing `audio_path`, `transcript`, `whisper_segments`, and metadata fields on `RawIncrementalVideoRecord`; atomically updates `videos_4m.jsonl` and `crawl_manifest.json` after each video so partial progress is crash-safe and resumable.
  4. Runs `ingest_incremental_batch_to_gold(..., update_existing=True)` atop `base_corpus_dir` (or the prior pilot snapshot) into a new immutable Gold snapshot (`m3_3_pilot_snapshot_v2` or auto-versioned `--output-gold`) so `fact_comments.parquet` and `fact_absa_reviews.parquet` are populated without mutating `20261118_taxonomy_fix_v1` or `m3_3_pilot_snapshot_v1`.
  5. Updates `comment_count_collected` in `sample_inspection_sheet.jsonl` while preserving existing `assigned_reviewer`, `human_verified`, and `reviewer_notes` fields verbatim.

---

## 3. Authorized Credential Reconciliation and Bounded Rerun (2026-11-25)

The owner supplied a fresh local browser cookie export and authorized using that export for one new M3.3 live pilot attempt. This activity preserves the earlier M3.3 acceptance record and treats its new run as a separate measurement.

- Convert the supplied JSON export into a local Netscape cookies file without printing, logging, or committing cookie values. Use the `msToken` scoped to `www.tiktok.com` for the single `MS_TOKEN` value because the installed TikTokApi opens `https://www.tiktok.com` and assigns that token to that host. Exclude any conflicting `msToken` rows from the converted cookie jar.
- Keep `MS_TOKEN` only in gitignored `.env`. Point `TIKTOK_COOKIES_FILE` to the converted local file. Preserve the original JSON export and any pre-existing cookie file.
- Validate file format, cookie expiration, credential alignment, preflight readiness, and secret hygiene before the live call. Record only booleans, counts, timings, and sanitized errors in task evidence.
- Run at most one bounded `live_pilot` attempt with distinct work, Gold, BM25, receipt, and inspection paths. Stop on any anti-bot/CAPTCHA result under the existing fail-closed rule; do not treat a new blocked run as a revision of the already completed historical M3.3 acceptance.
- Report the actual receipt, verification result, and any remaining blocker in English. Do not change the milestone or G3 status based on the new attempt alone.

## 4. Authorized Full-Session Cookie Propagation Fix (2026-11-25)

The owner requested a concrete remedy after the token-only TikTokApi discovery returned `anti_bot_challenge_blocked` with zero candidates. The confirmed implementation gap is that `TikTokApiCollectorProvider` receives `cookies_file` but does not pass its cookies into `create_sessions`; only `MS_TOKEN` reaches Playwright.

- Load the configured Netscape cookie file through Python's cookie jar without printing or persisting values. Select only unexpired cookies applicable to `www.tiktok.com` (exclude host-only `tiktok.com` cookies), prefer the most specific domain for duplicate names, and force the existing `MS_TOKEN` value for `msToken`.
- Pass the resulting name/value mapping to TikTokApi's existing `create_sessions(cookies=[...])` parameter. Keep token-only behavior when no cookie file is configured. Reject unreadable or malformed configured files with a generic message that does not reveal cookie contents.
- Add offline regression tests proving full-cookie propagation, host scoping, token precedence, no-cookie compatibility, and secret-safe malformed-file handling before changing production code.
- Preserve the existing single-session limit, bounded collection ceilings, protected historical IDs, and immediate fail-closed behavior on anti-bot/CAPTCHA. A new owner-authorized live attempt may run once with distinct output paths after tests and preflight; never retry or switch backend after an anti-bot result.
- Record actual live yield and stage timings. A successful offline unit test alone does not satisfy fresh-data collection; if TikTok still blocks, report the external limitation and feasible authorized data sources without claiming the crawl succeeded.

## 5. Authorized Comment-File Import Path (2026-11-25)

The owner authorized the practical data path after TikTok blocked two new live attempts. No approved Research API credential or creator-provided comment file has been supplied. The deliverable is an offline-tested importer ready for a real authorized file; it must not fabricate comments or mark live collection successful.

- Accept a normalized UTF-8 CSV or JSONL file containing `video_id`, `comment_id`, and nonblank `text`; optional `author_handle`, `like_count`, and `reply_count` default to empty/zero. Require a nonblank `source_label` for provenance and store the input SHA256, row counts, and base snapshot ID in a receipt, without copying the source file or leaking its contents into logs.
- Accept comments only for existing video IDs in a SHA256-verified Gold base snapshot whose video creation times are within the 120-day rolling window at a supplied `as_of_utc` (default current UTC). Reject unknown/out-of-window IDs, blank text, duplicate comment IDs, negative counts, malformed CSV rows, and files exceeding 1,000 rows or 50 comments per video; the merged per-video total must also stay within 50. Preserve unstripped nonblank comment text for M5.2 offsets and preserve prior comment author/count values when an update omits optional fields.
- Construct sparse `RawIncrementalVideoRecord` rows from the verified base video IDs and comments, then call the existing `ingest_incremental_batch_to_gold(..., update_existing=True)` into a new immutable snapshot. Preserve the source file and base snapshot bytes; never overwrite an existing output directory. The converter must populate `fact_comments.parquet` with `original_text` retained across repeated enrichments, refresh `fact_absa_reviews.parquet`, and carry forward video metadata and voice rows.
- Provide an explicit `--preflight-only` mode that checks input shape/IDs/bounds without writing a batch or Gold snapshot, and a human-readable input template. Real success requires a non-synthetic authorized source file; fixture tests demonstrate wiring only.
- Keep all new report prose in English, record the actual verification and remaining missing input, and leave the earlier M3.3 `PASS` acceptance and G3 state intact.

## 6. Direct Playwright Comment Capture from Known Video URLs (2026-11-25)

The owner chose a browser-page capture route because Research Tools access is unavailable and the accepted Gold snapshot already contains video URLs. Probe one known fresh video page with the existing scoped cookie set and report only page state and DOM selector counts. The probe revealed TikTok's slider CAPTCHA when comments were opened; the owner explicitly offered to solve it manually in the visible browser. Allow one bounded wait for the owner's own interaction, without automated CAPTCHA solving or circumvention. Continue to implementation only if the page then exposes real comment cards; otherwise stop with an honest blocked result.

- Accept only `https://www.tiktok.com/@<handle>/video/<id>` URLs whose IDs are present in the SHA256-verified accepted Gold and within the 120-day window. Bound capture to at most 50 comments per video and one page/session at a time. Reuse the existing Netscape cookie mapping without printing values.
- Read comment text and visible author from rendered browser DOM, using the real observed structure. If TikTok does not expose a native comment ID on a card, derive and label a deterministic local ID from the video ID, author, text, and card position; do not present it as a TikTok ID. Preserve unstripped text. Do not infer unavailable likes/replies.
- Produce a UTF-8 normalized JSONL file compatible with `pipelines.import_authorized_comments`, with provenance stating browser-rendered capture and an honest count. Import it into a new immutable Gold snapshot only if live capture yields validated real comments. Never overwrite prior raw data, Gold, receipts, or the accepted M3.3 snapshot.
- Add offline tests for URL allowlisting, card parsing, bounded count, empty/challenge detection, and no-write behavior on failure. Run one bounded live capture attempt against an existing accepted video URL, permitting only the owner's manual slider completion in the visible browser; record the actual result and measured timing. No claim of success may rest on fixtures alone.

## 7. Single-Session Remaining-Pilot Batch Capture with Cooldown and Checkpointing (2026-11-25)

After two videos (`39` comments) were verified end-to-end, the owner approved a bounded extension of `pipelines.capture_playwright_comments` to capture comments across the remaining `28` fresh pilot videos in a single visible browser session with polite inter-video cooldowns:

- **Remaining-pilot target selection (`--remaining-pilot`):** Load the SHA256-verified `--base-corpus`, exclude videos outside the 120-day rolling window and any `video_id` already present in `fact_comments.parquet`, and iterate deterministically (`create_time` descending, `video_id` ascending) in **one reusable visible Chromium context** so session state is preserved across videos. `--url` and `--remaining-pilot` are mutually exclusive.
- **Inter-video cooldown, bounded scroll, and ceilings:** Sleep `cooldown_seconds + uniform(0, jitter_seconds)` (default `10.0`s + `0..4.0`s = `10–14`s; bounds `0..120`s and `0..60`s) before each subsequent video visit. Within each video's comment panel, optionally scroll up to `scroll_rounds` (`0..6`, default `4` in batch mode with `1.5`s settle and early break when card count stops growing or reaches `limit`) to collect up to `50` rendered comments per video and at most `1,000` comments across the batch, matching `pipelines.import_authorized_comments`.
- **Zero-comment tolerance & fail-closed checkpointing (`--resume`):** In batch mode, videos that genuinely have `0` visible comments (empty-comment placeholder or bounded `no_comment_wait_seconds` expiry without challenge) or unavailable/deleted pages are recorded in `.state.json` / `.receipt.json` and skipped cleanly rather than aborting the batch. Login gates (`/login`) and unsolved CAPTCHAs (`AntiBotChallengeError` after `manual_wait_seconds`) halt the batch immediately without automated circumvention while preserving all already-checkpointed JSONL rows on disk for `--resume` or `pipelines.import_authorized_comments`.

## 8. Owner-Authorized 100-Video Fresh Metadata + Comment Expansion (2026-11-25)

Following completion of the `30`-video `M3.3` pilot (`394` real comments in `v3`), the owner explicitly authorized an expansion batch of `100` additional fresh (`<= 120`-day) F&B videos and their rendered comments (metadata-only `max_audio_minutes=0.0`, preserving all `70,996` historical IDs and `30` pilot IDs untouched):

- **Bounded `5,000`-row ceiling (`100` videos × `<= 50` comments/video):** Keep the default `1,000`-row ceiling for standard `<= 30`-video batches while supporting an explicit `--max-total-comments` (`1..5000` on `pipelines.capture_playwright_comments`) and `max_rows` / `--max-rows` (`1..5000` on `pipelines.import_authorized_comments`) so a `100`-video comment batch never truncates at row `1,001`.
- **Two-stage immutable Dual-Sink pipeline:** (1) Discover and collect `100` fresh (`<= 120`-day) F&B video metadata records via `pipelines.crawl_incremental` (`--backend ytdlp --max-audio-minutes 0`, protecting all `71,026` existing Gold IDs) and ingest them into a new SHA256-verified snapshot (`v4`); (2) run `--remaining-pilot --resume --max-total-comments 5000` in a single visible Playwright session (`8–12 s` inter-video cooldown) over those `100` new fresh URLs and import the captured comments into a new SHA256-verified snapshot (`v5`). Preserve `m3_3_original_pass_receipt.json` and leave `G3` (`M3.G`) status explicit.
