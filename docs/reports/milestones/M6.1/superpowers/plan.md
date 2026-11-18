# M6.1 — Execution & Verification Plan

## Windows repair and authorized merge plan — 2026-11-18

**Goal:** Resolve the upstream Windows resource import/type blocker and deliver the current PR safely into main.
**Spec:** [spec.md](spec.md), owner-authorized repair addendum.
**Execution:** native `executing-plans`, `systematic-debugging`, `test-driven-development`, `verification-before-completion`, one read-only `requesting-code-review`, then the already authorized `finishing-a-development-branch` publication/merge. The earlier process skills remain loaded in this conversation; no repeated approval is needed for the selected action.

### Task1: Portable truthful process peak memory

Files: create `packages/common/resources.py` and `tests/unit/test_resource_measurements.py`; modify only the two affected M6.1 pipeline imports/measurements and add unit/scope metadata to new receipts. Preserve original result artifacts.

Verification-discovered style scope: correct only the five existing UP017 UTC aliases in `pipelines/crawl_incremental/__main__.py` and `crawler_service.py` so the full pipeline lint target passes. Existing behavior tests cover the unchanged cutoff logic; no style-only tests are added.

- [x] Record the existing ImportError/mypy root cause and baseline hashes before implementation; archive current reports.
- [x] Write behavior regressions first: import both pipelines without resource, Windows byte conversion, Linux KiB conversion, invalid/nonfinite readings and OS errors; exercise the native helper on the current OS. Expected RED for the missing portable boundary, not an unrelated syntax error.
- [x] Implement the shared OS-backed helper and wire both pipeline consumers; retain the legacy field name with explicit MiB and process-lifetime meaning. No fake/current-RSS fallback.
- [x] Run focused tests and both Windows/Linux type-analysis targets where feasible. Expected: no platform-specific import/type failures; no provider/network calls.

### Task2: Verify, review and merge PR3

Files: M6.1/G0 current reports, existing canonical spec/plan/workflow evidence, distinct `windows-*` / `merge-*` receipts, milestone index and necessary byte-preservation attributes.

- [x] Run complete pytest, contract/smoke, configured mypy, required Ruff including changed code/tests, source secret scan and pip check. Run asserting G0 probe and clean wheel/installed-ASGI verification. Expected: all required checks exit0 on the same source hashes.
- [x] Request one fresh-context read-only review; resolve material findings through one RED/GREEN fix pass and revalidate affected source. Do not fabricate human K/N sign-off.
- [x] Update both canonical reports/index and PR title/body to the final implementation, preserving dated failed receipts and scientific limitations. Validate report layout/links, source scope, hashes and protected originals.
- [x] Run the required secret scanner before every commit; stage only authorized source/test/report/attribute paths, commit conventionally and push normally. Reconfirm main has not advanced incompatibly.
- [x] Mark PR3 ready and merge with a merge commit after required verification. Fetch remote main, verify the merged tree/source hashes and full tests on main, then record actual merge/remote state and synchronize local main without force/reset or unrelated file loss.

The user explicitly authorized the final PR merge. A successful merge does not by itself set G0 PASS or complete M6.1's human relevance/scientific gates.

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

Verified integration outcome (2026-11-18): PR3 merged at eb43b0df3d46007b7550de8f4314dc2dbca9c51f; post-merge full main verification 120 passed in 58.09s. A documentation-only follow-up persists those actual receipts; final branch/main identities are checked externally after its merge. Formal G0 and scientific task decisions stay unchanged.
