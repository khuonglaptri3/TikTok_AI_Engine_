# M3.3 — Capped Capture-to-Transcript-to-Search Pilot & Hybrid `21KHDL-TikTok-Analytics` Collector Upgrade

- Status: IN_PROGRESS (Phase 1 end-to-end `pipelines/pilot_m3_3/` capture -> CPU ASR -> Dual-Sink Gold -> BM25 -> searchability orchestrator + host `.venv` `yt-dlp`/`ffmpeg`/`faster-whisper` verification complete; Phase 2 hybrid `TikTokApi -> yt-dlp` `--backend auto` upgrade grounded in `TrggTin/21KHDL-TikTok-Analytics`, authenticated `64 kbps` `.mp3` extraction, `--auto-creators`, `--resume`, and `--preflight-only` verified across `205` pytest tests and `101`-file Linux/`win32` `mypy`; live network run awaits home execution with `MS_TOKEN` and `K`+`N` 50/50 inspection)
- Execution date: 2026-11-23 (Asia/Ho_Chi_Minh; Phase 1 baseline 2026-11-20)
- Requirement source: [TikTok_AI_Engine_Milestone.md](../../../planning/TikTok_AI_Engine_Milestone.md) (`M3.3`)
- Repository version: branch `feat/k-m3.3-hybrid-crawler-upgrade` (forked from `main` @ `60b80147`)
- Owners: Nguyễn Việt Nguyên (`N`) & Trần Đình Khương (`K`) (shared integration & 50/50 inspection)
- Specification: [spec.md](superpowers/spec.md)
- Execution plan: [plan.md](superpowers/plan.md)

## Conclusion

Built, tested, and host-verified the bounded end-to-end `M3.3` orchestrator in [pipelines/pilot_m3_3/](../../../../pipelines/pilot_m3_3/) (`models.py`, `asr.py`, `runner.py`, `__main__.py`) and upgraded the incremental collector in [pipelines/crawl_incremental/](../../../../pipelines/crawl_incremental/) (`mappers.py`, `providers.py`, `worker.py`, `crawler_service.py`, `__main__.py`) by directly adapting the verified crawling mechanics of [`TrggTin/21KHDL-TikTok-Analytics`](https://github.com/TrggTin/21KHDL-TikTok-Analytics) (`f142e5656a220f94f8024de168b0832754b3bd9e`) into a safe, resumable, turnkey home-crawling workflow.

- **Phase 2 Hybrid Collector Upgrade (`feat/k-m3.3-hybrid-crawler-upgrade`, authored by `K`):**
  - **`21KHDL-TikTok-Analytics` Mechanics Integrated ([mappers.py](../../../../pipelines/crawl_incremental/mappers.py), [providers.py](../../../../pipelines/crawl_incremental/providers.py)):** Adapted full `itemStruct` field extraction (`poi.{id, name, address, city, ttTypeNameTiny}`, `isAd`, `isECVideo`, `playlistId`, `statsV2.collectCount`, `authorStats.followerCount`, `challenges`/`textExtra` hashtags), the `crawler.py:97-118` `isPinnedItem` skip + unpinned reverse-chronological early `break` against `cutoff_utc`, zero-extra-HTTP `video.as_dict` caching during profile discovery, top-level `/api/comment/list/` comment pagination (`reply_comment_total -> reply_count`, preserving raw unstripped `text` for exact `M5.2` `NFC` span offsets), sanitized `raw_provider_payloads.jsonl` archiving (`VQScore`, `volumeInfo`, `collectTime`), and `author_unique_ids.txt` + Chapter 3 (`median_play_count >= 40,000`, `median_engagement_rate >= 0.03`) F&B creator selection.
  - **Pluggable `--backend auto` (`TikTokApi` -> `yt-dlp` Fallback) & Fail-Closed Anti-Bot Gate ([providers.py](../../../../pipelines/crawl_incremental/providers.py), [worker.py](../../../../pipelines/crawl_incremental/worker.py)):** Prefers official `TikTokApi` when installed on the home PC and falls back automatically to authenticated `yt-dlp` (`Cookie: msToken=...` + optional `--cookies` forwarded to discovery, detail, comments, AND `64 kbps` `.mp3` extraction with cross-platform UTF-8 subprocess safety). Any CAPTCHA or human-verification gate raises `AntiBotChallengeError` and halts immediately (`attempts=1`, `stopped_reason="anti_bot_challenge_blocked"`) with zero fallback bypass and full credential/path redaction.
  - **Turnkey Home CLI Controls ([runner.py](../../../../pipelines/pilot_m3_3/runner.py), [__main__.py](../../../../pipelines/pilot_m3_3/__main__.py)):** Auto-loads gitignored `.env` (`MS_TOKEN` or legacy `ms_token`, `TIKTOK_COOKIES_FILE`, `TIKTOK_BROWSER`, `TIKTOK_HEADLESS`), supports `--auto-creators 5`, forwards `--resume` into `BoundedIncrementalCollector.run(...)`, and adds `--preflight-only` (0 network calls) to verify home readiness before live crawling.
- **Phase 1 Host Tools & Real Audio Baseline Preserved:** Host `.venv` `yt-dlp`, `ffmpeg` (`imageio-ffmpeg` 16kHz PCM workaround for PyAV 19), and `faster-whisper` CPU int8 ASR (`RTF=0.1278`, `445.49 MiB` peak RSS on real Vietnamese `.mp3` audio) verified with `0` secret leaks.

## Work performed

- **Unified `21KHDL` & `yt-dlp` schema mappers ([mappers.py](../../../../pipelines/crawl_incremental/mappers.py)):** Added `map_tiktok_item_struct_to_detail`, `map_tiktok_comment_to_input`, `map_ytdlp_json_to_detail`, and `parse_timestamp_to_iso_utc`.
- **Hybrid live providers, raw payload sanitization & fail-closed anti-bot gate ([providers.py](../../../../pipelines/crawl_incremental/providers.py), [worker.py](../../../../pipelines/crawl_incremental/worker.py), [crawler_service.py](../../../../pipelines/crawl_incremental/crawler_service.py)):** Added `TikTokApiCollectorProvider`, `AutoHybridTikTokCollectorProvider`, `build_live_collector_provider`, `AntiBotChallengeError`, authenticated UTF-8 `download_audio_mp3_64k`, `load_dotenv_if_present`, `select_curated_fnb_creators`, and recursive cookie/header redaction on `raw_provider_payloads.jsonl` and `CollectorItemReceipt.reason`.
- **Bounded CPU ASR & end-to-end M3.3 pilot runner ([asr.py](../../../../pipelines/pilot_m3_3/asr.py), [runner.py](../../../../pipelines/pilot_m3_3/runner.py), [models.py](../../../../pipelines/pilot_m3_3/models.py), [__main__.py](../../../../pipelines/pilot_m3_3/__main__.py)):** Wired `M33PreflightReport` (`run_m3_3_preflight`), `--backend {auto,tiktokapi,ytdlp}`, `--cookies-file`, `--tiktok-browser`, `--tiktok-headless` / `--no-tiktok-headless`, `--auto-creators`, `--resume`, and `--preflight-only`, while preserving hard ceilings (`<= 5` creators, `<= 50` candidates, `<= 30` videos, `<= 60.0` audio minutes, `<= 10` ASR videos / `<= 20.0` ASR audio minutes, `70,996` protected historical IDs).

## Outputs

| File | Purpose |
| --- | --- |
| [workflow.md](evidence/workflow.md) | `M3.3` Phase 1 & Phase 2 Superpowers TDD ledger, upstream `21KHDL` audit notes, rulings, and verification receipts |
| [red-m3_3-tests.log](evidence/red-m3_3-tests.log), [green-m3_3-tests.log](evidence/green-m3_3-tests.log) | Phase 1 TDD RED -> GREEN logs for `pipelines/pilot_m3_3/` |
| [m3_3_live_preflight_receipt.json](evidence/m3_3_live_preflight_receipt.json) | Honest `live_pilot` fail-closed receipt (`pilot_status = "BLOCKED"` when `MS_TOKEN` is absent) |
| [pytest-full-m3_3.log](evidence/pytest-full-m3_3.log) | Workspace pytest verification receipt |

## Run at Home Guide (Step-by-Step)

1. **Provision Python runtime tools (no `sudo` required):**
   - **Quick mode (`yt-dlp` + `ffmpeg` + `faster-whisper` only):**
     ```bash
     uv pip install --python .venv/bin/python yt-dlp faster-whisper imageio-ffmpeg
     ln -sf "$(.venv/bin/python -c 'import imageio_ffmpeg; print(imageio_ffmpeg.get_ffmpeg_exe())')" .venv/bin/ffmpeg
     ```
   - **Recommended enriched mode (`TikTokApi` + Playwright Chromium for full `itemStruct` POI/EC/Ad/comments, with automatic `yt-dlp` fallback):**
     ```bash
     uv pip install --python .venv/bin/python TikTokApi playwright yt-dlp faster-whisper imageio-ffmpeg
     ln -sf "$(.venv/bin/python -c 'import imageio_ffmpeg; print(imageio_ffmpeg.get_ffmpeg_exe())')" .venv/bin/ffmpeg
     .venv/bin/playwright install chromium
     ```
     *(On Windows PowerShell without system `ffmpeg`: `Copy-Item (.\.venv\Scripts\python.exe -c "import imageio_ffmpeg; print(imageio_ffmpeg.get_ffmpeg_exe())") .\.venv\Scripts\ffmpeg.exe` and replace `.venv/bin/python` with `.\.venv\Scripts\python.exe` below.)*

2. **Add `MS_TOKEN` to gitignored `.env` (auto-loaded by CLI — no manual `source .env` needed):**
   - Open `https://www.tiktok.com` in your desktop browser, inspect Cookies in DevTools (`Application -> Cookies`), copy `msToken`, and set in `.env`:
     ```dotenv
     MS_TOKEN=<paste_your_msToken_here>
     # Optional: Netscape cookies.txt exported from browser if TikTok restricts audio/comments
     TIKTOK_COOKIES_FILE=
     TIKTOK_BROWSER=chromium
     TIKTOK_HEADLESS=true
     ```

3. **Run zero-network preflight check (`--preflight-only`) before crawling:**
   ```bash
   .venv/bin/python -m pipelines.pilot_m3_3 \
     --mode live_pilot --allow-live-network \
     --backend auto --auto-creators 5 \
     --preflight-only
   ```
   Confirm `"ready_for_live_pilot": true`, `"ms_token_present": true`, `"historical_protected_count": 70996`, and `"selected_creators"` lists the 5 curated F&B creators (`spicykim9386`, `haidangrevieww`, `khaikhampha`, `putaangi`, `trangtam2607`).

4. **Execute bounded `M3.3` live pilot at home (`<= 5` creators, `<= 30` fresh videos, `<= 10` CPU ASR videos / `<= 20` min):**
   ```bash
   .venv/bin/python -m pipelines.pilot_m3_3 \
     --mode live_pilot --allow-live-network \
     --backend auto --auto-creators 5 \
     --asr-model small
   ```
   - **Desktop tip (`21KHDL` `tiktok.py:490`):** If headless Chromium triggers `EmptyResponseException`, append `--no-tiktok-headless` so Playwright opens a visible browser window, or pass `--backend ytdlp` to use `yt-dlp` directly.
   - **Crash / interruption recovery:** Re-run the exact command above with `--resume` appended; already-succeeded videos in `data/raw_incremental/m3_3_pilot_run/batch/collector_checkpoint.json` are skipped without re-downloading, and if `data/corpus/m3_3_pilot_snapshot_v1` already exists from a partial run, `--resume` automatically allocates `m3_3_pilot_snapshot_v1_resume_1` without mutating prior snapshots.
   - **Anti-bot / CAPTCHA policy:** If TikTok presents a CAPTCHA challenge, the collector halts immediately (`stopped_reason="anti_bot_challenge_blocked"`). Wait, refresh `MS_TOKEN` from a normal browser session, and resume later with `--resume`.

5. **Inspect outputs & run secret check before committing results:**
   - Receipt: `docs/reports/milestones/M3.3/evidence/m3_3_pilot_receipt.json`
   - 50/50 `K`/`N` inspection sheet: `docs/reports/milestones/M3.3/evidence/sample_inspection_sheet.jsonl`
   - Raw `itemStruct` archive (gitignored under `data/raw_incremental/`): `data/raw_incremental/m3_3_pilot_run/batch/raw_provider_payloads.jsonl`
   - Run `python3 scripts/check_secrets.py` (`0` leaks required).

## Verification

| Check | Result | Scope / evidence |
| --- | --- | --- |
| `python3 -m pytest tests/unit/test_bounded_collector_worker.py tests/unit/test_m3_3_pilot_pipeline.py -v` | PASS (`29 passed`: `21` collector worker + `8` M3.3 pilot) | `21KHDL` `itemStruct`/comment/`yt-dlp` mappers, `isPinnedItem` chronological loop, `video.as_dict` cache, single-session Playwright reuse, `--backend auto` single-call fallback + circuit breaker, multi-creator round-robin balancing, fail-closed `AntiBotChallengeError` across discovery/detail/comments/`.mp3` audio, multi-cookie (`sid_tt`/`sessionid_ss`/`msToken`) & `--cookies` redaction, `.env` `ms_token` + inline `#` comment handling, `--auto-creators`, `--preflight-only`, and non-colliding `--resume` |
| `python3 -m mypy packages apps pipelines` & `python3 -m mypy --platform win32 packages apps pipelines` | PASS (`101` source files clean on Linux & `win32`) | Static typing across Linux and Windows home environments |
| `python3 -m pytest -v` & `python3 scripts/check_secrets.py` | PASS (`205 passed`; `0` secret leaks) | Full repository regression suite and secret hygiene |
| Host real audio test (`FasterWhisperCpuAsrEngine(model_size="tiny", language="vi")`) | PASS (`failed_count=0`, `RTF=0.1278`) | Verified on temporary 64k `.mp3` copy (`1.0` min, `6` segments, `7.671s` wall, `445.49 MiB` peak RSS; `data/` untouched) |

## Open issues

| Issue | Impact | Follow-up / responsible task |
| --- | --- | --- |
| Live TikTok session requires home network + fresh `MS_TOKEN` in gitignored `.env` | `M3.3` remains `IN_PROGRESS` until live pilot produces `>= 5` real fresh searchable transcribed videos | Contributor `K` runs Step 3 (`--preflight-only`) and Step 4 (`--mode live_pilot --allow-live-network --backend auto --auto-creators 5`) at home |
| `K` & `N` 50/50 inspection of real captured videos pending live run | Required before `M3.3` acceptance and Gate `G3` (`M3.G`) | Both inspect their assigned 50% rows in `sample_inspection_sheet.jsonl` after the home crawl |

## Acceptance and handoff

| Task criterion | Result | Evidence |
| --- | --- | --- |
| Bounded ceilings (`5` creators, `50` cands, `30` videos, `60`m audio, `1,000` comments, `2`h), hybrid `21KHDL` `TikTokApi -> yt-dlp` collector, & CPU ASR (`<= 10` videos / `<= 20`m) wired + verified | Met (`29/29` dedicated tests + `205/205` full suite + `101`-file Linux/`win32` `mypy`) | [mappers.py](../../../../pipelines/crawl_incremental/mappers.py), [providers.py](../../../../pipelines/crawl_incremental/providers.py), [worker.py](../../../../pipelines/crawl_incremental/worker.py), [runner.py](../../../../pipelines/pilot_m3_3/runner.py) |
| Real non-synthetic receipts, disk/RAM/time, `>= 5` searchable real fresh videos, and 50/50 `K`/`N` inspection | Pending home live capture with `MS_TOKEN` | [m3_3_live_preflight_receipt.json](evidence/m3_3_live_preflight_receipt.json) |

Final task status: **`IN_PROGRESS`** (Phase 1 end-to-end ASR/Gold/BM25 pipeline and Phase 2 `21KHDL-TikTok-Analytics` hybrid `--backend auto` collector upgrade complete and verified; turnkey for contributor `K`'s home crawling session).
