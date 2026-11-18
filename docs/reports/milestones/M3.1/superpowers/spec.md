# M3.1 — Repeated Dual-Sink Ingestion Repair Specification

- **Task ID:** `M3.1`
- **Primary Owner:** Nguyễn Việt Nguyên (`N`)
- **Peer Reviewer:** Trần Đình Khương (`K`)
- **Requirement Source:** [TikTok_AI_Engine_Milestone.md](../../../../planning/TikTok_AI_Engine_Milestone.md) (`M3.1`)
- **Date:** 2026-11-18 (Asia/Ho_Chi_Minh)

## Scope

Repair `pipelines/ingest_incremental_to_gold/` and its verification checks ahead of any live 120-day acquisition pilot, ensuring fail-closed input validation, real-Parquet enrichment compatibility, typed multimodal schemas when modalities are missing, complete staging verification across all 5 tables, and safe recovery from interrupted publication.

## Acceptance Criteria

1. **Sequential, replay & enrichment continuity:** Batches `A`, `B`, `replay`, `empty batch`, and explicit same-video `update_existing=True` transcript/comment enrichment retain/deduplicate keyed video, voice, comment, and ABSA rows while keeping base snapshot bytes identical and rejecting output collisions (`FileExistsError`).
2. **Fail-closed timestamps & accurate window provenance:** Invalid/unparseable `create_time` raises validation failure rather than substituting wall-clock UTC time; empty/no-new-row batches preserve `base_manifest.date_window_end` while non-empty batches advance `date_window_end` to `max(base_window_end, max_batch_date)`.
3. **Real Parquet enrichment compatibility:** `update_existing=True` normalizes pandas `NaN`/`pd.NA` nullable fields and `numpy.ndarray` list fields when preserving base rows from real Gold snapshots (e.g., `20261118_taxonomy_fix_v1`).
4. **Missing modalities:** Batches omitting `transcript`, `whisper_segments`, `pitch_std`/`energy_cv`, or `comments` produce well-typed non-null Arrow Parquet schemas for `fact_voice_segments.parquet`, `fact_comments.parquet`, and `fact_absa_reviews.parquet` that append cleanly with subsequent populated batches.
5. **Interrupted publication & CLI support:** Interrupted ingestion (bad JSONL line mid-batch or staged write exception) publishes zero partial target files, cleans `.staging-*` and `.publish.lock`, preserves base bytes, and retries cleanly; staging verification validates all 5 tables; CLI `__main__.py` exposes `--update-existing`.
6. **Peer review:** Independent check by Trần Đình Khương (`K`) on base preservation and replay receipts before marking `M3.1` `COMPLETE`.
