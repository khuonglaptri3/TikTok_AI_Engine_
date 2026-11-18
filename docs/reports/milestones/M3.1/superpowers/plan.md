# M3.1 — Execution & Verification Plan

1. **TDD RED:** Add failing unit tests in `tests/unit/test_snapshot_continuity.py` covering:
   - Invalid `create_time` failing closed instead of defaulting to current UTC time.
   - Empty batch preserving `base_manifest.date_window_end`.
   - Enriching a real-Parquet-shaped row containing `NaN` nullable strings and `numpy.ndarray` hashtags (`update_existing=True`).
   - Missing modalities (metadata-only batch with no transcript/whisper/prosody/comments) maintaining typed Arrow schemas across consecutive batches.
   - Interrupted publication during `ingest_incremental_batch_to_gold` leaving zero partial target, cleaning staging/lock artifacts, and allowing clean retry.
   - CLI `--update-existing` flag wiring and all-5-table staging verification.
2. **Implementation:**
   - Enforce ISO-8601 `create_time` validation in `packages/data_contracts/multimodal.py` (`RawIncrementalVideoRecord`) and fail-closed parsing + accurate `date_window_end` calculation in `pipelines/ingest_incremental_to_gold/converter.py`.
   - Normalize `old_row` `NaN`/`pd.NA`/`np.ndarray` fields cleanly before `RawIncrementalVideoRecord.model_copy(update=preserved)` and `RawCommentInput.model_validate(...)` in `converter.py`.
   - Define explicit PyArrow schemas (`_VOICE_SEGMENTS_SCHEMA`, `_COMMENTS_SCHEMA`, `_ABSA_REVIEWS_SCHEMA`) in `converter.py` and verify every declared Parquet file in `manifest.files` via PyArrow metadata/read checks.
   - Add `--update-existing` to `pipelines/ingest_incremental_to_gold/__main__.py` and update `datetime.now(UTC)` imports for clean Ruff compliance.
3. **TDD GREEN & Gate Checks:** Verify targeted tests, `ruff check`, strict `mypy packages apps pipelines`, full `pytest -v`, and `scripts/check_secrets.py`.
4. **Reporting:** Record `M3.1/evidence/workflow.md`, `M3.1/README.md`, and `docs/reports/milestones/README.md` (`IN_PROGRESS` pending `K` verification).
