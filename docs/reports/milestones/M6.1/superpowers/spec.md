# M6.1 — CPU Dense & Hybrid Retrieval Pilot Specification

- **Task ID:** `M6.1` (Text-Only Spike on CPU)
- **Primary Owner:** Nguyễn Việt Nguyên (`N`)
- **Peer Reviewer:** Trần Đình Khương (`K`)
- **Requirement Source:** [TikTok_AI_Engine_Milestone.md](../../../../planning/TikTok_AI_Engine_Milestone.md) (`M6.1`)
- **Date:** 2026-11-18 (Asia/Ho_Chi_Minh)

## Scope

Build and measure a CPU-feasible **populated dense vector index + Reciprocal Rank Fusion (RRF) hybrid retrieval pipeline** over at most **5,000** eligible transcribed records (`<= 5,000`), enforcing identical corpus, metadata filter, and query parity across `bm25`, `dense`, and `hybrid_rrf`. Also extend `QdrantDenseAdapter` with collection creation and vector upsert support so the same populated embeddings can sync to Qdrant when Docker Qdrant is running.

## Technical Design & Acceptance Criteria

1. **CPU-feasible dense encoder (`packages/retrieval/dense/encoder.py`):**
   - Provide a pluggable `DenseTextEncoder` abstraction supporting optional external neural backends (`fastembed`, `sentence-transformers` with E5 `query:` / `passage:` prefixes) plus a zero-dependency deterministic CPU **`TruncatedSvdDenseEncoder`** (`scipy.sparse.linalg.svds` over Vietnamese NFC TF-IDF word + character n-grams, L2-normalized `float32` vectors) that runs cleanly offline in `< 8 GiB` RAM.
2. **Populated versioned dense index (`packages/retrieval/dense/local_index.py` & `pipelines/build_dense_sparse_index/dense.py`):**
   - Enforce `max_records <= 5000`, reject output collisions (`FileExistsError`), save pickle-free artifacts (`embeddings.npy`, `video_ids.json`, `encoder_artifacts.npz`/`vocab.json`, `dense-receipt.json` with SHA256 hashes, `corpus_snapshot_id`, `build_time_sec`, `peak_rss_mb`, and `index_bytes`).
   - Implement exact metadata-filtered cosine search (`allowed_video_ids`) matching `QdrantDenseAdapter.search_vectors` semantics.
3. **Qdrant population & Hybrid service integration (`packages/retrieval/dense/qdrant_adapter.py`, `packages/retrieval/service.py`):**
   - Add `ensure_collection(...)` and `upsert_vectors(...)` to `QdrantDenseAdapter`.
   - Wire optional `dense_index` + `dense_encoder` into `HybridRetrievalService` and `HybridRetrievalService.from_dirs(...)` so `mode="dense"` and `mode="hybrid_rrf"` work locally on CPU even without a Docker Qdrant daemon.
4. **Measured parity benchmark (`pipelines/benchmark_retrieval/dense_hybrid_pilot.py`):**
   - Restrict all three backends (`bm25`, `dense`, `hybrid_rrf`) to the **exact same populated `<= 5,000`-record ID set**, identical `_resolve_candidate_pool` metadata filters, and identical queries.
   - Measure build time, index bytes, peak RSS RAM (`<= 8 GiB`), 100-request warm `p50`/`p95` latency (`<= 1,000 ms`), and paired `delta_mrr@10` / `delta_ndcg@10` with 95% paired bootstrap confidence intervals.
   - Recommend retaining the simplest backend (`bm25`) if dense/hybrid shows no justified quality/resource gain.
5. **Honest Milestone Boundaries:** Keep `M6.1` status `IN_PROGRESS` until `M2.2`'s frozen human-judged test set (`40` queries), optional multimodal voice segments (`M4.G`/`M5.G`), and `K` peer review of parity/cost evidence are completed.
