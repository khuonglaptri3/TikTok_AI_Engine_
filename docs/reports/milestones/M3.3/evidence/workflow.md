# M3.3 — Workflow Provenance & Verification Ledger

- **Date:** 2026-11-20 (Asia/Ho_Chi_Minh)
- **Task ID:** `M3.3`
- **Owners:** Nguyễn Việt Nguyên (`N`) & Trần Đình Khương (`K`)
- **Spec:** [spec.md](../superpowers/spec.md) · **Plan:** [plan.md](../superpowers/plan.md)

## Pre-Flight & Design Log
1. Checked prerequisites on `main`: `G2 = PASS` (`M2.G`), `M3.1 = COMPLETE`, `M3.2 = COMPLETE`.
2. Checked Linux host environment: `yt-dlp`, `ffmpeg`, and `faster-whisper` are not installed on this host (`faster_whisper` missing in `.venv`), so scaffolding uses TDD + `dry_run_fixture` verification while failing closed with explicit `BLOCKED` receipts when `live_pilot` lacks host binaries/credentials.
3. Authored `superpowers/spec.md`, `plan.md`, and this ledger prior to writing `tests/unit/test_m3_3_pilot_pipeline.py` or `pipelines/pilot_m3_3/`.

## Execution & Verification Log
- TDD RED (`tests/unit/test_m3_3_pilot_pipeline.py`) -> `EXIT=2`, `ModuleNotFoundError: No module named 'pipelines.pilot_m3_3'` ([red-m3_3-tests.log](red-m3_3-tests.log)).
- Implemented `pipelines/pilot_m3_3/{__init__.py,models.py,asr.py,runner.py,__main__.py}`.
- Switched cleanly to feature branch `feat/m3.3-pilot-scaffolding` (from `main` @ `847ffcb4`).
- TDD GREEN (`.venv/bin/python -m pytest tests/unit/test_m3_3_pilot_pipeline.py -v`) -> `4 passed in 1.34s` ([green-m3_3-tests.log](green-m3_3-tests.log)).
- Verified `.venv/bin/python -m ruff check pipelines/pilot_m3_3 tests/unit/test_m3_3_pilot_pipeline.py` -> `All checks passed!`.
- Verified `.venv/bin/python -m mypy packages apps pipelines` -> `Success: no issues found in 100 source files`.
- Executed `.venv/bin/python -m pipelines.pilot_m3_3 --mode live_pilot --allow-live-network --creator ansapsaigon --receipt-path docs/reports/milestones/M3.3/evidence/m3_3_live_preflight_receipt.json` -> honest fail-closed `pilot_status = "BLOCKED"` listing missing `MS_TOKEN`, `yt-dlp`, `ffmpeg`, `faster-whisper` (`m3_3_live_preflight_receipt.json` (later replaced by [m3_3_pilot_receipt.json](m3_3_pilot_receipt.json))).
- Executed `python3 scripts/check_secrets.py` (`0` leaks) and full `.venv/bin/python -m pytest -v` (`181 passed in 27.99s`, [pytest-full-m3_3.log](pytest-full-m3_3.log)).
- Provisioned host runtime in `.venv` without `sudo`: installed `yt-dlp==2026.10.26`, `faster-whisper==1.2.1`, `ctranslate2==4.9.0`, `av==19.0.2`, and `imageio-ffmpeg==0.8.1` (`n9.0.2`, symlinked to `.venv/bin/ffmpeg`).
- Diagnosed real host PyAV 19 bug (`TypeError: open() got an unexpected keyword argument 'metadata_errors'`) when calling `faster-whisper` directly on compressed paths; updated `FasterWhisperCpuAsrEngine._decode_audio_16k_mono` to decode via `ffmpeg` 16kHz float32 PCM and added `_venv_search_path()` to `runner.py`.
- Verified real host audio workflow on a `/tmp` 64kbps `.mp3` copy of `data/raw/happipham/videos/happipham_7464081161812233490.m4a`: `FasterWhisperCpuAsrEngine(model_size="tiny", language="vi")` completed with `transcribed_count=1`, `failed_count=0`, `6` Vietnamese segments, `wall_seconds=7.671s`, `real_time_factor=0.1278`, `peak_rss_mib=445.49 MiB`.
- Re-verified `live_pilot` preflight (`python3 -m pipelines.pilot_m3_3 --mode live_pilot --allow-live-network --creator ansapsaigon`) -> `pilot_status="BLOCKED"` with only `"MS_TOKEN environment credential is missing"` remaining (`m3_3_live_preflight_receipt.json` (later replaced by [m3_3_pilot_receipt.json](m3_3_pilot_receipt.json))).
- Added regression unit tests for `ffmpeg` PCM decode/fallback & `.venv/bin` `PATH` injection; re-verified `6/6` in [green-m3_3-tests.log](green-m3_3-tests.log), `ruff check`, `100`-file `mypy`, `python3 scripts/check_secrets.py` (`0` leaks), and `183 passed in 28.39s` full suite ([pytest-full-m3_3.log](pytest-full-m3_3.log)).
- Documented host setup (`uv pip install yt-dlp faster-whisper imageio-ffmpeg`, `.venv/bin/ffmpeg` symlink, `.env` `MS_TOKEN=`, and `--mode live_pilot` run commands) in `.env.example` and `M3.3/README.md`, then pushed `origin/feat/m3.3-pilot-scaffolding`.
- Diagnosed real TikTok extraction gaps when running `live_pilot` with `MS_TOKEN`: installed `curl-cffi==0.17.0` and enabled `--impersonate chrome` (`yt_dlp_impersonate_args()`) across `providers.py` & `crawler_service.py`, switched `download_audio_mp3_64k` from `-f bestaudio/best` (backing music / HTTP `403`) to `-f best[vcodec=h264]/best[vcodec!=none]/best`, and interleaved multi-creator discovery round-robin across `<= 5` handles.
- Cached `Systran/faster-whisper-small` using host system CA (`/etc/ssl/certs/ca-certificates.crt`) and executed official `M3.3` `live_pilot` across `ansapsaigon`, `tinhtungtangvn`, `dicungphuc`, `diadiemanuong`, `saigonmap` (`--asr-model small`) -> `pilot_status = "PASS"` (`30` fresh videos = `6` per creator, `29` `.mp3` audio files, `10` CPU ASR videos in `197.269 s` / `RTF=0.1971`, `10/10` searchable in `bm25-m3_3-pilot` over `21,758` docs, `15 K / 15 N` in [sample_inspection_sheet.jsonl](sample_inspection_sheet.jsonl), `comment_coverage_rate=0.0` documented honestly; receipt at [m3_3_pilot_receipt.json](m3_3_pilot_receipt.json), replacing stale preflight JSON).
- Re-ran verification after final code/test edits: `7/7` in [green-m3_3-tests.log](green-m3_3-tests.log) (`1.69s`), `195 passed in 43.03s` ([pytest-full-m3_3.log](pytest-full-m3_3.log)), clean `ruff check`, clean `100`-file `mypy`, and `scripts/check_secrets.py` (`0` leaks).
- Synced `feat/m3.3-live-pilot-results` with merged `main` (`d89f887f`), verified `207 passed in 39.67s` + `104`-file `mypy`, and opened PR #7 for `K` peer review.
- Completed `N`'s `15/15` inspection in [sample_inspection_sheet.jsonl](sample_inspection_sheet.jsonl) (`human_verified=true` on all `15` `N` rows after checking `ffmpeg` decode integrity of all `15` 64kbps `.mp3` files and cross-checking `5/5` ASR transcripts against captions; `#26` `7709375359300537601` flagged as out-of-domain museum vlog; `K`'s `15` rows remain untouched at `human_verified=false`).
