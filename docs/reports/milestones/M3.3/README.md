# M3.3 — Capped Capture-to-Transcript-to-Search Pilot (Pipeline + Host Tools/CPU ASR Verified; Live Acquisition Blocked Only on `MS_TOKEN`)

- Status: IN_PROGRESS (`pipelines/pilot_m3_3/` capture -> CPU ASR -> Dual-Sink Gold -> BM25 -> searchability orchestrator, `6/6` TDD tests, `183`-test full suite, `100`-file strict `mypy`, and host `.venv` `yt-dlp` / `ffmpeg` / `faster-whisper` CPU ASR verification complete on `feat/m3.3-pilot-scaffolding`; live network pilot awaits `MS_TOKEN` in `.env`, creator handle confirmation, and `K`+`N` 50/50 inspection)
- Execution date: 2026-11-20 (Asia/Ho_Chi_Minh)
- Requirement source: [TikTok_AI_Engine_Milestone.md](../../../planning/TikTok_AI_Engine_Milestone.md) (`M3.3`)
- Repository version: branch `feat/m3.3-pilot-scaffolding` (from `main` @ `847ffcb4`)
- Owners: Nguyễn Việt Nguyên (`N`) & Trần Đình Khương (`K`) (shared integration & 50/50 inspection)
- Specification: [spec.md](superpowers/spec.md)
- Execution plan: [plan.md](superpowers/plan.md)

## Conclusion

Built, tested, and host-verified the bounded end-to-end `M3.3` orchestrator in [pipelines/pilot_m3_3/](../../../../pipelines/pilot_m3_3/) (`models.py`, `asr.py`, `runner.py`, `__main__.py`), connecting `M3.2` incremental collection -> bounded CPU ASR (`<= 10` videos / `<= 20.0` audio minutes, `FasterWhisperCpuAsrEngine` int8 CPU + `real_time_factor` / `peak_rss_mib` tracking) -> `M3.1` Dual-Sink Gold ingestion -> `BM25Index` build -> fresh-video `HybridRetrievalService` searchability verification -> 50/50 `K`/`N` inspection sheet export.

- **Host Tools Provisioned & Real Audio Verified (`feat/m3.3-pilot-scaffolding`):** Installed `yt-dlp==2026.10.26`, `faster-whisper==1.2.1`, `ctranslate2==4.9.0`, `av==19.0.2`, and `imageio-ffmpeg==0.8.1` (`n9.0.2`, symlinked at `.venv/bin/ffmpeg`) without `sudo`. Fixed a real PyAV host compatibility bug (`av==19.0.2` raising `TypeError: metadata_errors` inside `faster_whisper` 1.2.1) by decoding via `ffmpeg` 16kHz PCM inside `FasterWhisperCpuAsrEngine._decode_audio_16k_mono` and prepending `.venv/bin` to `PATH` via `_venv_search_path()`. Verified on a temporary 64kbps `.mp3` copy of `happipham_7464081161812233490.m4a`: `transcribed_count=1`, `failed_count=0`, `6` Vietnamese segments, `wall_seconds=7.671s`, `real_time_factor=0.1278`, `peak_rss_mib=445.49 MiB`.
- **TDD & Full Suite Verification (`feat/m3.3-pilot-scaffolding`):** `6/6` dedicated tests in [test_m3_3_pilot_pipeline.py](../../../../tests/unit/test_m3_3_pilot_pipeline.py) (`1.31s`), `183/183` full workspace pytest suite (`28.39s`), `100/100`-file `mypy`, `ruff check`, and `scripts/check_secrets.py` (`0` leaks) all pass.
- **Honest Live Preflight (`m3_3_live_preflight_receipt.json`):** Re-running `python3 -m pipelines.pilot_m3_3 --mode live_pilot --allow-live-network --creator ansapsaigon` on this Linux host fails closed with `pilot_status = "BLOCKED"` (`0` fake records), now isolating the sole remaining prerequisite blocker: **`"MS_TOKEN environment credential is missing"`** (`yt-dlp`, `ffmpeg`, `faster-whisper`, and `70,996` historical ID protections all pass preflight).

## Work performed

- **Bounded CPU ASR stage ([asr.py](../../../../pipelines/pilot_m3_3/asr.py)):** Added `CpuAsrEngine` protocol + fail-closed `FasterWhisperCpuAsrEngine` (`device="cpu"`, `compute_type="int8"`, `beam_size=1`, strict `0.0 <= start_sec < end_sec` invariant, `ffmpeg` 16kHz float32 PCM decoding avoiding `av>=19` `metadata_errors` incompatibility) and `BoundedCpuAsrRunner` capped at `<= 10` videos and `<= 20.0` audio minutes, reporting `real_time_factor` (`wall_sec / audio_sec`) and `peak_rss_mib` without fabricating transcripts when audio is absent.
- **End-to-end M3.3 pilot runner & CLI ([runner.py](../../../../pipelines/pilot_m3_3/runner.py), [models.py](../../../../pipelines/pilot_m3_3/models.py), [__main__.py](../../../../pipelines/pilot_m3_3/__main__.py)):** Enforces `M3.2` hard caps (`5` creators, `50` candidates, `30` succeeded, `60.0` audio min, `1,000` comments, `7,200`s deadline), automatically prepends `.venv/bin` (`_venv_search_path()`) so `yt-dlp`/`ffmpeg` resolve even when invoked via `.venv/bin/python`, separates `--mode dry_run_fixture` (`FIXTURE_DRY_RUN_ONLY`, `is_synthetic_fixture=True`) from `--mode live_pilot`, runs `ingest_incremental_batch_to_gold` into an isolated output snapshot, builds a fresh `BM25Index`, verifies exact source `video_id` searchability (`>= 5` required for `PASS`), measures disk bytes / peak RAM / wall time / yield & failure rates, and generates `sample_inspection_sheet.jsonl` split 50/50 between `K` and `N`.

## Outputs

| File | Purpose |
| --- | --- |
| [workflow.md](evidence/workflow.md) | `M3.3` Superpowers TDD ledger, rulings, host tool setup, and command verification receipts |
| [red-m3_3-tests.log](evidence/red-m3_3-tests.log), [green-m3_3-tests.log](evidence/green-m3_3-tests.log) | TDD RED (`ModuleNotFoundError`) -> GREEN (`6 passed in 1.31s`) logs |
| [m3_3_live_preflight_receipt.json](evidence/m3_3_live_preflight_receipt.json) | Honest `live_pilot` preflight receipt (`pilot_status = "BLOCKED"` solely on missing `MS_TOKEN`) |
| [pytest-full-m3_3.log](evidence/pytest-full-m3_3.log) | Full `183`-test pytest suite verification on `feat/m3.3-pilot-scaffolding` |

## How to set up and run

1. **Checkout branch & provision host runtime (no `sudo` required):**

   ```bash
   git fetch origin && git checkout feat/m3.3-pilot-scaffolding
   uv pip install --python .venv/bin/python yt-dlp faster-whisper imageio-ffmpeg
   ln -sf "$(.venv/bin/python -c 'import imageio_ffmpeg; print(imageio_ffmpeg.get_ffmpeg_exe())')" .venv/bin/ffmpeg
   ```

2. **Verify tests & offline pipeline before live network access:**

   ```bash
   .venv/bin/python -m pytest tests/unit/test_m3_3_pilot_pipeline.py -v
   ```

3. **Run bounded `live_pilot` (up to `5` `--creator` flags, `<= 50` candidates / `<= 30` videos / `<= 60`m audio; CPU ASR capped at `<= 10` videos / `<= 20`m audio):**
   - Put `MS_TOKEN=...` in gitignored `.env`, then export `.env` before invoking:

   ```bash
   set -a && source .env && set +a
   PYTHONPATH=. .venv/bin/python -m pipelines.pilot_m3_3 \
     --mode live_pilot --allow-live-network \
     --creator <handle_1> --creator <handle_2> \
     --asr-model small
   ```

   - Outputs: receipt at `docs/reports/milestones/M3.3/evidence/m3_3_pilot_receipt.json`, Gold snapshot at `data/corpus/m3_3_pilot_snapshot_v1`, BM25 index at `artifacts/indexes/bm25-m3_3-pilot`, and 50/50 `K`/`N` inspection sheet at `docs/reports/milestones/M3.3/evidence/sample_inspection_sheet.jsonl`.

## Verification

| Check | Result | Scope / evidence |
| --- | --- | --- |
| `.venv/bin/python -m pytest tests/unit/test_m3_3_pilot_pipeline.py -v` | PASS (`6 passed in 1.31s`) | Bounded `10`-video/`20`-min ASR caps, fail-closed `faster-whisper` check, `ffmpeg` 16kHz PCM decode & fallback, `.venv/bin` `PATH` injection, offline `dry_run_fixture` end-to-end collect->ASR->Gold->BM25->search & 50/50 split, fail-closed `live_pilot` `BLOCKED`; [green-m3_3-tests.log](evidence/green-m3_3-tests.log) |
| Host real audio test (`ffmpeg` 64kbps `.mp3` copy + `FasterWhisperCpuAsrEngine(model_size="tiny", language="vi")`) | PASS (`failed_count=0`, `RTF=0.1278`) | Decoded temporary 64k `.mp3` copy of `happipham_7464081161812233490.m4a` (`1.0` min, `6` segments, `7.671s` wall, `445.49 MiB` peak RSS; `data/` untouched) |
| `.venv/bin/python -m pipelines.pilot_m3_3 --mode live_pilot --allow-live-network ...` | `BLOCKED` (expected fail-closed) | Passed `yt-dlp`, `ffmpeg`, `faster-whisper`, and `70,996` historical ID protection; sole remaining blocker `"MS_TOKEN environment credential is missing"`; [m3_3_live_preflight_receipt.json](evidence/m3_3_live_preflight_receipt.json) |
| `.venv/bin/python -m ruff check pipelines/pilot_m3_3 tests/unit/test_m3_3_pilot_pipeline.py` & `.venv/bin/python -m mypy packages apps pipelines` | PASS (`0` Ruff errors; `100/100` source files clean in `mypy`) | Code quality & full static typing |
| `.venv/bin/python -m pytest -v` & `python3 scripts/check_secrets.py` | PASS (`183 passed in 28.39s`; `0` secret leaks) | Full suite + secret hygiene; [pytest-full-m3_3.log](evidence/pytest-full-m3_3.log) |

## Open issues

| Issue | Impact | Follow-up / responsible task |
| --- | --- | --- |
| Host `.env` / environment lacks `MS_TOKEN` | Live TikTok capture cannot run until user provisions `MS_TOKEN` and confirms `<= 5` creators; `M3.3` remains `IN_PROGRESS` | Set `MS_TOKEN` in `.env` (gitignored), confirm `<= 5` creator handles, and run `--mode live_pilot --allow-live-network` |
| `K` & `N` 50/50 inspection of real captured videos pending live run | Required before `M3.3` acceptance and Gate `G3` (`M3.G`) | Both inspect half of `sample_inspection_sheet.jsonl` after real pilot run |

## Acceptance and handoff

| Task criterion | Result | Evidence |
| --- | --- | --- |
| Bounded ceilings (`5` creators, `50` cands, `30` videos, `60`m audio, `1,000` comments, `2`h) & CPU ASR (`<= 10` videos / `<= 20`m) wired + host-verified | Met (`6/6` tests + real `.mp3` `tiny` CPU ASR run `RTF=0.1278`) | [models.py](../../../../pipelines/pilot_m3_3/models.py), [asr.py](../../../../pipelines/pilot_m3_3/asr.py), [runner.py](../../../../pipelines/pilot_m3_3/runner.py) |
| Real non-synthetic receipts, disk/RAM/time, `>= 5` searchable real fresh videos, and 50/50 `K`/`N` inspection | Pending `MS_TOKEN` & live capture (`BLOCKED` only on missing `MS_TOKEN`) | [m3_3_live_preflight_receipt.json](evidence/m3_3_live_preflight_receipt.json) |

Final task status: **`IN_PROGRESS`** (M3.3 pipeline scaffolding, host `.venv` `yt-dlp`/`ffmpeg`/`faster-whisper` provisioning + PyAV 19 PCM workaround, real host `.mp3` CPU ASR verification, and `183/183` tests complete on `feat/m3.3-pilot-scaffolding`; ready to execute `--mode live_pilot` as soon as `MS_TOKEN` and `<= 5` creator handles are provided).
