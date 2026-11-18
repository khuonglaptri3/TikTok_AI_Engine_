# M2.1 — Workflow Provenance & Verification Ledger

- **Date:** 2026-11-18 (Asia/Ho_Chi_Minh)
- **Task ID:** `M2.1`
- **Primary Owner:** Nguyễn Việt Nguyên (`N`)
- **Peer Reviewer:** Trần Đình Khương (`K`, pending)

## Process & Decisions
1. Created feature branch `feat/m2.1-niche-benchmarks` from `main` (`c3348e93`) before modifying code.
2. Authored `superpowers/spec.md` and `superpowers/plan.md` prior to implementation.
3. Wrote TDD RED tests first in `tests/unit/test_analytics_and_retrieval.py` covering hand-calculated quantiles, zero-division, sparse-slice abstention (`n == 0` and `n < 5`), filter relaxation, cohort/observation/missingness fields, and non-causal/non-optimum wording (`red-analytics-tests.log`: `2 failed, 3 passed`).
4. Added backward-compatible fields (`cohort_window_start`, `cohort_window_end`, `observation_snapshot`, `sparse_slice_abstained`, `missingness`) to `NicheBenchmarkSummary` and `format_benchmark_markdown`.
5. First 100-request latency run measured `warm_wall_ms.p50 = 24.06 ms`, **`p95 = 265.58 ms`** (exceeding `250 ms` provisional budget on full-corpus 70,996-row unfiltered slices due to DataFrame `.iloc` copying and Python loops over hashtags/POIs).
6. Refactored `NicheAnalyticsEngine` to pre-index numpy vectors, occasion masks, factorized POI codes, and flat hashtag postings with `np.bincount`, eliminating per-query DataFrame slice copies and cutting `warm_wall_ms.p95` from `265.58 ms` to **`17.57 ms`** (`cold = 10.08 ms`).

## Commands & Verification Receipts
- `.venv/bin/python -m pytest tests/unit/test_analytics_and_retrieval.py -v` (RED) -> `EXIT=1`, `2 failed, 3 passed` ([red-analytics-tests.log](red-analytics-tests.log))
- `.venv/bin/python docs/reports/milestones/M2.1/evidence/benchmark_m2_1.py` (post-optimization) -> `cold = 10.08 ms`, `warm p50 = 5.37 ms`, `warm p95 = 17.57 ms`, `budget_met = true` ([latency_benchmark_100.json](latency_benchmark_100.json), [benchmark.log](benchmark.log))
- `.venv/bin/python -m pytest tests/unit/test_analytics_and_retrieval.py -v` (GREEN) -> `EXIT=0`, `5 passed in 3.81s` ([green-analytics-tests.log](green-analytics-tests.log))
- `.venv/bin/python -m ruff check packages/analytics packages/data_contracts/analytics.py apps/demo/presentation.py tests/unit/test_analytics_and_retrieval.py` -> `EXIT=0`, `All checks passed!` ([ruff.log](ruff.log))
- `.venv/bin/python -m mypy packages apps pipelines` -> `EXIT=0`, `Success: no issues found in 76 source files` ([mypy.log](mypy.log))
- `.venv/bin/python -m pytest -v` -> `EXIT=0`, `65 passed in 17.57s` ([pytest-full.log](pytest-full.log))
- `.venv/bin/python scripts/check_secrets.py` -> `EXIT=0`, `PASS: Zero secret leaks detected across workspace.` ([check-secrets.log](check-secrets.log))

## Peer Review & Two-Snapshot Reproduction (`2026-11-18`, Trần Đình Khương)
- Read and applied `using-superpowers`, `receiving-code-review`, and `verification-before-completion`.
- Audited quantile math, sparse-slice abstention (`n == 0` and `n < 5`), zero-division safety, and non-causal/non-optimum wording (`0` violations).
- Independently reproduced the 100-request `concurrency=1` CPU benchmark on Windows 11 across both `20261117_recovered_v1` (`warm p95 = 38.81 ms`) and `20261118_taxonomy_fix_v1` (`warm p95 = 40.92 ms`), recorded in [khuong_m2_1_reproduction.json](khuong_m2_1_reproduction.json) and [khuong-peer-review.md](khuong-peer-review.md). Approved `M2.1` as `COMPLETE`.
