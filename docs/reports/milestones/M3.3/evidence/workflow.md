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
- Executed `.venv/bin/python -m pipelines.pilot_m3_3 --mode live_pilot --allow-live-network --creator ansapsaigon --receipt-path docs/reports/milestones/M3.3/evidence/m3_3_live_preflight_receipt.json` -> honest fail-closed `pilot_status = "BLOCKED"` listing missing `MS_TOKEN`, `yt-dlp`, `ffmpeg`, `faster-whisper` ([m3_3_live_preflight_receipt.json](m3_3_live_preflight_receipt.json)).
- Executed `python3 scripts/check_secrets.py` (`0` leaks) and full `.venv/bin/python -m pytest -v` (`181 passed in 27.99s`, [pytest-full-m3_3.log](pytest-full-m3_3.log)).
