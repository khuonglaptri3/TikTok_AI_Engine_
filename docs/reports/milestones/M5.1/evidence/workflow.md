# M5.1 — Workflow Provenance & Verification Ledger

- **Date:** 2026-11-19 (Asia/Ho_Chi_Minh)
- **Task ID:** `M5.1` (Observable duplicate, contact/link, and noise comment indicators)
- **Primary Owner:** Nguyễn Việt Nguyên (`N`)
- **Peer Reviewer:** Trần Đình Khương (`K`, pending `M3.3` real comments & peer review)
- **Branch:** `feat/m5.1-observable-comment-indicators` (branched from `main` @ `dcdd6233`)
- **Spec & Plan:** [spec.md](../superpowers/spec.md), [plan.md](../superpowers/plan.md)

## Process Check (`AGENTS.md` Section 7)

1. Audited `docs/planning/TikTok_AI_Engine_Milestone.md` (lines 61 & 110), `packages/seeding/detector.py`, `packages/data_contracts/multimodal.py`, `apps/api/app/routers/trust.py`, `apps/demo/{presentation,ui}.py`, and `pipelines/ingest_incremental_to_gold/converter.py`. Confirmed `data/raw_incremental/` and real `fact_comments.parquet` are not yet collected (waiting on `M3.2` / `M3.3`).
2. Authored [spec.md](../superpowers/spec.md), [plan.md](../superpowers/plan.md), and [annotation_guidelines.md](annotation_guidelines.md) before modifying source files.
3. Executed TDD (`RED -> GREEN`): wrote `tests/unit/test_m5_1_comment_indicators.py` first (`red-m5_1-tests.log`), then implemented observable labels, `original_text` retention, organic short-phrase exemption (`min_duplicate_words=5`), `packages/seeding/evaluation.py`, diagnostic-only API/UI defaults, filter sensitivity computation, and `converter.py` manifest column-count exactness (`int(pa_table.num_columns)` + schema projection).
4. Verified the organic-duplicate improvement on the authored edge fixture (`legacy_min_words_1_false_positives = 24 -> guarded_min_words_5_false_positives = 0`) and confirmed `recommended_mode = "diagnostic_only_without_filtering"` when real pilot comments are absent.

## Key Engineering & Integrity Decisions

1. **Non-Accusatory Observable Terminology & Original Retention:** `CommentRecord` preserves `original_text` verbatim alongside trimmed `text`, adds `observable_label`, `observable_reason_codes`, and `diagnostic_only=True`, and keeps legacy `is_seeding`/`seeding_reason` + 10-column Parquet `_COMMENTS_SCHEMA` compatibility intact.
2. **Diagnostic-Only Runtime Default (`>= 150`, P >= 0.85, R >= 0.60 Gate):** Until `150–300` real pilot comments are collected under `M3.3` and double-annotated to pass held-out thresholds, `/api/v1/trust/audit-video` and `/demo/` default to `diagnostic_only_unvalidated` (`hide_seeding=False` checkbox unchecked by default) and display exact before/after ABSA `filter_sensitivity`.
3. **Strict Video/Thread-Disjoint Splitting:** `split_comments_by_video` guarantees zero shared `video_id` across `dev`, `calibration`, and `held_out_third`, avoiding within-thread comment leakage.

## Verification Receipts

- `.venv/bin/python -m pytest tests/unit/test_m5_1_comment_indicators.py -v` (RED) -> `ModuleNotFoundError` ([red-m5_1-tests.log](red-m5_1-tests.log))
- `.venv/bin/python -m pipelines.audit_m5_1_comments.run_baseline_checks --mode fixture_dry_run` -> `EXIT=0`, `legacy_org_dup_fp=24 -> guarded=0`, `recommended_mode=diagnostic_only_without_filtering` ([m5_1_fixture_dry_run.json](../../../../../artifacts/benchmarks/m5_1_fixture_dry_run.json))
- `.venv/bin/python -m pytest -v` -> `EXIT=0`, `142 passed in 21.91s` ([m5_1-pytest.log](m5_1-pytest.log))
- `.venv/bin/python -m ruff check packages apps pipelines scripts tests/unit/test_m5_1_comment_indicators.py` -> `EXIT=0`, `All checks passed!` ([m5_1-ruff.log](m5_1-ruff.log))
- `.venv/bin/python -m mypy packages apps pipelines` & `--platform win32` -> verified in [m5_1-mypy.log](m5_1-mypy.log) and [m5_1-mypy-win32.log](m5_1-mypy-win32.log)
- `python3 scripts/check_secrets.py` -> `EXIT=0`, `PASS: Zero secret leaks detected across workspace.` ([m5_1-secrets.log](m5_1-secrets.log))

## Phase 2 — `K` Baseline Code, Leakage & Filter-Sensitivity Peer Review (2026-11-20)

- **Reviewer:** Trần Đình Khương (`K`) on branch `feat/k-m4.2-m5.1-m6.1-peer-reviews` (from `main` @ `1531174e`).
- **Skills loaded:** `using-superpowers`, `brainstorming`, `receiving-code-review`, `dispatching-parallel-agents`, `test-driven-development`, `verification-before-completion`.
- **Key findings & TDD fixes ([khuong_baseline_peer_review.md](khuong_baseline_peer_review.md)):**
  1. Added `5` TDD regressions in `tests/unit/test_m5_1_comment_indicators.py` ([red-k-review-fixes.log](red-k-review-fixes.log) `5 failed` -> [green-k-review-fixes.log](green-k-review-fixes.log) `11 passed` with M3.1 suite).
  2. Fixed `held_out_third` gate reachability (`total_annotated_pool_count >= 150` + `len(rows) >= 45`), blinded `build_annotation_pool` (`include_predictions=False`) while grouping video threads contiguously and adding `reconstruct_observable_predictions` for 10-column Gold Parquet, exempted 5–8 syllable Vietnamese organic diner inquiries, isolated `contact_or_link`/`noise_or_empty` before duplicate clustering, restored `template_phrase_match` reachability, unified transitive clusters via Union-Find, bounded 10-digit phone regex against 19-digit TikTok IDs, fixed `/demo/` bare `https://` colon parsing (`parse_demo_comment_lines`), and abstained (`after_filter_abstained=True`) when `unflagged_comment_count == 0`.
  3. Generated [m5_1_fixture_dry_run_v2_k_review.json](../../../../../artifacts/benchmarks/m5_1_fixture_dry_run_v2_k_review.json) while keeping original `m5_1_fixture_dry_run.json` byte-identical.
