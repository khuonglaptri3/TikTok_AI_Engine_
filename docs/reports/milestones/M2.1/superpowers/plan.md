# M2.1 — Execution & Verification Plan

- **Date:** 2026-11-18
- **Task ID:** `M2.1`
- **Primary Owner:** Nguyễn Việt Nguyên (`N`)

## Execution Steps
1. **TDD RED:** Expand `tests/unit/test_analytics_and_retrieval.py` with hand-checkable aggregate/IQR fixture tests, zero-division / empty-corpus tests, sparse-slice abstention (`n < 5`), filter-relaxation tests, cohort/observation/missingness field checks, and descriptive wording checks on `format_benchmark_markdown`. Capture RED failure log in `evidence/red-analytics-tests.log`.
2. **Implement Hardening & Optimization:**
   - Extend `NicheBenchmarkSummary` in `packages/data_contracts/analytics.py` with backward-compatible optional fields (`cohort_window_start`, `cohort_window_end`, `observation_snapshot`, `sparse_slice_abstained`, `missingness`) and `p75_plays >= median_plays` check.
   - Update `NicheAnalyticsEngine` in `packages/analytics/engine.py` to pre-normalize filter columns for sub-250ms queries (including `occasion` filter), compute slice missingness, expose cohort/observation metadata, abstain cleanly on `n == 0` and `0 < n < 5` slices, and guard zero-division cases.
   - Update `format_benchmark_markdown` in `apps/demo/presentation.py` to display cohort window, observation snapshot, missingness, and sparse-slice abstention notices using purely descriptive wording.
3. **TDD GREEN & Verification:**
   - Run `pytest tests/unit/test_analytics_and_retrieval.py -v` -> save `evidence/green-analytics-tests.log`.
   - Run `evidence/benchmark_m2_1.py` (`cold` + `100` warm fixed requests at concurrency 1) -> save `evidence/latency_benchmark_100.json` and `evidence/benchmark.log`.
   - Run `ruff`, `scripts/check_secrets.py`, `mypy`, and full `pytest -v`.
4. **Report & Index:**
   - Author `docs/reports/milestones/M2.1/README.md`, `evidence/workflow.md`, and update `docs/reports/milestones/README.md` with `IN_PROGRESS` (ready for `K` peer review).
