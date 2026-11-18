# M0.G ? G0 Repairs and GitHub Publication Review

- Status: IN_PROGRESS (G0 repairs verified; updated-main Windows integration blocker and owner decision remain open).
- Gate result: NOT_RUN (no owner PASS/FAIL decision recorded).
- Current technical recommendation: HOLD acceptance of the updated branch until the M6.1 Windows integration issue is resolved.
- Publication status: prepared for a draft PR on `fix/g0-call-budget-and-lint`; remote publication receipt will record the actual result.
- Execution date: 2026-11-18 (Asia/Saigon).
- Requirement source: [milestone plan](../../../planning/TikTok_AI_Engine_Milestone.md), M0.G, and the owner's requests to fix the two G0 findings and push to GitHub with a branch-workflow check.
- Repository version: topic branch based on fetched `origin/main` at `ad7eb92f76cddbfa8526bb16d53f8d7f8db30810`; exact tested source hashes and environment are in [publication verification](evidence/publish-check-results.json).
- Specification: [spec.md](superpowers/spec.md).
- Execution plan: [plan.md](superpowers/plan.md).

## Conclusion

**The two requested G0 repairs are implemented and remain verified.** Settings reject budgets above2, including environment overrides. The client independently caps copied higher budgets at2 and rejects invalid consumed counters or copied budgets, including NaN, before RPM/SDK work. Budget1 remains stricter. Ruff I001/UP017 are fixed and the required lint command is clean.

The earlier repair tree based on `c6c36131` passed **100 tests, configured mypy for76 files, clean Ruff,38 runtime assertions and clean installed-package validation**; that dated outcome is preserved in the [pre-publication repair report](evidence/fix-report-before-publication.md). It is not presented as a passing full-suite result for the later updated-main tree.

Fresh GitHub inspection found four newer main commits containing M3.1/M6.1. After integrating the G0 patch onto that base, **38 focused budget/provider tests,11 contract/smoke tests,38 runtime assertions, Ruff, dependency integrity and the secret scan pass**. However, **full pytest exits2 during collection** because unchanged M6.1 code imports Unix-only `resource`, and **mypy exits1 with four resource-attribute errors across80 files**. Therefore the publication is a **draft PR**, with no claim of merge readiness or unconditional G0 acceptance. The owner still makes the formal gate decision.

All validation uses CPU/offline execution, synthetic SDK stubs where needed,0 live provider/crawler calls and USD0 spend. No source data was changed.

## Branch workflow and publication scope

The remote had `main` and a previously merged topic branch, with no `develop` and no open PR at inspection. This is a `main` plus topic-PR workflow, consistent with GitHub flow; it is **not classic Gitflow**, whose original model has both main/master and develop and routes feature work through develop. [Original Gitflow model](https://nvie.com/posts/a-successful-git-branching-model/).

Publication uses the new `fix/g0-call-budget-and-lint` branch and a draft PR into `main`. The prior merged feature branch is not reused. Creating develop/release branches or changing branch protections is outside the owner's requested publication. No direct push to main, force push, PR merge, release, deployment or gate approval is performed.

The authorized G0 paths were preserved with a path-scoped stash, applied on the new base, and independently checked. Settings retained the incoming optional dense-index fields. A milestone-index conflict was resolved by retaining incoming M3.1/M6.1 rows and the G0 row. Three unrelated untracked publication logs were preserved. [Baseline](evidence/publish-baseline.json), [integration receipt](evidence/publish-git-integration.json).

## Work performed

- Fixed [settings](../../../../packages/common/settings/__init__.py) and [Gemini client](../../../../packages/llm/clients/gemini.py), preserving public call signatures, missing-key errors, strict budget1, timeout/RPM behavior and zero paid fallback.
- Corrected import grouping in [health.py](../../../../apps/api/app/routers/health.py) and UTC alias usage in [bm25.py](../../../../packages/retrieval/sparse/bm25.py).
- Added [25 regression cases](../../../../tests/unit/test_llm_call_budget.py). Initial RED:12 failures/9 controls; initial GREEN:34 focused passes. A read-only reviewer found copied NaN configuration could bypass min; review-fix RED:3 failures/1 control; final repair GREEN:38 passes. [Review and resolution](evidence/fix-code-review.md).
- Rebased the working changes by creating a fresh topic branch on current main and applying the scoped saved patch, preserving independent upstream changes. No historical commit rewriting was used.
- Re-ran integrated checks into distinct `publish-*` receipts and identified the unchanged M6.1 Windows resource issue. This publication task does not silently modify or accept the incoming research modules.

## Verification

| Check | Current result | Scope / evidence |
| --- | --- | --- |
| Budget/provider guardrail tests | PASS:38 | [Integrated focused log](evidence/publish-budget.log); uses real settings/client/limiter and SDK stubs. |
| Contract and smoke | PASS:11 | [Integrated log](evidence/publish-contract-smoke.log). |
| Full project pytest | **FAIL:exit2, one collection error** | [Integrated log](evidence/publish-pytest-full.log): `tests/unit/test_dense_hybrid_retrieval.py` imports `dense_hybrid_pilot.py`, whose unchanged `import resource` fails on Windows. No claim that the remaining collected tests executed. |
| Configured mypy | **FAIL:4 errors in2 files,80 files checked** | [Integrated log](evidence/publish-mypy.log): missing `getrusage`/`RUSAGE_SELF` in the two unchanged M6.1 pipelines. |
| Required Ruff plus new regression file | PASS:exit0 | [Integrated log](evidence/publish-ruff.log); no lint exclusions. |
| Secret scanner and dependencies | PASS | [Source scan](evidence/publish-secrets.log), [pip check](evidence/publish-pip-check.log); staged text is checked separately before commits. Scanner coverage is limited to supported patterns. |
| Asserting G0 runtime probe | PASS:38/38 | [Integrated receipt](evidence/publish-runtime-receipt.json), [console](evidence/publish-runtime.log); real Gold/BM25, API/demo/errors, source membership, finite ms timings, redaction, budget boundaries and artifact preservation. |
| Earlier full repair validation | Historical PASS:100 tests; mypy76; package/runtime checks | [Repair receipt](evidence/fix-check-results.json), [package receipt](evidence/fix-package-results.json), [archived report](evidence/fix-report-before-publication.md). These predate the updated main. |
| Data preservation | PASS for recorded runtime artifacts and no data diff | Runtime receipts retain the10 Gold/BM25 hashes; originals stay untouched. This is not a fresh exhaustive37,840-file scan. |
| Publication integrity | See publication handoff receipt | [Workflow](evidence/workflow.md); current publication hashes and Git/PR receipts are saved alongside it. Integrity PASS does not mean failed integration checks passed. |

The default runtime remains historical BM25; M6.1's optional dense-index fields are preserved without claiming new relevance or multimodal acceptance. Prior clean wheel validation is retained as a dated result; a fresh package/container build on the updated tree is not claimed.

## Open issues and recorded boundaries

| Item | Assessment / actual impact | Follow-up |
| --- | --- | --- |
| G0-REV-1: above-two LLM budget | Resolved, including copied NaN/invalid count handling; fresh focused/runtime checks pass | Retain regressions and the existing stateless consumed-count interface; no new session accounting claim. |
| G0-REV-2: clean Ruff | Resolved; current required Ruff exits0 | Retain required lint verification. |
| **G0-INTEGRATION-1: upstream M6.1 Windows resource usage** | **Open, blocks updated-tree full suite and configured mypy.** Both pipeline files match fetched main; the failure is not presented as caused by G0 edits. | M6.1 owner/reviewer should implement truthful cross-platform resource measurement, with regressions, then rerun full pytest/mypy before treating the draft PR as merge-ready or G0 as accepted. |
| Formal G0 decision | Pending owner | No AI-assisted review/commit/push creates human K/N sign-off. |
| Dataset rights, unavailable old inventory, UI/draft semantics and scientific quality | Existing limits unchanged | [M0.1](../M0.1/README.md), [M0.3](../M0.3/README.md), M1.G/M2.2/M2.3 and later gates retain ownership. |
| Docker, browser, provider entitlement and hosting | No fresh container/browser/live-provider/public-hosting validation inferred | Earlier Docker info eventually became reachable, but no container execution was performed; release/hosting prerequisites remain outside this draft publication. |

## Outputs and planning records

| File | Purpose |
| --- | --- |
| [Spec](superpowers/spec.md), [plan](superpowers/plan.md), [workflow](evidence/workflow.md) | Prospective task phases, authorization, actual skills/commands and pending gate decision. |
| [Publication handoff](evidence/publish-handoff.json), [current hashes](evidence/publish-artifact-hashes.json) | Current report/source/link/preservation checks; integrity PASS does not imply full-suite/mypy PASS. |
| [Publication baseline](evidence/publish-baseline.json), [Git integration](evidence/publish-git-integration.json) | Branch/base, scoped file inventory, recovery stash, conflict and preservation receipts. |
| [Check runner](evidence/publish-run-checks.py), [current check receipt](evidence/publish-check-results.json) | Actual integrated PASS/FAIL results, environment, exit codes, source hashes and log hashes. |
| [Runtime probe](evidence/publish-probe.py), [current runtime receipt](evidence/publish-runtime-receipt.json) | Independent asserting G0 verification against the updated-main source. |
| [Prior independent HOLD report](evidence/peer-review-report-before-fixes.md), [verified repair report](evidence/fix-report-before-publication.md), [original contributor report](evidence/contributor-report-c6c36131.md) | Dated narrative archives retaining original relative-link context. |
| [Repair review](evidence/fix-code-review.md), [repair source/result receipt](evidence/fix-check-results.json) | Original RED/GREEN and reviewed100-test repair evidence. Historical peer/fix inventories remain dated inventories, not current report checksums. |

## Acceptance and handoff

| Criterion | Current assessment |
| --- | --- |
| Two requested G0 code/lint repairs | Met; current focused/runtime/Ruff checks pass. |
| Updated-main full suite and mypy | **Not met**; upstream M6.1 Windows blocker recorded. |
| Honest branch workflow and reviewable publication | New topic branch/draft PR follows existing GitHub flow; not classic Gitflow. Actual push/PR outcome is recorded before final handoff. |
| Preserved historical evidence, original data and unrelated files | Required checks and hashes retained; publication handoff verifies current scope. |
| Owner gate decision | Pending; M0.G IN_PROGRESS and G0 NOT_RUN. |

The verified G0 repair is published for review with the updated-tree integration failure visible. Do not merge or infer G0 PASS from successful GitHub publication. The next technical follow-up is the M6.1 Windows resource issue; the owner's acceptance decision remains separate.
