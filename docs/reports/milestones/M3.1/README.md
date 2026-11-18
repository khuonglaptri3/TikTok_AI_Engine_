# M3.1 — Repeated Dual-Sink Ingestion Repair & Continuity Verification

- Status: IN_PROGRESS (`N`'s code repairs, missing-modality schema typing, interrupted-publication tests, and full suite verification PASS on `feat/m3.1-incremental-ingestion`; awaiting `K` independent check of base preservation & replay receipts)
- Execution date: 2026-11-18 (Asia/Ho_Chi_Minh)
- Requirement source: [TikTok_AI_Engine_Milestone.md](../../../planning/TikTok_AI_Engine_Milestone.md) (`M3.1`)
- Repository version: `feat/m3.1-incremental-ingestion` (branched from `main` @ `c6c36131`)
- Primary owner: Nguyễn Việt Nguyên (`N`) · Peer reviewer: Trần Đình Khương (`K`)
- Specification: [spec.md](superpowers/spec.md)
- Execution plan: [plan.md](superpowers/plan.md)

## Conclusion

Completed and verified `N`'s `M3.1` repair across [pipelines/ingest_incremental_to_gold/](../../../../pipelines/ingest_incremental_to_gold/), [packages/data_contracts/multimodal.py](../../../../packages/data_contracts/multimodal.py), and [packages/analytics/engine.py](../../../../packages/analytics/engine.py) (`26/26` snapshot-continuity tests, `81/81` full pytest suite in `17.81s`, strict `mypy` across `76` source files, scoped `ruff`, and `check_secrets.py` with `0` leaks). After reproducing `4` initial TDD RED failures (silent `datetime.now()` fallback on invalid `create_time`, empty batch advancing `date_window_end` to wall-clock today, untyped `null` Arrow columns on missing-modality batches, and missing CLI `--update-existing` flag), all `6` identified gaps were fixed and covered by automated unit tests including real-Parquet `NaN`/`numpy.ndarray` enrichment and interrupted-publication retry checks. Task status remains `IN_PROGRESS` pending Trần Đình Khương's (`K`) independent check of base preservation and replay receipts.

## Work performed

- **Fail-closed timestamps & accurate snapshot window ([multimodal.py](../../../../packages/data_contracts/multimodal.py), [converter.py](../../../../pipelines/ingest_incremental_to_gold/converter.py)):** Validated ISO-8601 `create_time` on `RawIncrementalVideoRecord` and removed the silent `datetime.now(timezone.utc)` fallback during ingestion; preserved `base_manifest.date_window_end` on empty/no-new-row batches and set `max(base_window_end, *observed_dates)` when records are applied.
- **Real-Parquet enrichment normalization ([converter.py](../../../../pipelines/ingest_incremental_to_gold/converter.py)):** Added `_normalize_scalar` and `_normalize_preserved_row` so nullable `float('nan')` / `pd.NA` columns and `numpy.ndarray` list fields (`hashtags`) from real Gold Parquet snapshots normalize cleanly during `update_existing=True` enrichment (including prior comments).
- **Typed Arrow schemas for missing modalities ([converter.py](../../../../pipelines/ingest_incremental_to_gold/converter.py)):** Pinned `_VOICE_SEGMENTS_SCHEMA`, `_COMMENTS_SCHEMA`, and `_ABSA_REVIEWS_SCHEMA` so 0-row multimodal tables retain exact `int64`/`float64`/`bool`/`string` types and append cleanly across consecutive batches.
- **5-table integrity & CLI `--update-existing` ([engine.py](../../../../packages/analytics/engine.py), [__main__.py](../../../../pipelines/ingest_incremental_to_gold/__main__.py), [converter.py](../../../../pipelines/ingest_incremental_to_gold/converter.py)):** Extended `load_verified_corpus` to validate Parquet metadata and `(rows, columns)` shape for all declared `.parquet` files in `manifest.files`, verified staged multimodal tables via `pq.read_table` prior to atomic publication, and added `--update-existing` to the CLI entrypoint.
- **TDD continuity, missing-modality & interruption suite ([test_snapshot_continuity.py](../../../../tests/unit/test_snapshot_continuity.py)):** Expanded from `20` to `26` passing unit tests covering invalid `create_time`, empty-batch window preservation, `NaN`/`ndarray` enrichment, missing modalities, interrupted JSONL publication + lock/staging cleanup + retry, CLI `--update-existing`, and corrupted multimodal base fail-closed rejection.

## Outputs

| File | Purpose |
| --- | --- |
| [workflow.md](evidence/workflow.md) | Skill/process provenance, decisions, and command ledger |
| [red-m3_1-tests.log](evidence/red-m3_1-tests.log) | TDD RED test run showing `4` initial failures before fixes |
| [green-m3_1-tests.log](evidence/green-m3_1-tests.log) | Post-fix `test_snapshot_continuity.py` output (`26 passed in 2.71s`) |
| [ruff.log](evidence/ruff.log) | Scoped Ruff output (`All checks passed!`) |
| [mypy.log](evidence/mypy.log) | Project-wide mypy typecheck (`76 source files`, `0` issues) |
| [pytest-full.log](evidence/pytest-full.log) | Full pytest suite (`81 passed in 17.81s`) |
| [check-secrets.log](evidence/check-secrets.log) | Workspace secret scan (`0` leaks) |

## Verification

| Check | Result | Scope / evidence |
| --- | --- | --- |
| `.venv/bin/python -m pytest tests/unit/test_snapshot_continuity.py -v` | PASS (`26 passed`) | Sequential A/B, replay, empty batch, enrichment, `NaN`/`ndarray`, missing modalities, interrupted ingest + retry, CLI; [green-m3_1-tests.log](evidence/green-m3_1-tests.log) |
| `.venv/bin/python -m ruff check pipelines/ingest_incremental_to_gold packages/data_contracts/multimodal.py packages/analytics/engine.py tests/unit/test_snapshot_continuity.py` | PASS | Lint & import formatting across touched modules; [ruff.log](evidence/ruff.log) |
| `.venv/bin/python -m mypy packages apps pipelines` | PASS (`76 source files`) | Strict project-wide static typecheck; [mypy.log](evidence/mypy.log) |
| `.venv/bin/python -m pytest -v` | PASS (`81 passed in 17.81s`) | Full contract, unit, eval, and smoke suites; [pytest-full.log](evidence/pytest-full.log) |
| `.venv/bin/python scripts/check_secrets.py` | PASS (`0` leaks) | Workspace secret scan; [check-secrets.log](evidence/check-secrets.log) |

## Open issues

| Issue | Impact | Follow-up / responsible task |
| --- | --- | --- |
| Independent verification by Trần Đình Khương (`K`) pending | `M3.1` acceptance requires `K` to independently verify base preservation and replay receipts before closing | Review `feat/m3.1-incremental-ingestion` and mark `M3.1 COMPLETE` |

## Acceptance and handoff

| Task criterion | Result | Evidence |
| --- | --- | --- |
| A, B, replay, empty batch & same-video enrichment preserve base bytes & deduplicate rows | Met | [test_snapshot_continuity.py](../../../../tests/unit/test_snapshot_continuity.py), [green-m3_1-tests.log](evidence/green-m3_1-tests.log) |
| Collisions fail & only complete verified snapshots publish across all 5 tables | Met | [snapshots.py](../../../../packages/common/snapshots.py), [engine.py](../../../../packages/analytics/engine.py), [converter.py](../../../../pipelines/ingest_incremental_to_gold/converter.py) |
| Missing modalities & interrupted publication tested (including `NaN`/`ndarray` & bad `create_time`) | Met | [test_snapshot_continuity.py](../../../../tests/unit/test_snapshot_continuity.py), [green-m3_1-tests.log](evidence/green-m3_1-tests.log) |
| Independent check of base preservation & replay receipts by `K` | Pending `K` review | Ready on `feat/m3.1-incremental-ingestion` |

Final task status: **IN_PROGRESS** (`N`'s `M3.1` repair and tests are complete on `feat/m3.1-incremental-ingestion`; awaiting independent `K` review before closing `M3.1`).
