# M2.1 — Specification: Descriptive Niche Benchmarks, Abstention, Provenance & Latency Budget

- **Date:** 2026-11-18
- **Task ID:** `M2.1`
- **Primary Owner:** Nguyễn Việt Nguyên (`N`)
- **Peer Reviewer:** Trần Đình Khương (`K`)
- **Requirement Source:** [TikTok_AI_Engine_Milestone.md](../../../planning/TikTok_AI_Engine_Milestone.md) (`M2.1`)

## Scope & Requirements
1. Revalidate and harden `packages/analytics/` (`NicheAnalyticsEngine`) and `packages/data_contracts/analytics.py` (`NicheBenchmarkSummary`) while preserving API compatibility with downstream consumers (`GroundedScriptEngine`, `/api/v1/analytics/niche-benchmark`, `/demo/`).
2. Expose **cohort date**, **observation/capture date**, **support `n`** (`matched_videos`), and **per-slice missingness** (`transcript_missing_pct`, `poi_missing_pct`, `city_missing_pct`, `price_unspecified_pct`) on every benchmark response and render them in `apps/demo/presentation.py`.
3. Enforce **sparse-slice abstention**:
   - When `matched_videos == 0` (empty corpus/slice), abstain cleanly (`sparse_slice_abstained=True`, `0.0` durations instead of fabricated `25/45/75` defaults, empty rankings).
   - When `0 < matched_videos < 5` (`min_slice_support = 5`), set `sparse_slice_abstained=True` and abstain from ranking `top_posting_hours` and `top_poi_venues`.
4. Verify hand-checkable aggregates & IQR ordering (`q25 <= median <= q75`, `p75_plays >= median_plays`, `hashtag_q25 <= hashtag_q75`), zero-division safety (`play_count=0`, `duration_sec=0`, missing transcripts), progressive filter relaxation, and strictly descriptive non-causal/non-optimum/non-current-trend wording.
5. Measure **cold** and **warm (`>= 100` fixed requests, concurrency 1)** CPU latency excluding initial Parquet load and verify `p95 <= 250 ms` (or report honestly if exceeded).

## Acceptance Criteria
- Hand-calculated fixture tests, zero-division tests, sparse-slice abstention tests, filter-relaxation tests, and descriptive-wording tests pass via TDD (RED -> GREEN).
- `100`-request fixed benchmark (`concurrency=1`, hardware recorded) documents cold latency and warm `p50` / `p95` (`<= 250 ms` budget).
- `scripts/check_secrets.py`, `ruff`, `mypy`, and full `pytest` pass cleanly; peer review of evidence and wording assigned to `K`.
