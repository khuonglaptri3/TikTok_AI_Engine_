# M0.1 — Execution & Verification Plan

- **Date:** 2026-11-16
- **Task ID:** `M0.1`

## Execution Steps
1. Inventory all `data/` subdirectories and recover dropped official TikTok GPS POI columns (`poi.name`, `poi.address`, `poi.city`, `isECVideo`) from `data/interim/final_raw_videos.csv`.
2. Scrub hardcoded API keys across 16 legacy files, copy legacy app Parquet files to `data/legacy_app_data/`, and relocate coursework directories to `archive/legacy_coursework/`.
3. Implement `packages/` (`common`, `data_contracts`, `taxonomy`, `analytics`, `retrieval`, `llm`, `script_engine`, `seeding`, `absa`), `pipelines/` (`build_gold_corpus`, `build_dense_sparse_index`, `benchmark_retrieval`, `crawl_incremental`, `ingest_incremental_to_gold`), and `apps/` (`api` + `demo`).
4. Build `data/corpus/20261116_v1`, `artifacts/indexes/bm25-v1`, and `artifacts/benchmarks/retrieval_v1.json`.

## Verification Plan
- Run `python3 scripts/check_secrets.py` -> expect exit code `0`.
- Run `python3 -m mypy packages apps pipelines` -> expect `0` issues.
- Run `python3 -m pytest -v` -> expect `100%` pass across contract, unit, eval, and smoke suites.
