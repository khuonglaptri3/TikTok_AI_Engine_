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
4. **Phase 3 — `K` Blinded Co-Annotation, TDD `real_eval` Harness & Final Evaluation (`2026-11-26`):**
   - Extract `K`'s `180` assigned comments (`m5_1_001..m5_1_060` `double_review_N_K` + `m5_1_181..m5_1_300` `K_only`) together with full within-thread comment context from `m5_1_pilot_pool.jsonl` / `m3_3_pilot_snapshot_v2`, strictly masking `N_label`, `N_note`, `adjudicated_label`, and keeping `m5_1_pilot_pool_locked_predictions.jsonl` unread.
   - Present all `180` `K` candidate annotations in a review artifact for `K`'s explicit human inspection and confirmation before setting `K_human_verified = True` on disk.
   - TDD (`RED -> GREEN`): add `validate_and_summarize_annotated_pool` in `packages/seeding/evaluation.py` and `--mode real_eval` in `pipelines/audit_m5_1_comments/run_baseline_checks.py` with unit tests in `tests/unit/test_m5_1_comment_indicators.py` verifying fail-closed rejection of unverified/missing human rows, prediction-key mismatch, video-overlap checks, IAA computation, held-out `1/3` bootstrap CIs, and real-corpus filter sensitivity.
   - After `K` confirms `180/180` annotations (and any `N` vs `K` overlap disagreements are adjudicated), run `python3 -m pipelines.audit_m5_1_comments.run_baseline_checks --mode real_eval`, verify full `pytest`, Linux/Windows `mypy`, `check_secrets.py`, and docs hygiene, update `M5.1/README.md` (`COMPLETE`), `milestones/README.md`, and `TikTok_AI_Engine_Milestone.md`, and push to `origin/main`.
