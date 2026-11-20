# M4.2 — Observed Disclosure/Commerce and Promotional Language

- Status: COMPLETE (`N` flag/lexical separation + `K` adversarial peer-review TDD hardening, leakage-free author-cluster bootstrap & campaign-tag ablation study (`PR-AUC=0.8915`, `0.8728` without MCN/Shop tags), and `100/100` two-contributor full-transcript human annotations (`N=65/65`, `K=65/65`, `30`-item overlap `22/30 = 73.33%`, `Cohen's kappa = 0.6364`) complete; undisclosed sponsorship probability modeling strictly `DEFERRED`)
- Execution date: 2026-11-19 to 2026-11-20 (Asia/Ho_Chi_Minh)
- Requirement source: [TikTok_AI_Engine_Milestone.md](../../../planning/TikTok_AI_Engine_Milestone.md) (`M4.2`)
- Repository version: `main` (merging `feat/k-m4.2-m5.1-m6.1-peer-reviews` over `14becda0`)
- Primary owner: Nguyễn Việt Nguyên (`N`, implementation & `65/65` human audit complete) · Peer reviewer: Trần Đình Khương (`K`, peer review, TDD fixes & `65/65` human audit complete)
- Specification: [spec.md](superpowers/spec.md)
- Execution plan: [plan.md](superpowers/plan.md)

## Conclusion

**All `M4.2` acceptance criteria are satisfied (`COMPLETE`; `194 passed` full pytest, `100`-file Linux/Windows `mypy`, `0` secret leaks).**

- Platform disclosure/commerce flags (`is_ad`, `is_ec_video`) are cleanly separated from lexical promotional cues across runtime contracts, ABSA scoring, `/api/v1/trust/audit-video`, and `/demo/` Tab 3 (which exposes `is_ad`/`is_ec_video` controls and negation/word-boundary-hardened matching in `packages/absa/disclosure.py`). Unflagged items strictly remain `unlabeled_unknown` (never verified negatives), zero historical audio/prosody features are joined, and undisclosed sponsorship probability modeling remains **`DEFERRED`**.
- **Post-review corpus & classifier audit ([m4_2_observed_disclosure_study_v2_k_review.json](../../../../artifacts/benchmarks/m4_2_observed_disclosure_study_v2_k_review.json)):** After blocking inline `#ad`/`#quảngcáo` caption bigram leakage, adding indirect flag/POI column guards (`video_format`, `has_cta`, `poi_*`), and upgrading from row-level i.i.d. bootstrap to **`author_handle` cluster bootstrap**, creator-disjoint `is_ad_only` (`3,321`) vs `is_ec_only` (`4,340`) achieves `PR-AUC = 0.8915` (cluster 95% CI **`[0.7845, 0.9502]`**, `Brier = 0.1324`), **`0.8728`** (`[0.7420, 0.9462]`) when also ablating platform MCN/Shop tags (`#vtmgr`, `#dcgr`, `#tiktokshop`, `#muataitiktok`), and **`0.9183`** (`[0.8389, 0.9642]`) on transcribed rows without MCN/Shop tags (`N`'s pre-review v1 baseline preserved untouched in [m4_2_observed_disclosure_study.json](../../../../artifacts/benchmarks/m4_2_observed_disclosure_study.json)).
- **Two-contributor `100/100` full-transcript human audit ([review_sample_100.jsonl](../../../../data/evaluation/m4_2_disclosure/review_sample_100.jsonl), [n_k_100_combined_audit_summary.json](evidence/n_k_100_combined_audit_summary.json)):** `N` (`m4_2_001..065`, `N_human_verified=True`, [nguyen_signoff_receipt.json](evidence/nguyen_signoff_receipt.json)) and `K` (`m4_2_001..030` + `m4_2_066..100`, `K_human_verified=True`, [khuong_peer_review.md](evidence/khuong_peer_review.md)) independently inspected full untruncated captions + transcripts (`transcript_full`). On the `30` `double_review_N_K` overlap items, exact 4-class agreement is **`22 / 30 = 73.33%`** (**`Cohen's kappa = 0.6364`**); all `8` boundary differences (`m4_2_006, 013, 014, 015, 016, 022, 026, 030` — e.g., caption-only brand/price hooks vs `explicit_promo_cta`, or 6-word missing-transcript captions) are preserved transparently with per-reviewer notes. Both reviewers confirmed that `unlabeled_unknown` includes explicit discount/cart CTAs (`m4_2_002`, `m4_2_011`, `m4_2_063`) while `observed_ad` includes ordinary street-food reviews (`m4_2_007`), proving why neither platform flags nor promo phrases establish hidden sponsorship ground truth.

## Work performed

- **Separated observable flags & hardened promo lexicon ([disclosure.py](../../../../packages/absa/disclosure.py)):** Added `classify_observed_disclosure_flags`, Unicode word-boundary + negation-aware (`"không quảng cáo"`, `"không nhận tài trợ"`, `"quảng cáo lố"`) 4-category promotional matching, diacritic disclosure hashtag support (`#quảngcáo`, `#tàitrợ`, `#ad`, `#sponsored`), and fail-closed `assert_no_feature_leakage` blocking direct flags, `video_format`, `has_cta`, `poi_*`, and `prosody_*`/`audio_*`/`whisper_*`/`voice_*`.
- **Contract, ABSA & Demo UI integration ([multimodal.py](../../../../packages/data_contracts/multimodal.py), [analyzer.py](../../../../packages/absa/analyzer.py), [trust.py](../../../../apps/api/app/routers/trust.py), [presentation.py](../../../../apps/demo/presentation.py), [ui.py](../../../../apps/demo/ui.py)):** Extended `AbsaComparisonRecord` and `TrustAuditRequest` (`hashtags`, `is_ad`, `is_ec_video`), wired `is_ad`/`is_ec_video` checkboxes in `/demo/` Tab 3, and kept `undisclosed_pr_risk` strictly labeled as a non-probability compatibility heuristic.
- **Leakage-free author-cluster study & two-human `100`-item audit ([disclosure_eval.py](../../../../packages/absa/disclosure_eval.py), [run_study.py](../../../../pipelines/audit_m4_2_disclosure/run_study.py), [llm_draft_annotate.py](../../../../pipelines/audit_m4_2_disclosure/llm_draft_annotate.py)):** Blocked inline caption hashtag bigram leakage before bigram construction, enforced `PYTHONHASHSEED`-deterministic feature tie-breaking, switched to `author_handle` cluster bootstrap CIs, added `transcript_full` to `review_sample_100.jsonl` so closing CTAs beyond `600` chars (`m4_2_010`, `m4_2_020`) are preserved, and merged `N`'s `65/65` + `K`'s `65/65` human judgments ([n_k_100_combined_audit_summary.json](evidence/n_k_100_combined_audit_summary.json)).

## Quantitative findings (`20261118_taxonomy_fix_v1`, v2 word-boundary/negation-hardened)

| Observable Flag Stratum | Corpus Rows | Authors | Transcribed | Promo Lexicon Hit Rate (v2) | `N` 65-Item Labels (`CTA / Brand / Organic / Noisy`) | `K` 65-Item Labels (`CTA / Brand / Organic / Noisy`) |
| --- | ---: | ---: | ---: | ---: | --- | --- |
| `observed_ad` (`is_ad` only) | `3,321` | `178` | `915` | `16.26%` | `6 / 6 / 1 / 1` (`n=14`) | `4 / 8 / 3 / 2` (`n=17`) |
| `observed_ecommerce` (`is_ec_video` only) | `4,340` | `156` | `797` | `11.98%` | `6 / 6 / 3 / 1` (`n=16`) | `6 / 4 / 3 / 3` (`n=16`) |
| `observed_ad_and_ecommerce` | `1,458` | `122` | `484` | `20.58%` | `6 / 6 / 0 / 0` (`n=12`) | `5 / 4 / 1 / 1` (`n=11`) |
| `unlabeled_unknown` (not verified negative) | `61,877` | `264` | `19,552` | `8.72%` | `4 / 7 / 10 / 2` (`n=23`) | `2 / 2 / 10 / 7` (`n=21`) |
| **Total (`70,996` corpus / `100` sample)** | **`70,996`** | **`264`** | **`21,748`** | **`9.50%`** | **`22 / 25 / 14 / 4` (`n=65`)** | **`17 / 18 / 17 / 13` (`n=65`)** |

- **Author-disjoint held-out `is_ad_only` vs `is_ec_only` (`0` author overlap, author-cluster bootstrap 95% CIs):**
  - All labeled (`n_train=5,564`, `n_test=2,097` / `68` authors): `PR-AUC = 0.8915` (`[0.7845, 0.9502]`), `Brier = 0.1324` (`[0.0970, 0.1729]`); **ablating `#vtmgr`/`#dcgr`/`#tiktokshop`/`#muataitiktok`:** `PR-AUC = 0.8728` (`[0.7420, 0.9462]`), `Brier = 0.1517`.
  - Transcribed only (`n_train=1,111`, `n_test=601` / `48` authors): `PR-AUC = 0.9180` (`[0.8407, 0.9613]`), `Brier = 0.1666`; **ablating MCN/Shop tags:** `PR-AUC = 0.9183` (`[0.8389, 0.9642]`), `Brier = 0.1704`.
- **Two-human double-review agreement (`m4_2_001..030`):** `22/30` exact 4-class match (`73.33%`, `Cohen's kappa = 0.6364`). Both `N` and `K` independently overturned truncated `600`-char draft errors (`m4_2_010`, `m4_2_020` late TikTok Shop CTAs; `m4_2_004`, `m4_2_021`, `m4_2_027` ASR song lyrics / sparse text).

## Outputs

| File | Purpose |
| --- | --- |
| [workflow.md](evidence/workflow.md) | Skill provenance, `N` baseline + `K` peer-review TDD ledger, and two-human convergence record |
| [khuong_peer_review.md](evidence/khuong_peer_review.md), [nguyen_signoff_receipt.json](evidence/nguyen_signoff_receipt.json) | `K`'s adversarial code/target review + `65`-item audit report and `N`'s `65`-item sign-off receipt |
| [n_k_100_combined_audit_summary.json](evidence/n_k_100_combined_audit_summary.json) | Merged `100/100` `N`+`K` label counts, stratum cross-tabulation, `30`-item `Cohen's kappa = 0.6364`, and `8` boundary diffs |
| [m4_2_observed_disclosure_study_v2_k_review.json](../../../../artifacts/benchmarks/m4_2_observed_disclosure_study_v2_k_review.json) / [m4_2_observed_disclosure_study.json](../../../../artifacts/benchmarks/m4_2_observed_disclosure_study.json) | Post-review leakage-free author-cluster study + campaign-tag ablation (v1 study preserved untouched) |
| [review_sample_100.jsonl](../../../../data/evaluation/m4_2_disclosure/review_sample_100.jsonl) | Finalized `100`-item historical workbook with `transcript_full`, `N_human_verified=True` (`65/65`), and `K_human_verified=True` (`65/65`) |
| [khuong_65_full_transcript_audit.jsonl](evidence/khuong_65_full_transcript_audit.jsonl) / [khuong_65_audit_summary.json](evidence/khuong_65_audit_summary.json) | `K`'s `65` blinded full-transcript human annotations and cross-tabulation vs. flags & LLM draft |
| [review_sample_100_llm_draft.jsonl](../../../../data/evaluation/m4_2_disclosure/review_sample_100_llm_draft.jsonl) / [m4_2_llm_audit_summary.json](evidence/m4_2_llm_audit_summary.json) | Initial `600`-char blinded `gemini-3.1-flash-lite` assistant draft preserved for comparison |
| [red-k-review-fixes.log](evidence/red-k-review-fixes.log) / [green-k-review-fixes.log](evidence/green-k-review-fixes.log) | `K` peer-review TDD RED (`4 failed`) -> GREEN (`11 passed`) logs ([test_m4_2_disclosure.py](../../../../tests/unit/test_m4_2_disclosure.py)) |
| [m4_2-pytest.log](evidence/m4_2-pytest.log), [k-review-full-pytest.log](evidence/k-review-full-pytest.log), [k-review-mypy.log](evidence/k-review-mypy.log) | Baseline and post-review pytest/mypy verification logs |

## Verification

| Check | Result | Scope / evidence |
| --- | --- | --- |
| `python3 docs/reports/milestones/M4.2/evidence/run_k_m4_2_verification_and_audit.py` | PASS (`PR-AUC=0.8915` / `0.8728` no-MCN; `N=65/65`, `K=65/65`) | Full `70,996` v2 study + `100/100` `N`+`K` workbook convergence; [m4_2_observed_disclosure_study_v2_k_review.json](../../../../artifacts/benchmarks/m4_2_observed_disclosure_study_v2_k_review.json), [n_k_100_combined_audit_summary.json](evidence/n_k_100_combined_audit_summary.json) |
| `python3 -m pytest tests/unit/test_m4_2_disclosure.py -v` | PASS (`11 passed in 8.48s`) | `7` baseline + `4` `K`-review regressions; [green-k-review-fixes.log](evidence/green-k-review-fixes.log) |
| `python3 -m pytest -v` | PASS (`194 passed in 29.62s`) | Full post-merge workspace suite on `main` |
| `python3 -m mypy packages apps pipelines` (+ `--platform win32`) | PASS (`100 source files` each) | Strict Linux & Windows static type checks on merged `main` |
| `python3 scripts/check_secrets.py` | PASS (`0` leaks) | Full workspace secret hygiene |

## Open issues

| Issue | Impact | Follow-up / responsible task |
| --- | --- | --- |
| Legacy `undisclosed_pr_risk` column retained in Gold `fact_absa_reviews.parquet` schema | Kept strictly for `M3.1` Parquet schema compatibility while runtime UI/API explicitly mark it non-probability heuristic | Retain compatibility notice through `M4.G` |
| Audio/prosody cues excluded (`historical_audio_prosody_joined=false`) | Intentional per `M4.2` rule until `M4.1` delivers pilot `audio_derived` segments | Evaluate fresh audio cues only after `M4.1` closes; `M4.G` stays `NOT_RUN` until `M4.1` completes |

## Acceptance and handoff

| Task criterion | Result | Evidence |
| --- | --- | --- |
| Separate observed `is_ad`/`is_ec_video` flags from lexical promotional cues; retain `unlabeled_unknown` | Met (`N` + `K` verified across contracts, API & `/demo/`) | [disclosure.py](../../../../packages/absa/disclosure.py), [ui.py](../../../../apps/demo/ui.py) |
| No output calls flag prediction a probability of undisclosed sponsorship; no unlabeled negative; no flag leakage or historical prosody join | Met (`K` verified + inline bigram/indirect column guards added) | [disclosure_eval.py](../../../../packages/absa/disclosure_eval.py), [khuong_peer_review.md](evidence/khuong_peer_review.md) |
| Grouped held-out evaluation reporting PR-AUC/Brier strictly for genuinely labeled targets (`is_ad_only` vs `is_ec_only`) | Met (author-cluster bootstrap + MCN/Shop tag ablation) | [m4_2_observed_disclosure_study_v2_k_review.json](../../../../artifacts/benchmarks/m4_2_observed_disclosure_study_v2_k_review.json) |
| Review `100` historical texts (`30` double-reviewed) & `K` peer check of target validity/claims | Met (`100/100` `N`+`K` full-transcript verified; `22/30 = 73.33%`, `kappa=0.6364`; `K` peer review complete) | [review_sample_100.jsonl](../../../../data/evaluation/m4_2_disclosure/review_sample_100.jsonl), [n_k_100_combined_audit_summary.json](evidence/n_k_100_combined_audit_summary.json) |

Final task status: **COMPLETE** (`M4.G` gate remains **`NOT_RUN`** until `M4.1` completes CPU timestamp/prosody evaluation on fresh `M3.3` pilot audio).
