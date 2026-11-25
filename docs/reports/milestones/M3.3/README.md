# M3.3 — Capped Capture-to-Transcript-to-Search Pilot (`live_pilot = PASS`, `30/30` `N`+`K` Verified) & Hybrid `21KHDL-TikTok-Analytics` Collector Upgrade

- Status: COMPLETE (`live_pilot` capture -> `faster-whisper/small-cpu-int8` ASR -> `TikTokApi` desktop comment enrichment (`454` real comments across `28/30` videos, `452` unique `fact_comments.parquet` rows) -> `M3.1` Dual-Sink Gold (`m3_3_pilot_snapshot_v2`) -> `BM25Index` -> searchability **executed and passed** on real TikTok data: `30` fresh videos across `5` creators, `29` 64kbps `.mp3` files, `10` CPU-transcribed videos (`16.683` min, `RTF=0.1971`), **`10/10` searchable**, **`30/30` (`15 N` + `15 K`) audio + transcript inspection completed** (`human_verified=true`), combined with Phase 2/3 `21KHDL-TikTok-Analytics` hybrid `TikTokApi -> yt-dlp` `--backend auto` + `--enrich-comments-only` upgrade across `221` repo tests + `105`-file Linux/`win32` `mypy`; Gate `G3` (`M3.G`) remains `NOT_RUN` pending formal gate review)
- Execution date: 2026-11-20 to 2026-11-25 (Asia/Ho_Chi_Minh)
- Requirement source: [TikTok_AI_Engine_Milestone.md](../../../planning/TikTok_AI_Engine_Milestone.md) (`M3.3`)
- Repository version: `main` (`bde4017f`) + `feat/m3.3-live-comment-enrichment` (`K` `15/15` + `N` `15/15` sign-off & Phase 3 comment enrichment)
- Owners: Nguyễn Việt Nguyên (`N`) & Trần Đình Khương (`K`) (shared integration & 50/50 inspection)
- Specification: [spec.md](superpowers/spec.md)
- Execution plan: [plan.md](superpowers/plan.md)

## Conclusion

Executed the official bounded **`M3.3` `live_pilot`** pipeline ([m3_3_pilot_receipt.json](evidence/m3_3_pilot_receipt.json)) across **5 active Vietnamese F&B creators** (`ansapsaigon`, `tinhtungtangvn`, `dicungphuc`, `diadiemanuong`, `saigonmap` — `6` captured fresh videos per creator, `<= 120` days, protecting all `70,996` historical IDs) and integrated the Phase 2 [`TrggTin/21KHDL-TikTok-Analytics`](https://github.com/TrggTin/21KHDL-TikTok-Analytics) (`f142e5656a220f94f8024de168b0832754b3bd9e`) hybrid collector (`--backend auto`):

- **Real Live Capture (`pilot_status = "PASS"`, `is_synthetic_fixture = false`):** Requested `50` candidates -> captured **`30/30` succeeded** (`0` failed, `20` skipped at ceiling, `capture_yield_rate = 0.60`), extracted **`29` 64kbps `.mp3`** audio files (`1` slideshow promo post `7709372899198602514` had no video audio track, cleanly skipped with `skipped_no_audio_count = 1`), `batch_disk_bytes = 22,646,824` (`21.60 MiB`).
- **Bounded CPU ASR (`faster-whisper/small-cpu-int8`):** Transcribed **`10/10`** videos (`16.683` audio minutes `<= 20.0` cap; remaining `19` capped via `skipped_asr_ceiling_count`) in **`197.269 s`** (`real_time_factor = 0.1971`, ASR peak RSS `1,009.46 MiB`, `0` failed).
- **Dual-Sink Gold Ingest (`M3.1`) & Searchability:** Published immutable Gold snapshots [m3_3_pilot_snapshot_v1](../../../../data/corpus/m3_3_pilot_snapshot_v1/manifest.json) (`58,965,140` B, initial audio/ASR slice) and comment-enriched [m3_3_pilot_snapshot_v2](../../../../data/corpus/m3_3_pilot_snapshot_v2/manifest.json) (`58,994,470` B, preserving `20261118_taxonomy_fix_v1` and `m3_3_pilot_snapshot_v1` untouched, with `452` deduplicated rows in `fact_comments.parquet` and `30` rows in `fact_absa_reviews.parquet`) and [bm25-m3_3-pilot](../../../../artifacts/indexes/bm25-m3_3-pilot/bm25-receipt.json) (`44,129,154` B, `21,758` total docs = `21,748` historical + `10` fresh transcribed). **`10/10` fresh transcribed videos retrieved with exact `video_id` matches.**
- **Total Pilot Resource Cost & 50/50 Split (`30/30` Verified):** Initial capture + ASR wall time `744.154 s` (`12.4` min, peak RSS `3,214.92 MiB`); Phase 3 comment enrichment + Gold v2 publication wall time `41.141 s` (`28.77 s` comment collection, peak RSS `2,911.02 MiB`), total disk `125,835,108` B (`120.01 MiB`). Both contributors verified their assigned halves in [sample_inspection_sheet.jsonl](evidence/sample_inspection_sheet.jsonl) (`15/15 N` + `15/15 K` = **`30/30` `human_verified = true`**; `29/29` `.mp3` files decode cleanly via `ffmpeg` 16kHz PCM, `#19` `7709372899198602514` confirmed as a no-audio slideshow promo, `10/10` ASR transcripts match Vietnamese F&B topics with minor loanword/dialect typos, `#13` flagged as mixed photo/food festival, and `#26` flagged as an out-of-domain museum vlog).
- **Phase 2/3 Hybrid `TikTokApi -> yt-dlp` & Live Comment Enrichment (`454` Comments Collected, `comment_coverage_rate = 0.9333`):** During the initial `yt-dlp` pilot run, `collected_comments_count` was `0` because `yt-dlp`'s TikTok extractor does not implement `_get_comments`. Phase 2 (`K`) integrated the `21KHDL-TikTok-Analytics` `TikTokApi` provider (`video.comments()` `/api/comment/list/`, `itemStruct` POI/EC/Ad mapping, `isPinnedItem` chronological loop, single-session Playwright reuse), and Phase 3 (`N` & `K`) added `--enrich-comments-only` (`BoundedIncrementalCollector.enrich_existing_comments` + minimal `aid=1988` `/api/comment/list/` signing fix for `TikTokApi 7.3.5`) and executed live desktop comment enrichment (`--backend tiktokapi --no-tiktok-headless`) across all `30` pilot videos (`30/30` succeeded, `0` failed, **`454` raw comments collected across `28/30` videos**, `comment_coverage_rate = 0.9333`, yielding **`452` unique `fact_comments.parquet` rows** in `m3_3_pilot_snapshot_v2` to unblock `M5.1` and `M5.2`).

## Work performed

- **Real-world TikTok `yt-dlp` hardening ([crawler_service.py](../../../../pipelines/crawl_incremental/crawler_service.py), [providers.py](../../../../pipelines/crawl_incremental/providers.py)):** Added `curl-cffi` TLS Chrome impersonation (`yt_dlp_impersonate_args()`), switched `download_audio_mp3_64k` to `-f best[vcodec=h264]/best[vcodec!=none]/best` so spoken creator audio downloads reliably instead of backing music / HTTP `403`, and interleaved multi-creator discovery round-robin across `<= 5` handles.
- **Phase 2 `21KHDL-TikTok-Analytics` hybrid upgrade ([mappers.py](../../../../pipelines/crawl_incremental/mappers.py), [providers.py](../../../../pipelines/crawl_incremental/providers.py), [worker.py](../../../../pipelines/crawl_incremental/worker.py)):** Added `map_tiktok_item_struct_to_detail`, `map_tiktok_comment_to_input` (preserving unstripped `text` for exact `M5.2` `NFC` offsets), `map_ytdlp_json_to_detail`, `TikTokApiCollectorProvider` (`isPinnedItem` skip + unpinned `cutoff_utc` break + cached `video.as_dict` + single reusable Playwright session), `AutoHybridTikTokCollectorProvider` (`--backend auto`), fail-closed `AntiBotChallengeError` across discovery/detail/comments/`.mp3` audio, multi-cookie (`sid_tt`/`sessionid_ss`/`uid_tt`/`ttwid`/`odin_tt`/`msToken`) & `--cookies` redaction, sanitized `raw_provider_payloads.jsonl` archiving, `select_curated_fnb_creators`, and `load_dotenv_if_present`.
- **Bounded CPU ASR & end-to-end M3.3 pilot runner ([asr.py](../../../../pipelines/pilot_m3_3/asr.py), [runner.py](../../../../pipelines/pilot_m3_3/runner.py), [models.py](../../../../pipelines/pilot_m3_3/models.py), [__main__.py](../../../../pipelines/pilot_m3_3/__main__.py)):** Enforces `M3.2` hard caps (`5` creators, `50` candidates, `30` succeeded, `60.0` audio min, `1,000` comments, `7,200`s deadline) and `M3.3` CPU ASR caps (`<= 10` videos / `<= 20.0` min, `ffmpeg` 16kHz PCM decode avoiding PyAV 19 `metadata_errors`), plus `--backend`, `--cookies-file`, `--tiktok-browser`, `--tiktok-headless` / `--no-tiktok-headless`, `--auto-creators`, non-colliding `--resume`, `--enrich-comments-only` (`run_m3_3_comment_enrichment`), and `--preflight-only`.

## Outputs

| File | Purpose |
| --- | --- |
| [m3_3_pilot_receipt.json](evidence/m3_3_pilot_receipt.json) | Official `live_pilot` Phase 3 receipt (`pilot_status = "PASS"`, `30` succeeded, `454` raw comments / `93.33%` coverage, `10` ASR `small` `RTF=0.1971`, `10/10` searchable, `2.84 GiB` enrichment peak RSS, `41.141 s` enrichment wall time, `120.01 MiB` total disk; Phase 1 `50 -> 30` capture & `744.154 s` metrics preserved in narrative and git `bde4017f`) |
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
| Official `live_pilot` across `5` F&B creators (`--asr-model small`) + desktop `TikTokApi` comment enrichment (`--enrich-comments-only`) | **PASS (`30/30` collected, `454` comments / `93.33%` coverage, `10/10` ASR searchable)** | `16.683` min audio in `197.269 s` (`RTF=0.1971`), `452` unique `fact_comments.parquet` rows in `m3_3_pilot_snapshot_v2`, `21,758` BM25 docs; [m3_3_pilot_receipt.json](evidence/m3_3_pilot_receipt.json) |
| `python3 -m pytest tests/unit/test_bounded_collector_worker.py tests/unit/test_m3_3_pilot_pipeline.py -v` | PASS (`32 passed`: `22` collector worker + `10` M3.3 pilot) | `h264` + `--impersonate chrome`, `21KHDL` `itemStruct`/comment/`yt-dlp` mappers, `isPinnedItem` loop, `video.as_dict` cache, single-session Playwright reuse, `--backend auto` fallback + circuit breaker, `--enrich-comments-only`, paginated `comment_id` deduplication, multi-creator round-robin, fail-closed `AntiBotChallengeError`, multi-cookie redaction, `--preflight-only`, and non-colliding `--resume` |
| `python3 -m mypy packages apps pipelines` & `python3 -m mypy --platform win32 packages apps pipelines` | PASS (`105` source files clean on Linux & `win32`) | Full static typing across Linux and Windows environments |
| `python3 -m pytest -q` & `python3 scripts/check_secrets.py` | PASS (`221 passed`; `0` secret leaks) | Full repository regression suite and secret hygiene |

## Open issues

| Issue | Impact | Follow-up / responsible task |
| --- | --- | --- |
| Two pilot videos (`7707183296874106119` with metadata `comment_count=0` and `7710598047721458945` returning `comments: null` from `/api/comment/list/`) have `0` comments while `28/30` videos yielded `454` raw comments (`452` unique rows in `fact_comments.parquet`) | `comment_coverage_rate = 0.9333` (`28/30` videos) exceeds the `150`–`300` comment pool needed by `M5.1` and the `120`–`200` unit pool across `>= 10` videos needed by `M5.2` | Export blinded `M5.1` and `M5.2` real pools from `data/corpus/m3_3_pilot_snapshot_v2` and proceed to `M3.G`, `M5.1`, and `M5.2` |
| Two creator posts (`#26` `7709375359300537601` museum vlog; `#13` `7710262606010846484` mixed photo/food festival) are non-pure F&B posts on F&B creator feeds | Observed naturally in creator-feed crawling; documented in `reviewer_notes` so downstream `M4.1` utterance selection can filter to pure F&B speech | Filter/record domain tags during `M4.1` utterance sampling |

## Acceptance and handoff

| Task criterion | Result | Evidence |
| --- | --- | --- |
| Bounded ceilings (`5` creators, `50` cands, `30` videos, `60`m audio, `1,000` comments, `2`h), hybrid `21KHDL` collector, & CPU ASR (`<= 10` videos / `<= 20`m) | Met (`30` succeeded, `29` `.mp3`, `454` comments, `10` ASR `small` `16.683` min `RTF=0.1971`, `32/32` collector/pilot tests) | [m3_3_pilot_receipt.json](evidence/m3_3_pilot_receipt.json), [providers.py](../../../../pipelines/crawl_incremental/providers.py) |
| Real non-synthetic receipts, coverage/failure rates, disk/RAM/time, repeatable `M3.1` Gold snapshot, and `>= 5` searchable real fresh videos | Met (`10/10` searchable in `bm25-m3_3-pilot`; `452` rows in `fact_comments.parquet`; `120.01 MiB` total disk; `2.84 GiB`–`3.14 GiB` peak RSS) | [m3_3_pilot_receipt.json](evidence/m3_3_pilot_receipt.json), [m3_3_pilot_snapshot_v2](../../../../data/corpus/m3_3_pilot_snapshot_v2/manifest.json) |
| Both contributors inspect half of the successful sample (`15 K / 15 N`) | **Met (`30/30` verified: `N = 15/15`, `K = 15/15`, `human_verified = true`)** | [sample_inspection_sheet.jsonl](evidence/sample_inspection_sheet.jsonl) |

Final task status: **`COMPLETE`** (all technical capture/ASR/comment/Gold/BM25/searchability criteria, `30/30` two-contributor sample inspection, and Phase 2/3 `21KHDL` hybrid collector + desktop comment enrichment satisfied; related gate **`G3` (`M3.G`) remains `NOT_RUN`** and receives `m3_3_pilot_receipt.json`, `sample_inspection_sheet.jsonl`, `m3_3_pilot_snapshot_v2` (`452` comments), and `comment_coverage_rate = 0.9333` as direct inputs).
