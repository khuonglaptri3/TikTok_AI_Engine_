# M2.1 — Descriptive Niche Benchmarks, Abstention & Latency Verification

- Status: IN_PROGRESS (`N`'s scope complete: implementation, 100-request latency benchmark, and local checks passed; awaiting peer review of evidence and wording by Trần Đình Khương)
- Execution date: 2026-11-18 (Asia/Ho_Chi_Minh)
- Requirement source: [TikTok_AI_Engine_Milestone.md](../../../planning/TikTok_AI_Engine_Milestone.md) (`M2.1`)
- Repository version: `feat/m2.1-niche-benchmarks` (branched from `main` at `c3348e93`)
- Specification: [spec.md](superpowers/spec.md)
- Execution plan: [plan.md](superpowers/plan.md)

## Conclusion

Hardened and benchmarked `NicheAnalyticsEngine` (`packages/analytics/`) and `NicheBenchmarkSummary` (`packages/data_contracts/analytics.py`) for `M2.1`. Every benchmark response now exposes cohort dates, observation snapshot metadata, support `n`, per-slice `missingness` percentages, and explicit `sparse_slice_abstained` behavior when `matched_videos == 0` or `< 5`. After observing an initial `warm p95 = 265.58 ms` on full-70,996-row slices (above the `250 ms` provisional budget), pre-indexing numpy columns and hashtag/POI postings reduced latency to **`cold = 10.08 ms`**, **`warm p50 = 5.37 ms`**, and **`warm p95 = 17.57 ms`** across `100` fixed requests (`concurrency = 1` on `Intel Core i5-6500 @ 3.20GHz`, `4` logical CPUs, `15.33 GB` RAM). All `65/65` pytest tests, `mypy`, `ruff`, and `check_secrets.py` pass. Task status remains `IN_PROGRESS` pending `K` peer review.

## Work performed

- **Provenance, missingness & quantile guards ([analytics.py](../../../../packages/data_contracts/analytics.py)):** Added backward-compatible `cohort_window_start`, `cohort_window_end`, `observation_snapshot`, `sparse_slice_abstained`, and bounded `[0.0, 100.0]` `missingness` fields plus `p75_plays >= median_plays` validation.
- **Sparse-slice abstention & vectorized aggregation ([engine.py](../../../../packages/analytics/engine.py)):**
  - Empty slices (`n == 0`) return `0.0` durations/plays/wps and `sparse_slice_abstained=True` instead of fabricated default quantiles (`25s/45s/75s`).
  - Small slices (`0 < n < 5`) set `sparse_slice_abstained=True` and abstain from ranking `top_posting_hours` and `top_poi_venues`.
  - Pre-indexed normalized filter columns, occasion bitmasks, factorized POI codes, and flat hashtag postings with `np.bincount` to eliminate per-query DataFrame copies and Python loops.
- **Descriptive UI formatting ([presentation.py](../../../../apps/demo/presentation.py)):** Rendered cohort dates, observation snapshot, missingness percentages, and abstention notices using strictly descriptive non-causal, non-optimum wording.
- **TDD & latency verification:** Added hand-checkable fixture, zero-division, abstention, filter-relaxation, and wording tests in [test_analytics_and_retrieval.py](../../../../tests/unit/test_analytics_and_retrieval.py); benchmarked `100` fixed warm requests via [benchmark_m2_1.py](evidence/benchmark_m2_1.py).

## Outputs

| File | Purpose |
| --- | --- |
| [workflow.md](evidence/workflow.md) | Decisions, optimization history, and command receipts |
| [benchmark_m2_1.py](evidence/benchmark_m2_1.py) | Reproducible cold + 100-request warm benchmark script (`concurrency=1`) |
| [latency_benchmark_100.json](evidence/latency_benchmark_100.json) | Measured hardware, cold latency (`10.08 ms`), warm `p50` (`5.37 ms`), `p95` (`17.57 ms`) |
| [benchmark.log](evidence/benchmark.log) | Console output from `benchmark_m2_1.py` |
| [red-analytics-tests.log](evidence/red-analytics-tests.log) | TDD RED test output before implementation |
| [green-analytics-tests.log](evidence/green-analytics-tests.log) | TDD GREEN analytics test output (`5 passed`) |
| [ruff.log](evidence/ruff.log) | Scoped Ruff output (`All checks passed!`) |
| [mypy.log](evidence/mypy.log) | Project-wide mypy typecheck (`76 source files`) |
| [pytest-full.log](evidence/pytest-full.log) | Full pytest suite (`65 passed in 17.57s`) |
| [check-secrets.log](evidence/check-secrets.log) | Secret scanner output (`0` leaks) |

## Verification

| Check | Result | Scope / evidence |
| --- | --- | --- |
| `.venv/bin/python docs/reports/milestones/M2.1/evidence/benchmark_m2_1.py` | PASS (`p95 = 17.57 ms <= 250 ms`) | Cold + 100 warm fixed requests, `concurrency=1`, `70,996` rows; [latency_benchmark_100.json](evidence/latency_benchmark_100.json) |
| `.venv/bin/python -m pytest tests/unit/test_analytics_and_retrieval.py -v` | PASS (`5 passed`) | Hand-checkable IQR, zero-division, abstention, relaxation, wording; [green-analytics-tests.log](evidence/green-analytics-tests.log) |
| `.venv/bin/python -m ruff check packages/analytics packages/data_contracts/analytics.py apps/demo/presentation.py tests/unit/test_analytics_and_retrieval.py` | PASS | Lint & style checks on touched files; [ruff.log](evidence/ruff.log) |
| `.venv/bin/python -m mypy packages apps pipelines` | PASS (`76 source files`) | Full strict static typing; [mypy.log](evidence/mypy.log) |
| `.venv/bin/python -m pytest -v` | PASS (`65 passed`) | Full test suite across contract, unit, eval, smoke; [pytest-full.log](evidence/pytest-full.log) |
| `.venv/bin/python scripts/check_secrets.py` | PASS (`0` leaks) | Workspace secret scan; [check-secrets.log](evidence/check-secrets.log) |

## Open issues

| Issue | Impact | Follow-up / responsible task |
| --- | --- | --- |
| Peer review by Trần Đình Khương (`K`) pending | Two-person plan requires `K` review of evidence and descriptive wording before closing `M2.1` | `feat/m2.1-niche-benchmarks` is pushed; request `K` review |
| Cohort-date/missingness reflects `20261117_recovered_v1` | New taxonomy-fixed counts will reflect after `K` builds the `M1.2` snapshot | Re-run smoke/benchmark after merging `M1.2` |

## Acceptance and handoff

| Task criterion | Result | Evidence |
| --- | --- | --- |
| Hand-checkable aggregates/IQR ordering & zero-division tests | Met | [test_analytics_and_retrieval.py](../../../../tests/unit/test_analytics_and_retrieval.py) |
| Cohort date, observation date, support `n`, missingness & sparse abstention | Met | [engine.py](../../../../packages/analytics/engine.py), [presentation.py](../../../../apps/demo/presentation.py) |
| No optimum/causal/current-trend wording | Met (awaiting `K` wording review) | [presentation.py](../../../../apps/demo/presentation.py) |
| Cold & >=100 warm requests (`concurrency=1`, `p95 <= 250 ms`) | Met (`p95 = 17.57 ms`) | [latency_benchmark_100.json](evidence/latency_benchmark_100.json) |

Final task status: **IN_PROGRESS** (`N`'s implementation, benchmark, and local checks are complete and pushed on `feat/m2.1-niche-benchmarks`; awaiting peer review by `K` before closing `M2.1`).
