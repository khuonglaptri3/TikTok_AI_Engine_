# M3.1 — Workflow Provenance & Verification Ledger

- **Date:** 2026-11-18 (Asia/Ho_Chi_Minh)
- **Task ID:** `M3.1`
- **Primary Owner:** Nguyễn Việt Nguyên (`N`)
- **Peer Reviewer:** Trần Đình Khương (`K`, pending independent check)
- **Branch:** `feat/m3.1-incremental-ingestion` (branched from `main` @ `c6c36131`)

## Process Check (`AGENTS.md` Section 7)
- Authored [spec.md](../superpowers/spec.md) and [plan.md](../superpowers/plan.md) before modifying code.
- Applied TDD (`RED -> GREEN`): added 6 regression/coverage tests to [test_snapshot_continuity.py](../../../../../tests/unit/test_snapshot_continuity.py) and confirmed 4 initial failures ([red-m3_1-tests.log](red-m3_1-tests.log)) prior to patching.

## Key Engineering Decisions
1. **Fail-Closed `create_time` Validation:** Enforced ISO-8601 parsing inside `RawIncrementalVideoRecord` ([multimodal.py](../../../../../packages/data_contracts/multimodal.py)) and removed the silent `except Exception: datetime.now(...)` fallback in [converter.py](../../../../../pipelines/ingest_incremental_to_gold/converter.py), keeping `date_window_end` anchored to `max(base_window_end, *observed_dates)` so empty batches never advance the calendar window.
2. **Real-Parquet Enrichment Normalization:** Added `_normalize_scalar` and `_normalize_preserved_row` in `converter.py` so pandas `NaN` / `pd.NA` / numpy scalars and `numpy.ndarray` list columns read from real Gold snapshots do not corrupt or fail Pydantic validation during `update_existing=True` enrichment.
3. **Explicit Arrow Multimodal Schemas & Full Verification:** Pinned explicit `pyarrow.Schema` objects (`_VOICE_SEGMENTS_SCHEMA`, `_COMMENTS_SCHEMA`, `_ABSA_REVIEWS_SCHEMA`) so 0-row missing-modality tables retain typed columns instead of `null`, and extended `load_verified_corpus` + staging checks to verify Parquet readability and row/column integrity across all declared files.

## Commands & Verification Receipts
- `.venv/bin/python -m pytest tests/unit/test_snapshot_continuity.py -v` (RED) -> `4 failed, 22 passed` ([red-m3_1-tests.log](red-m3_1-tests.log))
- `.venv/bin/python -m pytest tests/unit/test_snapshot_continuity.py -v` (GREEN) -> `EXIT=0`, `26 passed in 2.71s` ([green-m3_1-tests.log](green-m3_1-tests.log))
- `.venv/bin/python -m ruff check pipelines/ingest_incremental_to_gold packages/data_contracts/multimodal.py packages/analytics/engine.py tests/unit/test_snapshot_continuity.py` -> `EXIT=0`, `All checks passed!` ([ruff.log](ruff.log))
- `.venv/bin/python -m mypy packages apps pipelines` -> `EXIT=0`, `Success: no issues found in 76 source files` ([mypy.log](mypy.log))
- `.venv/bin/python -m pytest -v` -> `EXIT=0`, `81 passed in 17.81s` ([pytest-full.log](pytest-full.log))
- `.venv/bin/python scripts/check_secrets.py` -> `EXIT=0`, `PASS: Zero secret leaks detected across workspace.` ([check-secrets.log](check-secrets.log))

## Independent Peer Review & Real-Snapshot Reproduction (`K` — 2026-11-18)
- **Authorization & Skills:** Project owner (`Trần Đình Khương`, `K`) approved the bounded peer-review plan and closing `M3.1 = COMPLETE` upon passing real-snapshot checks (`using-superpowers`, `brainstorming`, `writing-plans`, `executing-plans`, `verification-before-completion`).
- **Preservation:** Archived pre-review `M3.1/README.md` byte-for-byte to [report-before-khuong-peer-review.md](report-before-khuong-peer-review.md).
- **Ruling:** `M3.1` reproduction probe initially asserted `0` rows on `fact_absa_reviews.parquet` for a 1-video metadata-only batch, whereas `converter.py` intentionally writes `1` video-level ABSA summary row per new video (`0` voice segments, `0` comments) and `0` rows across all 3 tables on an empty batch — updated probe to assert exact expected row counts (`0/0/1` on metadata-only batch and `0/0/0` on empty batch) with zero `"null"` Arrow columns on both — cost if wrong: zero production impact, stronger probe specificity.
- **Commands & Receipts (`Windows-11-10.0.26300-SP0`, Python `3.12.14`, `main` @ `e050d7d5`):**
  - `pytest tests/unit/test_snapshot_continuity.py -v` -> `EXIT=0`, `26 passed in 13.29s` ([khuong-pytest-continuity-windows.log](khuong-pytest-continuity-windows.log)).
  - `python docs/reports/milestones/M3.1/evidence/run_khuong_m3_1_reproduction.py` -> `EXIT=0`, `160.878s`, `100%` base byte identity on `20261118_taxonomy_fix_v1` ([khuong_m3_1_reproduction.json](khuong_m3_1_reproduction.json), [khuong_m3_1_reproduction.log](khuong_m3_1_reproduction.log), [khuong-peer-review.md](khuong-peer-review.md)).
