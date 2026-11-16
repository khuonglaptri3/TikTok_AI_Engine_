# 03. AI Engineer Architecture Specification (SenticRAG-Aligned)

- **Status:** DRAFT FOR OWNER REVIEW
- **Date:** 2026-11-16
- **Owner Role:** Single AI Engineer (AI-only scope, typed FastAPI + lightweight Gradio `/demo/`, zero-cost Gemini Free-Tier profile)
- **Reference Architecture:** `SenticRAG — Retrieval-Augmented Aspect Sentiment & Feedback Intelligence Engine`
- **Chosen Stack Decisions:**
  1. **Serving & UI:** Single FastAPI service + mounted Gradio UI (`/demo/`) via in-process ASGI transport (displaying Niche Micro-Benchmarks, Video Citations, Grounded Scripts, Shooting Notes, and Per-Stage Latency `ms`). No login, user accounts, or CRUD bloat.
  2. **Storage & Infrastructure:** Docker Compose (`Qdrant v1.20.0` for Dense Vectors + `Redis 7` for sliding-window rate-limiting & bounded cache) + `DuckDB` (in-process OLAP over immutable Parquet corpus snapshots) + local `BM25` (`rank-bm25`).

---

## 1. Purpose & Core Value Loop

Transform the legacy `21KHDL-TikTok-Analytics` student repository (disconnected Streamlit BI pages + static LLM prompt templates) into a production-disciplined **Evidence-Based Viral Content Intelligence Engine** for Vietnamese F&B TikTok, operating on a closed-loop 3-layer lifecycle:

| Value Layer | User Question | Technical Mechanism | Data Scope | Verified Output |
| :--- | :--- | :--- | :--- | :--- |
| **1. Quantitative** | *"What is the performance baseline in this F&B niche?"* | `DuckDB` aggregation over immutable Gold Parquet (`packages/analytics`) | 100% Corpus (`70,996` videos, `264` creators, `23,448` POIs) | Niche Micro-Benchmark: median views, IQR duration, median `word_per_second`, top posting hours by median engagement, `viral_multiplier` distribution. |
| **2. Qualitative** | *"Why did outperforming videos in this niche win?"* | Metadata Filter + **Hybrid Retrieval** (`Qdrant` Dense + `BM25` Lexical + `RRF` + `Cross-Encoder` Rerank) sorted by `viral_multiplier` | Enriched Corpus (`~22,516` transcribed videos) | Top-$K$ Viral Evidence Cards with verified **Citations** (`@author`, `video_id`, TikTok URL, `viral_multiplier`, `hook_text`, `body_beats`, `cta_text`). |
| **3. Actionable** | *"How should I script and shoot my video?"* | Structured Gemini Synthesis + Deterministic Timeline & Guardrail Verifier (`packages/script_engine`) | Niche Benchmark + Top-$K$ Evidence Pack + User Intent | Scene-by-scene Script + Shooting Guide with recalculated `mm:ss` timestamps, explicit `citation_video_ids` per section, guardrail check status, and stage timings. |

---

## 2. Target Monorepo Directory Structure

```text
21KHDL-TikTok-Analytics/
├── .env                                       # Ignored local secrets (GEMINI_API_KEY only here)
├── .env.example                               # Committed environment template
├── .gitignore                                 # Blocks .env, .venv, artifacts/, data/raw/, __pycache__
├── .dockerignore
├── AGENTS.md                                  # AI-only scope, zero-cost rules & milestone reporting spec
├── Makefile                                   # install, lint, typecheck, test, check-secrets, run-api, run-demo
├── pyproject.toml                             # Poetry/PEP 621 metadata + ruff + mypy + pytest configs
│
├── apps/                                      # Thin Serving & UI Runtimes (zero raw data munging)
│   ├── api/
│   │   └── app/
│   │       ├── main.py                        # FastAPI app factory (/health/live, /health/ready, /api/v1/*)
│   │       ├── dependencies/                  # Settings, Qdrant, Redis, DuckDB & LLM client injection
│   │       ├── middleware/                    # Redis rate-limiter, request ID & stage latency tracker
│   │       ├── routers/                       # benchmark.py, retrieval.py, script.py, evaluation.py
│   │       └── schemas/                       # HTTP request/response wrappers re-exporting data_contracts
│   └── demo/
│       ├── main.py                            # Mounts Gradio at /demo/ onto FastAPI app
│       ├── ui.py                              # 3-tab Gradio workspace (Search/Rerank, Script Studio, Benchmarks)
│       ├── presentation.py                    # Evidence cards, citation badges, timing breakdown formatters
│       └── theme.py                           # Packaged local theme (no remote font dependencies)
│
├── packages/                                  # Domain-Driven Core AI Packages
│   ├── common/
│   │   ├── settings/                          # Pydantic BaseSettings (.env loader, fail-closed validation)
│   │   ├── logging/                           # Structured JSON logging + per-stage latency & token telemetry
│   │   └── exceptions/                        # Typed bounded errors (QuotaBlockedError, CorpusNotReadyError...)
│   ├── data_contracts/                        # Strict Pydantic v2 contracts across all module boundaries
│   │   ├── corpus.py                          # CreatorRecord, VideoEnrichedRecord, CorpusManifest
│   │   ├── query.py                           # NicheIntentFilter, RetrievalRequest, ScriptGenerationRequest
│   │   ├── retrieval.py                       # VideoCitation, EvidenceCard, HybridSearchResult
│   │   ├── analytics.py                       # NicheBenchmarkSummary, DurationProfile, PostingWindowStat
│   │   ├── script.py                          # ScriptBeat, ShootingNote, GroundedScriptResponse, GuardrailReport
│   │   └── errors.py                          # CanonicalErrorResponse
│   ├── taxonomy/                              # F&B Vietnamese domain normalization
│   │   ├── food_hierarchy.py                  # 7 top-level categories + normalized dish tags
│   │   ├── location_poi.py                    # Priority resolver: TikTok POI GPS > standardized LLM location
│   │   └── context_enums.py                   # VideoFormat, PriceTier, Occasion, TargetPersona, DurationBucket
│   ├── analytics/                             # Quantitative Layer (DuckDB over Gold Parquet)
│   │   ├── engine.py                          # Read-only parameterized DuckDB queries (zero SQL injection)
│   │   └── benchmarks.py                      # Creator median baselines, viral_multiplier, niche percentiles
│   ├── retrieval/                             # Qualitative Layer (Hybrid RAG)
│   │   ├── sparse/                            # NFC-normalized Vietnamese diacritic-preserving BM25
│   │   ├── dense/                             # Multilingual E5 / BGE-M3 embeddings + Qdrant client adapter
│   │   ├── fusion/                            # Reciprocal Rank Fusion (RRF) + viral_multiplier score boosting
│   │   ├── rerank/                            # Local Cross-Encoder reranker (mmarco-mMiniLMv2 / bge-reranker)
│   │   └── citations/                         # TikTok URL builder & offset/quote provenance verifier
│   ├── llm/                                   # Foundation Model Layer
│   │   ├── clients/                           # Gemini client with Redis rate-limit, timeout & 0-paid-fallback
│   │   ├── prompts/                           # Versioned prompt templates (.md / .yaml)
│   │   ├── structured_outputs/                # Intent parser & JSON-schema enforced script synthesizer
│   │   └── guardrails/                        # Word-per-second duration recalculator, cliché filter, citation check
│   └── script_engine/                         # Actionable Layer Orchestrator
│       └── service.py                         # Coordinates Intent -> Analytics + Hybrid Retrieval -> Synthesis -> Guardrail
│
├── pipelines/                                 # Reproducible CLI Workflows (python -m pipelines.<name>)
│   ├── sanitize_repo/                         # Scans & strips leaked API keys; verifies clean working tree
│   ├── build_gold_corpus/                     # Merges final_raw_videos.csv (restoring 23k POIs) + 23k transcripts -> snapshot
│   ├── enrich_taxonomy_batch/                 # Resumable checkpointed batch job extracting occasion, price_tier, hook/body/cta
│   ├── build_dense_sparse_index/              # Builds BM25 snapshot + Qdrant collection + immutable build receipt
│   ├── benchmark_retrieval/                   # Dev/Eval split benchmark for BM25 vs Dense vs Hybrid RRF + Rerank
│   └── eval_script_generation/                # Evaluates duration compliance, schema pass rate & citation grounding
│
├── configs/
│   ├── environments/                          # local.yaml, ci.yaml, docker.yaml
│   ├── retrieval/                             # RRF k, candidate_k, viral_multiplier boost weights
│   └── evaluation/                            # Frozen rubrics and benchmark configurations
│
├── data/
│   ├── raw/                                   # Read-only legacy raw JSON/CSV/transcripts (gitignored)
│   ├── corpus/
│   │   └── <YYYYMMDDTHHMMSSZ-hash>/           # Immutable Gold snapshot: dim_creators.parquet, fact_videos.parquet, manifest.json
│   └── evaluation/
│       └── v1/                                # Golden queries, qrels.jsonl, script_eval_cases.jsonl
│
├── artifacts/                                 # Ignored local runtime indexes, BM25 snapshots, build receipts, checkpoints
│
├── infra/
│   ├── compose/
│   │   └── docker-compose.yml                 # Qdrant (6333/6334) + Redis (6379) + API (8000) with healthchecks
│   └── docker/
│       └── Dockerfile.api                     # Non-root Python 3.11 slim image
│
├── scripts/
│   ├── dev.py                                 # Unified cross-platform developer CLI (install, lint, typecheck, test, run-demo)
│   ├── check_secrets.py                       # Pre-commit / CI scanner blocking AIzaSy* and token leaks
│   └── smoke_api.py                           # Liveness, readiness, Qdrant/Redis & bounded search smoke check
│
├── tests/
│   ├── unit/                                  # Taxonomy, viral_multiplier math, timeline calculator, guardrails
│   ├── contract/                              # Pydantic schema parity & OpenAPI export checks
│   ├── integration/                           # Live Qdrant + Redis + DuckDB container integration tests
│   ├── eval/                                  # Retrieval Recall@K/MRR/nDCG & script guardrail regression tests
│   └── smoke/                                 # End-to-end ASGI /demo/ and /api/v1/* turn smoke tests
│
└── docs/
    ├── architecture/                          # System architecture & data-flow specs
    ├── data-cards/                            # Provenance, selection bias caveats (2023-2025 window) & schema docs
    └── reports/
        └── milestones/                        # SenticRAG convention: <TASK-ID>/{README.md, evidence/, superpowers/{spec.md, plan.md}}
```

---

## 3. Environment, Settings & Infrastructure Contracts

### 3.1. `.env.example` Specification
All hardcoded keys across the 16 legacy files are eliminated. Runtime configuration is strictly typed with prefix `TIKTOK_RAG_` (except standard `GEMINI_API_KEY`):

```ini
# === Provider Credentials (Never commit .env; Free-Tier USD0 spend cap) ===
GEMINI_API_KEY=

# === Application Profile ===
TIKTOK_RAG_ENV=local
TIKTOK_RAG_CORPUS_DIR=data/corpus/20261116T000000Z-v1
TIKTOK_RAG_BM25_INDEX_DIR=artifacts/indexes/bm25-v1

# === Docker Infrastructure ===
TIKTOK_RAG_QDRANT_URL=http://127.0.0.1:6333
TIKTOK_RAG_QDRANT_COLLECTION=tiktok_fnb_videos_v1
TIKTOK_RAG_REDIS_URL=redis://127.0.0.1:6379/0

# === Local Retrieval & Reranking Models ===
TIKTOK_RAG_EMBEDDING_MODEL=intfloat/multilingual-e5-base
TIKTOK_RAG_EMBEDDING_DEVICE=cpu
TIKTOK_RAG_RERANKER_MODEL=cross-encoder/mmarco-mMiniLMv2-L12-H384-v1
TIKTOK_RAG_RERANKER_ENABLED=true

# === Bounded LLM & Safety Controls ===
TIKTOK_RAG_GEMINI_FAST_MODEL=gemini-2.5-flash
TIKTOK_RAG_MAX_LLM_CALLS_PER_TURN=2
TIKTOK_RAG_LLM_DEADLINE_SECONDS=30
TIKTOK_RAG_RATE_LIMIT_RPM=15
```

### 3.2. `infra/compose/docker-compose.yml`
Mirrors `SenticRAG`:
- **`qdrant`** (`qdrant/qdrant:v1.20.0`, ports `6333:6333`, `6334:6334`, persistent volume `qdrant_data`, TCP healthcheck).
- **`redis`** (`redis:7-alpine`, port `6379:6379`, persistent volume `redis_data`, `redis-cli ping` healthcheck — backs sliding-window RPM rate-limiting for Gemini Free-Tier protection and query benchmark caching).
- **`api`** (`infra/docker/Dockerfile.api`, port `8000:8000`, `depends_on` healthy `qdrant` and `redis`, mounts read-only `data/corpus/` and `artifacts/indexes/`).

---

## 4. Gold Corpus Schema & Mathematical Definitions (`M1`)

### 4.1. Unified Gold Tables (`data/corpus/<snapshot-id>/`)
1. **`dim_creators.parquet` (`264` rows):**
   - `author_id` (PK, `str`), `unique_id` (`str`), `nickname`, `verified` (`bool`), `follower_count`, `heart_count`, `lifetime_video_count`, `follower_tier` (`low | mid | high` by 33%/66% quantiles).
   - Sample-derived robust baselines (from the 70-week corpus): `sample_video_count`, `median_play_count`, `median_engagement_rate`, `median_duration_sec`, `avg_videos_per_week`.
2. **`fact_videos.parquet` (`70,996` rows total; `~22,516` rows `has_transcript=True`):**
   - **Core Metadata & Stats:** `video_id` (PK, `str`), `author_id` (FK), `unique_id`, `create_time` (`datetime64[ns, Asia/Ho_Chi_Minh]`), `year_week`, `desc_raw`, `desc_clean`, `hashtags` (`list[str]`), `hashtag_count`, `duration_sec`, `duration_bucket` (`ultra_short_lt20s | short_20_45s | medium_45_90s | long_gt90s`), `play_count`, `digg_count`, `comment_count`, `share_count`, `collect_count`, `is_ad` (`bool`), `is_ec_video` (`bool | None`), `playlist_id` (`str | None`).
   - **Restored TikTok Official POI (`23,448` non-null rows from `final_raw_videos.csv`):** `poi_name`, `poi_address`, `poi_city`, `poi_category_tiny`.
   - **Canonical Metrics (Unified across the entire codebase):**
     - `engagement_rate` $= \frac{\text{digg\_count} + \text{comment\_count} + \text{share\_count} + \text{collect\_count}}{\max(\text{play\_count}, 1)}$
     - `viral_multiplier` $= \frac{\text{play\_count}}{\max(\text{creator\_median\_play\_count}, 1000)}$
   - **Resolved Location (`location_source = poi_gps | llm_inferred | unknown`):** `city_norm`, `district_norm`, `region` (`north | central | south | international | unknown`). Priority rule: if `poi_city` / `poi_address` is present, resolve city/district from GPS POI first to eliminate dish-name location hallucinations (e.g., *"Bún đậu Hà Nội ở Quận 7"* $\rightarrow$ `city_norm="hồ chí minh"`, `district_norm="quận 7"`).
   - **Transcript & Script Anatomy (`~22,516` rows):** `has_transcript` (`bool`), `transcript`, `word_count`, `word_per_second`, `video_format`, `food_category`, `dish_entities` (`list[str]`), `price_tier`, `occasion` (`list[str]`), `target_persona`, `hook_text`, `body_beats` (`list[str]`), `cta_text`, `rag_document` (`str`).
3. **`manifest.json`:** Records `snapshot_id`, `created_at`, git commit SHA, exact row counts, SHA256 checksums of both Parquet files, and known dataset scope caveats (`2023-11-25` to `2025-03-19`, active-2025 creator survivorship note).

---

## 5. API Contracts, Hybrid Retrieval & Grounded Synthesis (`M2` – `M4`)

### 5.1. Typed FastAPI Endpoints (`apps/api/`)
| Endpoint | Method | Purpose |
| :--- | :---: | :--- |
| `/health/live` | `GET` | Process liveness (`200 OK`). |
| `/health/ready` | `GET` | Verifies Gold corpus manifest checksum, DuckDB handle, Qdrant collection readiness, and Redis ping (`503` with `CanonicalErrorResponse` on failure; never falls back to fake data). |
| `/api/v1/demo/modules` | `GET` | Reports active status/versions of Corpus, BM25, Qdrant Dense, Reranker, and Gemini profile. |
| `/api/v1/analytics/niche-benchmark` | `POST` | Runs parameterized DuckDB query for `NicheIntentFilter` $\rightarrow$ returns sample size $N$, median views, IQR duration, median `word_per_second`, optimal hashtag IQR, top 3 posting hours by median views, and top POI neighborhoods. |
| `/api/v1/retrieval/search` | `POST` | Supports `mode = bm25 | dense | hybrid_rrf` + soft-relaxation metadata filter (`duration_bucket` & `video_format` strict; `occasion`, `price_tier`, `city_norm` soft) + optional Cross-Encoder rerank + `viral_multiplier` log-boost $\rightarrow$ returns Top-$K$ `EvidenceCard` items and stage latencies (`filter_ms`, `sparse_ms`, `dense_ms`, `rerank_ms`, `total_ms`). |
| `/api/v1/script/generate` | `POST` | Executes: (1) Intent extraction (1st Gemini call or explicit UI filters), (2) Niche Benchmark + Hybrid Retrieval (`top_k=5`), (3) Structured Script & Shooting Synthesis (2nd Gemini call) grounded strictly in retrieved `hook_text` / `body_beats` / `cta_text` + POI/format context, (4) Deterministic Python recalculation of `mm:ss-mm:ss` per scene using niche `median_word_per_second` + Guardrail verification. |
| `/api/v1/evaluation/summary` | `GET` | Serves frozen, receipt-verified retrieval (`Recall@10`, `MRR@10`, `nDCG@10`) and script generation (`duration_compliance_rate`, `citation_validity_rate`) benchmark reports. |

### 5.2. Gradio Demonstration Workspace (`apps/demo/`, mounted at `/demo/`)
Follows `SenticRAG` UI principles (responsive side-by-side desktop layout, zero auth, explicit status strip, clear failure reporting):
1. **Tab 1 — Viral Evidence Retrieval & Reranking:** Input dish/idea + optional filters (`Format`, `Duration Bucket`, `Occasion`, `Price Tier`, `City`, `Mode: BM25 / Dense / Hybrid RRF + Rerank`). Displays Top-5 real TikTok `EvidenceCard` results with original TikTok URLs, `@author`, `viral_multiplier` badge (e.g., `6.4x creator median`), extracted `hook_text` / `body_beats` / `cta_text`, and measured stage latencies.
2. **Tab 2 — Evidence-Grounded Script & Shooting Studio:** Input video brief $\rightarrow$ displays side-by-side: **(Left)** Niche Micro-Benchmark card + Cited Viral Reference Videos, and **(Right)** Generated Scene-by-Scene Script (`time_range`, `visual_angle`, `dialogue`, `cited_source_ids`), Format-Specific Shooting Notes, Guardrail Verification Strip, and Markdown export.
3. **Tab 3 — Frozen Evaluation & Corpus Audit:** Displays verified `manifest.json` stats and frozen retrieval/generation benchmark tables without rerunning paid/heavy jobs live.

---

## 6. Legacy Repository Migration & Disposal Rules

- **Immediate Security Action (`M0`):** Run `pipelines.sanitize_repo` + `scripts/check_secrets.py` to purge hardcoded keys across all 16 legacy files; move `development/apis.py` and `development/test_api.ipynb` out of active code and rotate/revoke leaked keys in Google AI Studio.
- **Archive / Retire (`archive/legacy_2025_coursework/` or git history):** Retire `notebooks/`, `reports/` (LaTeX course report), `slides/`, `src/app/` (multi-page Streamlit monolith), and duplicate CSV/Parquet copies scattered across `data/interim/`, `data/processed/`, `data/ScriptGen-data/`, `src/app/*/data/`.
- **Preserve Read-Only Inputs (`data/raw/`):** Retain `data/raw/`, `data/interim/final_raw_videos.csv`, `data/interim/final_raw_users.csv`, `data/transcripts/*.json` (`23,122` files), and `data/foods-and-locations/*.json` (`14,252` files) as immutable upstream inputs for `pipelines.build_gold_corpus`.

---

## 7. Milestone Decomposition Preview (For Upcoming Implementation Plan)

- **`M0` — Repo Hygiene, Secret Purge & Monorepo Foundation:** `.env.example`, `pyproject.toml`, `Makefile`, `scripts/dev.py`, `scripts/check_secrets.py`, `packages/common/settings`, `packages/data_contracts`, `infra/compose/docker-compose.yml` (`Qdrant` + `Redis`), `AGENTS.md`.
- **`M1` — Unified Gold Corpus & Context Enrichment:** `pipelines/build_gold_corpus` (recovering `23,448` POIs + merging `~22,516` transcripts + computing `viral_multiplier` & `manifest.json`) + `pipelines/enrich_taxonomy_batch` (`occasion`, `price_tier`, `hook_text / body_beats / cta_text`).
- **`M2` — Hybrid Retrieval & Reranking Engine:** `packages/retrieval` (`BM25` + `Qdrant` Dense + `RRF` + `Cross-Encoder` Rerank) + `pipelines/build_dense_sparse_index` + `pipelines/benchmark_retrieval`.
- **`M3` — DuckDB Niche Analytics & Grounded Script Engine:** `packages/analytics` + `packages/llm` (bounded Gemini Free-Tier client + guardrails) + `packages/script_engine` + `pipelines/eval_script_generation`.
- **`M4` — Typed FastAPI Service & Gradio `/demo/` Workspace:** `apps/api`, `apps/demo`, container verification, smoke/contract/eval test suite.
