# M4.2 — Observed Disclosure/Commerce and Promotional Language

- Status: IN_PROGRESS (`N`'s flag/lexical separation + `K`'s peer-review TDD hardening, author-cluster bootstrap & campaign-tag ablation study (`PR-AUC=0.8915`, `0.8728` without MCN/Shop tags), and `K`'s `65/65` blinded full-transcript human verification complete; awaiting `N`'s `65`-item manual annotation on [nguyen_65_blinded_fulltext_sheet.jsonl](evidence/nguyen_65_blinded_fulltext_sheet.jsonl))
- Execution date: 2026-11-19 to 2026-11-20 (Asia/Ho_Chi_Minh)
- Requirement source: [TikTok_AI_Engine_Milestone.md](../../../planning/TikTok_AI_Engine_Milestone.md) (`M4.2`)
- Repository version: `feat/k-m4.2-m5.1-m6.1-peer-reviews` (branched from `main` @ `1531174e`)
- Primary owner: Nguyễn Việt Nguyên (`N`) · Peer reviewer: Trần Đình Khương (`K`, peer review & `65`-item audit complete)
- Specification: [spec.md](superpowers/spec.md)
- Execution plan: [plan.md](superpowers/plan.md)

## Conclusion

**Code separation, `K` adversarial peer-review TDD fixes, leakage-free author-cluster evaluation, and `K`'s `65`-item blinded full-transcript human audit are complete and verified (`188 passed`, `95`-file Linux/Windows `mypy`); `N`'s `65`-item manual annotation (`30` overlap + `35` `N_only`) remains pending (`IN_PROGRESS`).**

- Platform disclosure/commerce flags (`is_ad`, `is_ec_video`) are cleanly separated from lexical promotional cues across runtime contracts, ABSA scoring, `/api/v1/trust/audit-video`, and `/demo/` Tab 3 (which now exposes `is_ad`/`is_ec_video` controls and negation/word-boundary-hardened matching in `packages/absa/disclosure.py`). Unflagged items strictly remain `unlabeled_unknown` (never verified negatives), zero historical audio/prosody features are joined, and undisclosed sponsorship probability modeling remains **`DEFERRED`**.
- **Post-review corpus & classifier audit ([m4_2_observed_disclosure_study_v2_k_review.json](../../../../artifacts/benchmarks/m4_2_observed_disclosure_study_v2_k_review.json)):** After blocking inline `#ad`/`#quảngcáo` caption bigram leakage, adding indirect flag/POI column guards (`video_format`, `has_cta`, `poi_*`), and upgrading from row-level i.i.d. bootstrap to **`author_handle` cluster bootstrap**, creator-disjoint `is_ad_only` (`3,321`) vs `is_ec_only` (`4,340`) achieves `PR-AUC = 0.8915` (cluster 95% CI **`[0.7845, 0.9502]`**, `Brier = 0.1324`), **`0.8728`** (`[0.7420, 0.9462]`) when also ablating platform MCN/Shop tags (`#vtmgr`, `#dcgr`, `#tiktokshop`, `#muataitiktok`), and **`0.9183`** (`[0.8389, 0.9642]`) on transcribed rows without MCN/Shop tags.
- **`K` 65-item blinded full-transcript human audit ([khuong_peer_review.md](evidence/khuong_peer_review.md), [khuong_65_audit_summary.json](evidence/khuong_65_audit_summary.json)):** `K` read full untruncated captions + transcripts (`32/65` exceeded `600` chars) blinded to `observed_flag_status`, setting `K_human_verified=True` on all `65` `K`-assigned items (`17` `explicit_promo_cta`, `18` `brand_or_venue_focus_no_cta`, `17` `organic_or_general_review`, `13` `unclear_or_noisy_text`; `67.69%` agreement with the `550`-char LLM draft, overturning `21` items due to post-600-char TikTok Shop CTAs, ASR song lyrics, and out-of-domain appliances). `N_human_verified` remains `False` (`0/65`), with a flag-blinded untruncated sheet prepared at [nguyen_65_blinded_fulltext_sheet.jsonl](evidence/nguyen_65_blinded_fulltext_sheet.jsonl).

## Work performed

- **Separated observable flags & hardened promo lexicon ([disclosure.py](../../../../packages/absa/disclosure.py)):** Added `classify_observed_disclosure_flags`, Unicode word-boundary + negation-aware (`"không quảng cáo"`, `"không nhận tài trợ"`, `"quảng cáo lố"`) 4-category promotional matching, diacritic disclosure hashtag support (`#quảngcáo`, `#tàitrợ`, `#ad`, `#sponsored`), and fail-closed `assert_no_feature_leakage` blocking direct flags, `video_format`, `has_cta`, `poi_*`, and `prosody_*`/`audio_*`/`whisper_*`/`voice_*`.
- **Contract, ABSA & Demo UI integration ([multimodal.py](../../../../packages/data_contracts/multimodal.py), [analyzer.py](../../../../packages/absa/analyzer.py), [presentation.py](../../../../apps/demo/presentation.py), [ui.py](../../../../apps/demo/ui.py)):** Extended `AbsaComparisonRecord` and `TrustAuditRequest` (`hashtags`, `is_ad`, `is_ec_video`), wired `is_ad`/`is_ec_video` checkboxes in `/demo/` Tab 3, and kept `undisclosed_pr_risk` strictly labeled as a non-probability compatibility heuristic.
- **Leakage-free author-cluster study & untruncated 100-item workbook ([disclosure_eval.py](../../../../packages/absa/disclosure_eval.py), [run_study.py](../../../../pipelines/audit_m4_2_disclosure/run_study.py), [llm_draft_annotate.py](../../../../pipelines/audit_m4_2_disclosure/llm_draft_annotate.py)):** Blocked inline caption hashtag bigram leakage before bigram construction, enforced `PYTHONHASHSEED`-deterministic feature tie-breaking, switched to `author_handle` cluster bootstrap CIs, added `transcript_full` to `review_sample_100.jsonl` so closing CTAs beyond `600` chars are never hidden, and recorded `K`'s `65/65` human judgments ([khuong_65_full_transcript_audit.jsonl](evidence/khuong_65_full_transcript_audit.jsonl)).

## Quantitative findings (`20261118_taxonomy_fix_v1`, v2 word-boundary/negation-hardened)

| Observable Flag Stratum | Rows | Authors | Transcribed | Promo Lexicon Hit Rate (v1 -> v2) | `K` 65-Item Human Labels (`CTA / Brand / Organic / Noisy`) |
| --- | ---: | ---: | ---: | ---: | --- |
| `observed_ad` (`is_ad` only) | `3,321` | `178` | `915` | `16.26%` | `4 / 8 / 3 / 2` (`n=17`) |
| `observed_ecommerce` (`is_ec_video` only) | `4,340` | `156` | `797` | `11.98%` | `6 / 4 / 3 / 3` (`n=16`) |
| `observed_ad_and_ecommerce` | `1,458` | `122` | `484` | `20.58%` | `5 / 4 / 1 / 1` (`n=11`) |
| `unlabeled_unknown` (not verified negative) | `61,877` | `264` | `19,552` | `8.72%` | `2 / 2 / 10 / 7` (`n=21`) |

- **Author-disjoint held-out `is_ad_only` vs `is_ec_only` (`0` author overlap, author-cluster bootstrap 95% CIs):**
  - All labeled (`n_train=5,564`, `n_test=2,097` / `68` authors): `PR-AUC = 0.8915` (`[0.7845, 0.9502]`), `Brier = 0.1324` (`[0.0970, 0.1729]`); **ablating `#vtmgr`/`#dcgr`/`#tiktokshop`/`#muataitiktok`:** `PR-AUC = 0.8728` (`[0.7420, 0.9462]`), `Brier = 0.1517`.
  - Transcribed only (`n_train=1,111`, `n_test=601` / `48` authors): `PR-AUC = 0.9180` (`[0.8407, 0.9613]`), `Brier = 0.1666`; **ablating MCN/Shop tags:** `PR-AUC = 0.9183` (`[0.8389, 0.9642]`), `Brier = 0.1704`.

## Outputs

| File | Purpose |
| --- | --- |
| [workflow.md](evidence/workflow.md) | Skill provenance, `N` baseline + `K` peer-review TDD ledger, and command verification receipts |
| [khuong_peer_review.md](evidence/khuong_peer_review.md) | `K`'s adversarial code/target review, TDD fix summary, and `65`-item full-transcript audit report |
| [m4_2_observed_disclosure_study_v2_k_review.json](../../../../artifacts/benchmarks/m4_2_observed_disclosure_study_v2_k_review.json) / [m4_2_observed_disclosure_study.json](../../../../artifacts/benchmarks/m4_2_observed_disclosure_study.json) | Post-review leakage-free author-cluster study + campaign-tag ablation (v1 study preserved untouched) |
| [review_sample_100.jsonl](../../../../data/evaluation/m4_2_disclosure/review_sample_100.jsonl) | `100`-item historical workbook with `transcript_full`, `K_human_verified=True` (`65/65`), and `N_human_verified=False` (`0/65`) |
| [khuong_65_full_transcript_audit.jsonl](evidence/khuong_65_full_transcript_audit.jsonl) / [khuong_65_audit_summary.json](evidence/khuong_65_audit_summary.json) | `K`'s `65` blinded full-transcript human annotations and cross-tabulation vs. flags & LLM draft |
| [nguyen_65_blinded_fulltext_sheet.jsonl](evidence/nguyen_65_blinded_fulltext_sheet.jsonl) | Flag-blinded, untruncated `65`-item full-transcript workbook ready for `N`'s independent human review |
| [review_sample_100_llm_draft.jsonl](../../../../data/evaluation/m4_2_disclosure/review_sample_100_llm_draft.jsonl) / [m4_2_llm_audit_summary.json](evidence/m4_2_llm_audit_summary.json) | Initial `550`-char blinded `gemini-3.1-flash-lite` assistant draft preserved for comparison |
| [red-k-review-fixes.log](evidence/red-k-review-fixes.log) / [green-k-review-fixes.log](evidence/green-k-review-fixes.log) | `K` peer-review TDD RED (`4 failed`) -> GREEN (`11 passed`) logs (`test_m4_2_disclosure.py`) |

## Verification

| Check | Result | Scope / evidence |
| --- | --- | --- |
| `python3 docs/reports/milestones/M4.2/evidence/run_k_m4_2_verification_and_audit.py` | PASS (`PR-AUC=0.8915` / `0.8728` no-MCN; `K=65/65`) | Full `70,996` v2 study + `K` 65-item workbook update; [m4_2_observed_disclosure_study_v2_k_review.json](../../../../artifacts/benchmarks/m4_2_observed_disclosure_study_v2_k_review.json) |
| `python3 -m pytest tests/unit/test_m4_2_disclosure.py -v` | PASS (`11 passed in 8.48s`) | `7` baseline + `4` `K`-review regressions; [green-k-review-fixes.log](evidence/green-k-review-fixes.log) |
| `python3 -m pytest -v` | PASS (`188 passed`) | Full workspace suite on `feat/k-m4.2-m5.1-m6.1-peer-reviews` |
| `python3 -m mypy packages apps pipelines` (+ `--platform win32`) | PASS (`95 source files` each) | Strict Linux & Windows static type checks |
| `python3 scripts/check_secrets.py` | PASS (`0` leaks) | Full workspace secret hygiene |

## Open issues

| Issue | Impact | Follow-up / responsible task |
| --- | --- | --- |
| `N`'s `65` human annotations pending (`N_human_verified=false`) | `30`-item `N`/`K` double-review Cohen's kappa and disagreement adjudication await `N`'s manual pass | `N` annotates [nguyen_65_blinded_fulltext_sheet.jsonl](evidence/nguyen_65_blinded_fulltext_sheet.jsonl) and merges into `review_sample_100.jsonl` to close `M4.2` |
| Legacy `undisclosed_pr_risk` column retained in Gold `fact_absa_reviews.parquet` schema | Kept strictly for `M3.1` Parquet schema compatibility while runtime UI/API mark it non-probability heuristic | Retain compatibility notice through `M4.G` |
| Audio/prosody cues excluded (`historical_audio_prosody_joined=false`) | Intentional per `M4.2` rule until `M4.1` delivers pilot `audio_derived` segments | Evaluate fresh audio cues only after `M4.1` closes |

## Acceptance and handoff

| Task criterion | Result | Evidence |
| --- | --- | --- |
| Separate observed `is_ad`/`is_ec_video` flags from lexical promotional cues; retain `unlabeled_unknown` | Met (`N` + `K` verified across API & `/demo/`) | [disclosure.py](../../../../packages/absa/disclosure.py), [ui.py](../../../../apps/demo/ui.py) |
| No output calls flag prediction a probability of undisclosed sponsorship; no unlabeled negative; no flag leakage or historical prosody join | Met (`K` verified + inline bigram/indirect column guards added) | [disclosure_eval.py](../../../../packages/absa/disclosure_eval.py), [khuong_peer_review.md](evidence/khuong_peer_review.md) |
| Grouped held-out evaluation reporting PR-AUC/Brier strictly for genuinely labeled targets (`is_ad_only` vs `is_ec_only`) | Met (author-cluster bootstrap + MCN tag ablation) | [m4_2_observed_disclosure_study_v2_k_review.json](../../../../artifacts/benchmarks/m4_2_observed_disclosure_study_v2_k_review.json) |
| Review `100` historical texts (`30` double-reviewed) & `K` peer check of target validity/claims | `K` peer check & `K` `65/65` human audit complete; awaiting `N` `65/65` | [khuong_65_full_transcript_audit.jsonl](evidence/khuong_65_full_transcript_audit.jsonl), [nguyen_65_blinded_fulltext_sheet.jsonl](evidence/nguyen_65_blinded_fulltext_sheet.jsonl) |

Final task status: **IN_PROGRESS** (`K`'s target-validity peer review, TDD leakage/bootstrap hardening, and `65/65` full-transcript human annotations are complete; ready for `N` to complete `N`'s `65` blinded annotations and close `M4.2` prior to `M4.G`).
