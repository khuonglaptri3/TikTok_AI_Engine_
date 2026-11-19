# M4.2 — Observed Disclosure/Commerce and Promotional Language

- Status: IN_PROGRESS (`N`'s flag/lexical separation across contracts, ABSA, trust API, `/demo/` UI, `70,996`-row corpus study, creator-disjoint `is_ad_only` vs `is_ec_only` baseline, and `100`-item review workbook complete; awaiting `N`/`K` human manual annotation of `review_sample_100.jsonl` and `K` peer check of target validity/wording)
- Execution date: 2026-11-19 (Asia/Ho_Chi_Minh)
- Requirement source: [TikTok_AI_Engine_Milestone.md](../../../planning/TikTok_AI_Engine_Milestone.md) (`M4.2`)
- Repository version: `feat/m4.2-observed-disclosure-promo` (branched from `main` @ `dcdd6233`)
- Primary owner: Nguyễn Việt Nguyên (`N`) · Peer reviewer: Trần Đình Khương (`K`)
- Specification: [spec.md](superpowers/spec.md)
- Execution plan: [plan.md](superpowers/plan.md)

## Conclusion

**Code separation and historical corpus audit implemented and verified; human double-review (`100` texts) and `K` sign-off remain pending (`IN_PROGRESS`).** Platform disclosure/commerce flags (`is_ad`, `is_ec_video`) are now cleanly separated from lexical promotional cues across runtime contracts, ABSA scoring, `/api/v1/trust/audit-video`, and the `/demo/` trust presentation (`packages/absa/disclosure.py`). Unflagged items strictly remain `unlabeled_unknown` (never treated as verified non-sponsored negatives), zero historical audio/prosody features are joined, and undisclosed sponsorship probability modeling remains explicitly **`DEFERRED`**.

Across all `70,996` records in `data/corpus/20261118_taxonomy_fix_v1`, `8.72%` of `unlabeled_unknown` rows (`61,877` total) still match explicit promotional lexicon cues (`5.77%` venue/branch promos, `2.08%` cart CTAs, `1.61%` discounts/vouchers), proving quantitatively that unflagged TikTok posts cannot serve as verified negatives. Restricting supervised evaluation strictly to the genuinely labeled `is_ad_only` (`3,321`) vs `is_ec_only` (`4,340`) contrast over creator-disjoint (`0` overlapping authors) held-out splits achieves `PR-AUC = 0.8916` (95% CI `[0.8739, 0.9090]`, `Brier = 0.1323`) on all rows and `PR-AUC = 0.9184` (`[0.8967, 0.9381]`, `Brier = 0.1664`) on transcribed rows without flag/hashtag leakage.

## Work performed

- **Separated observable flags & promo lexicon ([disclosure.py](../../../../packages/absa/disclosure.py)):** Added `classify_observed_disclosure_flags` (`observed_ad`, `observed_ecommerce`, `observed_ad_and_ecommerce`, `unlabeled_unknown`), 4-category promotional indicator matching (excluding uniform baseline word `"review"`), and fail-closed `assert_no_feature_leakage` blocking platform flags, `#ad`/`#quangcao` hashtags, and `prosody_*`/`audio_*`/`whisper_*` features.
- **Contract, ABSA & Demo UI integration ([multimodal.py](../../../../packages/data_contracts/multimodal.py), [analyzer.py](../../../../packages/absa/analyzer.py), [presentation.py](../../../../apps/demo/presentation.py)):** Extended `AbsaComparisonRecord` with defaulted `disclosure_flag_status`, `promotional_language_indicators`, `lexical_promo_score`, `sponsorship_ground_truth_status="undisclosed_sponsorship_deferred"`, and `disclosure_target_note` (keeping `undisclosed_pr_risk` strictly as a deprecated legacy heuristic baseline); updated `/demo/` Markdown to display flags and promotional cues separately with an explicit deferral disclaimer.
- **Corpus PU audit, `100`-item workbook & author-grouped evaluation ([disclosure_eval.py](../../../../packages/absa/disclosure_eval.py), [run_study.py](../../../../pipelines/audit_m4_2_disclosure/run_study.py)):** Analyzed all `70,996` historical rows (`1,080.79 MiB` peak RSS), generated `data/evaluation/m4_2_disclosure/review_sample_100.jsonl` (`30` `double_review_N_K`, `35` `N_only`, `35` `K_only`, `human_review_completed=false`), and evaluated creator-disjoint L2 logistic regression on genuinely flagged `is_ad_only` vs `is_ec_only` targets.

## Quantitative findings (`20261118_taxonomy_fix_v1`)

| Observable Flag Stratum | Rows | Authors | Transcribed | Promo Lexicon Hit Rate | Dominant Lexical Category / Domain |
| --- | ---: | ---: | ---: | ---: | --- |
| `observed_ad` (`is_ad` only) | `3,321` | `178` | `915` | `16.26%` | `branch_venue_promo` (`9.79%`), `Lẩu & Nướng` (`714`), venue campaigns (`#vtmgr`, `quán`) |
| `observed_ecommerce` (`is_ec_video` only) | `4,340` | `156` | `797` | `11.98%` | `commerce_cart_cta` (`10.94%`), packaged/snack (`Ăn vặt`, `combo`, `giỏ hàng`, `mua`) |
| `observed_ad_and_ecommerce` | `1,458` | `122` | `484` | `20.58%` | `commerce_cart_cta` (`18.66%`) |
| `unlabeled_unknown` (not verified negative) | `61,877` | `264` | `19,552` | `8.72%` | `branch_venue_promo` (`5.77%`), `commerce_cart_cta` (`2.08%`) |

- **Author-disjoint held-out `is_ad_only` vs `is_ec_only` (`0` author overlap, `61,877` unlabeled excluded, `1,458` both-flagged excluded):**
  - All labeled (`n_train=5,564` / `157` authors, `n_test=2,097` / `68` authors): `PR-AUC = 0.8916` (`[0.8739, 0.9090]`), `Brier = 0.1323` (`[0.1246, 0.1394]`), `ECE = 0.0882`.
  - Transcribed only (`n_train=1,111` / `111` authors, `n_test=601` / `48` authors): `PR-AUC = 0.9184` (`[0.8967, 0.9381]`), `Brier = 0.1664` (`[0.1578, 0.1753]`), `ECE = 0.1917`.
- **Qualitative error/domain notes from initial `review_sample_100.jsonl` sample check:** `m4_2_002` (`unlabeled_unknown`) contains explicit check-in discount wording despite lacking platform flags; `m4_2_007` (`observed_ad`) is an MCN/boosted street-vendor review (`#vtmgr`) with `0` promo phrases; `m4_2_008` (`observed_ad`) praises a bakery brand with `0` discount phrases; `m4_2_004` illustrates ASR background-song lyric noise.

## Outputs

| File | Purpose |
| --- | --- |
| [workflow.md](evidence/workflow.md) | Skill provenance, target-validity decisions, and command verification receipts |
| [m4_2_observed_disclosure_study.json](../../../../artifacts/benchmarks/m4_2_observed_disclosure_study.json) | Corpus strata summary, grouped PR-AUC/Brier metrics, feature weights, and SHA256 provenance |
| [review_sample_100.jsonl](../../../../data/evaluation/m4_2_disclosure/review_sample_100.jsonl) | Deterministic `100`-item stratified historical audit sheet (`30` `double_review_N_K`, `35` `N_only`, `35` `K_only`) |
| [test_m4_2_disclosure.py](../../../../tests/unit/test_m4_2_disclosure.py) | `6` TDD unit/API/UI regressions covering separation, unknown retention, leakage guards, and splits |
| [m4_2-pytest.log](evidence/m4_2-pytest.log) / [red-m4_2-tests.log](evidence/red-m4_2-tests.log) | TDD RED import failure and post-edit full pytest suite (`145 passed in 22.00s`) |
| [m4_2-mypy.log](evidence/m4_2-mypy.log) / [m4_2-mypy-win32.log](evidence/m4_2-mypy-win32.log) | Strict `mypy` across `87` source files (Linux & `--platform win32`) |
| [m4_2-ruff.log](evidence/m4_2-ruff.log) / [m4_2-secrets.log](evidence/m4_2-secrets.log) | Scoped Ruff lint pass and workspace secret scan (`0` leaks) |

## Verification

| Check | Result | Scope / evidence |
| --- | --- | --- |
| `.venv/bin/python -m pipelines.audit_m4_2_disclosure.run_study` | PASS (`PR-AUC=0.8916`, `Brier=0.1323`) | Full `70,996` corpus study + `100`-item workbook; [m4_2_observed_disclosure_study.json](../../../../artifacts/benchmarks/m4_2_observed_disclosure_study.json) |
| `.venv/bin/python -m pytest -v` | PASS (`145 passed in 22.00s`) | Full repository suite including 6 M4.2 tests + trust/demo smoke; [m4_2-pytest.log](evidence/m4_2-pytest.log) |
| `.venv/bin/python -m ruff check packages apps pipelines scripts tests/unit/test_m4_2_disclosure.py` | PASS (`All checks passed!`) | Source, scripts, and M4.2 tests; [m4_2-ruff.log](evidence/m4_2-ruff.log) |
| `.venv/bin/python -m mypy packages apps pipelines` (+ `--platform win32`) | PASS (`87 source files` each) | Strict Linux & Windows static checks; [m4_2-mypy.log](evidence/m4_2-mypy.log) |
| `python3 scripts/check_secrets.py` | PASS (`0` leaks) | Full workspace secret hygiene; [m4_2-secrets.log](evidence/m4_2-secrets.log) |

## Open issues

| Issue | Impact | Follow-up / responsible task |
| --- | --- | --- |
| `100`-item human review not yet filled (`N_human_verified=false`, `K_human_verified=false`) | Human wording/error agreement across `30` double-reviewed texts is still pending | `N` and `K` complete independent annotations in [review_sample_100.jsonl](../../../../data/evaluation/m4_2_disclosure/review_sample_100.jsonl) |
| Legacy `undisclosed_pr_risk` column retained in Gold `fact_absa_reviews.parquet` schema | Retained strictly for schema compatibility while runtime UI/API explicitly label it non-probability heuristic | `K` verifies target validity wording & M4.G gate decision |
| Audio/prosody cues excluded (`historical_audio_prosody_joined=false`) | Intentional per `M4.2` rule until `M4.1` delivers pilot `audio_derived` segments | Evaluate fresh audio cues only after `M4.1` closes |

## Acceptance and handoff

| Task criterion | Result | Evidence |
| --- | --- | --- |
| Separate observed `is_ad`/`is_ec_video` flags from lexical promotional cues; retain `unlabeled_unknown` | Met | [disclosure.py](../../../../packages/absa/disclosure.py), [presentation.py](../../../../apps/demo/presentation.py) |
| No output calls flag prediction a probability of undisclosed sponsorship; no unlabeled negative; no flag leakage or historical prosody join | Met (enforced in code + tests + study) | [disclosure_eval.py](../../../../packages/absa/disclosure_eval.py), [test_m4_2_disclosure.py](../../../../tests/unit/test_m4_2_disclosure.py) |
| Grouped held-out evaluation reporting PR-AUC/Brier strictly for genuinely labeled targets (`is_ad_only` vs `is_ec_only`) | Met | [m4_2_observed_disclosure_study.json](../../../../artifacts/benchmarks/m4_2_observed_disclosure_study.json) |
| Review `100` historical texts (`30` double-reviewed) & `K` peer check of target validity/claims | Workbook generated; human annotations & `K` review pending | [review_sample_100.jsonl](../../../../data/evaluation/m4_2_disclosure/review_sample_100.jsonl) |

Final task status: **IN_PROGRESS** (code/contract/UI separation, corpus audit, grouped genuine-target baseline, and 100-item review workbook complete on `feat/m4.2-observed-disclosure-promo`; awaiting human `N`/`K` double-review of the 100 sampled texts and `K` peer review before `M4.G`).
