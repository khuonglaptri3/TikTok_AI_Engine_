# M6.1 — CPU Dense & Hybrid Retrieval Pilot Specification

- **Task ID:** `M6.1` (Text-Only Spike on CPU)

## Owner-authorized Windows repair and integration — 2026-11-18

The owner explicitly requested resolving the Windows integration blocker, updating PR #3, and merging today's completed implementation work into `main` after checks pass. This repair does not complete the scientific M6.1 acceptance or approve G0.

- Remove unconditional Unix-only `resource` imports from the dense builder and parity benchmark. Both modules must import and their existing tests must collect on Windows without a `resource` module.
- Add a standard-library shared process-peak resident-memory helper: Windows reads `GetProcessMemoryInfo` / `PeakWorkingSetSize` in bytes; Linux reads `resource.getrusage(RUSAGE_SELF).ru_maxrss` in KiB. Normalize to MiB and keep the existing `peak_rss_mb` receipt field for compatibility, with explicit MiB/process-lifetime metadata on newly generated receipts.
- Never substitute current RSS or fabricated zero for an unavailable peak measurement. Propagate OS errors or invalid/nonfinite/negative readings; no new paid dependency, model download, crawl, provider call or historical artifact rewrite.
- Preserve all original benchmark artifacts and dated Linux measurements. Tests use OS-boundary doubles for deterministic unit conversion/error behavior plus a real native-process measurement on the current machine.
- Use RED/GREEN regressions, full pytest, configured mypy, required Ruff, secret/dependency checks, G0 runtime assertions and a clean installed-package smoke check before publication. Record actual source hashes and results.
- The full pipeline Ruff check also exposed five existing UTC-alias violations in the two crawl helper modules. Apply the equivalent Python3.11+ `datetime.UTC` alias there so the full requested lint scope is clean; preserve behavior, original artifacts and existing cutoff tests. These are low-impact style fixes and need no redundant tests.
- Update the canonical M6.1 and G0 reports/index with the repair and current validation while preserving their IN_PROGRESS / owner-pending statuses and unmet scientific criteria.
- User authorization includes normal commits/pushes, readying PR #3 and merging it to `main` once required checks/review pass. Preserve unrelated logs, original raw/Gold/index bytes and existing branch history. Confirm final remote main ancestry and PR state rather than inferring merge success.
- Post-merge verification/receipts may be persisted through a documentation-only follow-up PR into main so actual merge evidence is included without a direct main push. Its source hashes must match the already tested merge; no scientific/gate status is inferred from the evidence commit.
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
