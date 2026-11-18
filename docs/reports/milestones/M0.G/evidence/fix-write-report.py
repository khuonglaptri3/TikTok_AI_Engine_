"""Finalize the current G0 report from completed remediation receipts."""
from __future__ import annotations

import json
import re
from pathlib import Path

OUT = Path(__file__).resolve().parent
BUNDLE = OUT.parent
ROOT = Path(__file__).resolve().parents[5]


def main() -> None:
    checks = json.loads((OUT / "fix-check-results.json").read_text(encoding="utf-8"))
    runtime = json.loads((OUT / "fix-runtime-receipt.json").read_text(encoding="utf-8"))
    package = json.loads((OUT / "fix-package-results.json").read_text(encoding="utf-8"))
    assert checks.get("completed_at") and all(c["exit_code"] == 0 for c in checks["checks"])
    assert not runtime["failed_checks"] and package["clean_install"]
    summaries = {}
    for label, file in (("full", "fix-pytest-full.log"), ("smoke", "fix-contract-smoke.log")):
        matches = re.findall(r"(\d+ passed in [^=\r\n]+)", (OUT / file).read_text(encoding="utf-8"))
        assert matches, file
        summaries[label] = matches[-1].strip()
    report = f"""# M0.G — Foundation Review and Verified Remediation

- Status: IN_PROGRESS (the two repairs are verified; owner gate decision pending).
- Gate result: NOT_RUN (no owner PASS/FAIL decision recorded).
- Technical recommendation: PASS within the recorded local CPU/offline foundation scope.
- Execution date: 2026-11-18 (Asia/Saigon); final verification completed {checks['completed_at']}.
- Requirement source: [milestone plan](../../../planning/TikTok_AI_Engine_Milestone.md), M0.G, and the owner's explicit instruction to fix the two review findings.
- Repository version: `feat/m0-m1-m2.1-complete-and-gold-v2`, base HEAD `c6c36131d2750b33fcede38871656e7c0ae703fc`, with uncommitted owner-authorized source changes pinned by [tested source SHA256 values](evidence/fix-check-results.json).
- Specification: [spec.md](superpowers/spec.md).
- Execution plan: [plan.md](superpowers/plan.md).

## Conclusion

**Both recorded acceptance gaps are resolved and verified.** Settings reject budgets above 2, including environment overrides. The client independently caps a copied higher budget at 2 and rejects malformed consumed counters or copied budgets before RPM accounting or SDK work. A configured budget of 1 remains stricter. The two Ruff violations are corrected and the required lint command is clean.

Final verification passes **{summaries['full']}**, **{summaries['smoke']}**, configured mypy across **76 source files**, source secret scan, dependency integrity, **38/38 independent runtime checks**, and a clean offline wheel installation with installed-package API/demo execution. Focused budget/provider-guardrail tests pass **38/38**. There were **0 live provider/crawler calls and USD 0 spend**.

The technical recommendation is now **PASS for the local CPU/offline foundation**, with the scope boundaries below. **Formal G0 remains NOT_RUN and M0.G remains IN_PROGRESS until the owner decides.** This AI-assisted review and repair do not constitute human K/N sign-off or public deployment approval.

## Work performed

- Retained the earlier [synchronization receipt](evidence/peer-git-sync.json): the requested local checkout was fast-forwarded from `6cf1a6ec` to fetched `origin/main` at `c6c36131`. No M3.1 changes were merged for this task.
- Fixed [AppSettings](../../../../packages/common/settings/__init__.py): a shared project maximum of 2 bounds the validated field and preserves default2 and lower budget1 behavior. Constructor and environment inputs above2 fail validation.
- Fixed [BoundedGeminiClient](../../../../packages/llm/clients/gemini.py): validate caller-supplied consumed counts and copied configuration values, enforce the independent hard cap, and return `QuotaBlockedError` before rate limiting or SDK work on invalid/exhausted inputs. No method signature, provider fallback or session subsystem was added.
- Corrected import grouping in [health.py](../../../../apps/api/app/routers/health.py) and replaced the UTC alias usage in [bm25.py](../../../../packages/retrieval/sparse/bm25.py), resolving I001 and UP017 without changing retrieval behavior.
- Added [25 budget regression cases](../../../../tests/unit/test_llm_call_budget.py). Initial RED showed 12 failures / 9 control passes; initial GREEN showed 34 passing budget/provider tests. Fresh-context review then found a copied NaN configuration bypass: the additional RED showed 3 failures / 1 control pass; the final GREEN shows 38 passes including 4 nonfinite-copy cases.
- Preserved the [earlier HOLD report](evidence/peer-review-report-before-fixes.md), all original `peer-*` receipts, and the first repair's 96-test/package/runtime results under `evidence/fix-before-review/`. Current results use separate `fix-*` artifacts; none of those dated observations is relabeled as the final measurement.

## Verification

Source tests and runtime checks used `uv run --offline --no-project --python 3.12 --with '.[demo,dev]' python ...` with provider keys blanked. The source-hash map in the current command, runtime and package receipts identifies the uncommitted code actually tested.

| Check | Result | Scope / evidence |
| --- | --- | --- |
| Budget regressions, observed RED to GREEN | PASS | [Initial RED](evidence/fix-red-budget.log), [initial GREEN](evidence/fix-green-budget.log), [review-fix RED](evidence/fix-red-review-budget.log), [final focused GREEN](evidence/fix-green-reviewed-budget.log). External SDK operations use stubs; real settings/client/limiter behavior is exercised. |
| Full pytest | PASS: {summaries['full']} | [Complete log](evidence/fix-pytest-full.log), [exit/environment/source receipt](evidence/fix-check-results.json). |
| Contract and smoke suites | PASS: {summaries['smoke']} | [Complete log](evidence/fix-contract-smoke.log). |
| Configured mypy | PASS: 76 source files | [Log](evidence/fix-mypy.log); project-configured flags, not a claim of all strict flags. |
| Required Ruff, plus the new test | PASS: exit0, no findings | `ruff check packages apps tests/contract tests/smoke tests/unit/test_llm_call_budget.py`; [log](evidence/fix-ruff.log). No Ruff exclusion was used. |
| Secret scan and dependencies | PASS | [Source scan](evidence/fix-secrets.log), [pip check](evidence/fix-pip-check.log), [final scan](evidence/fix-secrets-final.log). Source scanner coverage remains limited to its supported patterns. |
| Independent G0 runtime probe | PASS: 38/38 | [Receipt](evidence/fix-runtime-receipt.json), [console](evidence/fix-runtime.log): real Gold/BM25, API/demo, bounded missing-key/dense errors, invalid input, finite nonnegative `ms` timings, source membership, redaction and policy ceiling checks. |
| Gold/index preservation | PASS | Both snapshots retain 70,996 videos, 264 creators and 49 video columns; BM25 has 21,748 eligible IDs. The 10 checked runtime artifact SHA256 values match the recorded source and remain unchanged. This is not a fresh exhaustive 37,840-file historical scan. |
| Clean package and installed ASGI | PASS | [Receipt](evidence/fix-package-results.json), [build](evidence/fix-wheel-build.log), [install](evidence/fix-wheel-install.log), [installed routes](evidence/fix-installed-asgi.log). Wheel built from Docker COPY-context source; cached dependencies installed in a clean temporary environment; modules imported from installed paths outside the checkout. |
| Fresh-context review | Important finding resolved through RED/GREEN | [Review and resolution](evidence/fix-code-review.md). No second-reviewer or human approval is claimed. |
| Docker engine availability | PASS for version/info probes; container run NOT_RUN | [CLI](evidence/fix-docker-version.log), [engine query](evidence/fix-docker-info.log). The daemon is reachable in this later measurement; neither image build nor container execution was performed. |
| Report/source/evidence integrity | See final handoff receipt | [Handoff](evidence/fix-handoff.json), [current SHA256 inventory](evidence/fix-artifact-hashes.json). |

Default runtime still uses `20261117_recovered_v1` and its corresponding `bm25-v2` index; `20261118_taxonomy_fix_v1` is verified separately. The checks do not imply a rebuilt newer-snapshot index, human relevance judgments, factual claim entailment, fresh data quality or hybrid retrieval acceptance.

## Findings and remaining boundaries

| Item | Current assessment | Follow-up |
| --- | --- | --- |
| G0-REV-1: configurable above-two client ceiling | **Resolved**, including copied NaN/nonfinite configuration and invalid counter checks | Keep the new regressions; current service still has one explicit SDK invocation per request and uses the existing caller-supplied consumed-count interface. No new conversation/session accounting claim is made. |
| G0-REV-2: clean Ruff | **Resolved**, both I001 and UP017 fixed | Retain the required scoped lint check. |
| Original status-only G0 probe | Historical evidence limitation remains explicit | Current [asserting probe](evidence/fix-probe.py) supplies acceptance checks; original [probe](evidence/run_g0_checks.py) and receipt remain preserved. |
| Human gate decision | Pending | Owner reviews this report and chooses G0 PASS/FAIL. |
| Dataset rights and historical provenance | Unchanged documented limits from [M0.1](../M0.1/README.md) | Redistribution/public hosting eligibility remains outside this local foundation recommendation; M1.G/M6.G own follow-up. |
| Docker runtime, browser interactions and existing UI/draft quality notes | Outside verified scope | Actual container execution and browser clicks remain unexecuted; existing [M0.3](../M0.3/README.md) UI/semantic/draft notes stay with M2.3/M6.2/M6.G. |
| Live provider entitlement, scientific evaluation and fresh multimodal modules | Not accepted by these checks | Follow the active M2–M6 tasks and gates; no real provider request or collection was run here. |

## Outputs

| File | Purpose |
| --- | --- |
| [Workflow](evidence/workflow.md), [baseline](evidence/fix-baseline.json) | Authorization, actual skills/decisions, original source hashes, RED/GREEN ledger and remaining work. |
| [Check runner](evidence/fix-run-checks.py), [current receipt](evidence/fix-check-results.json) | Required commands, Python/package versions, exit codes, timings, log hashes and tested source hashes. |
| [Runtime probe](evidence/fix-probe.py), [current receipt](evidence/fix-runtime-receipt.json) | Asserted data/API/redaction/budget results, source and artifact hashes; original Vietnamese responses remain raw evidence. |
| [Package runner](evidence/fix-package.py), [current receipt](evidence/fix-package-results.json) | Clean offline build/install and installed ASGI reproduction against the final source. |
| [Code review](evidence/fix-code-review.md) | Material NaN finding, observed RED/GREEN correction and explicit review boundaries. |
| [Prior independent review](evidence/peer-review-report-before-fixes.md), [contributor report](evidence/contributor-report-c6c36131.md) | Archived narratives retaining their original dates/results and relative-link context. |
| [Handoff validator](evidence/fix-handoff.py), [receipt](evidence/fix-handoff.json), [hashes](evidence/fix-artifact-hashes.json) | Final report/index/layout/link/source/preservation checks and current artifact inventory. Historical `peer-artifact-hashes.json` remains a dated inventory, not the current report checksum. |

## Acceptance and owner decision

| Criterion | Result | Evidence |
| --- | --- | --- |
| M0.1–M0.3 completed evidence available | Met as recorded | [Milestone index](../README.md), prerequisite reports and retained receipts. |
| Source secret scan, configured mypy, clean Ruff, contract/smoke and full tests | Met for the final tested source | [Current command receipt](evidence/fix-check-results.json). |
| Maximum2 boundary and bounded invalid/exhausted input behavior | Met within the documented stateless client interface | [Regressions](../../../../tests/unit/test_llm_call_budget.py), [runtime receipt](evidence/fix-runtime-receipt.json). |
| Package installation, local CPU/offline API/demo and explicit limits | Met within recorded scope | [Package](evidence/fix-package-results.json), [runtime](evidence/fix-runtime-receipt.json), limitations above. |
| Final human gate decision | Pending owner | No G0 PASS/FAIL is recorded by this repair. |

The two authorized repairs are complete once the final handoff validator passes. **Technical recommendation: PASS** for the defined local CPU/offline foundation. **M0.G remains IN_PROGRESS; G0 remains NOT_RUN pending the owner decision.** No commit, push, deployment or unrelated milestone closure is performed by this task.
"""
    (BUNDLE / "README.md").write_text(report, encoding="utf-8")
    index = ROOT / "docs/reports/milestones/README.md"
    lines = index.read_text(encoding="utf-8").splitlines()
    for i, line in enumerate(lines):
        if line.startswith("| M0.G |"):
            lines[i] = "| M0.G | G0 review and verified call-ceiling/lint repairs; technical PASS recommendation, owner decision pending | IN_PROGRESS | [Read results](M0.G/README.md) |"
    index.write_text("\n".join(lines) + "\n", encoding="utf-8")
    print(json.dumps({"report_written": True, "pytest": summaries["full"], "contract_smoke": summaries["smoke"], "formal_gate": "NOT_RUN"}))


if __name__ == "__main__":
    main()
