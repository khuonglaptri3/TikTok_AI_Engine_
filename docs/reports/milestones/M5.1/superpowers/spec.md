# M5.1 — Observable Duplicate, Contact/Link, and Noise Comment Indicators Specification

- **Task ID:** `M5.1` (Duplicate/contact/noise indicators; existing heuristic baseline upgrade)
- **Primary Owner:** Nguyễn Việt Nguyên (`N`)
- **Peer Reviewer:** Trần Đình Khương (`K`)
- **Requirement Source:** [TikTok_AI_Engine_Milestone.md](../../../../planning/TikTok_AI_Engine_Milestone.md) (`M5.1`, line 110)
- **Date:** 2026-11-19 (Asia/Ho_Chi_Minh)
- **Branch:** `feat/m5.1-observable-comment-indicators` (branched from `main` @ `dcdd6233`)
- **Upstream Boundary:** Independent real comment sample (`150`–`300` comments) waits for `M3.3` / `M3.G` (`data/raw_incremental/` does not exist yet on disk).

## Problem Statement

The existing baseline (`packages/seeding/detector.py` and `/demo/`) uses accusatory wording (`is_seeding`, `"nghi Seeding/Spam bị lọc"`, `"khách thật"`), silently hides flagged comments by default (`hide_seeding=True`), applies a short-phrase Jaccard threshold that falsely flags repeated ordinary short reactions (e.g., `"ngon quá"`, `"xin địa chỉ"`) as near-duplicate clusters, and lacks video-disjoint splitting, inter-annotator agreement, per-class PR/F1 + bootstrap uncertainty, filter sensitivity reporting, and written annotation guidelines.

## Scope & Acceptance Requirements

1. **Preserve Originals, Observable Labels, and Organic Short-Duplicate Guard (`packages/seeding/detector.py`, `packages/data_contracts/multimodal.py`):**
   - Preserve original raw comment text (`original_text` + normalized `text`) and detailed reason codes (`observable_reason_codes`).
   - Emit observable indicator classes (`observable_duplicate`, `contact_or_link`, `noise_or_empty`, `template_phrase_match`, `no_indicator_observed`, `unknown_ambiguous`) without asserting bots, payment, coordinated seeding, or verified diner identity.
   - Guard near-duplicate clustering with a minimum word threshold (`min_duplicate_words = 5` by default) so short organic repeated phrases are exempted (`short_organic_phrase_exempt`) instead of causing organic-duplicate false positives.
   - Maintain 100% backward compatibility with `is_seeding`, `seeding_reason`, and Gold Parquet `fact_comments.parquet` schema.
2. **Diagnostic-Only Default & Filter Sensitivity Reporting (`apps/api/app/routers/trust.py`, `apps/demo/`):**
   - Enforce M5.1 gating: until held-out real pilot evaluation achieves `macro_precision >= 0.85` and `macro_recall >= 0.60` on `>= 150` annotated real comments, runtime defaults to **`diagnostic_only_unvalidated`** (UI defaults `hide_seeding=False`, displays observable indicator tags without claiming bots/seeding, and surfaces exact before/after ABSA `filter_sensitivity`).
3. **Video-Disjoint Split, Metrics & Sampler Framework (`packages/seeding/evaluation.py`, `pipelines/audit_m5_1_comments/run_baseline_checks.py`):**
   - Implement video/thread-disjoint 3-way partition (`dev`, `calibration`, `held_out_third`), inter-annotator Cohen's kappa retaining `unknown_ambiguous`, per-class precision/recall/F1, macro precision/recall, bootstrap 95% CIs, confusion matrix, automated `diagnostic_only_without_filtering` gate check, and `<= 300`-comment pool builder.
   - Author formal double-annotation guidelines in `docs/reports/milestones/M5.1/evidence/annotation_guidelines.md`.
   - Run verification against an explicit **non-real authored edge regression fixture** (explicitly tagged non-pilot) to verify metrics, sensitivity shift, and organic-duplicate improvements end-to-end while keeping `M5.1 = IN_PROGRESS` pending `M3.3` / `M3.G` real comments and `K` peer review.
4. **Phase 3 — Real `M3.3` Pilot Co-Annotation (`K`), Joint Adjudication & Frozen Held-Out Evaluation (`2026-11-26`):**
   - Complete `K`'s independent **blinded** human annotation across all `180` `K`-assigned real pilot comments (`60` `double_review_N_K` + `120` `K_only`) in `data/annotations/m5_1_pilot_pool.jsonl` following [annotation_guidelines.md](../evidence/annotation_guidelines.md), strictly blinded to both `N_label` and `data/annotations/m5_1_pilot_pool_locked_predictions.jsonl` prior to `K`'s explicit human confirmation (`K_human_verified = True` only after owner sign-off; preserve `N`'s `180/180` verified annotations untouched).
   - Compute raw agreement and multi-class Cohen's kappa (retaining `unknown_ambiguous`) on the `60` independently double-annotated overlap comments, adjudicate any `N` vs `K` disagreements into `adjudicated_label` with documented rationale, and populate `adjudicated_label` for single-reviewer items (`N_only`, `K_only`) from their verified owner labels.
   - Add strict `--mode real_eval` to `pipelines/audit_m5_1_comments/run_baseline_checks.py` (and strict pool-verification helper in `packages/seeding/evaluation.py`) via TDD to validate 100% human signoff (`300/300` verified, `0` invalid rows, exact 1-to-1 parity with `m5_1_pilot_pool_locked_predictions.jsonl`), evaluate per-class P/R/F1, confusion matrix, and video-cluster bootstrap 95% CIs on the frozen `held_out_third` (`seed=42`, `0` video overlap), compute real `22`-video ABSA filter sensitivity on `m3_3_pilot_snapshot_v2`, and enforce `auto_filter_eligible` (`macro_precision >= 0.85` and `macro_recall >= 0.60` required, else retain `diagnostic_only_without_filtering`).
