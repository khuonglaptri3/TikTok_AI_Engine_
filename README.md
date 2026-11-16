# ViralFoodRAG — Evidence-Based TikTok Content Intelligence & Script Engine

Production-structured AI Engineering monorepo transforming `70,996` Vietnamese F&B TikTok videos (`264` creators, `23,448` GPS POIs, `21,748` spoken transcripts) into **Columnar Niche Micro-Benchmarks**, **Vietnamese Hybrid Evidence Retrieval**, and **Citation-Grounded Video Script Synthesis**.

---

## Architecture Highlights

- **Immutable Gold Corpus (`data/corpus/20261116_v1/`):** Non-destructively unifies `cleaned_video_info.parquet` (`70,996` videos), `cleaned_user_info.parquet` (`264` creators), recovered official TikTok GPS POIs from `final_raw_videos.csv` (`23,448` venues), `23,122` transcript JSONs, and legacy food/content annotations — guarded by fail-closed SHA256 verification (`manifest.json`).
- **Columnar Niche Micro-Benchmark Engine (`packages/analytics/`):** Computes real-time empirical medians & IQRs (`median_plays`, `duration_q25..q75`, `median_word_per_second`, optimal hashtag counts, top posting hours, and top GPS POI venues) sliced by `video_format`, `food_category`, `price_tier`, `occasion`, and `city_norm`.
- **Vietnamese NFC Hybrid Retrieval & Reranking (`packages/retrieval/`):** Pickle-free CSR Okapi BM25 over `391,042` NFC-normalized Vietnamese unigrams & bigrams + optional Qdrant dense vectors (`hybrid_rrf`), creator-normalized `viral_multiplier` log-boost, and field-aware phrase/aspect reranking (`Recall@10 = 0.7094`, `MRR@10 = 0.8127`, `nDCG@10 = 0.7083`, `p95 = 21.0 ms`).
- **Bounded Grounded Script Engine (`packages/script_engine/` & `packages/llm/`):** Replaces disconnected static prompt templates with retrieval-augmented script synthesis (`gemini_free` bounded to Free-Tier RPM or `$0` `offline_grounded` blueprint mode), deterministic `mm:ss` beat timeline recalculation from empirical `word_per_second`, citation verification, and anti-cliché guardrails.
- **Single-Port API + Thin Gradio Demo (`apps/api/` + `apps/demo/`):** FastAPI service with canonical typed contracts (`Pydantic v2`) and a 3-tab Gradio 6 workspace mounted at `/demo/` over in-process ASGI transport.

---

## Repository Layout

```text
├── apps/
│   ├── api/                        # FastAPI service (/health/*, /api/v1/*)
│   └── demo/                       # Thin Gradio 6 UI mounted at /demo/ via ASGI transport
├── packages/
│   ├── common/                     # Typed .env settings, StageTimer, bounded exceptions
│   ├── data_contracts/             # Strict Pydantic v2 request/response/manifest contracts
│   ├── taxonomy/                   # VN F&B hierarchy, GPS POI resolver, context extractors
│   ├── analytics/                  # Fail-closed corpus loader & NicheAnalyticsEngine
│   ├── retrieval/                  # NFC BM25 CSR, Qdrant adapter, RRF fusion, reranker
│   ├── llm/                        # Sliding-window RPM Gemini client, prompts, guardrails
│   └── script_engine/              # Evidence-grounded script synthesis orchestrator
├── pipelines/
│   ├── build_gold_corpus/          # Builds dim_creators + fact_videos + manifest.json
│   ├── build_dense_sparse_index/   # Builds pickle-free CSR BM25 index (21,748 videos)
│   ├── benchmark_retrieval/        # Evaluates Recall@10, MRR@10, nDCG@10, p95 latency
│   └── enrich_taxonomy_batch/      # Optional resumable Free-Tier batch enricher
├── configs/                        # Default retrieval & ranking configuration
├── docs/data-cards/                # Dataset lineage, metrics, and caveats
├── infra/                          # Docker Compose (Qdrant + Redis + API) & Dockerfile.api
├── ReFactor_structure/             # Full audit, gap analysis, architecture spec & plan
├── archive/legacy_coursework/      # Preserved original coursework notebooks, app, and docs
└── tests/                          # Unit, contract, evaluation, and ASGI smoke tests
```

---

## Quickstart

### 1. Environment Configuration
```bash
cp .env.example .env
# Optional: set GEMINI_API_KEY in .env to enable live 'gemini_free' LLM synthesis.
# Without GEMINI_API_KEY, analytics, retrieval, and 'offline_grounded' script synthesis run 100% locally at $0 cost.
```

### 2. Reproducible Artifacts & Verification
```bash
python3 scripts/dev.py check-secrets
python3 scripts/dev.py build-corpus
python3 scripts/dev.py build-index
python3 scripts/dev.py benchmark
python3 scripts/dev.py typecheck
python3 scripts/dev.py test
```

### 3. Launch API + Interactive `/demo/` Workspace
```bash
python3 scripts/dev.py run-demo
```
- **Gradio Interactive Studio:** `http://127.0.0.1:8000/demo/`
- **OpenAPI / Swagger Docs:** `http://127.0.0.1:8000/docs`
- **Readiness Probe:** `http://127.0.0.1:8000/health/ready`
