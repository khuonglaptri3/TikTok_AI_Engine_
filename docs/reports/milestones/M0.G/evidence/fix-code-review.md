# Read-only review of G0 remediation

- Date: 2026-11-18 (Asia/Saigon).
- Reviewer: AI subagent `/root/g0_fix_review`, requested under Superpowers `requesting-code-review` 7.0.1. No human K/N sign-off is inferred.
- Base revision: `c6c36131d2750b33fcede38871656e7c0ae703fc`; reviewed uncommitted settings/client/lint changes and `tests/unit/test_llm_call_budget.py`.
- Requirements: the owner-authorized repair sections in [spec.md](../superpowers/spec.md) and [plan.md](../superpowers/plan.md).

## Review outcome before the final fix pass

Normal settings correctly restrict budgets to 1–2. Invalid/exhausted consumed counts are checked before RPM accounting; import grouping and the UTC alias preserve behavior. Regression tests use synthetic keys, SDK stubs and in-memory limiters, without provider calls.

The reviewer found one residual **Important** issue: an unvalidated settings copy containing `float('nan')` causes `min(configured_budget, 2)` to remain NaN. At `turn_calls_used=2`, the initial repair therefore reaches the stub SDK. The reviewer reproduced one stub call and no network call. Initial assessment: **With fixes**.

## Implementer resolution, independently observable in tests

The single review-fix pass first added nonfinite copied-budget regressions: [RED log](fix-red-review-budget.log) records 3 failures and 1 control pass. The client now rejects a copied configured budget unless it is a positive integer before calculating the effective limit. [GREEN log](fix-green-reviewed-budget.log) records 38 passing budget/provider-guardrail tests, including the 4 new nonfinite-copy cases. Final full-suite/type/lint/runtime/package results are recorded separately in the current [check receipt](fix-check-results.json), [runtime receipt](fix-runtime-receipt.json), and [package receipt](fix-package-results.json).

No second reviewer approval is claimed: the review finding was resolved through the prescribed RED/GREEN fix pass and fresh complete verification. The first-pass 96-test results and prior runtime/package receipts remain in `fix-before-review/` as dated evidence.

## Considered scope boundaries

The method remains stateless with a caller-supplied consumed-call count; the current HTTP service makes one explicit SDK invocation per request. This repair does not introduce a conversation/session accounting system, a live Gemini test, deployment, data collection, or a human gate sign-off. Final report, source hashes and evidence consistency are checked by the primary agent's handoff validator.
