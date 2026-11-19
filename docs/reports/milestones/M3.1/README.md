# M3.1 — Repeated Dual-Sink Ingestion Repair & Continuity Verification

- Status: COMPLETE (Implemented by Nguyễn Việt Nguyên; independently reproduced on Windows 11 against real `70,996`-video `20261118_taxonomy_fix_v1` snapshot and approved by Trần Đình Khương)
- Execution date: 2026-11-18 (Asia/Ho_Chi_Minh)
- Requirement source: [TikTok_AI_Engine_Milestone.md](../../../planning/TikTok_AI_Engine_Milestone.md) (`M3.1`)
- Repository version: `main` @ `e050d7d5bbcf90e310bbfd144407086d82479341` (merged `feat/m3.1-incremental-ingestion` + `K` peer review)
- Primary owner: Nguyễn Việt Nguyên (`N`) · Peer reviewer: Trần Đình Khương (`K`)
- Specification: [spec.md](superpowers/spec.md)
- Execution plan: [plan.md](superpowers/plan.md)

## Conclusion

Completed and independently verified the `M3.1` Dual-Sink ingestion repair across [pipelines/ingest_incremental_to_gold/](../../../../pipelines/ingest_incremental_to_gold/), [packages/data_contracts/multimodal.py](../../../../packages/data_contracts/multimodal.py), and [packages/analytics/engine.py](../../../../packages/analytics/engine.py). On `N`'s Linux environment (`26/26` continuity tests in `2.71s`, `81/81` pytest in `17.81s`) and `K`'s independent Windows 11 reproduction (`26/26` continuity tests in `13.29s` plus a `160.878s` end-to-end continuity run directly over the real `70,996`-video `data/corpus/20261118_taxonomy_fix_v1` snapshot), sequential `Batch A` -> `Batch B` -> `Replay` -> `Empty batch` -> `Same-video NaN/ndarray enrichment` -> `Missing modalities` -> `Collision rejection` -> `Interrupted publication & retry` all pass with **`100%` byte preservation of the base Gold snapshot** ([khuong_m3_1_reproduction.json](evidence/khuong_m3_1_reproduction.json), [khuong-peer-review.md](evidence/khuong-peer-review.md)).

All primary and reciprocal peer-review acceptance criteria are satisfied: task **`M3.1` is `COMPLETE`** (formal gate `M3.G` / `G3` remains `NOT_RUN` pending `M3.2` and `M3.3`).

## Work performed

- **Fail-closed timestamps & accurate snapshot window ([multimodal.py](../../../../packages/data_contracts/multimodal.py), [converter.py](../../../../pipelines/ingest_incremental_to_gold/converter.py)):** Validated ISO-8601 `create_time` on `RawIncrementalVideoRecord`, removed silent `datetime.now()` fallbacks, preserved `base_manifest.date_window_end` on empty/no-new-row batches, and anchored non-empty batches to `max(base_window_end, *observed_dates)`.
- **Real-Parquet enrichment normalization ([converter.py](../../../../pipelines/ingest_incremental_to_gold/converter.py)):** Added `_normalize_scalar` and `_normalize_preserved_row` so nullable `float('nan')` / `pd.NA` columns and `numpy.ndarray` list fields (`hashtags`) from real Gold Parquet snapshots normalize cleanly during `update_existing=True` enrichment while merging prior and new comments.
- **Typed Arrow schemas for missing modalities ([converter.py](../../../../pipelines/ingest_incremental_to_gold/converter.py)):** Pinned `_VOICE_SEGMENTS_SCHEMA`, `_COMMENTS_SCHEMA`, and `_ABSA_REVIEWS_SCHEMA` so 0-row multimodal tables retain exact `int64`/`float64`/`bool`/`string` types without `"null"` columns.
- **5-table integrity & CLI `--update-existing` ([engine.py](../../../../packages/analytics/engine.py), [__main__.py](../../../../pipelines/ingest_incremental_to_gold/__main__.py), [converter.py](../../../../pipelines/ingest_incremental_to_gold/converter.py)):** Validated Parquet readability and `(rows, columns)` shapes across all 5 declared tables prior to atomic publication and exposed `--update-existing` on the CLI.
- **Independent `K` peer review & real-snapshot reproduction (`2026-11-18`):** Executed `26` unit tests on Windows 11 and ran [run_khuong_m3_1_reproduction.py](evidence/run_khuong_m3_1_reproduction.py) against `20261118_taxonomy_fix_v1` (`70,996` rows, enriching real historical row `7382199247048920338` with `play_count = 655,200` preserved and `0` bytes mutated on base files).

## Outputs

| File | Purpose |
| --- | --- |
| [workflow.md](evidence/workflow.md) | Skill/process provenance, rulings, and command ledger (`N` + `K`) |
| [khuong-peer-review.md](evidence/khuong-peer-review.md) | Independent peer review sign-off by Trần Đình Khương (`K`) |
| [khuong_m3_1_reproduction.json](evidence/khuong_m3_1_reproduction.json) | Machine-readable real-snapshot (`20261118_taxonomy_fix_v1`) continuity & SHA256 preservation receipt |
| [run_khuong_m3_1_reproduction.py](evidence/run_khuong_m3_1_reproduction.py), [khuong_m3_1_reproduction.log](evidence/khuong_m3_1_reproduction.log) | Reproducible `K` continuity probe and console log (`160.878s`) |
| [khuong-pytest-continuity-windows.log](evidence/khuong-pytest-continuity-windows.log) | Windows 11 `test_snapshot_continuity.py` output (`26 passed in 13.29s`) |
| [report-before-khuong-peer-review.md](evidence/report-before-khuong-peer-review.md) | Byte-preserved `M3.1` report prior to `K` peer review |
| [red-m3_1-tests.log](evidence/red-m3_1-tests.log), [green-m3_1-tests.log](evidence/green-m3_1-tests.log) | `N`'s TDD RED (`4 failed`) and GREEN (`26 passed`) test logs |
| [ruff.log](evidence/ruff.log), [mypy.log](evidence/mypy.log), [pytest-full.log](evidence/pytest-full.log), [check-secrets.log](evidence/check-secrets.log) | `N`'s lint, strict `mypy`, full suite, and secret scan logs |

## Verification

| Check | Result | Scope / evidence |
| --- | --- | --- |
| `pytest tests/unit/test_snapshot_continuity.py -v` (`N` Linux & `K` Windows) | PASS (`26 passed` in `2.71s` / `13.29s`) | Sequential A/B, replay, empty batch, enrichment, `NaN`/`ndarray`, missing modalities, interrupted ingest + retry, CLI; [green-m3_1-tests.log](evidence/green-m3_1-tests.log), [khuong-pytest-continuity-windows.log](evidence/khuong-pytest-continuity-windows.log) |
| `python docs/reports/milestones/M3.1/evidence/run_khuong_m3_1_reproduction.py` (`K` Windows) | PASS (`160.878s`, `100%` base byte identity) | End-to-end A/B/replay/empty/enrichment/missing-modality/collision/abort-retry against real `70,996`-row `20261118_taxonomy_fix_v1`; [khuong_m3_1_reproduction.json](evidence/khuong_m3_1_reproduction.json) |
| `ruff`, `mypy`, full `pytest` (`120 passed` on `main`), and `scripts/check_secrets.py` | PASS (`0` issues, `0` leaks) | [ruff.log](evidence/ruff.log), [mypy.log](evidence/mypy.log), [main-verification.json](../M6.1/evidence/main-verification.json), [check-secrets.log](evidence/check-secrets.log) |

## Open issues

None within `M3.1` scope. Bounded live discovery/metadata/audio/comment worker (`M3.2`) and capped pilot capture (`M3.3`) follow separately.

## Acceptance and handoff

| Task criterion | Result | Evidence |
| --- | --- | --- |
| A, B, replay, empty batch & same-video enrichment preserve base bytes & deduplicate rows | Met | [test_snapshot_continuity.py](../../../../tests/unit/test_snapshot_continuity.py), [khuong_m3_1_reproduction.json](evidence/khuong_m3_1_reproduction.json) |
| Collisions fail & only complete verified snapshots publish across all 5 tables | Met | [snapshots.py](../../../../packages/common/snapshots.py), [converter.py](../../../../pipelines/ingest_incremental_to_gold/converter.py), [khuong_m3_1_reproduction.json](evidence/khuong_m3_1_reproduction.json) |
| Missing modalities & interrupted publication tested (including `NaN`/`ndarray` & bad `create_time`) | Met | [test_snapshot_continuity.py](../../../../tests/unit/test_snapshot_continuity.py), [khuong_m3_1_reproduction.json](evidence/khuong_m3_1_reproduction.json) |
| Independent check of base preservation & replay receipts by `K` | Met | [khuong-peer-review.md](evidence/khuong-peer-review.md), [khuong_m3_1_reproduction.json](evidence/khuong_m3_1_reproduction.json) |

Final task status: **`M3.1` is `COMPLETE`**. Ready as verified ingestion prerequisite for `M3.2` and `M3.3` (`G3` remains `NOT_RUN`).
