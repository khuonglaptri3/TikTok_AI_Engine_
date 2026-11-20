# M4.2 — Workflow Provenance & Verification Ledger

- **Date:** 2026-11-19 (Asia/Ho_Chi_Minh)
- **Task ID:** `M4.2` (Observed disclosure/commerce flags and promotional language; undisclosed sponsorship deferred)
- **Primary Owner:** Nguyễn Việt Nguyên (`N`)
- **Peer Reviewer:** Trần Đình Khương (`K`, pending human review)
- **Branch:** `feat/m4.2-observed-disclosure-promo` (branched from `main` @ `dcdd6233`)
- **Spec & Plan:** [spec.md](../superpowers/spec.md), [plan.md](../superpowers/plan.md)

## Process Check (`AGENTS.md` Section 7)

1. Inspected `docs/planning/TikTok_AI_Engine_Milestone.md` (lines 59 & 105), existing `packages/absa/analyzer.py`, `packages/data_contracts/multimodal.py`, `apps/demo/presentation.py`, `apps/api/app/routers/trust.py`, and Gold corpus `data/corpus/20261118_taxonomy_fix_v1`.
2. Authored [spec.md](../superpowers/spec.md) and [plan.md](../superpowers/plan.md) prospectively before creating or editing source files.
3. Executed TDD (`RED -> GREEN`): wrote `tests/unit/test_m4_2_disclosure.py` first (`red-m4_2-tests.log`: `ModuleNotFoundError: No module named 'packages.absa.disclosure'`), then implemented `packages/absa/disclosure.py`, `packages/absa/disclosure_eval.py`, updated `AbsaComparisonRecord`, `analyze_koc_vs_viewer_absa`, `format_trust_audit_markdown`, and `pipelines/audit_m4_2_disclosure/run_study.py`.
4. Audited real sampled rows (`review_sample_100.jsonl`) to verify observable flag heterogeneity (`m4_2_002` unlabeled promo vs `m4_2_007` creator/MCN `#vtmgr` boosted ad without promo wording vs `m4_2_008` subtle brand campaign vs `m4_2_004` ASR song lyric transcript).

## Key Engineering & Target Validity Decisions

1. **Zero Hidden-Intent Claim & Unlabeled Unknowns Preserved:** Separated `disclosure_flag_status` (`observed_ad`, `observed_ecommerce`, `observed_ad_and_ecommerce`, `unlabeled_unknown`) from categorized `promotional_language_indicators` (`discount_voucher`, `commerce_cart_cta`, `branch_venue_promo`, `explicit_text_disclosure`). Preserved `undisclosed_pr_risk` strictly as a deprecated legacy heuristic compatibility field with explicit disclaimers in code, API contracts, and `/demo/` Markdown.
2. **Baseline Corpus Vocabulary Exclusion:** Corpus audit showed `"review"` appears across all 4 strata at nearly identical rates (`43.76%`–`47.27%`), so neutral review framing is excluded from promotional triggers.
3. **Genuine Binary Target Without Unlabeled Negatives or Prosody:** Because `61,877` `unlabeled_unknown` rows carry `8.72%` (`5,396` videos) promotional lexicon matches, treated only the genuinely flagged binary contrast (`is_ad_only` vs `is_ec_only`, excluding `unlabeled_unknown` and `both_ad_and_ecommerce`) for PR-AUC / Brier evaluation over creator-disjoint (`author_handle`) splits with zero `#ad`/`#quangcao`/flag leakage and zero historical audio/prosody join.
4. **Honest Human Sign-Off Boundary:** Created `data/evaluation/m4_2_disclosure/review_sample_100.jsonl` (`30` `double_review_N_K`, `35` `N_only`, `35` `K_only`) with `N_human_verified=false` and `K_human_verified=false`; `M4.2` stays `IN_PROGRESS` until `N` and `K` complete independent human review and `K` checks target validity.

## Verification Ledger

- `.venv/bin/python -m pytest tests/unit/test_m4_2_disclosure.py -v` (RED) -> collection error ([red-m4_2-tests.log](red-m4_2-tests.log))
- `.venv/bin/python -m pipelines.audit_m4_2_disclosure.run_study` -> `EXIT=0`, `all PR-AUC=0.8916, Brier=0.1323`; `transcribed PR-AUC=0.9184, Brier=0.1664` ([m4_2_observed_disclosure_study.json](../../../../../artifacts/benchmarks/m4_2_observed_disclosure_study.json))
- `.venv/bin/python -m pytest -v` -> `EXIT=0`, `146 passed in 22.26s` ([m4_2-pytest.log](m4_2-pytest.log))
- `.venv/bin/python -m ruff check packages apps pipelines scripts tests/unit/test_m4_2_disclosure.py` -> `EXIT=0`, `All checks passed!` ([m4_2-ruff.log](m4_2-ruff.log))
- `.venv/bin/python -m mypy packages apps pipelines` & `--platform win32` -> verified in [m4_2-mypy.log](m4_2-mypy.log) and [m4_2-mypy-win32.log](m4_2-mypy-win32.log)
- `.venv/bin/python -m pipelines.audit_m4_2_disclosure.llm_draft_annotate --batch-size 10 --max-rpm 12 --min-interval-sec 5.0` -> `EXIT=0`, `100/100` annotated with `gemini-3.1-flash-lite`, `N_human_verified=false`, `K_human_verified=false` ([m4_2_llm_audit_summary.json](m4_2_llm_audit_summary.json))
- `python3 scripts/check_secrets.py` -> verified in [m4_2-secrets.log](m4_2-secrets.log)

## Phase 2 — `K` Adversarial Peer Review, TDD Hardening & 65-Item Full-Transcript Human Audit (2026-11-20)

- **Reviewer:** Trần Đình Khương (`K`) on branch `feat/k-m4.2-m5.1-m6.1-peer-reviews` (from `main` @ `1531174e`).
- **Skills loaded:** `using-superpowers`, `brainstorming` (*Bounded* Chặng 4 design approved by `K`), `receiving-code-review`, `dispatching-parallel-agents`, `test-driven-development`, `verification-before-completion`.
- **Key findings & TDD fixes ([khuong_peer_review.md](khuong_peer_review.md)):**
  1. Extracted full `caption` + full `transcript` from `fact_videos.parquet` (`32/65` `K` items exceeded the `600`-char excerpt ceiling) and completed blinded human inspection of all `65` `K`-assigned items (`K_human_verified=True`; `N_human_verified=False` untouched). Prepared [nguyen_65_blinded_fulltext_sheet.jsonl](nguyen_65_blinded_fulltext_sheet.jsonl) for `N`.
  2. Added `4` TDD regressions (`test_m4_2_disclosure.py`: [red-k-review-fixes.log](red-k-review-fixes.log) `4 failed` -> [green-k-review-fixes.log](green-k-review-fixes.log) `11 passed`) fixing inline `#ad`/`#quảngcáo` caption bigram leakage, indirect `video_format`/`has_cta`/`poi_*` leakage guards, Unicode word-boundary + negation matching (`"Ideal"`, `"không quảng cáo"`, `"quảng cáo lố"`), `author_handle` cluster bootstrap CIs, `PYTHONHASHSEED` tie-breaking, `transcript_full` workbook preservation, and `/demo/` Tab 3 `is_ad`/`is_ec_video` checkboxes.
  3. Generated [m4_2_observed_disclosure_study_v2_k_review.json](../../../../../artifacts/benchmarks/m4_2_observed_disclosure_study_v2_k_review.json) (`PR-AUC=0.8915`, cluster CI `[0.7845, 0.9502]`; `0.8728` without MCN/Shop tags; `0.9183` transcribed without MCN/Shop tags) while preserving original `m4_2_observed_disclosure_study.json` untouched.
