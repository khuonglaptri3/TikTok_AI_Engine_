# M6.1 — Execution & Verification Plan

1. **TDD RED:** Create `tests/unit/test_dense_hybrid_retrieval.py` covering:
   - `TruncatedSvdDenseEncoder` fit/save/load, L2 normalization, and dimensionality.
   - `LocalDenseIndex` build/save/load, collision rejection, missing/corrupt SHA256 fail-closed behavior, and filtered `search_vectors(allowed_video_ids=...)`.
   - `QdrantDenseAdapter.ensure_collection` and `upsert_vectors` via `httpx.MockTransport`.
   - `HybridRetrievalService` local `bm25`, `dense`, and `hybrid_rrf` parity (no Docker required).
   - `max_records <= 5000` bound enforcement and `paired_bootstrap_ci` delta calculation.
2. **Implementation:**
   - Implement `packages/retrieval/dense/encoder.py` and `packages/retrieval/dense/local_index.py`.
   - Extend `packages/retrieval/dense/qdrant_adapter.py` (`ensure_collection`, `upsert_vectors`) and `packages/retrieval/dense/__init__.py`.
   - Extend `packages/retrieval/service.py` (`dense_index`, `dense_encoder`, `from_dirs(..., dense_dir=...)`) preserving 100% backward compatibility.
   - Implement CLIs: `pipelines/build_dense_sparse_index/dense.py` and `pipelines/benchmark_retrieval/dense_hybrid_pilot.py`.
3. **TDD GREEN & Live Spike Measurement:**
   - Run targeted unit tests -> `ruff` -> `mypy packages apps pipelines` -> full `pytest -v`.
   - Build `artifacts/indexes/dense-svd-v1` (`<= 5,000` records from `20261117_recovered_v1`) and run `dense_hybrid_pilot` (`artifacts/benchmarks/m6_1_dense_hybrid_spike.json`), recording build time, bytes, peak RAM, 100-req warm p50/p95, and paired bootstrap deltas.
4. **Documentation & Cleanliness:** Author `M6.1/evidence/workflow.md`, `M6.1/README.md`, update `docs/reports/milestones/README.md`, and run `scripts/check_secrets.py`.
