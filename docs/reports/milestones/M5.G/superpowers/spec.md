# M5.G — Trust-Diagnostic Gate (`G5`) Specification

- **Task ID:** `M5.G` (`Gate G5` — Qualified comment/aspect diagnostics on independent real labels)
- **Shared Co-Owners:** Trần Đình Khương (`K`, `2` pts) & Nguyễn Việt Nguyên (`N`, `2` pts)
- **Requirement Source:** [TikTok_AI_Engine_Milestone.md](../../../../planning/TikTok_AI_Engine_Milestone.md) (`M5.G`, line 112)
- **Date:** 2026-11-26 (Asia/Ho_Chi_Minh)

## Scope & Acceptance Criteria

1. **`M5.1` Observable Comment Indicators Qualification:**
   - Verify `300` real `M3.3` comments (`22` videos from `m3_3_pilot_snapshot_v2`) independently verified by `N` (`180/180`) and `K` (`180/180`, `60` double-annotated: `93.33%` raw / `100.0%` positive-indicator agreement), `0` video overlap across 3-way splits, bootstrap 95% CIs, and real organic-duplicate FP reduction (`2 -> 0`).
   - Because natural positive indicator support on `held_out_third` lacks `contact_or_link` and `observable_duplicate` instances (`all_pool` `macro_precision = 0.3095`, `macro_recall = 0.3095`), **automatic comment filtering remains unaccepted (`auto_filter_eligible = false`)**; API (`comment_filter_policy = "diagnostic_only_unvalidated"`) and `/demo/` (`hide_seeding = False` default) must display observable diagnostic flags and before/after sensitivity without hiding comments by default.
2. **`M5.2` Four-Aspect Sentiment, NFC Spans & Support Abstention Qualification:**
   - Verify `180` real multimodal `M3.3` text units (`29` videos: `N` `115/115` + `K` `115/115` verified, `50` overlap: `kappa_presence = 0.8616`, `kappa_4state = 0.7731`), `44/44 = 100.0%` gold NFC span validity, `0` video overlap across `dev` (`14` videos), `held_out` (`15` videos), and `absa_train_video_disjoint_v1.jsonl` (`90` videos, `human_verified = false` never used as Gold test), and `held_out` `aspect_detection_macro_f1 = 0.9286 >= 0.65`, `observed_sentiment_macro_f1 = 0.8293 >= 0.60`, `predicted_span_validity = 1.0000 >= 0.95`.
   - Qualify `service` (`gold_support = 0` in the `180`-unit pilot sample; conservative 4-aspect `F1 = 0.6964 >= 0.65`), enforce mandatory `min_viewer_comments = 3` support abstention (`26/29` sparse real videos abstain), and frame creator-vs-viewer differences strictly as `sentiment_discrepancy` (never deception, food-safety truth, or diner consensus).
3. **Immutable Snapshot Integrity & Two-Person Governance:**
   - Verify SHA-256 digests across `20261118_taxonomy_fix_v1`, `m3_3_pilot_snapshot_v1`, `m3_3_pilot_snapshot_v2`, and `m3_3_playwright_comments_20261125_v5` (`0` byte mutations) and record `K` gate concurrence while keeping global `G5 = NOT_RUN` (`M5.G = IN_PROGRESS`) until `N` co-signs.
