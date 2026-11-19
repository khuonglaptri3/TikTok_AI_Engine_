# M5.1 — Execution & Verification Plan

**Goal:** Upgrade `packages/seeding/`, `TrustAuditResponse`, and `/demo/` to observable indicator semantics with diagnostic-only unvalidated fallback + filter sensitivity, and deliver the full video-disjoint evaluation pipeline and annotation guidelines ready for `M3.3` real pilot comments.
**Spec:** [spec.md](spec.md)

## Steps

1. **TDD RED (`tests/unit/test_m5_1_comment_indicators.py`):**
   - Test original text preservation, observable indicator labels, and exemption of repeated short organic phrases (`"ngon quá"`, `"xin địa chỉ"`).
   - Test `split_comments_by_video` strict zero-video-overlap invariant, Cohen's kappa with `unknown_ambiguous`, per-class P/R/F1, bootstrap CI bounds, and `auto_filter_eligible=False` enforcement when sample `< 150` or precision `< 0.85` or recall `< 0.60`.
   - Test `/api/v1/trust/audit-video` + `format_trust_audit_markdown` returning `comment_filter_policy="diagnostic_only_unvalidated"`, before/after `filter_sensitivity`, non-bot diagnostic wording, and visible comments by default.
2. **Implementation (`packages/`, `apps/`, `pipelines/`, `docs/`):**
   - Extend `CommentRecord` and `TrustAuditResponse` cleanly in `packages/data_contracts/multimodal.py`.
   - Update `packages/seeding/detector.py` (`original_text`, `observable_label`, `observable_reason_codes`, `min_duplicate_words=5` organic short-phrase guard, preserving `is_seeding`/`seeding_reason` compatibility).
   - Implement `packages/seeding/evaluation.py` and export cleanly via `packages/seeding/__init__.py`.
   - Update `apps/api/app/routers/trust.py`, `apps/demo/presentation.py`, and `apps/demo/ui.py` (`value=False` default checkbox + diagnostic labels + filter sensitivity).
   - Write `docs/reports/milestones/M5.1/evidence/annotation_guidelines.md` and `pipelines/audit_m5_1_comments/run_baseline_checks.py`.
3. **TDD GREEN & Full Verification:**
   - Run targeted unit tests, existing regression/snapshot/smoke tests (`test_incremental_absa_seeding.py`, `test_snapshot_continuity.py`, `test_api_and_demo.py`, `test_data_contracts.py`), then `pipelines.audit_m5_1_comments.run_baseline_checks`.
   - Run full `pytest -v`, `ruff check`, `mypy packages apps pipelines`, `mypy --platform win32 packages apps pipelines`, and `python3 scripts/check_secrets.py`.
   - Write `docs/reports/milestones/M5.1/evidence/workflow.md`, `docs/reports/milestones/M5.1/README.md`, update `docs/reports/milestones/README.md` (`IN_PROGRESS`), commit, and push `feat/m5.1-observable-comment-indicators`.
