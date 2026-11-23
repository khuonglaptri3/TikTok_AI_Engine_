# M3.3 — Capped Capture-to-Transcript-to-Search Pilot (`live_pilot = PASS`, `N` `15/15` Verified) & Hybrid `21KHDL-TikTok-Analytics` Collector Upgrade

- Status: IN_PROGRESS (`live_pilot` capture -> `faster-whisper/small-cpu-int8` ASR -> `M3.1` Dual-Sink Gold -> `BM25Index` -> searchability **executed and passed** on real TikTok data: `30` fresh videos across `5` creators, `29` 64kbps `.mp3` files, `10` CPU-transcribed videos (`16.683` min, `RTF=0.1971`), **`10/10` searchable**, **`N` completed `15/15` audio + transcript inspection** (`human_verified=true`), combined with Phase 2 `21KHDL-TikTok-Analytics` hybrid `TikTokApi -> yt-dlp` `--backend auto` upgrade across `218` repo tests + `105`-file Linux/`win32` `mypy`; awaiting only `K` (`15/15`) manual verification in `sample_inspection_sheet.jsonl` to mark `COMPLETE`)
- Execution date: 2026-11-20 to 2026-11-23 (Asia/Ho_Chi_Minh)
- Requirement source: [TikTok_AI_Engine_Milestone.md](../../../planning/TikTok_AI_Engine_Milestone.md) (`M3.3`)
- Repository version: `main` (integrating PR #7 live pilot results + PR #8 hybrid collector upgrade)
- Owners: Nguyễn Việt Nguyên (`N`) & Trần Đình Khương (`K`) (shared integration & 50/50 inspection)
- Specification: [spec.md](superpowers/spec.md)
- Execution plan: [plan.md](superpowers/plan.md)

## Conclusion

Executed the official bounded **`M3.3` `live_pilot`** pipeline ([m3_3_pilot_receipt.json](evidence/m3_3_pilot_receipt.json)) across **5 active Vietnamese F&B creators** (`ansapsaigon`, `tinhtungtangvn`, `dicungphuc`, `diadiemanuong`, `saigonmap` — `6` captured fresh videos per creator, `<= 120` days, protecting all `70,996` historical IDs) and integrated the Phase 2 [`TrggTin/21KHDL-TikTok-Analytics`](https://github.com/TrggTin/21KHDL-TikTok-Analytics) (`f142e5656a220f94f8024de168b0832754b3bd9e`) hybrid collector (`--backend auto`):

- **Real Live Capture (`pilot_status = "PASS"`, `is_synthetic_fixture = false`):** Requested `50` candidates -> captured **`30/30` succeeded** (`0` failed, `20` skipped at ceiling, `capture_yield_rate = 0.60`), extracted **`29` 64kbps `.mp3`** audio files (`1` slideshow promo post `7709372899198602514` had no video audio track, cleanly skipped with `skipped_no_audio_count = 1`), `batch_disk_bytes = 22,646,824` (`21.60 MiB`).
- **Bounded CPU ASR (`faster-whisper/small-cpu-int8`):** Transcribed **`10/10`** videos (`16.683` audio minutes `<= 20.0` cap; remaining `19` capped via `skipped_asr_ceiling_count`) in **`197.269 s`** (`real_time_factor = 0.1971`, ASR peak RSS `1,009.46 MiB`, `0` failed).
- **Dual-Sink Gold Ingest (`M3.1`) & Searchability:** Published immutable Gold snapshot [m3_3_pilot_snapshot_v1](../../../../data/corpus/m3_3_pilot_snapshot_v1/manifest.json) (`58,965,140` B, preserving `20261118_taxonomy_fix_v1` untouched) and [bm25-m3_3-pilot](../../../../artifacts/indexes/bm25-m3_3-pilot/bm25-receipt.json) (`44,129,144` B, `21,758` total docs = `21,748` historical + `10` fresh transcribed). **`10/10` fresh transcribed videos retrieved with exact `video_id` matches.**
- **Total Pilot Resource Cost & 50/50 Split:** Whole run wall time `744.154 s` (`12.4` min), peak RSS `3,214.92 MiB` (`3.14 GiB <= 8 GiB`), total disk `125,741,108` B (`119.92 MiB`). Exported `30`-row [sample_inspection_sheet.jsonl](evidence/sample_inspection_sheet.jsonl) split `15 K / 15 N` (`human_verified = false` pending joint audit).
- **Honest Comment Limitation & Phase 2 Hybrid `TikTokApi -> yt-dlp` Upgrade:** During the `yt-dlp` pilot run, `collected_comments_count = 0` (`comment_coverage_rate = 0.0`) because `yt-dlp 2026.10.26`'s TikTok extractor does not implement `_get_comments`. Phase 2 (`K`) integrates the `21KHDL-TikTok-Analytics` `TikTokApi` provider (`video.comments()` `/api/comment/list/`, `itemStruct` POI/EC/Ad mapping, `isPinnedItem` chronological loop, single-session Playwright reuse, automatic `yt-dlp` fallback, authenticated `.mp3`, `--auto-creators`, `--resume`, and `--preflight-only`) so real comments can be collected and enriched onto `m3_3_pilot_snapshot_v1` via `M3.1` (`update_existing=True`) for `M5.1`/`M5.2`.

## Work performed

- **Real-world TikTok `yt-dlp` hardening ([crawler_service.py](../../../../pipelines/crawl_incremental/crawler_service.py), [providers.py](../../../../pipelines/crawl_incremental/providers.py)):** Added `curl-cffi` TLS Chrome impersonation (`yt_dlp_impersonate_args()`), switched `download_audio_mp3_64k` to `-f best[vcodec=h264]/best[vcodec!=none]/best` so spoken creator audio downloads reliably instead of backing music / HTTP `403`, and interleaved multi-creator discovery round-robin across `<= 5` handles.
- **Phase 2 `21KHDL-TikTok-Analytics` hybrid upgrade ([mappers.py](../../../../pipelines/crawl_incremental/mappers.py), [providers.py](../../../../pipelines/crawl_incremental/providers.py), [worker.py](../../../../pipelines/crawl_incremental/worker.py)):** Added `map_tiktok_item_struct_to_detail`, `map_tiktok_comment_to_input` (preserving unstripped `text` for exact `M5.2` `NFC` offsets), `map_ytdlp_json_to_detail`, `TikTokApiCollectorProvider` (`isPinnedItem` skip + unpinned `cutoff_utc` break + cached `video.as_dict` + single reusable Playwright session), `AutoHybridTikTokCollectorProvider` (`--backend auto`), fail-closed `AntiBotChallengeError` across discovery/detail/comments/`.mp3` audio, multi-cookie (`sid_tt`/`sessionid_ss`/`uid_tt`/`ttwid`/`odin_tt`/`msToken`) & `--cookies` redaction, sanitized `raw_provider_payloads.jsonl` archiving, `select_curated_fnb_creators`, and `load_dotenv_if_present`.
- **Bounded CPU ASR & end-to-end M3.3 pilot runner ([asr.py](../../../../pipelines/pilot_m3_3/asr.py), [runner.py](../../../../pipelines/pilot_m3_3/runner.py), [models.py](../../../../pipelines/pilot_m3_3/models.py), [__main__.py](../../../../pipelines/pilot_m3_3/__main__.py)):** Enforces `M3.2` hard caps (`5` creators, `50` candidates, `30` succeeded, `60.0` audio min, `1,000` comments, `7,200`s deadline) and `M3.3` CPU ASR caps (`<= 10` videos / `<= 20.0` min, `ffmpeg` 16kHz PCM decode avoiding PyAV 19 `metadata_errors`), plus `--backend`, `--cookies-file`, `--tiktok-browser`, `--tiktok-headless` / `--no-tiktok-headless`, `--auto-creators`, non-colliding `--resume`, and `--preflight-only`.

## Outputs

| File | Purpose |
| --- | --- |
| [m3_3_pilot_receipt.json](evidence/m3_3_pilot_receipt.json) | Official `live_pilot` receipt (`pilot_status = "PASS"`, `30` succeeded, `10` ASR `small` `RTF=0.1971`, `10/10` searchable, `3.14 GiB` RAM, `119.92 MiB` disk) |
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
| Official `live_pilot` across `5` F&B creators (`--asr-model small`) | **PASS (`30/30` collected, `10/10` ASR searchable)** | `16.683` min audio in `197.269 s` (`RTF=0.1971`), `21,758` BM25 docs, `744.154 s` total, `3,214.92 MiB` RAM, `119.92 MiB` disk; [m3_3_pilot_receipt.json](evidence/m3_3_pilot_receipt.json) |
| `python3 -m pytest tests/unit/test_bounded_collector_worker.py tests/unit/test_m3_3_pilot_pipeline.py -v` | PASS (`30 passed`: `21` collector worker + `9` M3.3 pilot) | `h264` + `--impersonate chrome`, `21KHDL` `itemStruct`/comment/`yt-dlp` mappers, `isPinnedItem` loop, `video.as_dict` cache, single-session Playwright reuse, `--backend auto` fallback + circuit breaker, multi-creator round-robin, fail-closed `AntiBotChallengeError`, multi-cookie redaction, `--preflight-only`, and non-colliding `--resume` |
| `python3 -m mypy packages apps pipelines` & `python3 -m mypy --platform win32 packages apps pipelines` | PASS (`105` source files clean on Linux & `win32`) | Full static typing across Linux and Windows environments |
| `python3 -m pytest -q` & `python3 scripts/check_secrets.py` | PASS (`218 passed`; `0` secret leaks) | Full repository regression suite and secret hygiene |

## Open issues

| Issue | Impact | Follow-up / responsible task |
| --- | --- | --- |
| `K` half (`15/15` `K` rows) in [sample_inspection_sheet.jsonl](evidence/sample_inspection_sheet.jsonl) pending (`N` completed `15/15`, `human_verified=true`) | Required to flip `M3.3` -> `COMPLETE` and evaluate Gate `G3` (`M3.G`) | `K` inspects the `15` `K` rows (note: `N` confirmed `15/15` valid `64 kb/s` `.mp3` streams, `5/5` topic/timestamp alignment with minor loanword/street-name ASR typos, and flagged `#26` `7709375359300537601` as an out-of-domain museum vlog) |
| Initial `yt-dlp` pilot batch has `collected_comments_count=0` (`comment_coverage_rate=0.0`) | Audio/transcript/search milestones (`M3.3`, `M3.G`, `M4.1`) are unblocked; `M5.1`/`M5.2` real-comment double-annotation requires comment enrichment keyed on these `30` `video_id`s via `M3.1` (`update_existing=True`) | Use the integrated `TikTokApiCollectorProvider` (`--backend tiktokapi` / `auto`) on a desktop session with `MS_TOKEN` to enrich real comments prior to `M5.1`/`M5.2` evaluation |

## Acceptance and handoff

| Task criterion | Result | Evidence |
| --- | --- | --- |
| Bounded ceilings (`5` creators, `50` cands, `30` videos, `60`m audio, `1,000` comments, `2`h), hybrid `21KHDL` collector, & CPU ASR (`<= 10` videos / `<= 20`m) | Met (`30` succeeded, `29` `.mp3`, `10` ASR `small` `16.683` min `RTF=0.1971`, `30/30` collector/pilot tests) | [m3_3_pilot_receipt.json](evidence/m3_3_pilot_receipt.json), [providers.py](../../../../pipelines/crawl_incremental/providers.py) |
| Real non-synthetic receipts, coverage/failure rates, disk/RAM/time, repeatable `M3.1` Gold snapshot, and `>= 5` searchable real fresh videos | Met (`10/10` searchable in `bm25-m3_3-pilot`; `119.92 MiB` total disk; `3.14 GiB` peak RSS) | [m3_3_pilot_receipt.json](evidence/m3_3_pilot_receipt.json), [m3_3_pilot_snapshot_v1](../../../../data/corpus/m3_3_pilot_snapshot_v1/manifest.json) |
| Both contributors inspect half of the successful sample (`15 K / 15 N`) | **Partial (`N = 15/15 verified`; `K = 0/15 pending`)** | [sample_inspection_sheet.jsonl](evidence/sample_inspection_sheet.jsonl) |

Final task status: **`IN_PROGRESS`** (all technical/capture/ASR/Gold/BM25/searchability checks **PASSED** on real TikTok data in `m3_3_pilot_receipt.json`, `N` completed `15/15` inspection, and Phase 2 hybrid `TikTokApi -> yt-dlp` collector integrated (`218` tests, `105`-file `mypy`); awaiting only `K` `15/15` verification of `sample_inspection_sheet.jsonl` to mark `COMPLETE` and proceed to `M3.G` / `G3`).
