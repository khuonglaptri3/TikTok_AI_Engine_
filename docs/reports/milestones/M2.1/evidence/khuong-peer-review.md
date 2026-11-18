# M2.1 — Peer Review & Independent Reproduction by Trần Đình Khương (`K`)

- **Review date:** 2026-11-18 (Asia/Saigon)
- **Task ID:** `M2.1`
- **Primary Owner:** Nguyễn Việt Nguyên (`N`)
- **Peer Reviewer:** Trần Đình Khương (`K`)
- **Reviewed merge:** `origin/feat/m2.1-niche-benchmarks` (`5db290e9`) merged into local `main`

## 1. Review Summary & Approval Verdict

- **Overall Verdict:** **APPROVED — `M2.1` is `COMPLETE`** (all primary-owner and peer-reviewer acceptance criteria satisfied; formal milestone gate `M2.G` remains `NOT_RUN`).
- **Mathematical & Contract Correctness (`PASS`):**
  - Inspected `packages/data_contracts/analytics.py` and `packages/analytics/engine.py`: quantile ordering (`duration_q25_sec <= duration_median_sec <= duration_q75_sec`, `p75_plays >= median_plays`, `hashtag_q25 <= hashtag_q75`), bounded `[0.0, 100.0]` `missingness` percentages, zero-division safety, and progressive filter relaxation (`duration_bucket -> occasion -> price_tier -> city_norm -> region -> food_category -> video_format`) are exact and hand-checkable (`test_analytics_and_retrieval.py` `5/5` passed).
  - Sparse-slice abstention (`n == 0` returning `0.0` durations/plays/wps instead of fabricated `25s/45s/75s` defaults; `0 < n < 5` setting `sparse_slice_abstained=True` and suppressing `top_posting_hours` and `top_poi_venues`) directly resolves the narrow-slice (`n=2`) ranking issue previously observed during `M0.3`.
- **Descriptive Wording Audit (`PASS`):**
  - Audited `apps/demo/presentation.py` across all 10 benchmark filter slices: `0` causal, optimum, or current-trend wording violations (`descriptive_wording_violations = []`). Cohort window (`cohort_window_start` → `cohort_window_end`), `observation_snapshot`, support `n`, `missingness`, and selection-bias caveats render clearly.
- **Independent 100-Request CPU Latency Reproduction on Both Snapshots (`PASS`):**
  - Reproduced at `concurrency = 1` on `Windows-11-10.0.26300-SP0` (`12` logical Intel CPUs, Python `3.12.14`) in [khuong_m2_1_reproduction.json](khuong_m2_1_reproduction.json):
    - **`20261117_recovered_v1` (`70,996` rows):** `load_and_preindex_ms = 1,887.17 ms`; `cold = 22.98 ms` (`matched_videos = 9,631`); `warm p50 = 12.50 ms`, **`warm p95 = 38.81 ms <= 250 ms`** (`internal p95 = 28.07 ms`).
    - **`20261118_taxonomy_fix_v1` (`70,996` rows, `M1.2` taxonomy-corrected snapshot):** `load_and_preindex_ms = 1,809.76 ms`; `cold = 22.24 ms` (`matched_videos = 13,347` for HCMC `Review quán ăn`, `+3,716` recovered videos); `warm p50 = 12.57 ms`, **`warm p95 = 40.92 ms <= 250 ms`** (`internal p95 = 29.78 ms`).
