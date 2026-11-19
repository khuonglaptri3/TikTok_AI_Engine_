# M3.1 — Peer Review & Real-Snapshot Reproduction by Trần Đình Khương (`K`)

- **Review date:** 2026-11-18 (Asia/Saigon)
- **Task ID:** `M3.1`
- **Primary Owner:** Nguyễn Việt Nguyên (`N`)
- **Peer Reviewer:** Trần Đình Khương (`K`)
- **Reviewed revision:** `main` @ `e050d7d5bbcf90e310bbfd144407086d82479341`

## 1. Review Summary & Approval Verdict

- **Overall Verdict:** **APPROVED — `M3.1` is `COMPLETE`** (all primary-owner and reciprocal peer-review acceptance criteria satisfied; formal acquisition gate `M3.G` / `G3` remains `NOT_RUN` pending `M3.2` and `M3.3`).
- **Code & Schema Inspection (`PASS`):**
  - Inspected [converter.py](../../../../../pipelines/ingest_incremental_to_gold/converter.py), [__main__.py](../../../../../pipelines/ingest_incremental_to_gold/__main__.py), [multimodal.py](../../../../../packages/data_contracts/multimodal.py), and [engine.py](../../../../../packages/analytics/engine.py).
  - Verified fail-closed ISO-8601 `create_time` validation (`RawIncrementalVideoRecord`), preservation of `base_manifest.date_window_end` on empty/no-new-row batches, `_normalize_scalar` / `_normalize_preserved_row` handling of real Parquet `NaN` / `pd.NA` / `numpy.ndarray` fields during `update_existing=True` enrichment, explicit PyArrow schemas (`_VOICE_SEGMENTS_SCHEMA`, `_COMMENTS_SCHEMA`, `_ABSA_REVIEWS_SCHEMA`), 5-table staging verification, and atomic `snapshot_workspace` rollback.
- **Automated Continuity Test Suite on Windows 11 (`PASS`):**
  - Executed `pytest tests/unit/test_snapshot_continuity.py -v` on `Windows-11-10.0.26300-SP0` (`12` logical CPUs, Python `3.12.14`): **`26 passed in 13.29s`** ([khuong-pytest-continuity-windows.log](khuong-pytest-continuity-windows.log)).
- **Independent Reproduction on Real `70,996`-Video Gold Snapshot (`PASS`):**
  - Executed [run_khuong_m3_1_reproduction.py](run_khuong_m3_1_reproduction.py) (`160.878s`) against the immutable `M1.2` snapshot `data/corpus/20261118_taxonomy_fix_v1` in an isolated temporary directory ([khuong_m3_1_reproduction.json](khuong_m3_1_reproduction.json)):
    1. **100% Base Byte Preservation:** `dim_creators.parquet` (`0a704391...`), `fact_videos.parquet` (`9684c438...`), and `manifest.json` (`49f23739...`) matched byte-for-byte before and after all ingestion steps (`base_bytes_100_percent_identical = true`).
    2. **Sequential, Replay & Empty-Batch Continuity:** `Batch A` (`70,997` videos, `265` creators, `date_window_end = 2026-10-05`) -> `Batch B` (`70,998` videos, `2026-10-12`) -> `Replay B` (`70,998` videos, `2026-10-12`) -> `Empty batch` (`70,998` videos, `date_window_end = 2026-10-12` preserved without advancing to wall-clock date).
    3. **Real-Parquet `NaN`/`ndarray` Enrichment (`update_existing=True`):** Enriched real historical video `7382199247048920338` (null POI & `numpy.ndarray` hashtags) while preserving `play_count = 655,200`, advancing `transcribed_videos` by `+1`, and merging prior + fresh comments (`["c_k_1", "c_k_2"]`) on `inc_k_v1`.
    4. **Missing-Modality Typed Schemas:** Verified zero `"null"`-typed PyArrow columns on both metadata-only batches (`0` voice, `0` comments, `1` ABSA summary row) and empty batches (`0` rows across all three multimodal tables).
    5. **Collision & Interrupted Publication Recovery:** Confirmed `FileExistsError` on output collision with zero byte mutation, clean rollback on mid-batch corrupt JSONL (`0` partial output directories, `0` leftover `.staging-*`/`.lock` files), and clean retry into `70,999` videos (`2026-10-15`).
