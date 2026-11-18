# M2.1 — Descriptive Niche Benchmarks, Abstention & Latency Verification

- Status: COMPLETE (Implemented by Nguyễn Việt Nguyên; independently reproduced on both `20261117_recovered_v1` and `20261118_taxonomy_fix_v1` and approved by Trần Đình Khương)
- Execution date: 2026-11-18 (Asia/Ho_Chi_Minh)
- Requirement source: [TikTok_AI_Engine_Milestone.md](../../../planning/TikTok_AI_Engine_Milestone.md) (`M2.1`)
- Repository version: `main` (merged `origin/feat/m2.1-niche-benchmarks` @ `5db290e9` + `K` peer review)
- Primary owner: Nguyễn Việt Nguyên (`N`) · Peer reviewer: Trần Đình Khương (`K`)
- Specification: [spec.md](superpowers/spec.md)
- Execution plan: [plan.md](superpowers/plan.md)

## Conclusion

Hardened, vectorized, and independently verified `NicheAnalyticsEngine` (`packages/analytics/`) and `NicheBenchmarkSummary` (`packages/data_contracts/analytics.py`) for `M2.1`. Every benchmark response exposes cohort dates, observation snapshot metadata, support `n`, per-slice `missingness` percentages, and explicit `sparse_slice_abstained` behavior when `matched_videos == 0` or `< 5`, with strictly descriptive non-causal, non-optimum wording.

Across two independent hardware environments (`concurrency = 1`, `100` fixed warm requests over `70,996` videos) and both Gold snapshots:
- **Primary owner (`N`, Linux Intel i5-6500, 4 CPUs, `20261117_recovered_v1`):** `cold = 10.08 ms`, `warm p50 = 5.37 ms`, **`warm p95 = 17.57 ms <= 250 ms`** ([latency_benchmark_100.json](evidence/latency_benchmark_100.json)).
- **Peer reviewer (`K`, Windows 11 Intel 12 CPUs):**
  - `20261117_recovered_v1`: `cold = 22.98 ms`, `warm p50 = 12.50 ms`, **`warm p95 = 38.81 ms <= 250 ms`**;
  - `20261118_taxonomy_fix_v1` (`M1.2` snapshot): `cold = 22.24 ms` (`13,347` matched HCMC `Review quán ăn` videos), `warm p50 = 12.57 ms`, **`warm p95 = 40.92 ms <= 250 ms`** ([khuong_m2_1_reproduction.json](evidence/khuong_m2_1_reproduction.json), [khuong-peer-review.md](evidence/khuong-peer-review.md)).

All primary and reciprocal peer-review criteria are satisfied: task `M2.1` is **COMPLETE** (gate `M2.G` remains `NOT_RUN`).

## Work performed

- **Provenance, missingness & quantile guards ([analytics.py](../../../../packages/data_contracts/analytics.py)):** Added backward-compatible `cohort_window_start`, `cohort_window_end`, `observation_snapshot`, `sparse_slice_abstained`, and bounded `[0.0, 100.0]` `missingness` fields plus `p75_plays >= median_plays` validation.
- **Sparse-slice abstention & vectorized aggregation ([engine.py](../../../../packages/analytics/engine.py)):**
  - Empty slices (`n == 0`) return `0.0` durations/plays/wps and `sparse_slice_abstained=True` instead of fabricated default quantiles (`25s/45s/75s`).
  - Small slices (`0 < n < 5`) set `sparse_slice_abstained=True` and abstain from ranking `top_posting_hours` and `top_poi_venues`.
  - Pre-indexed normalized filter columns, occasion bitmasks, factorized POI codes, and flat hashtag postings with `np.bincount` (`warm p95` reduced from `265.58 ms` to `17.57 ms` on `N`'s machine and `38.81–40.92 ms` on `K`'s machine).
- **Descriptive UI formatting ([presentation.py](../../../../apps/demo/presentation.py)):** Rendered cohort dates, observation snapshot, missingness percentages, and abstention notices using strictly descriptive non-causal, non-optimum wording.
- **Peer review & two-snapshot reproduction (`K`, `2026-11-18`):** Audited quantile math, zero-division, abstention, and wording (`0` violations) and reproduced the 100-request benchmark on both `20261117_recovered_v1` and `20261118_taxonomy_fix_v1`.

## Outputs

| File | Purpose |
| --- | --- |
| [workflow.md](evidence/workflow.md) | Decisions, optimization history, and command receipts |
| [khuong-peer-review.md](evidence/khuong-peer-review.md) | Peer review sign-off and descriptive wording audit by Trần Đình Khương (`K`) |
| [khuong_m2_1_reproduction.json](evidence/khuong_m2_1_reproduction.json) | `K`'s independent 100-request latency & wording reproduction on `20261117_recovered_v1` and `20261118_taxonomy_fix_v1` |
| [benchmark_m2_1.py](evidence/benchmark_m2_1.py) | Reproducible cold + 100-request warm benchmark script (`concurrency=1`) |
| [latency_benchmark_100.json](evidence/latency_benchmark_100.json) | `N`'s measured hardware, cold latency (`10.08 ms`), warm `p50` (`5.37 ms`), `p95` (`17.57 ms`) |
| [benchmark.log](evidence/benchmark.log) | Console output from `benchmark_m2_1.py` |
| [red-analytics-tests.log](evidence/red-analytics-tests.log) / [green-analytics-tests.log](evidence/green-analytics-tests.log) | TDD RED (`2 failed`) and GREEN (`5 passed`) analytics test logs |
| [ruff.log](evidence/ruff.log) / [mypy.log](evidence/mypy.log) / [pytest-full.log](evidence/pytest-full.log) / [check-secrets.log](evidence/check-secrets.log) | Lint, typecheck, full test suite, and secret scan logs |

## Verification

| Check | Result | Scope / evidence |
| --- | --- | --- |
| `benchmark_m2_1.py` (`N` Linux i5-6500) | PASS (`p95 = 17.57 ms <= 250 ms`) | Cold + 100 warm fixed requests, `concurrency=1`, `70,996` rows; [latency_benchmark_100.json](evidence/latency_benchmark_100.json) |
| Independent 100-request reproduction (`K` Windows 11, both snapshots) | PASS (`p95 = 38.81 ms` & `40.92 ms <= 250 ms`) | `20261117_recovered_v1` and `20261118_taxonomy_fix_v1`, `0` wording violations; [khuong_m2_1_reproduction.json](evidence/khuong_m2_1_reproduction.json) |
| `pytest tests/unit/test_analytics_and_retrieval.py -v` | PASS (`5 passed`) | Hand-checkable IQR, zero-division, abstention, relaxation, wording; [green-analytics-tests.log](evidence/green-analytics-tests.log) |
| `python scripts/check_secrets.py` | PASS (`0` leaks) | Workspace secret scan |

## Open issues

None for `M2.1` scope (switching default `AppSettings.corpus_dir` from `20261117_recovered_v1` to `20261118_taxonomy_fix_v1` is coordinated with the paired `bm25-v3` build in `M2.2`).

## Acceptance and handoff

| Task criterion | Result | Evidence |
| --- | --- | --- |
| Hand-checkable aggregates/IQR ordering & zero-division tests | Met | [test_analytics_and_retrieval.py](../../../../tests/unit/test_analytics_and_retrieval.py) |
| Cohort date, observation date, support `n`, missingness & sparse abstention | Met | [engine.py](../../../../packages/analytics/engine.py), [presentation.py](../../../../apps/demo/presentation.py) |
| No optimum/causal/current-trend wording (reviewed by `K`) | Met | [presentation.py](../../../../apps/demo/presentation.py), [khuong-peer-review.md](evidence/khuong-peer-review.md) |
| Cold & >=100 warm requests (`concurrency=1`, `p95 <= 250 ms`) | Met (`17.57 ms` `N`; `38.81 ms` / `40.92 ms` `K`) | [latency_benchmark_100.json](evidence/latency_benchmark_100.json), [khuong_m2_1_reproduction.json](evidence/khuong_m2_1_reproduction.json) |

Final task status: **COMPLETE**. Formal gate `M2.G` (`G2`) remains `NOT_RUN` pending `M2.2` and `M2.3`.
