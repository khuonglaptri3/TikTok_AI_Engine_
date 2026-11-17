# TikTok_AI_Engine_ — AI development and demonstration resources

- Owner decision: 2026-11-16; one AI Engineer (Trần Đình Khương), modular AI packages/pipelines, FastAPI, and one ASGI-mounted Gradio UI (`/demo/`).
- Current [milestone plan](TikTok_AI_Engine_Milestone.md) and [AGENTS.md](../../AGENTS.md) define the active scope and reporting rules.

## 1. Local CPU-first development

Use available local CPU resources and measure every active stage via `StageTimer` (`ms`). Keep Python 3.11+ compatibility across core packages (`fastapi`, `pydantic`, `gradio`, `pandas`, `pyarrow`, `numpy`, `httpx`). Heavy optional runtime dependencies (`qdrant-client`, `redis`, `faster-whisper`, `librosa`, `yt-dlp`, `TikTokApi`) are isolated behind clean adapters so core analytics, Vietnamese NFC BM25 CSR search (`p95 = 21.0 ms`), Seeding/ABSA baselines, and `$0` `offline_grounded` script generation run immediately without requiring GPU hardware or Docker daemons.

## 2. Model & storage execution profile

| Component | Local development | Optional Docker / Online profile |
| --- | --- | --- |
| Gold Corpus & Niche Analytics | In-process PyArrow/Pandas over Snappy Parquet (`data/corpus/<snapshot>/`) | Optional DuckDB SQL / read-only volume mount |
| Sparse & Dense Retrieval | Local pickle-free CSR Okapi BM25 (`artifacts/indexes/bm25-v1/`) + Phrase/Aspect Reranker | Docker `Qdrant v1.20.0` (`Hybrid RRF` + payload filters) |
| Voice & Seeding / ABSA | Rule/shingle Seeding Cleanser + Vietnamese F&B 4-Aspect Lexicon Baseline (`$0`) | CPU `faster-whisper` (`int8`) + `Librosa` + ONNX `BGE-M3` + batched Gemini Free-Tier |
| Grounded Script Synthesis | `offline_grounded` blueprint synthesizer (`$0`, zero API calls) | `gemini_free` (`gemini-2.5-flash`, `<= 2` calls/turn, `15 RPM` sliding window) |
| API & Demo UI | Single Uvicorn process serving FastAPI + `/demo/` Gradio 6 workspace | `infra/compose/docker-compose.yml` (`qdrant` + `redis` + `api`) |

## 3. Dual-tier data storage & Git hygiene

1. **Git-Tracked Artifacts (`< 1 MB`):** Source code (`apps/`, `packages/`, `pipelines/`), tests (`tests/`), planning & milestone reports (`docs/`), corpus checksum manifests (`data/corpus/*/manifest.json`), evaluation queries (`data/evaluation/v1/queries.jsonl`), and frozen JSON benchmark reports (`artifacts/benchmarks/*.json`).
2. **Local-Only Gitignored Assets (`~1.56 GB`):**
   - Upstream historical datasets (`data/raw/`, `data/interim/`, `data/processed/`, `data/transcripts/`, `data/foods-and-locations/`, `data/content_analysis/`, `data/legacy_app_data/`) and `archive/legacy_coursework/`.
   - Fresh 4-month incremental captures (`data/raw_incremental/`), Gold Parquet binaries (`data/corpus/*/*.parquet`), and compiled CSR index binaries (`artifacts/indexes/`).
   - Recreate Gold Parquet and BM25 index artifacts deterministically on any machine holding `data/` via:
     ```bash
     python3 scripts/dev.py build-corpus
     python3 scripts/dev.py build-index
     python3 scripts/dev.py benchmark
     ```

## 4. Measurements & cost discipline

- Record active stage latencies (`domain_gate_ms`, `filter_ms`, `bm25_ms`, `fusion_ms`, `rerank_ms`, `llm_synthesis_ms`, `guardrail_ms`, `total_ms`) separately from frozen offline evaluation reports (`artifacts/benchmarks/`).
- Authorized cloud/GPU spend is strictly `USD 0`. Free-Tier Gemini quota exhaustion returns bounded `429 QUOTA_BLOCKED`; missing `.env` key returns `503 PROVIDER_KEY_MISSING`. Never enable paid fallbacks or hardcode keys in source files.

## 5. Official references

- [FastAPI Response Models](https://fastapi.tiangolo.com/tutorial/response-model/)
- [Gradio Mounting inside FastAPI](https://www.gradio.app/docs/gradio/mount_gradio_app)
- [Qdrant Hybrid & Filtered Search Documentation](https://qdrant.tech/documentation/concepts/hybrid-queries/)
