# M5.1 — Independent Baseline Code, Leakage & Sensitivity Peer Review (`K`)

- **Reviewer:** Trần Đình Khương (`K`)
- **Primary Owner:** Nguyễn Việt Nguyên (`N`)
- **Review Date:** 2026-11-20 (Asia/Ho_Chi_Minh)
- **Reviewed Baseline:** `main` @ `1531174e` (`M5.1` merge `9ca2a129`)
- **Post-Fix Verification Branch:** `feat/k-m4.2-m5.1-m6.1-peer-reviews`
- **Verdict:** **`K` BASELINE CODE/LEAKAGE/SENSITIVITY REVIEW COMPLETE (`M5.1` stays `IN_PROGRESS` pending `150–300` real pilot comments from `M3.3` & `N`/`K` double-annotation)**

## 1. Scope Verified Clean

- **Non-Accusatory Observable Labels & `original_text` Preservation:** `CommentRecord` preserves verbatim `original_text`, sets `diagnostic_only=True`, and emits strictly observable categories (`observable_duplicate`, `contact_or_link`, `noise_or_empty`, `template_phrase_match`, `no_indicator_observed`, `unknown_ambiguous`) while keeping `10`-column `fact_comments.parquet` Dual-Sink continuity intact.
- **Video-Disjoint 3-Way Partitioning:** `split_comments_by_video` enforces `0` `video_id` overlap across `dev`, `calibration`, and `held_out_third`, and multi-class Cohen's kappa retains `unknown_ambiguous` explicitly.
- **Diagnostic-Only Runtime Default:** Both `/api/v1/trust/audit-video` (`comment_filter_policy="diagnostic_only_unvalidated"`) and `/demo/` (`hide_seeding=False` unchecked by default) keep comments visible by default prior to passing the `M5.1` real-data gate.

## 2. Defects Found During `K` Adversarial Audit & Resolved via TDD (`RED -> GREEN`)

All defects were reproduced first in [red-k-review-fixes.log](red-k-review-fixes.log) (`5 failed, 3 passed`) and resolved in [green-k-review-fixes.log](green-k-review-fixes.log) (`8/8` M5.1 + `3/3` M3.1 tests passed):

1. **`[C1]` Mathematical Gate Deadlock on `held_out_third` (`evaluation.py`):** Because `build_annotation_pool` caps total comments at `<= 300`, a 3-way split yields `50–100` rows in `held_out_third`, making the prior check `len(rows) >= 150` mathematically unreachable (`300 / 3 = 100 < 150`).
   - **Fix:** Added `total_annotated_pool_count` to `evaluate_comment_indicator_metrics`, gating `auto_filter_eligible` on `total_annotated_pool_count >= 150`, `len(rows) >= 45` on `held_out_third`, `human_signoff_complete=True`, `macro_precision >= 0.85`, and `macro_recall >= 0.60`, with video-cluster bootstrap resampling.
2. **`[C2]` Annotation Pool Label Leakage, Thread Fragmentation, & Gold Parquet Prediction Collapse (`evaluation.py`, `run_baseline_checks.py`):** `build_annotation_pool` previously injected `predicted_observable_label` directly into human annotator sheets, shuffled comments across videos (breaking within-thread duplicate observability), and collapsed all `fact_comments.parquet` rows (which lack `observable_label`) to `"no_indicator_observed"`.
   - **Fix:** Defaulted `build_annotation_pool(..., include_predictions=False)` to sample whole/contiguous `video_id` threads blinded to model predictions, and added `reconstruct_observable_predictions` (writing a separate `*_locked_predictions.jsonl` key during `--mode real_pool`).
3. **`[C3]` Empty-After-Filter Sensitivity Contradiction (`evaluation.py`, `presentation.py`):** When `100%` of comments on a video were flagged (`unflagged_comment_count == 0`), `compute_comment_filter_sensitivity` previously fabricated neutral `0.0` viewer sentiment (`after_filter_hype_gap = +koc_mean`), contradicting `AbsaComparisonRecord.pr_hype_gap == 0.0`.
   - **Fix:** Added explicit abstention (`after_filter_abstained=True`, `after_filter_viewer_mean=None`, `mean_score_shift=None`, `after_filter_hype_gap=0.0`) and rendered explicit abstention text in `/demo/`.
4. **`[I1]`, `[I2]`, `[I5]` Vietnamese 5–7 Syllable Organic Inquiries, Spam Contamination, Template Shadowing, & 19-Digit ID Regex (`detector.py`):**
   - Exempted ordinary 5–8 syllable Vietnamese diner inquiries (`"Cho mình xin địa chỉ"`, `"Quán này ở đâu vậy"`, `"Cho mình xin địa chỉ quán với/ạ"`) before duplicate clustering (`min_duplicate_words >= 5`).
   - Isolated `contact_or_link` and `noise_or_empty` before pairwise Jaccard clustering so a spammer appending `"zalo"` never contaminates a lone clean viewer into `observable_duplicate`; prioritized `template_phrase_match` ahead of generic duplicate labels; unified transitive duplicate chains via Union-Find; bounded phone-number digits `(?<!\d)...(?!\d)` so 19-digit TikTok video IDs never false-positive; and added Telegram/Facebook link + repeated-character noise patterns matching [annotation_guidelines.md](annotation_guidelines.md).
5. **`[I3]`, `[I4]`, `[M1]` `/demo/` Bare-URL Colon Parser, Strict Label Validation, & Neutral Example Handles:** Added `parse_demo_comment_lines` so bare `"Xem menu tại https://example.com/quan-an"` or `"Giá: 45k"` lines are never split on `:`, replaced `@spam_bot`/`@khach_that_*` example handles in `apps/demo/ui.py` with `@viewer_01..@viewer_05`, enforced strict `OBSERVABLE_COMMENT_CLASSES` validation (rejecting `None`/typos), and restricted `macro_recall` averaging strictly to classes with `support > 0`.

## 3. Re-Verified Synthetic Dry-Run Receipt

Re-ran `python3 -m pipelines.audit_m5_1_comments.run_baseline_checks --mode fixture_dry_run --output artifacts/benchmarks/m5_1_fixture_dry_run_v2_k_review.json` ([m5_1_fixture_dry_run_v2_k_review.json](../../../../../artifacts/benchmarks/m5_1_fixture_dry_run_v2_k_review.json)) while keeping original `m5_1_fixture_dry_run.json` untouched: `legacy_org_dup_fp = 24 -> guarded = 0`, `recommended_mode = "diagnostic_only_without_filtering"`, `max_abs_mean_score_shift > 0.0`.
