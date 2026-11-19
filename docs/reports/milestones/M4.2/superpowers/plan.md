# M4.2 — Execution & Verification Plan

**Goal:** Deliver clean code/contract/UI separation between observed disclosure/commerce flags and lexical promotional cues, author a leakage-free author-grouped corpus & genuine-target study on `20261118_taxonomy_fix_v1`, and prepare the 100-item K/N audit sheet while keeping `M4.2` `IN_PROGRESS` pending human review.
**Spec:** [spec.md](spec.md)

## Steps

1. **TDD RED (`tests/unit/test_m4_2_disclosure.py`):**
   - Write failing tests for:
     - Observable flag statuses (`observed_ad`, `observed_ecommerce`, `observed_ad_and_ecommerce`, `unlabeled_unknown`) verifying unlabeled inputs never emit verified negative or undisclosed-sponsorship probability wording.
     - Categorized lexical promotional cue extraction cleanly separated from `is_ad` / `is_ec_video`.
     - Feature-leakage guard rejecting flag/disclosure/prosody columns (`is_ad`, `is_ec_video`, `commerce_user`, `#ad`, `f0_mean`, `prosody_*`).
     - Author-grouped (`author_handle`-disjoint) train/test splitter and pure-scipy logistic regression PR-AUC / Brier output sanity.
     - `analyze_koc_vs_viewer_absa` + `POST /api/v1/trust/audit-video` + `format_trust_audit_markdown` exposing separated flag/lexical fields while keeping legacy `undisclosed_pr_risk` compatibility.
2. **Implementation (`packages/` & `apps/`):**
   - Implement `packages/absa/disclosure.py` and export helpers via `packages/absa/__init__.py`.
   - Extend `AbsaComparisonRecord` in `packages/data_contracts/multimodal.py`.
   - Wire `analyze_disclosure_and_promo` into `packages/absa/analyzer.py` and `apps/demo/presentation.py`.
   - Implement `pipelines/audit_m4_2_disclosure/run_study.py` + `packages/absa/disclosure_eval.py` (or clean helper module) for the corpus audit, 100-item review workbook, and grouped `is_ad_only` vs `is_ec_only` PR-AUC / Brier evaluation.
3. **TDD GREEN & Corpus Execution:**
   - Run targeted unit & smoke tests -> `ruff` -> `mypy` (Linux & `--platform win32`) -> full `pytest -v`.
   - Execute `python -m pipelines.audit_m4_2_disclosure.run_study` against `data/corpus/20261118_taxonomy_fix_v1` producing:
     - `data/evaluation/m4_2_disclosure/review_sample_100.jsonl`
     - `artifacts/benchmarks/m4_2_observed_disclosure_study.json`
4. **Verification, Reporting & Publication:**
   - Re-run full `pytest -v`, `ruff check`, `mypy packages apps pipelines`, `mypy --platform win32 packages apps pipelines`, and `python3 scripts/check_secrets.py` after final edits.
   - Author `docs/reports/milestones/M4.2/evidence/workflow.md`, `docs/reports/milestones/M4.2/README.md`, and add `M4.2` (`IN_PROGRESS`) to `docs/reports/milestones/README.md`.
   - Commit and push `feat/m4.2-observed-disclosure-promo`.
5. **LLM-Assisted 100-Item Draft Annotation Addendum:**
   - Add unit tests for blinded prompt building, strict enum validation, and non-fabrication of human sign-off (`N_human_verified=false`, `K_human_verified=false`).
   - Implement `pipelines/audit_m4_2_disclosure/llm_draft_annotate.py` reusing `BoundedGeminiClient` (`<= 12 RPM`, blinded 10-item batches).
   - Run live against `data/evaluation/m4_2_disclosure/review_sample_100.jsonl` -> emit `review_sample_100_llm_draft.jsonl` + `m4_2_llm_audit_summary.json`.
   - Re-run full `pytest`, `ruff`, `mypy`, `check_secrets.py`, update `M4.2/README.md` + `workflow.md`, commit, and push.

