# M3.3 — Capped Capture-to-Transcript-to-Search Pilot (`live_pilot = PASS`, `30/30` `N`+`K` Verified) & Hybrid `21KHDL-TikTok-Analytics` Collector Upgrade

- Status: COMPLETE (`live_pilot` capture -> `faster-whisper/small-cpu-int8` ASR -> `TikTokApi` desktop comment enrichment (`454` raw / `452` Gold `fact_comments` rows in `m3_3_pilot_snapshot_v2` across `28/30` pilot videos) + owner-authorized `100`-video fresh metadata & Playwright DOM comment expansion (`2,823` real comments across `118/130` fresh F&B videos in `m3_3_playwright_comments_20261125_v5`) -> `BM25Index` -> searchability **executed and passed** on real TikTok data: `30` pilot videos across `5` creators (`29` 64kbps `.mp3` files, `10` CPU-transcribed videos `16.683` min `RTF=0.1971`, **`10/10` searchable**, **`30/30` `15 N` + `15 K` `human_verified=true`**); Gate `G3` (`M3.G`) evaluated separately)
- Execution date: 2026-11-20 to 2026-11-25 (Asia/Ho_Chi_Minh; original pilot acceptance on 2026-11-23, `TikTokApi` `v2` enrichment on 2026-11-24, Playwright `v5` expansion on 2026-11-25)
- Requirement source: [TikTok_AI_Engine_Milestone.md](../../../planning/TikTok_AI_Engine_Milestone.md) (`M3.3`)
- Repository version: `main` (`bde4017f`) + `feat/m3.3-live-comment-enrichment` (`K` `15/15` + `N` `15/15` sign-off & Phase 3 comment enrichment)
- Owners: Nguyễn Việt Nguyên (`N`) & Trần Đình Khương (`K`) (shared integration & 50/50 inspection)
- Specification: [spec.md](superpowers/spec.md)
- Execution plan: [plan.md](superpowers/plan.md)

## Conclusion

Direct Playwright visits combined with an owner-authorized `100`-video fresh (`<= 120`-day) `yt-dlp` metadata expansion produced **`2,823` real visible comments across `118` commented videos out of `130` total fresh F&B videos** (`70,996` historical IDs untouched):
- **Initial `30`-video `M3.3` pilot batch (`v1` -> `v3`):** Visited all `30/30` pilot video URLs (`19` + `20` + `355` = **`394` real comments** across `28` commented videos, `2` zero-comment videos) into [m3_3_playwright_comments_20261125_v3](../../../../data/corpus/m3_3_playwright_comments_20261125_v3/manifest.json).
- **Owner-authorized `100`-video fresh F&B expansion (`v4_meta` -> `v5`):** Collected `100` additional fresh (`<= 120`-day) F&B video metadata records (`max_audio_minutes=0`, `failed=0`) across `12` active F&B creators into [m3_3_playwright_comments_20261125_v4_meta](../../../../data/corpus/m3_3_playwright_comments_20261125_v4_meta/manifest.json) (`71,126` videos), then captured **`2,429` additional real comments** across `90` of those `100` videos (`4` zero-comment + `6` disabled/slideshow pages skipped cleanly, `manual_challenge_count=4` solved manually by the owner in `2,383.062 s` with `8–12 s` inter-video cooldowns) and imported them into SHA256-verified [m3_3_playwright_comments_20261125_v5](../../../../data/corpus/m3_3_playwright_comments_20261125_v5/manifest.json) (**`71,126` videos, `2,823` comments across `118` videos with `2,823/2,823` nonblank `original_text`, `130` ABSA rows, and `436` preserved Whisper voice segments**).

TikTok did not expose native comment IDs in the rendered cards, so the imported rows use clearly labeled local DOM-derived IDs (`dom_...`). The two earlier TikTokApi reruns remain **BLOCKED** at candidate discovery and did not produce data. Base `m3_3_pilot_snapshot_v1` and [m3_3_original_pass_receipt.json](evidence/m3_3_original_pass_receipt.json) remain untouched, while `v5` provides `2,823` real comments across `118` fresh F&B videos for `M5.1` and `M5.2`; `G3` (`M3.G`) remains `NOT_RUN` pending formal gate review. See [capture evidence](evidence/playwright_comment_capture_20261125.json).

Executed the official bounded **`M3.3` `live_pilot`** pipeline ([m3_3_original_pass_receipt.json](evidence/m3_3_original_pass_receipt.json)) across **5 active Vietnamese F&B creators** (`ansapsaigon`, `tinhtungtangvn`, `dicungphuc`, `diadiemanuong`, `saigonmap` — `6` captured fresh videos per creator, `<= 120` days, protecting all `70,996` historical IDs) and integrated the Phase 2 [`TrggTin/21KHDL-TikTok-Analytics`](https://github.com/TrggTin/21KHDL-TikTok-Analytics) (`f142e5656a220f94f8024de168b0832754b3bd9e`) hybrid collector (`--backend auto`):

- **Real Live Capture (`pilot_status = "PASS"`, `is_synthetic_fixture = false`):** Requested `50` candidates -> captured **`30/30` succeeded** (`0` failed, `20` skipped at ceiling, `capture_yield_rate = 0.60`), extracted **`29` 64kbps `.mp3`** audio files (`1` slideshow promo post `7709372899198602514` had no video audio track, cleanly skipped with `skipped_no_audio_count = 1`), `batch_disk_bytes = 22,646,824` (`21.60 MiB`).
- **Bounded CPU ASR (`faster-whisper/small-cpu-int8`):** Transcribed **`10/10`** videos (`16.683` audio minutes `<= 20.0` cap; remaining `19` capped via `skipped_asr_ceiling_count`) in **`197.269 s`** (`real_time_factor = 0.1971`, ASR peak RSS `1,009.46 MiB`, `0` failed).
- **Dual-Sink Gold Ingest (`M3.1`) & Searchability:** Published immutable Gold snapshots [m3_3_pilot_snapshot_v1](../../../../data/corpus/m3_3_pilot_snapshot_v1/manifest.json) (`58,965,140` B, initial audio/ASR slice) and comment-enriched [m3_3_pilot_snapshot_v2](../../../../data/corpus/m3_3_pilot_snapshot_v2/manifest.json) (`58,994,470` B, preserving `20261118_taxonomy_fix_v1` and `m3_3_pilot_snapshot_v1` untouched, with `452` deduplicated rows in `fact_comments.parquet` and `30` rows in `fact_absa_reviews.parquet`) and [bm25-m3_3-pilot](../../../../artifacts/indexes/bm25-m3_3-pilot/bm25-receipt.json) (`44,129,154` B, `21,758` total docs = `21,748` historical + `10` fresh transcribed). **`10/10` fresh transcribed videos retrieved with exact `video_id` matches.**
- **Total Pilot Resource Cost & 50/50 Split (`30/30` Verified):** Initial capture + ASR wall time `744.154 s` (`12.4` min, peak RSS `3,214.92 MiB`); Phase 3 comment enrichment + Gold v2 publication wall time `41.141 s` (`28.77 s` comment collection, peak RSS `2,911.02 MiB`), total disk `125,835,108` B (`120.01 MiB`). Both contributors verified their assigned halves in [sample_inspection_sheet.jsonl](evidence/sample_inspection_sheet.jsonl) (`15/15 N` + `15/15 K` = **`30/30` `human_verified = true`**; `29/29` `.mp3` files decode cleanly via `ffmpeg` 16kHz PCM, `#19` `7709372899198602514` confirmed as a no-audio slideshow promo, `10/10` ASR transcripts match Vietnamese F&B topics with minor loanword/dialect typos, `#13` flagged as mixed photo/food festival, and `#26` flagged as an out-of-domain museum vlog).
- **Phase 2/3 Hybrid `TikTokApi -> yt-dlp` & Live Comment Enrichment (`454` Comments Collected, `comment_coverage_rate = 0.9333`):** During the initial `yt-dlp` pilot run, `collected_comments_count` was `0` because `yt-dlp`'s TikTok extractor does not implement `_get_comments`. Phase 2 (`K`) integrated the `21KHDL-TikTok-Analytics` `TikTokApi` provider (`video.comments()` `/api/comment/list/`, `itemStruct` POI/EC/Ad mapping, `isPinnedItem` chronological loop, single-session Playwright reuse), and Phase 3 (`N` & `K`) added `--enrich-comments-only` (`BoundedIncrementalCollector.enrich_existing_comments` + minimal `aid=1988` `/api/comment/list/` signing fix for `TikTokApi 7.3.5`) and executed live desktop comment enrichment (`--backend tiktokapi --no-tiktok-headless`) across all `30` pilot videos (`30/30` succeeded, `0` failed, **`454` raw comments collected across `28/30` videos**, `comment_coverage_rate = 0.9333`, yielding **`452` unique `fact_comments.parquet` rows** in `m3_3_pilot_snapshot_v2` to unblock `M5.1` and `M5.2`).

## Work performed

- On 2026-11-25, converted the owner-supplied JSON cookie export into a local Netscape file with one `www.tiktok.com` `msToken`, aligned gitignored `.env`, passed zero-network preflight, and executed one fail-closed live attempt.
- Added scoped Netscape cookie loading to [providers.py](../../../../pipelines/crawl_incremental/providers.py) so TikTokApi receives the applicable browser cookies in `create_sessions`; added offline regression tests for token precedence, domain and expiry filtering, no-file compatibility, and malformed-file secret safety. A second bounded live attempt still stopped at discovery. No historical corpus data was changed.
- Added a bounded CSV/JSONL [comment importer](../../../../pipelines/import_authorized_comments/importer.py) with a no-write preflight, source SHA256 receipt, verified Gold video-ID and 120-day checks, configurable `--max-rows` (`1..5000`, default `1000`), cumulative 50-comment/video ceiling, malformed CSV rejection, and immutable dual-sink snapshot publication. Gold comments retain `original_text` alongside normalized `text` across repeated enrichments (`19` -> `v1`, `39` -> `v2`, `394` -> `v3`, and `2,823` -> `v5`).
- Added [direct Playwright comment capture](../../../../pipelines/capture_playwright_comments/capture.py) for known verified video URLs, including `--remaining-pilot` single-session batch mode with configurable randomized inter-video cooldowns, bounded `4`-round panel scrolling (`<= 50` comments/video, `--max-total-comments` `<= 5,000`), zero-comment/unavailable-post tolerance, and `.state.json` `--resume` checkpointing (`24/24` unit tests). Combined with a bounded `100`-video `yt-dlp` fresh metadata crawl (`v4_meta`), processed `130/130` fresh F&B videos (`118` with comments, **`2,823` total real comments** in `v5`). Raw DOM and normalized JSONL files remain under `data/raw_incremental/`; only sanitized counts and hashes are in the report evidence.
- **Real-world TikTok `yt-dlp` hardening ([crawler_service.py](../../../../pipelines/crawl_incremental/crawler_service.py), [providers.py](../../../../pipelines/crawl_incremental/providers.py)):** Added `curl-cffi` TLS Chrome impersonation (`yt_dlp_impersonate_args()`), switched `download_audio_mp3_64k` to `-f best[vcodec=h264]/best[vcodec!=none]/best` so spoken creator audio downloads reliably instead of backing music / HTTP `403`, and interleaved multi-creator discovery round-robin across `<= 5` handles.
- **Phase 2 `21KHDL-TikTok-Analytics` hybrid upgrade ([mappers.py](../../../../pipelines/crawl_incremental/mappers.py), [providers.py](../../../../pipelines/crawl_incremental/providers.py), [worker.py](../../../../pipelines/crawl_incremental/worker.py)):** Added `map_tiktok_item_struct_to_detail`, `map_tiktok_comment_to_input` (preserving unstripped `text` for exact `M5.2` `NFC` offsets), `map_ytdlp_json_to_detail`, `TikTokApiCollectorProvider` (`isPinnedItem` skip + unpinned `cutoff_utc` break + cached `video.as_dict` + single reusable Playwright session), `AutoHybridTikTokCollectorProvider` (`--backend auto`), fail-closed `AntiBotChallengeError` across discovery/detail/comments/`.mp3` audio, multi-cookie (`sid_tt`/`sessionid_ss`/`uid_tt`/`ttwid`/`odin_tt`/`msToken`) & `--cookies` redaction, sanitized `raw_provider_payloads.jsonl` archiving, `select_curated_fnb_creators`, and `load_dotenv_if_present`.
- **Bounded CPU ASR & end-to-end M3.3 pilot runner ([asr.py](../../../../pipelines/pilot_m3_3/asr.py), [runner.py](../../../../pipelines/pilot_m3_3/runner.py), [models.py](../../../../pipelines/pilot_m3_3/models.py), [__main__.py](../../../../pipelines/pilot_m3_3/__main__.py)):** Enforces `M3.2` hard caps (`5` creators, `50` candidates, `30` succeeded, `60.0` audio min, `1,000` comments, `7,200`s deadline) and `M3.3` CPU ASR caps (`<= 10` videos / `<= 20.0` min, `ffmpeg` 16kHz PCM decode avoiding PyAV 19 `metadata_errors`), plus `--backend`, `--cookies-file`, `--tiktok-browser`, `--tiktok-headless` / `--no-tiktok-headless`, `--auto-creators`, non-colliding `--resume`, `--enrich-comments-only` (`run_m3_3_comment_enrichment`), and `--preflight-only`.

## Outputs

| File | Purpose |
| --- | --- |
| [m3_3_pilot_receipt.json](evidence/m3_3_pilot_receipt.json) | Official `live_pilot` Phase 3 receipt (`pilot_status = "PASS"`, `30` succeeded, `454` raw comments / `93.33%` coverage -> `452` `fact_comments` rows in `m3_3_pilot_snapshot_v2`, `10` ASR `small` `RTF=0.1971`, `10/10` searchable, `41.141 s` enrichment wall time) |
| [m3_3_original_pass_receipt.json](evidence/m3_3_original_pass_receipt.json) | Original 2026-11-23 `live_pilot` receipt (`pilot_status = "PASS"`, `50` candidates -> `30` succeeded, `29` `.mp3`s, `10` ASR `small` `RTF=0.1971`, `744.154 s` wall, `3.14 GiB` RAM, `119.92 MiB` disk, `m3_3_pilot_snapshot_v1`) |
| [playwright_comment_capture_20261125.json](evidence/playwright_comment_capture_20261125.json) | Full `130`-video (`30` pilot + `100` expansion) real DOM capture/import provenance (`2,823` comments across `118` videos in `m3_3_playwright_comments_20261125_v5`), timings, local-ID limitation, and 20 SHA256 hashes |
| [live_attempt_20261125_before_cookie_sync.json](evidence/live_attempt_20261125_before_cookie_sync.json) | Earlier local blocked receipt retained before credential reconciliation |
| [live_attempt_20261125_cookie_sync.json](evidence/live_attempt_20261125_cookie_sync.json) | Bounded live receipt: blocked at discovery after local credential alignment |
| [live_attempt_20261125_cookie_sync_manifest.json](evidence/live_attempt_20261125_cookie_sync_manifest.json) | Collector stop reason, stage timings, and zero-candidate result for the cookie-sync attempt |
| [live_attempt_20261125_full_session.json](evidence/live_attempt_20261125_full_session.json) | Bounded live receipt after TikTokApi full-session cookie propagation: blocked at discovery |
| [live_attempt_20261125_full_session_manifest.json](evidence/live_attempt_20261125_full_session_manifest.json) | Fail-closed stop reason and measured stage timings for the full-session attempt |
| [live_attempt_20261125_full_session_checks.json](evidence/live_attempt_20261125_full_session_checks.json) | SHA256 evidence hashes and prior snapshot inventory (`71,026` video rows, zero comment rows) |
| [live_attempt_20261125_checks.json](evidence/live_attempt_20261125_checks.json) | Report layout, link, receipt, stop-reason, and evidence SHA256 checks |
| [authorized_comments_template.csv](evidence/authorized_comments_template.csv) | Header-only normalized input contract for an authorized creator comment export |
| [sample_inspection_sheet.jsonl](evidence/sample_inspection_sheet.jsonl) | `30`-video equal inspection workbook (`15` assigned to `K`, `15` assigned to `N`, `6` per creator) |
| [workflow.md](evidence/workflow.md) | `M3.3` Phase 1 live pilot & Phase 2 `21KHDL` hybrid collector TDD ledger, rulings, and verification receipts |
| [red-m3_3-tests.log](evidence/red-m3_3-tests.log), [green-m3_3-tests.log](evidence/green-m3_3-tests.log) | TDD RED -> GREEN logs for `pipelines/pilot_m3_3/` |
| [pytest-full-m3_3.log](evidence/pytest-full-m3_3.log) | Workspace pytest verification log |

## Run at Home / Reproduce Guide (Step-by-Step)

1. **Provision Python runtime tools (no `sudo` required):**
   - **Quick mode (`yt-dlp` + `curl-cffi` + `ffmpeg` + `faster-whisper`):**
     ```bash
     uv pip install --python .venv/bin/python yt-dlp curl-cffi faster-whisper imageio-ffmpeg
     ln -sf "$(.venv/bin/python -c 'import imageio_ffmpeg; print(imageio_ffmpeg.get_ffmpeg_exe())')" .venv/bin/ffmpeg
     ```
   - **Enriched mode (`TikTokApi` + Playwright Chromium for full `itemStruct` POI/EC/Ad/comments, with automatic `yt-dlp` fallback):**
     ```bash
     uv pip install --python .venv/bin/python TikTokApi playwright yt-dlp curl-cffi faster-whisper imageio-ffmpeg
     ln -sf "$(.venv/bin/python -c 'import imageio_ffmpeg; print(imageio_ffmpeg.get_ffmpeg_exe())')" .venv/bin/ffmpeg
     .venv/bin/playwright install chromium
     ```
     *(On Windows PowerShell without system `ffmpeg`: `Copy-Item (.\.venv\Scripts\python.exe -c "import imageio_ffmpeg; print(imageio_ffmpeg.get_ffmpeg_exe())") .\.venv\Scripts\ffmpeg.exe` and replace `.venv/bin/python` with `.\.venv\Scripts\python.exe` below.)*

2. **Add `MS_TOKEN` to gitignored `.env` (auto-loaded by CLI — no manual `source .env` needed):**
   ```dotenv
   MS_TOKEN=<paste_your_msToken_here>
   TIKTOK_COOKIES_FILE=
   TIKTOK_BROWSER=chromium
   TIKTOK_HEADLESS=true
   ```

3. **Run zero-network preflight check (`--preflight-only`):**
   ```bash
   .venv/bin/python -m pipelines.pilot_m3_3 \
     --mode live_pilot --allow-live-network \
     --backend auto --auto-creators 5 \
     --output-gold data/corpus/m3_3_pilot_snapshot_v2 \
     --preflight-only
   ```

4. **Execute bounded `live_pilot` (or pass `--resume` to recover interrupted runs):**
   ```bash
   .venv/bin/python -m pipelines.pilot_m3_3 \
     --mode live_pilot --allow-live-network \
     --backend auto --auto-creators 5 \
     --output-gold data/corpus/m3_3_pilot_snapshot_v2 \
     --asr-model small
   ```
   - **Desktop tip (`21KHDL` `tiktok.py:490`):** Append `--no-tiktok-headless` if headless Chromium triggers `EmptyResponseException`, or `--backend ytdlp` for `yt-dlp`-only mode.
   - **Anti-bot / CAPTCHA policy:** Any CAPTCHA challenge halts immediately (`stopped_reason="anti_bot_challenge_blocked"`). Refresh `MS_TOKEN` from a normal browser session and resume later with `--resume`.

## Verification

| Check | Result | Scope / evidence |
| --- | --- | --- |
| Official `live_pilot` across `5` F&B creators (`--asr-model small`) | **PASS (`30/30` collected, `10/10` ASR searchable)** | `16.683` min audio in `197.269 s` (`RTF=0.1971`), `21,758` BM25 docs, `744.154 s` total, `3,214.92 MiB` RAM, `119.92 MiB` disk; [m3_3_original_pass_receipt.json](evidence/m3_3_original_pass_receipt.json) |
| Desktop `TikTokApi` comment enrichment (`--enrich-comments-only` -> `m3_3_pilot_snapshot_v2`) | **PASS (`454` raw / `452` unique `fact_comments` across `28/30` pilot videos, `93.33%` coverage)** | `41.141 s` total wall time, `2,911.02 MiB` peak RSS, native TikTok IDs & like counts preserved; [m3_3_pilot_receipt.json](evidence/m3_3_pilot_receipt.json) |
| Playwright DOM capture, 100-video fresh metadata expansion, and Gold `v5` import | **PASS (`130` fresh videos, `118` with comments, `2,823` real comments)** | `30` pilot videos (`394` comments -> `v3`) + `100` fresh `yt-dlp` metadata videos (`v4_meta`, `0` failures) + `2,429` comments in `2,383.062 s` (`manual_challenge_count=4`) -> verified Gold [m3_3_playwright_comments_20261125_v5](../../../../data/corpus/m3_3_playwright_comments_20261125_v5/manifest.json) (`71,126` videos, `2,823/2,823` nonblank `original_text`, `130` ABSA rows, `436` voice segments); [capture evidence](evidence/playwright_comment_capture_20261125.json) |
| 2026-11-25 discovery-mode `TikTokApi` live attempts (`cookie_sync` & `full_session`) | BLOCKED (honest fail-closed record) | `ready_for_live_pilot=true` on preflight, then TikTokApi anti-bot at discovery (`0` candidates, `0` collected); [cookie_sync](evidence/live_attempt_20261125_cookie_sync.json), [full_session](evidence/live_attempt_20261125_full_session.json) |
| Collector, pilot, Playwright capture & importer unit suites | PASS (`24` Playwright capture + `34` collector/pilot + snapshot continuity tests) | `21KHDL` `itemStruct`/comment/`yt-dlp` mappers, `isPinnedItem` loop, `video.as_dict` cache, Netscape session cookies, `--enrich-comments-only`, paginated `comment_id` deduplication, DOM card parser, bounded scroll/cooldown, and `original_text` continuity |
| `python3 -m mypy packages apps pipelines` (Linux & `--platform win32`) & `python3 scripts/check_secrets.py` | PASS (`0` issues; `0` secret leaks) | Full cross-platform static typing and workspace secret hygiene |

## Open issues

| Issue | Impact | Follow-up / responsible task |
| --- | --- | --- |
| Two pilot videos (`7707183296874106119` with metadata `comment_count=0` and `7710598047721458945` returning `comments: null`) had `0` comments in `v2` (`452` native-ID comments across `28/30` pilot videos, `93.33%` coverage) | `m3_3_pilot_snapshot_v2` powers the blinded `M5.1` (`300` comments) and `M5.2` (`180` units) evaluation pools where `N` has already completed `180/180` and `115/115` human annotations | Preserve `m3_3_pilot_snapshot_v2` as the frozen pilot evaluation snapshot for `M5.1`/`M5.2` |
| Playwright DOM comment IDs & 50-comment/video cap in `v5` (`2,823` comments across `118/130` fresh F&B videos; `2` `TikTokApi` discovery reruns blocked) | DOM-derived `dom_` IDs omit native like/reply counts, while the `90` expansion videos (`2,429` comments in `absa_train_video_disjoint_v1.jsonl`) have `0` video overlap with the `30` pilot evaluation videos | Keep `TikTokApi` fail-closed stop intact; use `m3_3_playwright_comments_20261125_v5` & `absa_train_video_disjoint_v1` solely as video-disjoint development/lexicon data without overwriting `m5_1_pilot_pool.jsonl` / `m5_2_pilot_pool.jsonl` |
| Two creator posts (`#26` `7709375359300537601` museum vlog; `#13` `7710262606010846484` mixed photo/food festival) are non-pure F&B posts on F&B creator feeds | Observed naturally in creator-feed crawling; documented in `reviewer_notes` so downstream `M4.1` utterance selection can filter to pure F&B speech | Filter/record domain tags during `M4.1` utterance sampling |

## Data access after the live block

The original accepted snapshot remains usable for video, transcript, and search demonstrations and has `0` comments. The Playwright-enriched snapshots [m3_3_playwright_comments_20261125_v1](../../../../data/corpus/m3_3_playwright_comments_20261125_v1/manifest.json) (`19` comments), [m3_3_playwright_comments_20261125_v2](../../../../data/corpus/m3_3_playwright_comments_20261125_v2/manifest.json) (`39` comments), [m3_3_playwright_comments_20261125_v3](../../../../data/corpus/m3_3_playwright_comments_20261125_v3/manifest.json) (`394` comments across `28/30` pilot videos), [m3_3_playwright_comments_20261125_v4_meta](../../../../data/corpus/m3_3_playwright_comments_20261125_v4_meta/manifest.json) (`+100` fresh F&B metadata videos), and [m3_3_playwright_comments_20261125_v5](../../../../data/corpus/m3_3_playwright_comments_20261125_v5/manifest.json) (**`2,823` real rendered comments across `118` of `130` fresh F&B videos** plus `130` refreshed ABSA rows) are actual `yt-dlp` + browser-page measurements, not synthetic fixtures or successful TikTokApi crawls. TikTok's [Research Tools](https://developers.tiktok.com/docs/en/about-research-api) still require eligibility and approval; this capture did not use them.

For another known video in the verified Gold, capture visible comment cards into a new path with a normal Playwright window. If TikTok shows a slider, the owner must solve it manually before the bounded wait expires. The capture command never solves CAPTCHA itself:

```powershell
.\.venv\Scripts\python.exe -m pipelines.capture_playwright_comments --allow-live-network --url "https://www.tiktok.com/@creator/video/VIDEO_ID" --base-corpus data/corpus/m3_3_pilot_snapshot_v1 --output-jsonl data/raw_incremental/next_video_comments.jsonl --limit 50
```

Then run `pipelines.import_authorized_comments --preflight-only` against that JSONL, `--base-corpus data/corpus/m3_3_playwright_comments_20261125_v2`, and a new Gold output path (`v3`), followed by the same command without `--preflight-only`. Both the fail-closed path (`AntiBotChallengeError` with zero partial writes when an earlier background window's 300-second wait expired) and the live end-to-end capture/import path (`20` comments captured in `17.656 s` on `7710502428428356871` and merged into `v2` atop `v1`'s `19` comments) have now been verified on real TikTok video pages.

For a creator-authorized export, prepare a UTF-8 CSV or JSONL file with `video_id`, `comment_id`, and `text`; optional columns are `author_handle`, `like_count`, and `reply_count`. The [header-only template](evidence/authorized_comments_template.csv) gives the CSV order. IDs must belong to videos in the verified base snapshot and within the latest 120 days. Run `--preflight-only` first, then omit it to create a **new** Gold snapshot and receipt:

```powershell
.\.venv\Scripts\python.exe -m pipelines.import_authorized_comments --comments-file D:\authorized_comments.csv --source-label creator_export_20261125 --base-corpus data/corpus/m3_3_pilot_snapshot_v1 --work-dir data/raw_incremental/authorized_comments_20261125 --output-gold data/corpus/m3_3_authorized_comments_20261125 --preflight-only
```

The same command without `--preflight-only` performs the import after a successful preflight. These example paths have **not** been run against a real comment file. Do not reuse a populated work or output directory; each import must use new paths.

## Acceptance and handoff

| Task criterion | Result | Evidence |
| --- | --- | --- |
| Bounded ceilings (`5` creators, `50` cands, `30` videos, `60`m audio, `1,000` comments, `2`h), hybrid `21KHDL` collector, & CPU ASR (`<= 10` videos / `<= 20`m) | Met (`30` succeeded, `29` `.mp3`, `454` native comments in `v2` + `2,823` DOM comments across `130` fresh F&B videos in `v5`, `10` ASR `small` `16.683` min `RTF=0.1971`) | [m3_3_original_pass_receipt.json](evidence/m3_3_original_pass_receipt.json), [m3_3_pilot_receipt.json](evidence/m3_3_pilot_receipt.json), [playwright_comment_capture_20261125.json](evidence/playwright_comment_capture_20261125.json) |
| Real non-synthetic receipts, coverage/failure rates, disk/RAM/time, repeatable `M3.1` Gold snapshots, and `>= 5` searchable real fresh videos | Met (`10/10` searchable in `bm25-m3_3-pilot`; `452` comments in `m3_3_pilot_snapshot_v2` & `2,823` comments in `m3_3_playwright_comments_20261125_v5`; `0` base-byte mutations) | [m3_3_pilot_snapshot_v1](../../../../data/corpus/m3_3_pilot_snapshot_v1/manifest.json), [m3_3_pilot_snapshot_v2](../../../../data/corpus/m3_3_pilot_snapshot_v2/manifest.json), [m3_3_playwright_comments_20261125_v5](../../../../data/corpus/m3_3_playwright_comments_20261125_v5/manifest.json) |
| Both contributors inspect half of the successful sample (`15 K / 15 N`) | **Met (`30/30` verified: `N = 15/15`, `K = 15/15`, `human_verified = true`)** | [sample_inspection_sheet.jsonl](evidence/sample_inspection_sheet.jsonl) |

Final task status: **`COMPLETE`** (all technical capture/ASR/comment/Gold/BM25/searchability criteria, `30/30` two-contributor sample inspection, `TikTokApi` `v2` comment enrichment (`452` native comments), and Playwright `v5` expansion (`2,823` comments across `130` fresh F&B videos) satisfied; hands off directly to **`M3.G`**, **`M4.1`**, **`M5.1`**, and **`M5.2`**).
