# M4.2 — Independent Peer Review & K 65-Item Full-Transcript Audit

- **Reviewer:** Trần Đình Khương (`K`)
- **Primary Owner:** Nguyễn Việt Nguyên (`N`)
- **Review Date:** 2026-11-20 (Asia/Ho_Chi_Minh)
- **Reviewed Baseline:** `main` @ `1531174e` (`M4.2` commits `15341f81` & `db345e87`)
- **Post-Fix Verification Branch:** `feat/k-m4.2-m5.1-m6.1-peer-reviews`
- **Verdict:** **`K` PEER REVIEW & `K` 65-ITEM HUMAN AUDIT COMPLETE (`M4.2` stays `IN_PROGRESS` pending `N`'s 65-item manual annotation)**

## 1. Target Validity & Scientific Claim Check

1. **Separated Observable Flags vs. Lexical Promo Cues (`PASS`):** `classify_observed_disclosure_flags` cleanly separates `observed_ad`, `observed_ecommerce`, `observed_ad_and_ecommerce`, and `unlabeled_unknown` from lexical promotional categories across `packages/absa/disclosure.py`, `AbsaComparisonRecord`, `/api/v1/trust/audit-video`, and `/demo/`.
2. **Zero Undisclosed-Sponsorship Probability Claims (`PASS`):** No contract field, API response, study receipt, or `/demo/` string calls platform flag prediction or `undisclosed_pr_risk` a probability of hidden/undisclosed sponsorship; `sponsorship_ground_truth_status="undisclosed_sponsorship_deferred"` is enforced everywhere.
3. **No Unlabeled Negatives & No Historical Audio/Prosody Join (`PASS`):** All `61,877` `unlabeled_unknown` records and `1,458` dual-flagged records are excluded from binary supervised evaluation (`is_ad_only` vs `is_ec_only`), and zero historical audio/prosody features are joined.

## 2. Defects Found During `K` Adversarial Audit & Resolved via TDD (`RED -> GREEN`)

All findings were reproduced with failing tests in [red-k-review-fixes.log](red-k-review-fixes.log) (`4 failed, 7 passed`) and resolved in [green-k-review-fixes.log](green-k-review-fixes.log) (`11 passed`):

1. **`[C1]` Workbook & LLM Excerpt Truncation (`transcript[:600]` / `[:550]`):** `48/60` (`80.0%`) of transcribed items in `review_sample_100.jsonl` exceeded `600` characters, hiding closing TikTok Shop / promo CTAs in `9` sampled videos (`m4_2_010`, `m4_2_020`, `m4_2_025`, `m4_2_061`, `m4_2_064`, `m4_2_069`, `m4_2_072`, `m4_2_087`, `m4_2_097`) and explaining `6/9` of the prior `lex_only` rows.
   - **Fix:** Preserved `transcript_excerpt` (`<= 600` chars) while adding `transcript_full` in `run_study.py` and `review_sample_100.jsonl`, expanded blinded LLM prompt window in `llm_draft_annotate.py` to `3,500` chars, and exported a flag-blinded untruncated sheet [nguyen_65_blinded_fulltext_sheet.jsonl](nguyen_65_blinded_fulltext_sheet.jsonl) for `N`'s remaining `65` annotations.
2. **`[C2]` Inline Caption Hashtag Bigram Leakage & Indirect Flag-Derived Column Guard:** `_tokenize_for_study` previously constructed word bigrams from `caption` *before* filtering `FORBIDDEN_DISCLOSURE_HASHTAGS`, allowing inline `#ad` / `#quảngcáo` bigrams (`đãi_ad`) into TF-IDF features, and `llm_draft_annotate.py` passed raw `caption` without scrubbing inline `#ad` / `#quảngcáo`.
   - **Fix:** Added `strip_forbidden_inline_hashtags`, expanded `FORBIDDEN_DISCLOSURE_HASHTAGS` to cover Vietnamese diacritics (`quảngcáo`, `tàitrợ`, `ads`, `paid_partnership`), rejected indirect `is_ec_video`/POI-derived columns (`video_format`, `has_cta`, `poi_*`) in `assert_no_feature_leakage`, and added an explicit ablation removing platform MCN/Shop campaign tags (`#vtmgr`, `#dcgr`, `#tiktokshop`, `#muataitiktok`).
3. **`[I1]` Author-Cluster Bootstrap vs. Naive Row-Level i.i.d. Bootstrap & `PYTHONHASHSEED` Tie-Breaking:** Because `2,097` test videos come from only `68` test creators, row-level i.i.d. bootstrap underestimated uncertainty (`[0.8739, 0.9090]`).
   - **Fix:** Implemented `author_handle` cluster resampling in `_bootstrap_metric_ci` (`PR-AUC = 0.8915`, honest cluster 95% CI **`[0.7845, 0.9502]`**; `0.8728` when ablating `#vtmgr`/`#muataitiktok`, and **`0.9183`** on transcribed rows without MCN/Shop tags in [m4_2_observed_disclosure_study_v2_k_review.json](../../../../../artifacts/benchmarks/m4_2_observed_disclosure_study_v2_k_review.json)) and deterministic `(-df, token)` sorting in `_fit_tfidf_logreg`.
4. **`[I2]` & `[I3]` Word-Boundary + Negation Guard & `/demo/` Tab 3 Flag Controls:** Fixed substring false positives (`"Ideal"` no longer matches `"deal"`), exempted negated disclaimers (`"không quảng cáo"`, `"không nhận tài trợ"`, `"không booking"`, `"quảng cáo lố"`), wired `hashtags` through `TrustAuditRequest` / `analyze_koc_vs_viewer_absa`, and added `is_ad` / `is_ec_video` checkboxes to Gradio Tab 3 (`apps/demo/ui.py`).

## 3. Summary of `K`'s 65-Item Blinded Full-Transcript Human Audit

`K` manually inspected full `caption` + full `transcript` (`32/65` had `> 600` chars) blinded to `observed_flag_status` ([khuong_65_full_transcript_audit.jsonl](khuong_65_full_transcript_audit.jsonl), [khuong_65_audit_summary.json](khuong_65_audit_summary.json)):

| Observed Flag Stratum (unblinded post-audit) | `explicit_promo_cta` | `brand_or_venue_focus_no_cta` | `organic_or_general_review` | `unclear_or_noisy_text` | `K` Total |
| --- | ---: | ---: | ---: | ---: | ---: |
| `observed_ad` | `4` | `8` | `3` | `2` | `17` |
| `observed_ad_and_ecommerce` | `5` | `4` | `1` | `1` | `11` |
| `observed_ecommerce` | `6` | `4` | `3` | `3` | `16` |
| `unlabeled_unknown` | `2` | `2` | `10` | `7` | `21` |
| **`K` Verified Total (`65` items)** | **`17`** | **`18`** | **`17`** | **`13`** | **`65`** |

- **`K` vs. blinded LLM draft agreement:** `44 / 65` (`67.69%`). Full-transcript reading overturned `21` draft labels, including post-600-char TikTok Shop CTAs (`m4_2_010`, `m4_2_020`, `m4_2_025`), out-of-domain appliances/personal-care items (`m4_2_015` neck massager, `m4_2_025` antiperspirant, `m4_2_070` handheld fan, `m4_2_081` Lock&Lock cookers, `m4_2_095` dishwasher), ASR typo evasion (`m4_2_094` `"giờ hang"`), and ASR song-lyric noise (`m4_2_004`, `m4_2_021`, `m4_2_085`, `m4_2_086`, `m4_2_093` Korean lyrics, `m4_2_098`).
- **Next step for `N`:** Complete `N_observed_wording_label`, `N_error_or_domain_note`, and `N_human_verified=true` on `N`'s `65` items using [nguyen_65_blinded_fulltext_sheet.jsonl](nguyen_65_blinded_fulltext_sheet.jsonl), then compute `30`-item `N`/`K` double-review Cohen's kappa to close `M4.2`.
