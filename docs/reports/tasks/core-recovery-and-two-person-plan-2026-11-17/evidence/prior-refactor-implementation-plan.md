# ViralFoodRAG (SenticRAG-Aligned Refactor) Implementation Plan

> **For agentic workers:** REQUIRED SUB-SKILL: Use superpowers:executing-plans to implement this plan task-by-task. Steps use checkbox (`- [ ]`) syntax for tracking.

**Goal:** Refactor `21KHDL-TikTok-Analytics` into a production-grade, SenticRAG-aligned AI Engineering monorepo with zero data loss across all 1.50 GB (`37,840` files) of existing assets, unified Gold Parquet corpus (`70,996` videos, `23,448` restored GPS POIs, `~22,516` merged transcripts), Hybrid Retrieval + Reranking, Niche Analytics, Grounded Script Synthesis, and a typed FastAPI + Gradio (`/demo/`) runtime.

**Architecture:** Modular Python 3.11+ monorepo split into `packages/` (strict Pydantic v2 contracts, settings, taxonomy, columnar analytics, BM25 + Qdrant hybrid retrieval, bounded Gemini LLM client & guardrails, script orchestrator), `pipelines/` (offline reproducible CLIs), `apps/api` (FastAPI), and `apps/demo` (Gradio mounted on `/demo/` via ASGI transport), backed by `infra/compose/docker-compose.yml` (`Qdrant` + `Redis` + `API`).

**Tech Stack:** Python 3.11+, FastAPI, Gradio, Pydantic v2, PyArrow/Pandas (+ DuckDB/Qdrant/Redis adapters), Google GenAI SDK (`google-genai`), Pytest, Mypy.

**Spec:** `ReFactor_structure/03_AI_ENGINEER_ARCHITECTURE_SPEC.md`

## Global Constraints

- **100% Data Preservation:** Never delete or overwrite any file inside `data/` (`37,837` files, `1,475,677,482` bytes). Preserve `src/app/trend_analysis/data/*` and `src/app/video_analysis/data/*` into `data/legacy_app_data/` and keep archived copies under `archive/legacy_coursework/`.
- **Secret Hygiene:** Purge all hardcoded `AIzaSy*` and third-party API keys across all 16 legacy files; enforce via `scripts/check_secrets.py` (`0` leaks allowed). Keep `GEMINI_API_KEY` solely in `.env` (gitignored).
- **Zero Paid Spend:** Cap Gemini usage to owner's Free-Tier (`<= 2` calls per generation turn, sliding-window RPM guard, explicit `QuotaBlockedError` / `ProviderUnavailableError` without paid fallback).
- **Fail-Closed Integrity:** Verify `manifest.json` SHA256 checksums on corpus load; never fabricate metrics or silently fall back to synthetic mock results on live routes.

## Review Focus

- Missing `GEMINI_API_KEY` at runtime: `/api/v1/analytics/niche-benchmark` and `/api/v1/retrieval/search` must still work 100% locally; `/api/v1/script/generate` must return a clear, typed `PROVIDER_KEY_MISSING` error (or explicit `deterministic_outline` mode when requested) without crashing.
- Location dish-name ambiguity (e.g., *"Bún đậu Hà Nội ở Quận 7"*): `location_poi.py` must prioritize GPS `poi_city` / district-to-city resolution (`quận 7` -> `hồ chí minh`) over noisy speech city mentions.
- Division-by-zero on creator/video metrics: `play_count == 0` or `duration_sec == 0` must never produce `inf` or `NaN` in `engagement_rate`, `viral_multiplier`, or `word_per_second`.
- Vietnamese diacritics & NFC/NFD Unicode normalization in BM25 lexical search: equivalent Unicode forms must tokenize identically while preserving Vietnamese tones.
- Legacy coursework archival: moving `src/` and `notebooks/` to `archive/legacy_coursework/` must not break any data file path or delete `ReFactor_structure/`.

---

### Task 1: Secret Sanitization, Non-Destructive Legacy Archival & Monorepo Scaffold (`M0`)

**Files:**
- Create: `scripts/check_secrets.py`, `scripts/dev.py`, `.env.example`, `.gitignore`, `.dockerignore`, `Makefile`, `pyproject.toml`, `AGENTS.md`
- Create: `infra/compose/docker-compose.yml`, `infra/docker/Dockerfile.api`, `configs/retrieval/default.json`
- Move (non-destructive): `notebooks/`, `reports/`, `slides/`, `development/`, `src/`, `Team-Plan-and-Work-Distribution.md`, `packages.txt` -> `archive/legacy_coursework/` (after scrubbing all 16 files' hardcoded keys and copying `src/app/*/data/*` to `data/legacy_app_data/`)
- Test: `tests/unit/test_secret_hygiene.py`

- [x] **Step 1:** Scrub all hardcoded API keys in the 16 legacy files, preserve `src/app/*/data/*` into `data/legacy_app_data/`, archive legacy coursework into `archive/legacy_coursework/`, and verify `data/` byte count is unchanged (`>= 1,475,677,482` bytes).
- [x] **Step 2:** Create `scripts/check_secrets.py`, `.env.example`, `.gitignore`, `.dockerignore`, `pyproject.toml`, `Makefile`, `scripts/dev.py`, `AGENTS.md`, and `infra/` Docker files.
- [x] **Step 3:** Write and run `tests/unit/test_secret_hygiene.py` verifying zero leaked `AIzaSy` keys across the entire workspace.

---

### Task 2: Common Settings, Telemetry & Canonical Data Contracts (`M0`)

**Files:**
- Create: `packages/__init__.py`, `packages/common/settings/__init__.py`, `packages/common/logging/__init__.py`, `packages/common/exceptions/__init__.py`
- Create: `packages/data_contracts/__init__.py`, `packages/data_contracts/corpus.py`, `packages/data_contracts/query.py`, `packages/data_contracts/analytics.py`, `packages/data_contracts/retrieval.py`, `packages/data_contracts/script.py`, `packages/data_contracts/errors.py`
- Test: `tests/contract/test_data_contracts.py`

- [x] **Step 1:** Implement typed environment settings loader (`AppSettings`), stage timer (`StageTimer`), and bounded domain exceptions.
- [x] **Step 2:** Implement strict Pydantic v2 contracts for corpus records, niche queries, micro-benchmarks, evidence citations, grounded script responses, and canonical errors.
- [x] **Step 3:** Run `pytest tests/contract/test_data_contracts.py -v` and verify schema validation & edge-case guards.

---

### Task 3: Vietnamese F&B Taxonomy & Unified Gold Corpus Pipeline (`M1`)

**Files:**
- Create: `packages/taxonomy/__init__.py`, `packages/taxonomy/context_enums.py`, `packages/taxonomy/food_hierarchy.py`, `packages/taxonomy/location_poi.py`, `packages/taxonomy/rule_extractor.py`
- Create: `pipelines/__init__.py`, `pipelines/build_gold_corpus/__init__.py`, `pipelines/build_gold_corpus/builder.py`, `pipelines/build_gold_corpus/__main__.py`
- Create: `pipelines/enrich_taxonomy_batch/__init__.py`, `pipelines/enrich_taxonomy_batch/__main__.py`
- Test: `tests/unit/test_taxonomy_and_corpus.py`

- [x] **Step 1:** Implement POI-priority location resolver (`quận 7` + `hà nội` -> `hồ chí minh`), 7-category food hierarchy mapper, regex/rule extractors (`price_tier`, `occasion`, `duration_bucket`, `hook_text`, `cta_text`), and safe `engagement_rate` / `viral_multiplier` formulas.
- [x] **Step 2:** Implement and execute `python3 -m pipelines.build_gold_corpus --output data/corpus/20261116_v1` merging `final_raw_videos.csv` (`23,448` POIs), `cleaned_video_info.parquet` (`70,996` rows), `cleaned_user_info.parquet` (`264` rows), `data/transcripts/*.json` (`23,122` files), `final_location_food_data.parquet` (`14,252` rows), and `content_analysis_data.parquet` (`3,004` rows), emitting `manifest.json` with SHA256 hashes.
- [x] **Step 3:** Run `pytest tests/unit/test_taxonomy_and_corpus.py -v` against both unit fixtures and the built `data/corpus/20261116_v1` snapshot.

---

### Task 4: Niche Analytics Engine & Hybrid Retrieval + Reranking (`M2` & `M3a`)

**Files:**
- Create: `packages/analytics/__init__.py`, `packages/analytics/engine.py`
- Create: `packages/retrieval/__init__.py`, `packages/retrieval/sparse/bm25.py`, `packages/retrieval/dense/qdrant_adapter.py`, `packages/retrieval/fusion/rrf.py`, `packages/retrieval/rerank/scorer.py`, `packages/retrieval/service.py`
- Create: `pipelines/build_dense_sparse_index/__init__.py`, `pipelines/build_dense_sparse_index/__main__.py`
- Create: `pipelines/benchmark_retrieval/__init__.py`, `pipelines/benchmark_retrieval/__main__.py`, `data/evaluation/v1/queries.jsonl`
- Test: `tests/unit/test_analytics_and_retrieval.py`, `tests/eval/test_retrieval_benchmark.py`

- [x] **Step 1:** Implement fail-closed corpus loader (verifying `manifest.json` SHA256) and `NicheAnalyticsEngine` computing median views, IQR duration, median `word_per_second`, optimal hashtag IQR, top posting hours by median views, and top POI neighborhoods.
- [x] **Step 2:** Implement NFC-normalized Vietnamese BM25 index builder/searcher, Qdrant HTTP adapter (graceful status reporting when Docker Qdrant is offline, full hybrid RRF when online), `viral_multiplier` log-boost, and local phrase/overlap + optional Cross-Encoder reranker.
- [x] **Step 3:** Build `artifacts/indexes/bm25-v1` over all `~22,516` transcribed videos, run `pipelines.benchmark_retrieval` to freeze real metrics into `artifacts/benchmarks/retrieval_v1.json`, and verify via `pytest`.

---

### Task 5: Bounded Gemini Client, Grounded Script Engine, FastAPI & Gradio `/demo/` (`M3b` & `M4`)

**Files:**
- Create: `packages/llm/clients/gemini.py`, `packages/llm/prompts/templates.py`, `packages/llm/guardrails/verifier.py`
- Create: `packages/script_engine/service.py`
- Create: `apps/api/app/main.py`, `apps/api/app/routers/health.py`, `apps/api/app/routers/analytics.py`, `apps/api/app/routers/retrieval.py`, `apps/api/app/routers/script.py`
- Create: `apps/demo/main.py`, `apps/demo/ui.py`, `apps/demo/presentation.py`, `README.md`
- Test: `tests/unit/test_script_guardrails.py`, `tests/smoke/test_api_and_demo.py`

- [x] **Step 1:** Implement bounded Gemini client (reads `GEMINI_API_KEY` solely from settings/.env, Redis/in-memory RPM limiter, 0 paid fallback), deterministic grounded fallback blueprint when key is absent or `mode="offline_grounded"`, `mm:ss` timeline recalculator, and cliché/citation guardrail verifier.
- [x] **Step 2:** Implement FastAPI app factory (`/health/live`, `/health/ready`, `/api/v1/demo/modules`, `/api/v1/analytics/niche-benchmark`, `/api/v1/retrieval/search`, `/api/v1/script/generate`, `/api/v1/evaluation/summary`) and mount the 3-tab Gradio workspace at `/demo/` via ASGI transport.
- [x] **Step 3:** Update root `README.md` (preserving clean SenticRAG overview style), run full `pytest`, `mypy`, `scripts/check_secrets.py`, and verify 100% preservation of all original `37,840` data files.
