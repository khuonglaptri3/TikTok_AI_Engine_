# M0.G ? Independent G0 Foundation Review

- Status: IN_PROGRESS (independent technical review performed; owner decision pending).
- Gate result: NOT_RUN (no owner PASS/FAIL decision recorded).
- Review recommendation: HOLD unconditional G0 acceptance until `G0-REV-1` and the clean-lint acceptance gap `G0-REV-2` are resolved.
- Execution date: 2026-11-18 (Asia/Saigon); independent verification 09:06?09:11 UTC.
- Requirement source: [active milestone plan](../../../planning/TikTok_AI_Engine_Milestone.md), M0.G, and the owner's request to synchronize local code and assess G0 for their decision.
- Repository version: `feat/m0-m1-m2.1-complete-and-gold-v2` at `c6c36131d2750b33fcede38871656e7c0ae703fc`, matching fetched `origin/main`; review documentation is uncommitted.
- Specification: [spec.md](superpowers/spec.md).
- Execution plan: [plan.md](superpowers/plan.md).

## Conclusion

The local CPU/offline foundation works on the synchronized revision: **75/75 full tests**, **11/11 contract/smoke tests**, configured mypy for **76 files**, dependency checks, secret scan, real-corpus ASGI routes, the two M0.2 redaction regressions, and a clean offline wheel installation all pass. Both Gold snapshots and the 10 checked Gold/index files retain their verified bytes. No live provider or crawler calls were made.

**Do not approve G0 unconditionally yet.** Independent policy probes found one engineering issue with two failing checks: `AppSettings` accepts a call budget above the project-wide maximum of 2, and `BoundedGeminiClient` follows that higher value. With budget 3 and `turn_calls_used=2`, the SDK stub is called once instead of raising `QuotaBlockedError`. The default budget 2 correctly blocks the same attempt. This does not demonstrate an overrun in the current single-call HTTP route or an actual paid request, but it disproves the unconditional hard-cap claim in the foundation/provider contracts. See `G0-REV-1` below. Ruff also exits 1 on two existing style violations: the original G0 task spec explicitly requires a clean result, so this criterion is not met (`G0-REV-2`), regardless of the older report calling them non-blocking notices.

The owner can use this report to decide the gate. This review records no human sign-off and does not change `G0` to PASS. M0.1?M0.3 retain their existing task statuses; the new finding qualifies their gate acceptance rather than silently rewriting contributor history.

## Work performed

- Fetched remote refs and fast-forwarded the current local branch from `6cf1a6ec` to `c6c36131`, with no merge conflict. The three pre-existing untracked publication logs were preserved. M3.1 was not merged into the G0 baseline.
- Read the pre-existing G0 spec/plan from fetched `origin/main` before synchronization, added dated independent-review scope before evaluation, and preserved the [original contributor report](evidence/contributor-report-c6c36131.md) and all original receipts. The archived report is byte-exact and retains its original relative-link context.
- Reproduced the required checks using Python 3.12.14 on Windows 11 (12 logical CPUs), with the declared `.[demo,dev]` profile resolved from the local uv cache. Provider credentials were blanked in child processes.
- Replaced reliance on the original status-only G0 probe with an independent asserting probe: **36/38 checks passed**, with the two failures belonging to `G0-REV-1`. Tests include actual status/error codes, readiness, finite nonnegative `ms` timings, valid source IDs, draft qualification, redaction, and before/after artifact hashes.
- Built a wheel from the actual Docker COPY source directories, installed its base dependencies into a clean temporary virtual environment offline, verified installed module paths outside the checkout, checked dependencies, and served `/health/live` and `/demo/` through the installed wheel.

## Verification

Commands below run through `uv run --offline --no-project --python 3.12 --with '.[demo,dev]' python ...`; exact interpreter paths, package versions, durations and exit codes are retained in the receipts.

| Check | Result | Scope / evidence |
| --- | --- | --- |
| Fetch and local merge | PASS, fast-forward | [Git receipt](evidence/peer-git-sync.json); HEAD equals fetched `origin/main` at `c6c36131`. |
| `scripts/check_secrets.py` | PASS, exit 0 | [Secret scan](evidence/peer-secrets.log); supported source patterns only, not proof that every possible credential format is covered. |
| `python -m pip check` | PASS | [Dependency output](evidence/peer-pip-check.log). |
| `python -m mypy packages apps pipelines` | PASS, 76 source files | [Type-check output](evidence/peer-mypy.log). This is the project-configured check, not every mypy strict flag. |
| `python -m pytest tests/contract tests/smoke -v` | PASS, 11 tests in 12.73 s | [Contract/smoke output](evidence/peer-contract-smoke.log). |
| `python -m pytest -v` | PASS, 75 tests in 30.30 s | [Full output](evidence/peer-pytest-full.log); subprocess wall time 32.491 s. |
| `python -m ruff check packages apps tests/contract tests/smoke` | FAIL, exit 1: two existing style findings | [Ruff output](evidence/peer-ruff.log); I001 in `health.py`, UP017 in `bm25.py`. The original task spec requires clean Ruff; acceptance is not met unless fixed or explicitly excepted by the owner. No exception is assumed. |
| `peer-probe.py` | FAIL, exit 1: 36/38 checks pass | [Runtime receipt](evidence/peer-runtime-receipt.json), [console](evidence/peer-runtime.log); only failures are the above-two configuration and mocked third call. |
| Gold/index integrity and source IDs | PASS | Both snapshots: 70,996 videos, 264 creators, 49 video columns; BM25: 21,748 IDs matching the eligible corpus. Ten artifact hashes match Git and are unchanged after probing. [Receipt](evidence/peer-runtime-receipt.json). |
| ASGI valid/invalid requests | PASS | `/health/live`, `/health/ready`, `/demo/`, benchmark, BM25 search, offline draft, missing key 503, out-of-domain 422, blank query 422, invalid duration 422 and unavailable dense index 503. [Receipt](evidence/peer-runtime-receipt.json). |
| Fixed M0.2 redaction cases | PASS | Quoted JSON/dict secret fields, traceback and stack information tested with synthetic markers. [Receipt](evidence/peer-runtime-receipt.json). |
| Clean offline wheel build/install | PASS | Docker COPY-context wheel includes `apps`, `packages`, `pipelines`; clean dependency check and installed-package ASGI routes pass. [Package receipt](evidence/peer-package-results.json), [installed ASGI log](evidence/peer-installed-asgi.log). |
| Docker container runtime | NOT_RUN, daemon unavailable | CLI is present; Linux-engine named pipe is absent. [Docker probe](evidence/peer-docker-info.log). This is a recorded runtime boundary, not a container PASS. |
| Report/evidence integrity | PASS: layout, links, provenance and SHA256 inventory verified | [Handoff receipt](evidence/peer-handoff.json), [SHA256 inventory](evidence/peer-artifact-hashes.json). |

The default runtime still uses `20261117_recovered_v1` with its corresponding `bm25-v2` index; `20261118_taxonomy_fix_v1` was loaded and verified separately. This is intentional source/index parity, not an assertion that the newer snapshot has a rebuilt matching index.

## Open issues

| ID / severity | Finding and actual impact | Follow-up |
| --- | --- | --- |
| **G0-REV-1 ? Important; blocks an unconditional recommendation** | [AppSettings](../../../../packages/common/settings/__init__.py) permits `max_llm_calls_per_turn` up to 5, and [BoundedGeminiClient](../../../../packages/llm/clients/gemini.py) uses that configurable threshold. Setting 3 permits a third mocked SDK call. Default 2 blocks it; no live request or spend occurred. | M0.2/M2.3 owner (`N`) should enforce the project maximum at settings/client boundaries and cover above-two, default-two, invalid and exhausted budgets with regressions; `K` independently checks the fix. This audit implements no production fix. |
| **G0-EVID-1 ? original evidence weakness, addressed for this review** | The original [G0 probe](evidence/run_g0_checks.py) records response codes without asserting acceptance, so its zero exit alone cannot establish a pass. | The asserting [independent probe](evidence/peer-probe.py) supplies current evidence and fails on the policy gap. Keep original receipts as dated observations. |
| **G0-REV-2 ? Low code severity; explicit acceptance gap** | Ruff exits 1 for `I001` in `apps/api/app/routers/health.py:1` and `UP017` in `packages/retrieval/sparse/bm25.py:188`. The [original spec](superpowers/spec.md) requires clean lint. Calling them notices does not satisfy that requirement. | Fix these two style violations and rerun scoped Ruff, or have the owner explicitly record an exception before accepting the gate. This review does neither. |
| Existing UI/draft notes | Minor validation-error display issues, hardcoded retrieval header, and offline draft sentence quality remain recorded in [M0.3](../M0.3/README.md). | Retain for M2.3/M6.2; no new UI quality approval is inferred here. |
| Docker, dataset rights, scientific quality and hosting | Container execution is unverified; source redistribution rights remain unresolved; local checks do not establish retrieval relevance, factual entailment, fresh data, multimodal quality, free-tier entitlement or public hosting eligibility. | Docker/release: M6.G; rights: M1.G/M6.G; retrieval/scripts: M2.2/M2.3; fresh/trust: M3?M5. |

## Outputs

| File | Purpose |
| --- | --- |
| [Git synchronization receipt](evidence/peer-git-sync.json) | Before/after refs, commands, authorization scope and original untracked-log hashes. |
| [Check receipt](evidence/peer-check-results.json), [runner](evidence/peer-run-checks.py) | Environment/package versions, exact commands, exit codes, durations and log hashes. |
| [Runtime receipt](evidence/peer-runtime-receipt.json), [probe](evidence/peer-probe.py) | Asserted API/data/redaction/policy checks, response bodies and runtime artifact hashes. Original Vietnamese response text is preserved. |
| [Package receipt](evidence/peer-package-results.json), [runner](evidence/peer-package.py) | COPY-context wheel build, clean cached dependency installation, installed ASGI execution and Docker availability. Temporary installations were removed after checking. |
| [Fresh-context review](evidence/peer-review.md) | Independent read-only AI review confirms the two acceptance gaps; no human sign-off inferred. |
| [Workflow](evidence/workflow.md) | Skills actually read/applied, authorization, execution provenance, findings and remaining work. |
| [Original contributor report](evidence/contributor-report-c6c36131.md), [original receipt](evidence/g0_verification_receipt.json) | Historical contributor observations retained separately from the independent review. |
| [Harness error log](evidence/peer-runtime-harness-error.log) | A failed audit-script edit (IndentationError), corrected before the final runtime receipt; not a product failure or successful verification. |
| [Handoff receipt](evidence/peer-handoff.json), [artifact hashes](evidence/peer-artifact-hashes.json) | Final layout/link/scope/preservation/hash verification. |

## Acceptance and handoff

| Task criterion | Assessment | Evidence |
| --- | --- | --- |
| M0.1?M0.3 evidence and declared prerequisites | Existing task completion recorded; qualified by new G0-REV-1 | Prerequisite reports and independent policy probe. |
| Scanner, configured mypy, contracts and smoke pass at a pinned revision | Met | Fresh logs and [check receipt](evidence/peer-check-results.json). |
| Real historical CPU/offline API/demo foundation and source-package installation | Met within the recorded scope | [Runtime](evidence/peer-runtime-receipt.json) and [package](evidence/peer-package-results.json) receipts. |
| Project-wide hard maximum of 2 LLM calls/turn | **Not met for configurable settings/client use** | Two failing policy checks; default-two control passes. |
| Packaging, provider, data rights and hosting limitations reported honestly | Met | Verification and open-issues tables above. |
| Owner's gate decision | **Pending** | User explicitly reserved the PASS decision. No sign-off is fabricated. |

**Recommendation:** keep G0 pending, resolve G0-REV-1, then reproduce the focused budget regressions and required G0 checks at the fixed revision. The offline foundation is runnable now; that observation does not override the documented hard-cap requirement. Final task status remains **IN_PROGRESS**, formal **G0 = NOT_RUN** until the owner decides.

## Acceptance and owner decision

| Gate criterion | Independent assessment | Evidence |
| --- | --- | --- |
| M0.1?M0.3 status/evidence available | Met as recorded; new budget finding remains open for gate acceptance | [Prerequisite reports](../README.md), [workflow](evidence/workflow.md). |
| Source secret scan, configured mypy, contract/smoke and full tests | Met on synchronized source | [Check receipt](evidence/peer-check-results.json). |
| Clean Ruff required by the task spec | **Not met** | `G0-REV-2`, [Ruff log](evidence/peer-ruff.log). |
| Project maximum of 2 LLM calls per turn enforced by settings/client | **Not met under supported higher-budget configuration** | `G0-REV-1`, [default and higher-budget controls](evidence/peer-runtime-receipt.json). |
| Package installation, CPU/offline API/demo and bounded missing-capability errors | Met within recorded local scope | [Runtime](evidence/peer-runtime-receipt.json), [package](evidence/peer-package-results.json). |
| Licensing, UI, Docker, provider and hosting limits explicit | Met as documented boundaries; not endorsements of those capabilities | Open-issues table and Docker log. |
| Owner gate decision | Pending | No human approval is inferred from this AI-assisted review. |

**Recommendation: HOLD unconditional G0 approval.** Resolve the call-budget invariant and obtain a clean Ruff result, then review the focused new evidence; broader verification should be repeated only if production changes warrant it. The local historical offline demo is usable within its recorded limitations. This review does not implement fixes, approve a narrower exception, publish, or push.

Final task status remains **IN_PROGRESS** and formal **G0 = NOT_RUN** pending the owner's explicit decision. The owner receives the synchronized baseline, independent results, two acceptance gaps and exact follow-up checks. M1.G, M2.G and later gates are unchanged.
