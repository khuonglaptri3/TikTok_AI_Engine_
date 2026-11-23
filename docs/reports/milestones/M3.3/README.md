# M3.3 — Capped Capture-to-Transcript-to-Search Pilot (`live_pilot = PASS`; Awaiting `K`/`N` 50/50 Human Inspection)

- Status: IN_PROGRESS (`live_pilot` capture -> `faster-whisper/small-cpu-int8` ASR -> `M3.1` Dual-Sink Gold -> `BM25Index` -> searchability **executed and passed** on real TikTok data: `30` fresh videos across `5` creators, `29` 64kbps `.mp3` files, `10` CPU-transcribed videos (`16.683` min, `RTF=0.1971`), **`10/10` searchable**, `195` repo tests + `100`-file `mypy`; awaiting only `K` (`15`) + `N` (`15`) manual verification in `sample_inspection_sheet.jsonl` to mark `COMPLETE`)
- Execution date: 2026-11-20 to 2026-11-23 (Asia/Ho_Chi_Minh)
- Requirement source: [TikTok_AI_Engine_Milestone.md](../../../planning/TikTok_AI_Engine_Milestone.md) (`M3.3`)
- Repository version: `main` (post-`3c325ff9` live pilot commit)
- Owners: Nguyễn Việt Nguyên (`N`) & Trần Đình Khương (`K`) (shared integration & 50/50 inspection)
- Specification: [spec.md](superpowers/spec.md)
- Execution plan: [plan.md](superpowers/plan.md)

## Conclusion

Executed the official bounded **`M3.3` `live_pilot`** pipeline ([m3_3_pilot_receipt.json](evidence/m3_3_pilot_receipt.json)) across **5 active Vietnamese F&B creators** (`ansapsaigon`, `tinhtungtangvn`, `dicungphuc`, `diadiemanuong`, `saigonmap` — `6` captured fresh videos per creator, `<= 120` days, protecting all `70,996` historical IDs):

- **Real Live Capture (`pilot_status = "PASS"`, `is_synthetic_fixture = false`):** Requested `50` candidates -> captured **`30/30` succeeded** (`0` failed, `20` skipped at ceiling, `capture_yield_rate = 0.60`), extracted **`29` 64kbps `.mp3`** audio files (`1` slideshow promo post `7709372899198602514` had no video audio track, cleanly skipped with `skipped_no_audio_count = 1`), `batch_disk_bytes = 22,646,824` (`21.60 MiB`).
- **Bounded CPU ASR (`faster-whisper/small-cpu-int8`):** Transcribed **`10/10`** videos (`16.683` audio minutes `<= 20.0` cap; remaining `19` capped via `skipped_asr_ceiling_count`) in **`197.269 s`** (`real_time_factor = 0.1971`, ASR peak RSS `1,009.46 MiB`, `0` failed).
- **Dual-Sink Gold Ingest (`M3.1`) & Searchability:** Published immutable Gold snapshot [m3_3_pilot_snapshot_v1](../../../../data/corpus/m3_3_pilot_snapshot_v1/manifest.json) (`58,965,140` B, preserving `20261118_taxonomy_fix_v1` untouched) and [bm25-m3_3-pilot](../../../../artifacts/indexes/bm25-m3_3-pilot/bm25-receipt.json) (`44,129,144` B, `21,758` total docs = `21,748` historical + `10` fresh transcribed). **`10/10` fresh transcribed videos retrieved with exact `video_id` matches.**
- **Total Pilot Resource Cost & 50/50 Split:** Whole run wall time `744.154 s` (`12.4` min), peak RSS `3,214.92 MiB` (`3.14 GiB <= 8 GiB`), total disk `125,741,108` B (`119.92 MiB`). Exported `30`-row [sample_inspection_sheet.jsonl](evidence/sample_inspection_sheet.jsonl) split `15 K / 15 N` (`human_verified = false` pending joint audit).
- **Honest Comment Collection Limitation Recorded:** `collected_comments_count = 0` (`comment_coverage_rate = 0.0`) because `yt-dlp 2026.10.26`'s TikTok extractor populates `comment_count` metadata but does not implement `_get_comments`. Per `M3.1` (`update_existing=True` keyed on `video_id` + `comment_id`), real comments can be enriched onto these exact `30` videos prior to `M5.1`/`M5.2`.

## Work performed

- **Real-world TikTok acquisition hardening ([crawler_service.py](../../../../pipelines/crawl_incremental/crawler_service.py), [providers.py](../../../../pipelines/crawl_incremental/providers.py)):** Added `curl-cffi` TLS Chrome impersonation (`yt_dlp_impersonate_args()`, fixing empty `JSONDecodeError` on creator discovery), switched `download_audio_mp3_64k` from `-f bestaudio/best` (which selected background `music.playUrl` / returned HTTP `403`) to `-f best[vcodec=h264]/best[vcodec!=none]/best` so spoken creator audio downloads reliably, and interleaved multi-creator discovery round-robin so every creator in `<= 5` handles is equally sampled (`6` videos each).
- **Bounded CPU ASR stage ([asr.py](../../../../pipelines/pilot_m3_3/asr.py)):** Added `CpuAsrEngine` protocol + fail-closed `FasterWhisperCpuAsrEngine` (`device="cpu"`, `compute_type="int8"`, `beam_size=1`, strict `0.0 <= start_sec < end_sec` invariant, `ffmpeg` 16kHz float32 PCM decoding avoiding `av>=19` `metadata_errors` incompatibility) and `BoundedCpuAsrRunner` capped at `<= 10` videos and `<= 20.0` audio minutes, reporting `real_time_factor` (`wall_sec / audio_sec`) and `peak_rss_mib` without fabricating transcripts when audio is absent.
- **End-to-end M3.3 pilot runner & CLI ([runner.py](../../../../pipelines/pilot_m3_3/runner.py), [models.py](../../../../pipelines/pilot_m3_3/models.py), [__main__.py](../../../../pipelines/pilot_m3_3/__main__.py)):** Enforces `M3.2` hard caps (`5` creators, `50` candidates, `30` succeeded, `60.0` audio min, `1,000` comments, `7,200`s deadline), automatically prepends `.venv/bin` (`_venv_search_path()`) so `yt-dlp`/`ffmpeg` resolve even when invoked via `.venv/bin/python`, separates `--mode dry_run_fixture` (`FIXTURE_DRY_RUN_ONLY`, `is_synthetic_fixture=True`) from `--mode live_pilot`, runs `ingest_incremental_batch_to_gold` into an isolated output snapshot, builds a fresh `BM25Index`, verifies exact source `video_id` searchability (`>= 5` required for `PASS`), measures disk bytes / peak RAM / wall time / yield & failure rates, and generates `sample_inspection_sheet.jsonl` split 50/50 between `K` and `N`.

## Outputs

| File | Purpose |
| --- | --- |
| [m3_3_pilot_receipt.json](evidence/m3_3_pilot_receipt.json) | Official `live_pilot` receipt (`pilot_status = "PASS"`, `30` succeeded, `10` ASR `small` `RTF=0.1971`, `10/10` searchable, `3.14 GiB` RAM, `119.92 MiB` disk) |
| [sample_inspection_sheet.jsonl](evidence/sample_inspection_sheet.jsonl) | `30`-video equal inspection workbook (`15` assigned to `K`, `15` assigned to `N`, `6` per creator) |
| [workflow.md](evidence/workflow.md) | `M3.3` Superpowers TDD ledger, real TikTok/PyAV fixes, host setup, and command verification receipts |
| [red-m3_3-tests.log](evidence/red-m3_3-tests.log), [green-m3_3-tests.log](evidence/green-m3_3-tests.log) | TDD RED (`ModuleNotFoundError`) -> GREEN (`7 passed in 1.69s`) logs |
| [pytest-full-m3_3.log](evidence/pytest-full-m3_3.log) | Full `195`-test pytest suite verification on `main` |

## How to set up and run

1. **Checkout `main` & provision host runtime (no `sudo` required):**

   ```bash
   git fetch origin && git checkout main
   .venv/bin/python -m pip install yt-dlp curl-cffi faster-whisper imageio-ffmpeg
   ln -sf "$(.venv/bin/python -c 'import imageio_ffmpeg; print(imageio_ffmpeg.get_ffmpeg_exe())')" .venv/bin/ffmpeg
   ```

2. **Verify tests & offline pipeline before live network access:**

   ```bash
   .venv/bin/python -m pytest tests/unit/test_m3_3_pilot_pipeline.py -v
   ```

3. **Run bounded `live_pilot` (up to `5` `--creator` flags, `<= 50` candidates / `<= 30` videos / `<= 60`m audio; CPU ASR capped at `<= 10` videos / `<= 20`m audio):**
   - Put `MS_TOKEN=...` in gitignored `.env` (ensure LF line endings or load via `_parse_dotenv`), then run:

   ```bash
   set -a && source .env && set +a
   PYTHONPATH=. .venv/bin/python -m pipelines.pilot_m3_3 \
     --mode live_pilot --allow-live-network \
     --creator ansapsaigon --creator tinhtungtangvn \
     --creator dicungphuc --creator diadiemanuong --creator saigonmap \
     --asr-model small
   ```

   - Outputs: receipt at `docs/reports/milestones/M3.3/evidence/m3_3_pilot_receipt.json`, Gold snapshot at `data/corpus/m3_3_pilot_snapshot_v1`, BM25 index at `artifacts/indexes/bm25-m3_3-pilot`, and 50/50 `K`/`N` inspection sheet at `docs/reports/milestones/M3.3/evidence/sample_inspection_sheet.jsonl`.

## Verification

| Check | Result | Scope / evidence |
| --- | --- | --- |
| Official `live_pilot` across `5` F&B creators (`--asr-model small`) | **PASS (`30/30` collected, `10/10` ASR searchable)** | `16.683` min audio in `197.269 s` (`RTF=0.1971`), `21,758` BM25 docs, `744.154 s` total, `3,214.92 MiB` RAM, `119.92 MiB` disk; [m3_3_pilot_receipt.json](evidence/m3_3_pilot_receipt.json) |
| `.venv/bin/python -m pytest tests/unit/test_m3_3_pilot_pipeline.py tests/unit/test_bounded_collector_worker.py -v` | PASS (`19 passed in 1.40s`; `7/7` M3.3 in `1.69s`) | ASR caps, fail-closed checks, `ffmpeg` 16kHz PCM decode, `.venv/bin` `PATH`, `h264` + `--impersonate chrome` regression, offline `dry_run_fixture`, fail-closed `BLOCKED`; [green-m3_3-tests.log](evidence/green-m3_3-tests.log) |
| `.venv/bin/python -m ruff check packages apps pipelines tests scripts` & `.venv/bin/python -m mypy packages apps pipelines` | PASS (`0` Ruff errors; `100/100` source files clean in `mypy`) | Code quality & full static typing |
| `.venv/bin/python -m pytest -v` & `python3 scripts/check_secrets.py` | PASS (`195 passed in 43.03s`; `0` secret leaks) | Full suite + secret hygiene; [pytest-full-m3_3.log](evidence/pytest-full-m3_3.log) |

## Open issues

| Issue | Impact | Follow-up / responsible task |
| --- | --- | --- |
| `K` & `N` 50/50 inspection (`15 K / 15 N`) in [sample_inspection_sheet.jsonl](evidence/sample_inspection_sheet.jsonl) pending (`human_verified=false`) | Required to flip `M3.3` -> `COMPLETE` and evaluate Gate `G3` (`M3.G`) | `K` inspects the `15` `K` rows and `N` inspects the `15` `N` rows (audio + transcript sanity) |
| `yt-dlp` does not retrieve TikTok comments (`collected_comments_count=0`, `comment_coverage_rate=0.0`) | Audio/transcript/search milestones (`M3.3`, `M3.G`, `M4.1`) are unblocked; `M5.1`/`M5.2` real-comment double-annotation requires separate comment enrichment keyed on these `30` `video_id`s via `M3.1` (`update_existing=True`) | Add dedicated comment collector enrichment step before `M5.1`/`M5.2` real-pool evaluation |

## Acceptance and handoff

| Task criterion | Result | Evidence |
| --- | --- | --- |
| Bounded ceilings (`5` creators, `50` cands, `30` videos, `60`m audio, `1,000` comments, `2`h) & CPU ASR (`<= 10` videos / `<= 20`m) | Met (`30` succeeded, `29` `.mp3`, `10` ASR `small` `16.683` min `RTF=0.1971`) | [m3_3_pilot_receipt.json](evidence/m3_3_pilot_receipt.json) |
| Real non-synthetic receipts, coverage/failure rates, disk/RAM/time, repeatable `M3.1` Gold snapshot, and `>= 5` searchable real fresh videos | Met (`10/10` searchable in `bm25-m3_3-pilot`; `119.92 MiB` total disk; `3.14 GiB` peak RSS) | [m3_3_pilot_receipt.json](evidence/m3_3_pilot_receipt.json), [m3_3_pilot_snapshot_v1](../../../../data/corpus/m3_3_pilot_snapshot_v1/manifest.json) |
| Both contributors inspect half of the successful sample (`15 K / 15 N`) | Pending (`sample_inspection_sheet.jsonl` exported `15/15`, `human_verified=false`) | [sample_inspection_sheet.jsonl](evidence/sample_inspection_sheet.jsonl) |

Final task status: **`IN_PROGRESS`** (all technical/capture/ASR/Gold/BM25/searchability acceptance checks **PASSED** on real TikTok data in `m3_3_pilot_receipt.json`; awaiting only `K` + `N` 50/50 human verification of `sample_inspection_sheet.jsonl` to mark `COMPLETE` and proceed to `M3.G` / `G3`).
