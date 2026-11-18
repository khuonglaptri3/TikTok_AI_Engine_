# M2.3 — Qualified Scripts, Structural Guardrails & Bounded Provider Bounds

- Status: IN_PROGRESS (Guardrail/provider hardening, unit regressions, and `N`'s 15-draft structural run complete; awaiting human claim-entailment audit, `K`'s 15 queries, and peer review)
- Execution date: 2026-11-18 (Asia/Ho_Chi_Minh)
- Requirement source: [TikTok_AI_Engine_Milestone.md](../../../planning/TikTok_AI_Engine_Milestone.md) (`M2.3`)
- Repository version: `feat/m2.3-script-guardrails` (branched from `main` at `c3348e93`)
- Specification: [spec.md](superpowers/spec.md)
- Execution plan: [plan.md](superpowers/plan.md)

## Conclusion

Hardened `BoundedGeminiClient`, `recalculate_timeline_and_verify`, and `GroundedScriptEngine` for `M2.3` (`19/19` guardrail/draft tests, `66/66` full pytest suite, `mypy` over `76` source files, `ruff`, and `check_secrets.py` passing). Provider calls now enforce per-turn budgets (`<= max_llm_calls_per_turn`) and explicit HTTP deadlines (`llm_deadline_seconds`) with secret-redacted `QuotaBlockedError` / `ProviderKeyMissingError` bounds and zero paid fallback. Offline drafting now selects role-appropriate source excerpts (`hook_text` / `body_beats` / `cta_text`) per beat. Across `15` authored briefs run in `offline_grounded` mode (`0` provider calls), `15/15` achieved `0` fabricated IDs, `100%` valid source membership, and `100%` beat citation coverage, while `12/15` met the strict `±max(2s, 5%)` timing tolerance (`3` flagged honestly without fabricating padding). Task status remains `IN_PROGRESS` pending `K`'s 15 queries and two-person factual claim-entailment review across 30 drafts.

## Work performed

- **Bounded provider call budget & timeout ([gemini.py](../../../../packages/llm/clients/gemini.py)):** Enforced `turn_calls_used < max_llm_calls_per_turn` (`2` calls/turn), passed `HttpOptions(timeout=timeout_ms)` from `llm_deadline_seconds`, redacted exception strings, and mapped `TimeoutError` / quota errors into bounded `QuotaBlockedError`.
- **No-evidence guardrail clarity ([verifier.py](../../../../packages/llm/guardrails/verifier.py)):** Emits an explicit warning when `valid_evidence_ids` is empty while preserving separate `valid_citations_ratio` (source membership) and `citation_coverage_ratio` (beat coverage) reporting and `grounding_verified=False`.
- **Role-specific beat excerpt selection ([service.py](../../../../packages/script_engine/service.py)):** Differentiated `_build_offline_grounded_draft` excerpt priority per beat (`hook_text` for Beat 1, `body_beats` for Beats 2–3, `cta_text` for Beat 4) and passed `turn_calls_used=0` on `gemini_free` synthesis.
- **15-brief offline audit ([run_m2_3_audit.py](evidence/run_m2_3_audit.py)):** Authored [nguyen_15_queries.jsonl](evidence/nguyen_15_queries.jsonl) and generated [nguyen_15_drafts_audit.csv](evidence/nguyen_15_drafts_audit.csv): `15/15` have `0` fabricated IDs, `15/15` `valid_citations_ratio == 1.0`, `15/15` `citation_coverage_ratio == 1.0`, and `12/15` `timing_valid == True` (`n03`: `45.4s` vs `50s`; `n04`: `51.8s` vs `55s`; `n09`: `42.6s` vs `45s`).

## Outputs

| File | Purpose |
| --- | --- |
| [workflow.md](evidence/workflow.md) | Decisions and verification provenance |
| [nguyen_15_queries.jsonl](evidence/nguyen_15_queries.jsonl) | `15` authored Vietnamese F&B briefs by `N` |
| [run_m2_3_audit.py](evidence/run_m2_3_audit.py) | Reproducible `0`-provider-call audit script over `N`'s 15 briefs |
| [nguyen_15_drafts_audit.csv](evidence/nguyen_15_drafts_audit.csv) | Generated drafts, structural/membership metrics, and blank human claim-audit columns |
| [nguyen_15_summary.json](evidence/nguyen_15_summary.json) | Automated aggregate counts across the 15 drafts |
| [audit_15.log](evidence/audit_15.log) | Console output from `run_m2_3_audit.py` |
| [red-m2_3-tests.log](evidence/red-m2_3-tests.log) | TDD RED output before implementation |
| [green-m2_3-tests.log](evidence/green-m2_3-tests.log) | TDD GREEN unit test output (`19 passed`) |
| [ruff.log](evidence/ruff.log) | Scoped Ruff output (`All checks passed!`) |
| [mypy.log](evidence/mypy.log) | Strict project-wide mypy check (`76 source files`) |
| [pytest-full.log](evidence/pytest-full.log) | Full pytest suite (`66 passed in 15.89s`) |
| [check-secrets.log](evidence/check-secrets.log) | Secret scanner output (`0` leaks) |

## Verification

| Check | Result | Scope / evidence |
| --- | --- | --- |
| `.venv/bin/python -m pytest tests/unit/test_script_guardrails.py tests/unit/test_offline_draft.py -v` | PASS (`19 passed`) | Empty, foreign-ID, no-evidence, `max(2s, 5%)` timing, timeout/call-budget, and beat selection; [green-m2_3-tests.log](evidence/green-m2_3-tests.log) |
| `.venv/bin/python docs/reports/milestones/M2.3/evidence/run_m2_3_audit.py` | PASS (`15/15` valid membership/coverage; `12/15` timing) | `N`'s 15 briefs in `offline_grounded` mode (`0` provider calls); [nguyen_15_summary.json](evidence/nguyen_15_summary.json) |
| `.venv/bin/python -m ruff check packages/llm packages/script_engine tests/unit/test_script_guardrails.py tests/unit/test_offline_draft.py` | PASS | Lint & import style; [ruff.log](evidence/ruff.log) |
| `.venv/bin/python -m mypy packages apps pipelines` | PASS (`76 source files`) | Project-wide static types; [mypy.log](evidence/mypy.log) |
| `.venv/bin/python -m pytest -v` | PASS (`66 passed`) | Full test suite; [pytest-full.log](evidence/pytest-full.log) |
| `.venv/bin/python scripts/check_secrets.py` | PASS (`0` leaks) | Workspace secret scan; [check-secrets.log](evidence/check-secrets.log) |

## Open issues

| Issue | Impact | Follow-up / responsible task |
| --- | --- | --- |
| `K`'s 15 queries and 30-draft human claim-entailment audit pending | Structural tests alone do not verify factual entailment (`>= 90%` supported claims requirement) | `K` contributes 15 briefs; both annotate claim support across 30 drafts and review |
| `3/15` offline drafts (`n03`, `n04`, `n09`) fell `2.4s–4.6s` short of strict `5%` timeline tolerance | Guardrail accurately marks them `passed=False` rather than inventing padding | Expected bounded behavior for fixed offline blueprint on `50–55s` targets |

## Acceptance and handoff

| Task criterion | Result | Evidence |
| --- | --- | --- |
| Regressions for empty/foreign-ID/no-evidence/timing & `max(2s, 5%)` | Met | [test_script_guardrails.py](../../../../tests/unit/test_script_guardrails.py), [test_offline_draft.py](../../../../tests/unit/test_offline_draft.py) |
| Offline `0` calls; provider missing-key/quota/timeout & `<= 2` calls/turn | Met | [gemini.py](../../../../packages/llm/clients/gemini.py), [service.py](../../../../packages/script_engine/service.py) |
| `30`-draft human claim audit (`15` `N` + `15` `K`) & `K` peer review | Partial (`N` 15 drafts generated; human claim audit & `K` 15 drafts pending) | [nguyen_15_drafts_audit.csv](evidence/nguyen_15_drafts_audit.csv) |

Final task status: **IN_PROGRESS** (code/guardrail hardening and `N`'s 15-brief automated run complete; awaiting `K`'s 15 briefs, human claim audit, and peer review).
