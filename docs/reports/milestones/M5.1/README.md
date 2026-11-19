# M5.1 — Duplicate, Contact/Link, and Noise Comment Indicators

- Status: IN_PROGRESS (`N`'s observable indicator refactor, short-organic-duplicate false-positive guard, diagnostic-only API/UI default with filter sensitivity, video-disjoint evaluation pipeline, written annotation guidelines, and synthetic dry-run verification complete; awaiting `150`–`300` real pilot comments from `M3.3` / `M3.G`, human `N`/`K` double-annotation, and `K` peer review)
- Execution date: 2026-11-19 (Asia/Ho_Chi_Minh)
- Requirement source: [TikTok_AI_Engine_Milestone.md](../../../planning/TikTok_AI_Engine_Milestone.md) (`M5.1`)
- Repository version: `feat/m5.1-observable-comment-indicators` (branched from `main` @ `dcdd6233`)
- Primary owner: Nguyễn Việt Nguyên (`N`) · Peer reviewer: Trần Đình Khương (`K`)
- Specification: [spec.md](superpowers/spec.md)
- Execution plan: [plan.md](superpowers/plan.md)

## Conclusion

**Code, diagnostic-only defaults, video-disjoint evaluation harness, and annotation guidelines are complete and verified (`142 passed`, `86`-file Linux/Windows `mypy`); real-comment evaluation remains `BLOCKED` on `M3.3` / `M3.G` pilot collection (`IN_PROGRESS`).**

- `packages/seeding/detector.py` now preserves `original_text` alongside normalized `text`, emits non-accusatory observable classes (`observable_duplicate`, `contact_or_link`, `noise_or_empty`, `template_phrase_match`, `no_indicator_observed`, `unknown_ambiguous`) with zero bot/payment/verified-diner assertions, and exempts short organic repeated phrases (`min_duplicate_words = 5`, `short_organic_phrase_exempt`), eliminating `24 -> 0` organic short-duplicate false positives on the authored `12`-video edge fixture ([m5_1_fixture_dry_run.json](../../../../artifacts/benchmarks/m5_1_fixture_dry_run.json)).
- `/api/v1/trust/audit-video` (`apps/api/app/routers/trust.py`) and `/demo/` (`apps/demo/presentation.py`, `apps/demo/ui.py`) now default to **`diagnostic_only_unvalidated`** (`hide_seeding=False` checkbox unchecked by default), surfacing all comments with observable diagnostic tags plus exact before/after ABSA `filter_sensitivity` shifts rather than silently hiding comments before the M5.1 gate (`>= 150` annotated real comments, `macro precision >= 0.85`, `macro recall >= 0.60`) is met.
- `pipelines/ingest_incremental_to_gold/converter.py` now projects `CommentRecord` rows cleanly to `_COMMENTS_SCHEMA` and records `int(pa_table.num_columns)` so extended `CommentRecord` fields preserve 100% Gold Parquet schema continuity (`10` columns).

## Work performed

- **Observable indicator & contract upgrade ([detector.py](../../../../packages/seeding/detector.py), [multimodal.py](../../../../packages/data_contracts/multimodal.py), [converter.py](../../../../pipelines/ingest_incremental_to_gold/converter.py)):** Added `original_text`, `observable_label`, `observable_reason_codes`, and `diagnostic_only=True` on `CommentRecord`; added `comment_filter_policy`, `comment_filter_note`, and `filter_sensitivity` on `TrustAuditResponse`; added `min_duplicate_words=5` organic short-reaction exemption while preserving `is_seeding`/`seeding_reason` and Gold `fact_comments.parquet` compatibility.
- **Diagnostic-only UI & filter sensitivity ([trust.py](../../../../apps/api/app/routers/trust.py), [presentation.py](../../../../apps/demo/presentation.py), [ui.py](../../../../apps/demo/ui.py)):** Defaulted Gradio audit checkbox to `value=False`, replaced bot/seeding-spam labels with observable diagnostic tags, and rendered before/after filter sensitivity shifts.
- **Disjoint splitter, metrics, pool sampler & guidelines ([evaluation.py](../../../../packages/seeding/evaluation.py), [run_baseline_checks.py](../../../../pipelines/audit_m5_1_comments/run_baseline_checks.py), [annotation_guidelines.md](evidence/annotation_guidelines.md)):** Built `split_comments_by_video`, `compute_inter_annotator_agreement` (Cohen's kappa retaining `unknown_ambiguous`), `evaluate_comment_indicator_metrics` (per-class P/R/F1, confusion matrix, bootstrap 95% CIs, M5.1 gate enforcement), `build_annotation_pool` (capped at `<= 300`), and authored double-annotation guidelines.

## Outputs

| File | Purpose |
| --- | --- |
| [workflow.md](evidence/workflow.md) | Decisions, TDD trace, and command receipts |
| [annotation_guidelines.md](evidence/annotation_guidelines.md) | Written `N`/`K` double-annotation rules (`150`–`300` real comments, `unknown_ambiguous` & organic-duplicate policy) |
| [m5_1_fixture_dry_run.json](../../../../artifacts/benchmarks/m5_1_fixture_dry_run.json) | Non-real synthetic edge-fixture dry-run verifying `24 -> 0` organic-dup FP drop and `diagnostic_only_without_filtering` gate |
| [test_m5_1_comment_indicators.py](../../../../tests/unit/test_m5_1_comment_indicators.py) | `3` TDD unit/API/UI regressions covering observable labels, organic exemption, video-disjoint splits, and diagnostic UI |
| [m5_1-pytest.log](evidence/m5_1-pytest.log) / [red-m5_1-tests.log](evidence/red-m5_1-tests.log) | TDD RED log and final full suite (`142 passed in 21.91s`) |
| [m5_1-mypy.log](evidence/m5_1-mypy.log) / [m5_1-mypy-win32.log](evidence/m5_1-mypy-win32.log) | Strict `mypy` across `86` source files (Linux & `--platform win32`) |
| [m5_1-ruff.log](evidence/m5_1-ruff.log) / [m5_1-secrets.log](evidence/m5_1-secrets.log) | Scoped Ruff lint pass (`All checks passed!`) and workspace secret scan (`0` leaks) |

## Verification

| Check | Result | Scope / evidence |
| --- | --- | --- |
| `.venv/bin/python -m pipelines.audit_m5_1_comments.run_baseline_checks --mode fixture_dry_run` | PASS (`24 -> 0` org-dup FP; `recommended_mode=diagnostic_only_without_filtering`) | Non-real `12`-video/`80`-eval-row edge fixture; [m5_1_fixture_dry_run.json](../../../../artifacts/benchmarks/m5_1_fixture_dry_run.json) |
| `.venv/bin/python -m pytest -v` | PASS (`142 passed in 21.91s`) | Full repository suite (M5.1 tests, Dual-Sink continuity, trust/demo smoke); [m5_1-pytest.log](evidence/m5_1-pytest.log) |
| `.venv/bin/python -m ruff check packages apps pipelines scripts tests/unit/test_m5_1_comment_indicators.py` | PASS (`All checks passed!`) | Source, scripts, and M5.1 tests; [m5_1-ruff.log](evidence/m5_1-ruff.log) |
| `.venv/bin/python -m mypy packages apps pipelines` (+ `--platform win32`) | PASS (`86 source files` each) | Strict Linux & Windows static checks; [m5_1-mypy.log](evidence/m5_1-mypy.log) |
| `python3 scripts/check_secrets.py` | PASS (`0` leaks) | Full workspace secret hygiene; [m5_1-secrets.log](evidence/m5_1-secrets.log) |

## Open issues

| Issue | Impact | Follow-up / responsible task |
| --- | --- | --- |
| Real pilot comments (`150`–`300`) unavailable (`M3.3` / `M3.G` pending) | Held-out macro P/R/F1 on real TikTok comments and human Cohen's kappa cannot be measured yet; automated filtering remains disabled (`diagnostic_only_unvalidated`) | Collect real comments under `M3.3`, run `run_baseline_checks.py --mode real_pool`, and double-annotate (`N` & `K`) |
| `K` peer review pending | Independent audit of label leakage, organic-duplicate false positives, and filter sensitivity awaits `K` | Hand off `feat/m5.1-observable-comment-indicators` for `K` review |

## Acceptance and handoff

| Task criterion | Result | Evidence |
| --- | --- | --- |
| Preserve originals and reasons; observable duplicate/contact/noise labels; no bot/payment/seeding/identity assertions | Met | [detector.py](../../../../packages/seeding/detector.py), [presentation.py](../../../../apps/demo/presentation.py) |
| Diagnostic flags without automatic filtering until `>= 150` real annotated comments pass `P >= 0.85`, `R >= 0.60` | Met | [trust.py](../../../../apps/api/app/routers/trust.py), [ui.py](../../../../apps/demo/ui.py) |
| Video/thread-disjoint splitting, agreement, P/R/F1 + bootstrap uncertainty, written guidelines | Framework verified on fixtures; awaiting real comments | [evaluation.py](../../../../packages/seeding/evaluation.py), [annotation_guidelines.md](evidence/annotation_guidelines.md) |
| Independently annotate `150`–`300` real pilot comments & `K` peer review | Pending (`M3.3` prerequisite) | `data/raw_incremental/` absent on disk |

Final task status: **IN_PROGRESS** (M5.1 code hardening, diagnostic-only default, filter sensitivity, disjoint evaluator, and annotation guidelines complete on `feat/m5.1-observable-comment-indicators`; real-pilot annotation and quality gate await `M3.3` / `M3.G` real comments and `K` peer review).
