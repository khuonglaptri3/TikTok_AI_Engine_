# M1.2 — Execution & Verification Plan

- **Date:** 2026-11-18
- **Task ID:** `M1.2`
- **Primary Owner:** Trần Đình Khương (`K`)
- **Peer Reviewer:** Nguyễn Việt Nguyên (`N`)
- **Spec:** [spec.md](spec.md)

## Execution Steps
- [x] **Step 1: TDD RED — Parent Provenance & Fail-Closed Tests (`tests/unit/test_snapshot_continuity.py`)**
  - Added `test_historical_builder_records_verified_parent_provenance` and `test_historical_builder_fails_closed_on_corrupted_parent_snapshot`.
  - Ran `pytest tests/unit/test_snapshot_continuity.py -v` -> observed expected `2 failed, 18 passed` ([red-m1_2-tests.log](../evidence/red-m1_2-tests.log)).
- [x] **Step 2: TDD GREEN — Implement `parent_corpus_dir` / `--parent-corpus` in `pipelines/build_gold_corpus/`**
  - Updated `pipelines/build_gold_corpus/builder.py` and `pipelines/build_gold_corpus/__main__.py` to validate `parent_corpus_dir` via `load_verified_corpus` and bind `parent_snapshot_id` + `parent_manifest_sha256`.
  - Ran `pytest tests/unit/test_snapshot_continuity.py -v` -> `20 passed in 13.25s` ([green-m1_2-tests.log](../evidence/green-m1_2-tests.log)).
- [x] **Step 3: Build & Verify Immutable Snapshot `data/corpus/20261118_taxonomy_fix_v1`**
  - Hashed key historical inputs and `20261117_recovered_v1` before and after build (`100%` unchanged).
  - Built `data/corpus/20261118_taxonomy_fix_v1` (`--parent-corpus data/corpus/20261117_recovered_v1`, `637.32s`), verified collision rejection (`FileExistsError`), and computed taxonomy deltas in [m1.2-build-receipt.json](../evidence/m1.2-build-receipt.json).
- [x] **Step 4: Full Suite Verification & Report**
  - Executed `ruff`, `mypy`, full `pytest -v`, and `python scripts/check_secrets.py`.
  - Authored `docs/reports/milestones/M1.2/README.md` and `evidence/workflow.md`, and updated `docs/reports/milestones/README.md`.
