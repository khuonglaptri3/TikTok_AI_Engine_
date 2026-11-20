# M3.3 — Capped Capture-to-Transcript-to-Search Pilot (Scaffolding Ready; Live Acquisition Blocked on Host Tools/`MS_TOKEN`)

- Status: IN_PROGRESS (`pipelines/pilot_m3_3/` capture -> CPU ASR -> Dual-Sink Gold -> BM25 -> searchability orchestrator, `4/4` TDD tests, `181`-test full suite, and `100`-file strict `mypy` complete on `feat/m3.3-pilot-scaffolding`; live network pilot awaits host `yt-dlp`, `ffmpeg`, `faster-whisper`, `MS_TOKEN`, and `K`+`N` 50/50 inspection)
- Execution date: 2026-11-20 (Asia/Ho_Chi_Minh)
- Requirement source: [TikTok_AI_Engine_Milestone.md](../../../planning/TikTok_AI_Engine_Milestone.md) (`M3.3`)
- Repository version: branch `feat/m3.3-pilot-scaffolding` (from `main` @ `847ffcb4`)
- Owners: Nguyễn Việt Nguyên (`N`) & Trần Đình Khương (`K`) (shared integration & 50/50 inspection)
- Specification: [spec.md](superpowers/spec.md)
- Execution plan: [plan.md](superpowers/plan.md)

## Conclusion

Built, tested, and preflight-verified the bounded end-to-end `M3.3` orchestrator in [pipelines/pilot_m3_3/](../../../../pipelines/pilot_m3_3/) (`models.py`, `asr.py`, `runner.py`, `__main__.py`), connecting `M3.2` incremental collection -> bounded CPU ASR (`<= 10` videos / `<= 20.0` audio minutes, `FasterWhisperCpuAsrEngine` int8 CPU + `real_time_factor` / `peak_rss_mib` tracking) -> `M3.1` Dual-Sink Gold ingestion -> `BM25Index` build -> fresh-video `HybridRetrievalService` searchability verification -> 50/50 `K`/`N` inspection sheet export.

- **TDD & Full Suite Verification (`feat/m3.3-pilot-scaffolding`):** `4/4` dedicated tests in [test_m3_3_pilot_pipeline.py](../../../../tests/unit/test_m3_3_pilot_pipeline.py) (`1.34s`), `181/181` full workspace pytest suite (`27.99s`), `100/100`-file `mypy`, `ruff check`, and `scripts/check_secrets.py` (`0` leaks) all pass.
- **Honest Live Preflight (`m3_3_live_preflight_receipt.json`):** Executing `python3 -m pipelines.pilot_m3_3 --mode live_pilot --allow-live-network --creator ansapsaigon` on this Linux host fails closed with `pilot_status = "BLOCKED"` (`0` fake records), accurately listing the missing host dependencies: `MS_TOKEN`, `yt-dlp`, `ffmpeg`, and `faster-whisper`.

## Work performed

- **Bounded CPU ASR stage ([asr.py](../../../../pipelines/pilot_m3_3/asr.py)):** Added `CpuAsrEngine` protocol + fail-closed `FasterWhisperCpuAsrEngine` (`device="cpu"`, `compute_type="int8"`, `beam_size=1`, strict `0.0 <= start_sec < end_sec` invariant) and `BoundedCpuAsrRunner` capped at `<= 10` videos and `<= 20.0` audio minutes, reporting `real_time_factor` (`wall_sec / audio_sec`) and `peak_rss_mib` without fabricating transcripts when audio is absent.
- **End-to-end M3.3 pilot runner & CLI ([runner.py](../../../../pipelines/pilot_m3_3/runner.py), [models.py](../../../../pipelines/pilot_m3_3/models.py), [__main__.py](../../../../pipelines/pilot_m3_3/__main__.py)):** Enforces `M3.2` hard caps (`5` creators, `50` candidates, `30` succeeded, `60.0` audio min, `1,000` comments, `7,200`s deadline), separates `--mode dry_run_fixture` (`FIXTURE_DRY_RUN_ONLY`, `is_synthetic_fixture=True`) from `--mode live_pilot`, runs `ingest_incremental_batch_to_gold` into an isolated output snapshot, builds a fresh `BM25Index`, verifies exact source `video_id` searchability (`>= 5` required for `PASS`), measures disk bytes / peak RAM / wall time / yield & failure rates, and generates `sample_inspection_sheet.jsonl` split 50/50 between `K` and `N`.

## Outputs

| File | Purpose |
| --- | --- |
| [workflow.md](evidence/workflow.md) | `M3.3` Superpowers TDD ledger, rulings, and command verification receipts |
| [red-m3_3-tests.log](evidence/red-m3_3-tests.log), [green-m3_3-tests.log](evidence/green-m3_3-tests.log) | TDD RED (`ModuleNotFoundError`) -> GREEN (`4 passed in 1.34s`) logs |
| [m3_3_live_preflight_receipt.json](evidence/m3_3_live_preflight_receipt.json) | Honest `live_pilot` preflight receipt (`pilot_status = "BLOCKED"` listing missing host tools/`MS_TOKEN`) |
| [pytest-full-m3_3.log](evidence/pytest-full-m3_3.log) | Full `181`-test pytest suite verification on `feat/m3.3-pilot-scaffolding` |

## Verification

| Check | Result | Scope / evidence |
| --- | --- | --- |
| `.venv/bin/python -m pytest tests/unit/test_m3_3_pilot_pipeline.py -v` | PASS (`4 passed in 1.34s`) | Bounded `10`-video/`20`-min ASR caps, fail-closed `faster-whisper` check, offline `dry_run_fixture` end-to-end collect->ASR->Gold->BM25->search & 50/50 split, fail-closed `live_pilot` `BLOCKED`; [green-m3_3-tests.log](evidence/green-m3_3-tests.log) |
| `.venv/bin/python -m pipelines.pilot_m3_3 --mode live_pilot --allow-live-network ...` | `BLOCKED` (expected fail-closed) | Verified missing `MS_TOKEN`, `yt-dlp`, `ffmpeg`, `faster-whisper` preflight checks + `70,996` historical ID protection; [m3_3_live_preflight_receipt.json](evidence/m3_3_live_preflight_receipt.json) |
| `.venv/bin/python -m ruff check pipelines/pilot_m3_3 tests/unit/test_m3_3_pilot_pipeline.py` & `.venv/bin/python -m mypy packages apps pipelines` | PASS (`0` Ruff errors; `100/100` source files clean in `mypy`) | Code quality & full static typing |
| `.venv/bin/python -m pytest -v` & `python3 scripts/check_secrets.py` | PASS (`181 passed in 27.99s`; `0` secret leaks) | Full suite + secret hygiene; [pytest-full-m3_3.log](evidence/pytest-full-m3_3.log) |

## Open issues

| Issue | Impact | Follow-up / responsible task |
| --- | --- | --- |
| Host lacks `MS_TOKEN`, `yt-dlp`, `ffmpeg`, and `faster-whisper` | Live TikTok capture & real CPU ASR cannot run on this host until provisioned; `M3.3` remains `IN_PROGRESS` | Install `yt-dlp`, `ffmpeg`, `faster-whisper`, set `MS_TOKEN` in `.env`, agree on `<= 5` creators with `K`, and run `--mode live_pilot` |
| `K` & `N` 50/50 inspection of real captured videos pending live run | Required before `M3.3` acceptance and Gate `G3` (`M3.G`) | Both inspect half of `sample_inspection_sheet.jsonl` after real pilot run |

## Acceptance and handoff

| Task criterion | Result | Evidence |
| --- | --- | --- |
| Bounded ceilings (`5` creators, `50` cands, `30` videos, `60`m audio, `1,000` comments, `2`h) & CPU ASR (`<= 10` videos / `<= 20`m) wired | Met (verified in pipeline + unit/fixture tests) | [models.py](../../../../pipelines/pilot_m3_3/models.py), [asr.py](../../../../pipelines/pilot_m3_3/asr.py), [runner.py](../../../../pipelines/pilot_m3_3/runner.py) |
| Real non-synthetic receipts, disk/RAM/time, `>= 5` searchable real fresh videos, and 50/50 `K`/`N` inspection | Pending host tools/`MS_TOKEN` & live capture (`BLOCKED` in preflight) | [m3_3_live_preflight_receipt.json](evidence/m3_3_live_preflight_receipt.json) |

Final task status: **`IN_PROGRESS`** (M3.3 pipeline scaffolding, bounded ASR integration, 50/50 inspection export, and `181/181` tests complete on `feat/m3.3-pilot-scaffolding`; ready to execute `--mode live_pilot` once host dependencies & `MS_TOKEN` are available).
