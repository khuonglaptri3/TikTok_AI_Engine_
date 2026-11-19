# M4.2 — Observed Disclosure/Commerce Flags and Promotional Language Specification

- **Task ID:** `M4.2` (Observed disclosure/commerce and promotional language; undisclosed sponsorship deferred)
- **Primary Owner:** Nguyễn Việt Nguyên (`N`)
- **Peer Reviewer:** Trần Đình Khương (`K`)
- **Requirement Source:** [TikTok_AI_Engine_Milestone.md](../../../../planning/TikTok_AI_Engine_Milestone.md) (`M4.2`, line 105)
- **Date:** 2026-11-19 (Asia/Ho_Chi_Minh)
- **Branch:** `feat/m4.2-observed-disclosure-promo` (branched from `main` @ `dcdd6233`)
- **Upstream Prerequisite:** `M1.G` (`PASS` local-only; Gold corpus `data/corpus/20261118_taxonomy_fix_v1`, `70,996` rows). Audio/prosody stays strictly excluded until `M4.1` closes.

## Problem Statement

Prior repository code (`packages/absa/analyzer.py`) combined platform flags (`is_ad`, `is_ec_video`), caption/transcript promo keywords, seeding ratio, and hype gap into a single `undisclosed_pr_risk` score (`1.0` whenever `is_ad` or `is_ec_video` is true). That conflated disclosed commerce/ad flags with hidden sponsorship intent, relied on a tiny promo keyword list (`0.62%` hit rate on `is_ec_only`), and risked misinterpreting `is_ad=False, is_ec_video=False` (`61,877` rows) as verified non-sponsored negatives.

## Scope & Acceptance Requirements

1. **Separate Observable Platform Flags from Lexical Promotional Indicators:**
   - Add `packages/absa/disclosure.py` defining deterministic observable flag statuses (`observed_ad`, `observed_ecommerce`, `observed_ad_and_ecommerce`, `unlabeled_unknown`) and categorized Vietnamese promotional language indicators (`discount_voucher`, `commerce_cart_cta`, `branch_venue_promo`, `explicit_text_disclosure`).
   - Unlabeled items (`is_ad=False, is_ec_video=False`) MUST remain `"unlabeled_unknown"`, never `"verified_organic"` or `"verified_negative"`.
   - No output or UI text may describe platform flags or lexical indicators as a probability of undisclosed sponsorship.
2. **Contract, ABSA Service & Demo UI Integration:**
   - Extend `AbsaComparisonRecord` (`packages/data_contracts/multimodal.py`) with defaulted fields (`disclosure_flag_status`, `promotional_language_indicators`, `lexical_promo_score`, `sponsorship_ground_truth_status="undisclosed_sponsorship_deferred"`, `disclosure_target_note`) while preserving `undisclosed_pr_risk` compatibility.
   - Update `analyze_koc_vs_viewer_absa` and `/demo/` `format_trust_audit_markdown` to display platform flag status separately from lexical promotional cues with an explicit undisclosed-sponsorship deferral note.
3. **100-Item Stratified Historical Audit Pool & Corpus Study (`pipelines/audit_m4_2_disclosure/`):**
   - Stratify and analyze all `70,996` historical records in `data/corpus/20261118_taxonomy_fix_v1` for observable flags, lexical cue coverage, domain (`food_category`) differences, and unlabeled positive-cue leakage (proving why unlabeled rows cannot be verified negatives).
   - Export a balanced, deterministic `100`-item historical text review sheet (`data/evaluation/m4_2_disclosure/review_sample_100.jsonl`) with equal K/N assignments (`30` double-review overlap items) and `human_verified=false` placeholders for `K`/`N` manual inspection.
4. **Leakage-Free, Author-Grouped Genuine-Target Baseline (No Unlabeled Negatives, No Prosody Join):**
   - Provide an optional CPU L2-regularized logistic regression baseline (`numpy` + `scipy`) trained strictly within the genuinely labeled cohort (`is_ad_only` vs `is_ec_only`, excluding `both` and `unlabeled_unknown`) using creator-disjoint (`author_handle`) held-out splits.
   - Enforce automated feature-leakage rejection (`is_ad`, `is_ec_video`, `#ad`/`#quangcao` explicit disclosure tags, `commerce_user`, `undisclosed_pr_risk`, and any audio/prosody fields).
   - Report held-out PR-AUC, Brier score, and bootstrap 95% CIs exclusively for the genuine `is_ad_only` vs `is_ec_only` target; hidden-intent / undisclosed-sponsorship training stays `DEFERRED`.
5. **Milestone Boundaries:** `M4.2` stays `IN_PROGRESS` until `N` and `K` complete the 100-text manual double-review (`30` overlap) and `K` verifies target validity and report wording.
