# Fresh-context review of the independent G0 assessment

- Date: 2026-11-18 (Asia/Saigon).
- Reviewer: read-only AI subagent `/root/review_g0_assessment`, requested under Superpowers `requesting-code-review` 7.0.1. This is not a human K/N approval.
- Reviewed revision: `c6c36131d2750b33fcede38871656e7c0ae703fc`, plus the local independent-review artifacts.
- Inputs: task spec/plan, contributor report, peer check/runtime/package receipts, audit probes, settings and Gemini client source.
- Recommendation: **HOLD unconditional G0**. No critical issue found within the reviewed scope.

## Findings

1. **Important: configurable call ceiling violates the project maximum.** Settings accepts 3–5 calls and exposes the setting through the environment. The Gemini client trusts this threshold. The controlled probe records one SDK stub call at configured budget 3 / used count 2, while the default2 control blocks it. Current script generation has one explicit client call per request, so this is a policy-enforcement defect, not evidence of three live API calls. Enforce the hard ceiling and add regressions before claiming the invariant.
2. **Low runtime impact, unmet acceptance criterion: Ruff exits 1.** `health.py:1` (I001) and `bm25.py:188` (UP017) fail the task spec's clean-Ruff requirement. Fix the violations or obtain an explicit owner-approved exception. The report must not treat them as a passing check.
3. **Original evidence limitation:** the original G0 probe writes endpoint status values without asserting acceptance. Preserve its historical observations, but use the independent asserting probe for the current recommendation.

## Evidence assessment and scope

The peer probe checks corpus membership, qualified draft status, bounded HTTP errors, finite timings, redaction and preserved runtime bytes. The final receipt has 36/38 passing checks; both failures represent the same call-ceiling issue. Clean installation verifies module locations inside the installed environment and `/health/live` plus `/demo/`; it does not prove Docker execution.

Considered outside this review: Docker execution while its daemon is unavailable; live provider quota/billing eligibility; optional Redis concurrency; public hosting; semantic entailment, ASR/POI truth and retrieval-quality gates; browser interactions; unrelated M3.1 work. These are not silently marked accepted.

The primary review incorporates both acceptance gaps, retains explicit offline success and Docker limits, and leaves `G0 = NOT_RUN` for the owner's decision. No production fix, gate approval, Git mutation or file write was performed by the reviewer.
