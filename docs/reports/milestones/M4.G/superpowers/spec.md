# M4.G — Audio Timing/Provenance & Observable Promotion Gate (`G4`) Specification

- **Task ID:** `M4.G` (`Gate G4`)
- **Requirement Source:** [TikTok_AI_Engine_Milestone.md](../../../../planning/TikTok_AI_Engine_Milestone.md) (`M4.G`, line 106 & §4 line 128)
- **Primary Owner:** Nguyễn Việt Nguyên (`N`, `2` pts) · **Peer Reviewer & Gate Probe Author:** Trần Đình Khương (`K`, `2` pts)
- **Date:** 2026-11-26 (Asia/Ho_Chi_Minh)

## 1. Gate Scope & Mandatory Acceptance Invariants

1. **Upstream & Task Prerequisites:**
   - Verify `G0 = PASS`, `G1 = PASS` (local-only), `G2 = PASS`, `M4.1 = COMPLETE`, and `M4.2 = COMPLETE`.
   - Record upstream `M3.G` (`G3`) status transparently (`technical checks PASS`, awaiting final `N` co-sign); per two-person governance (`AGENTS.md`), `M4.G` stays `IN_PROGRESS` (`G4 = NOT_RUN`) until `N` co-signs both `G3` and `G4`.
2. **`M4.1` Audio Timing, Prosody & Resource Budget Gate:**
   - Cryptographically verify [m4_1_audio_pilot_receipt.json](../../M4.1/evidence/m4_1_audio_pilot_receipt.json), [m4_1_utterance_review_sheet.jsonl](../../M4.1/evidence/m4_1_utterance_review_sheet.jsonl), and [m4_1_joint_reference_eval_receipt.json](../../M4.1/evidence/m4_1_joint_reference_eval_receipt.json).
   - Enforce `processed_mp3_count == 29`, `total_audio_minutes <= 60.0`, combined ASR + prosody CPU wall time `<= 14,400 s` (`4` CPU hours), `peak_rss_mib <= 8,192 MiB`, `invariant_pass_rate == 1.0` (`436/436` `0 <= start < end <= media_duration`), and strict separation of `audio_derived` estimates vs historical `wps_estimated` interpolation.
   - Live-recompute `evaluate_m4_1_reference_set` and `compute_m4_1_annotator_agreement` over `m4_1_utterance_review_sheet.jsonl`: require `N` (`38/38`) + `K` (`38/38`) verified, `evaluated_utterance_count >= 50` (`53`), `invalid_verified_row_count == 0`, `total_sampled_audio_minutes <= 20.0`, `boundary_median_abs_err_sec <= 1.0`, and `boundary_p95_abs_err_sec <= 3.0`; otherwise fail closed (`ABSTAIN_PRECISE_PLAYBACK`).
3. **`M4.2` Observable Promotion Target, Anti-Leakage & Epistemic Guardrails:**
   - Verify [m4_2_observed_disclosure_study_v2_k_review.json](../../../../../artifacts/benchmarks/m4_2_observed_disclosure_study_v2_k_review.json), [review_sample_100.jsonl](../../../../../data/evaluation/m4_2_disclosure/review_sample_100.jsonl), [n_k_100_combined_audit_summary.json](../../M4.2/evidence/n_k_100_combined_audit_summary.json), and [nguyen_signoff_receipt.json](../../M4.2/evidence/nguyen_signoff_receipt.json).
   - Enforce `undisclosed_sponsorship_status == "DEFERRED"`, `unlabeled_items_treated_as_verified_negative == False`, `historical_audio_prosody_joined == False`, `100/100` unique historical items verified (`65 N` + `65 K`, `30`-item `Cohen's kappa >= 0.50`), and runtime `assert_no_feature_leakage` rejection of direct flags, `video_format`, `has_cta`, `poi_*`, and `prosody_*`/`audio_*`.
   - Verify ASGI `/api/v1/trust/audit-video` and `/api/v1/script/generate` epistemic guardrails: `sponsorship_ground_truth_status == "undisclosed_sponsorship_deferred"`, `disclosure_flag_status == "unlabeled_unknown"` when unflagged, and HTTP `422` refusal on hidden-sponsorship probability prompts.
4. **Post-`M4.1` Fresh `29`-Video Prosody vs. Observable Promotion Check (`M4.2` Open Item Resolution):**
   - Join `M4.1` `per_video_prosody` (`29` fresh pilot `.mp3`s) with `m3_3_pilot_snapshot_v2` `fact_videos.parquet` (`is_ad`, `is_ec_video`, caption/transcript promotional cues).
   - Report descriptive group medians/IQRs and enforce `prosody_promotion_classifier_accepted = False` and `undisclosed_sponsorship_from_prosody = "REJECTED_EPISTEMICALLY_INVALID"` (a gate can never convert disclosed-ad flags or acoustic excitement into undisclosed-sponsorship labels).
