# M0.G (G0) — Workflow Provenance & Verification Ledger

## Owner formal G0 PASS decision recorded 2026-11-18

- Authorization: on `2026-11-18T21:26:08+07:00`, the project owner (`Trần Đình Khương`, `K`) explicitly approved `G0 = PASS` (`M0.G = COMPLETE`) on synchronized `main` (`e050d7d5bbcf90e310bbfd144407086d82479341`, merged PR #3 `eb43b0df3d46007b7550de8f4314dc2dbca9c51f`).
- Skills read/applied: `using-superpowers`, `brainstorming` (bounded classification & explicit owner gate confirmation before recording `PASS`), `writing-plans`, `verification-before-completion`.
- Preservation: copied pre-decision `M0.G/README.md` byte-for-byte to [report-before-owner-pass-decision.md](report-before-owner-pass-decision.md) (`sha256=147ed89a51224aa9e4cdad2ac74eb61d55a958b9f85034029ca7233636a02b4c`) and recorded [owner-gate-decision-receipt.json](owner-gate-decision-receipt.json) with zero production code or data changes.
- Scope boundaries preserved: `G0 = PASS` applies strictly to the local CPU/offline foundation (`M0.1`–`M0.3`); `G1`–`G6` remain `NOT_RUN`, and `M2.3`, `M3.1`, and `M6.1` remain `IN_PROGRESS`.

## GitHub publication started 2026-11-18

- Authorization: owner requested "Push lên github đi theo chuản gitflow chưa ?" after verifying the two G0 repairs. This authorizes a distinct topic branch, conventional commits, normal push and a reviewable PR; it does not approve G0 or merge to main.
- Skills read/applied for publication: Superpowers 7.0.1 `using-superpowers`, `finishing-a-development-branch`, `verification-before-completion`; existing `writing-plans` guidance is reused for this prospective publication checklist. Installed paths are recorded below.
- Read-only discovery: private origin has `main` and the previously merged feature branch; no `develop` or open PR. The Gitflow reference defines long-lived main/master and develop, so this repository is not classic Gitflow. Publication follows its existing main-plus-topic-PR workflow without inventing a shared-branch migration.
- Fresh fetch advanced origin/main from `c6c36131` to `ad7eb92f`, incorporating M3.1 and M6.1 in four commits. Settings adds an optional dense-index path and the milestone index adds two rows. These incoming changes must survive the G0 fix integration; they are not acceptance decisions for those tasks.
- Prospective spec/plan above precede branch/stash/commit/push execution. Publication output and revalidation will use separate `publish-*` names, preserving all earlier measured results.
- Integrated validation found an upstream Windows issue: full pytest exits2 while collecting `tests/unit/test_dense_hybrid_retrieval.py` because unchanged `dense_hybrid_pilot.py:12` imports Unix-only `resource`; mypy exits1 with four missing `getrusage`/`RUSAGE_SELF` attributes in the two unchanged M6.1 pipelines. Required Ruff, pip check, source scan, 11 contract/smoke tests and 38 independent G0 runtime assertions pass. This does not invalidate the prior 100-test result on the earlier source, but it blocks an unconditional recommendation for the new tree. The authorized push will be a draft PR and keep these failures visible, without an unrelated M6.1 code change.
- Git diff whitespace check initially flagged Windows CRLF carriage returns as whitespace. The project files include CRLF; `git -c core.whitespace=cr-at-eol diff HEAD --check` passes without changing raw evidence or historical data. The initial stash apply's conflict and its actual exit1 are preserved in the integration receipt, followed by the explicit resolution.

## Owner-authorized remediation started 2026-11-18

- Authorization: "fix 2 diem do di" refers to the two immediately preceding findings, `G0-REV-1` and `G0-REV-2`. Implement in the already synchronized local checkout and report verification; do not approve G0 on the owner's behalf.
- Planning: the prospective fixes sections in `../superpowers/spec.md` and `../superpowers/plan.md` precede regression tests and production edits. Original audit sections/receipts remain historical evidence.
- Process skills read for this task: Superpowers 7.0.1 `using-superpowers` plus `references/codex-tools.md`, `systematic-debugging`, `receiving-code-review`, `writing-plans`, `executing-plans`, `test-driven-development` plus `writing-good-tests.md`, `using-git-worktrees`, `verification-before-completion`, and `requesting-code-review`, at the installed user-level skills path already recorded below.
- Applied sequence: verify the review findings against current source; write failing behavior regressions; implement the minimum settings/client and two lint changes; run focused then full checks; request one fresh-context read-only review; update evidence/report without gate approval.
- Root cause: settings upper bound5 propagates through the environment and the client uses it directly; caller-supplied consumed counts have no validity check. Existing default2 behavior is insufficient to enforce the project maximum under supported settings.
- Native execution ruling: reuse the owner's requested checkout with existing report changes and preserve unrelated logs. Repository-mandated `evidence/` storage owns the persistent ledger and raw command outputs; Windows-native runners replace the skill's Bash scratch/task wrappers. No scratch-wrapper run, commit, push, new worktree, or human approval is claimed. Cost if wrong: workflow automation parity rather than runtime behavior; explicit checklists and command receipts retain the required evidence.
- Pre-flight: Task2 consumes Task1's source/test changes and fixed runtime behavior. No shared-interface conflict found; public signatures stay unchanged. Additional invalid-counter cases are part of the same budget bypass boundary, not a new product feature.
- Task 1: IN_PROGRESS; baseline/source preservation and RED regression pending.

## Independent local review started 2026-11-18 (Asia/Saigon)

- Authorization: the project owner explicitly requested fetching/merging into local, independently evaluating G0, and reporting for the owner's PASS decision. Formal gate approval is reserved for the owner.
- Baseline synchronization: existing canonical G0 spec/plan were read at fetched `origin/main`; `merge --ff-only origin/main` advanced the requested checkout from `6cf1a6ec` to `c6c36131`. [Git receipt](peer-git-sync.json) records exact commands, SHA values and unrelated untracked-file hashes.
- Planning: independent-review addenda were written to `../superpowers/spec.md` and `../superpowers/plan.md` before evaluation. Original contributor records below remain dated evidence; no original verification receipt is overwritten.
- Skills actually read: Superpowers `7.0.1` at `C:/Users/lanph/.codex/plugins/cache/openai-curated-remote/superpowers/7.0.1/skills/`: `using-superpowers/SKILL.md`, its `references/codex-tools.md`, `writing-plans/SKILL.md`, `executing-plans/SKILL.md`, `using-git-worktrees/SKILL.md`, and `verification-before-completion/SKILL.md`.
- Applied: initial skill/instruction discovery, proportional audit spec/plan, explicit evidence-before-claims verification, and a persistent execution ledger here. `executing-plans` and worktree instructions were consulted; their feature-implementation/TDD/commit lifecycle is not claimed as executed for this audit. No product implementation is planned. The owner's requested local checkout is used without creating an unrelated worktree.
- Native execution continues under existing authorization; the implementation-plan handoff prompt is inapplicable to this already authorized audit of an existing agreed gate. Review artifacts and findings are retained for the owner's final decision.
- Initial environment discovery found system Anaconda Python 3.14.6 without the project build backend; this is not used as the project verification environment. Reuse the previously verified `uv` Python 3.12 declared `.[demo,dev]` profile with offline resolution.
- Review finding to verify: original `run_g0_checks.py` records statuses but contains no endpoint assertions. The independent probe must assert actual acceptance and return nonzero for mandatory failures.
- Progress: synchronized; prospective review plan recorded; fresh verification pending.

## Original contributor workflow (retained)

- **Date:** 2026-11-18 (Asia/Ho_Chi_Minh)
- **Task / Gate ID:** `M0.G` (`G0`)
- **Primary Owner:** Nguyễn Việt Nguyên (`N`)
- **Peer Reviewer:** Trần Đình Khương (`K`, pending gate sign-off)
- **Evaluated Revision:** `main` @ `1ff574fefa87b0453116f99e9b802221222593f4`

## Process Check (`AGENTS.md` Section 7)
- Authored [spec.md](../superpowers/spec.md) and [plan.md](../superpowers/plan.md) before executing G0 verification commands.
- Verified prerequisite task reports `M0.1`, `M0.2`, and `M0.3` are marked `COMPLETE` on `main`.
- Ran fresh verification suite directly on `main` (`1ff574fe`) without live Gemini calls (`USD 0`).

## Recorded Verification Commands & Receipts
- `.venv/bin/python scripts/check_secrets.py` -> `EXIT=0`, `PASS: Zero secret leaks detected across workspace.` ([check-secrets.log](check-secrets.log))
- `.venv/bin/python -m ruff check packages apps tests/contract tests/smoke` -> `EXIT=1` with 2 pre-existing style notices (`apps/api/app/routers/health.py:1` `I001`, `packages/retrieval/sparse/bm25.py:188` `UP017`) ([ruff.log](ruff.log))
- `.venv/bin/python -m mypy packages apps pipelines` -> `EXIT=0`, `Success: no issues found in 76 source files` ([mypy.log](mypy.log))
- `.venv/bin/python -m pytest tests/contract tests/smoke -v` -> `EXIT=0`, `11 passed in 6.51s` ([contract-smoke.log](contract-smoke.log))
- `.venv/bin/python -m pytest -v` -> `EXIT=0`, `75 passed in 17.03s` ([pytest-full.log](pytest-full.log))
- `.venv/bin/python -m pip check` -> `EXIT=0`, `No broken requirements found.` ([pip-check.log](pip-check.log))
- `docker --version` -> `Docker version 29.1.3` ([docker-check.log](docker-check.log)); `docker info` -> daemon socket `/var/run/docker.sock` absent in environment ([g0_verification_receipt.json](g0_verification_receipt.json)).
- `.venv/bin/python docs/reports/milestones/M0.G/evidence/run_g0_checks.py` -> `EXIT=0`, snapshots `20261117_recovered_v1` & `20261118_taxonomy_fix_v1` (`264` creators, `70,996` videos) and in-process ASGI endpoints (`/health/live`, `/health/ready`, `/demo/`, benchmark, retrieval, `offline_grounded`, OOD `422`) all pass ([g0_verification_receipt.json](g0_verification_receipt.json)).

## Independent results and review decisions

- Fresh source checks on `c6c36131`: scanner exit 0, pip check exit 0, configured mypy exit 0 (76 source files), contract/smoke exit 0 (11 tests), full pytest exit 0 (75 tests, 30.30 seconds; wall 32.491 seconds). Exact commands, package versions and logs: [peer-check-results.json](peer-check-results.json).
- Ruff exit 1 reproduces I001 and UP017. The original G0 spec explicitly requires clean lint; older narrative calling these non-blocking is not an owner-approved exception. This is `G0-REV-2`, an unmet acceptance criterion with low code severity.
- Independent runtime probe: 36/38 assertions passed, 2 failures for one above-two call-budget defect (`G0-REV-1`). Default2 control blocks; configured3 permits one stubbed third call with `turn_calls_used=2`. Actual provider calls and spend remain zero. Source tracing: settings allows up to5; environment override propagates directly; client compares against that value. Current HTTP generation still makes one call per invocation, so the probe is not evidence of an observed API overrun.
- Skills additionally read/applied: `systematic-debugging/SKILL.md` (root-cause tracing and controlled default/higher-budget reproduction; no production fix), `requesting-code-review/SKILL.md` and its `code-reviewer.md` (read-only fresh-context review requested through the available collaboration tool). Paths are in the same installed Superpowers 7.0.1 skills directory recorded above. The review is AI-assisted, not a human K/N sign-off.
- The initial successful probe saved the policy failures. A later edit adding the default-budget control introduced an audit-script IndentationError; its log is retained as [peer-runtime-harness-error.log](peer-runtime-harness-error.log). It was corrected, syntax checked, and the final complete probe produced [peer-runtime-receipt.json](peer-runtime-receipt.json), exit1 solely for the two policy assertions, with no unexpected error. No product source was changed.
- Package reproduction: wheel built from Docker COPY context; isolated venv installed dependencies from cache; installed module paths, dependency integrity and `/health/live` + `/demo/` pass. Docker CLI 29.6.2 is present, but the Linux-engine named pipe is absent; container execution NOT_RUN. [Package receipt](peer-package-results.json).
- Existing dataset rights, unavailable pre-recovery inventory, Docker runtime, UI polish and downstream semantic/fresh-data limitations remain explicit. The historical full-file preservation receipts were reviewed, not relabeled as a new 37,840-file hash scan. Fresh checks cover the 10 runtime Gold/BM25 files and their before/after bytes.
- Decision scope: recommendation HOLD unconditional G0; no gate PASS/FAIL, production fix, M3.1 merge, push or publication. The owner makes the formal decision.

- Fresh-context review completed: [peer-review.md](peer-review.md). It confirms HOLD unconditional G0, the above-two ceiling gap and unmet clean-Ruff criterion; no additional critical issue or product changes. Reviewed deferred scope is retained explicitly in the report.

- First handoff integrity run returned FAIL because its two output files did not yet exist and the inherited spec requirement-source link resolved one level too high. The outputs were generated and the relative spec link corrected before the final check. No product acceptance finding was erased.

- Handoff validation passed after link/output correction (18 initial checks); the final validator additionally checks original untracked-log SHA256 values and limits tracked changes to the G0 review bundle and milestone index. The final authoritative counts, source-scope checks and SHA256 inventory are [peer-handoff.json](peer-handoff.json) and [peer-artifact-hashes.json](peer-artifact-hashes.json). Final secret scan exits0. G0 remains NOT_RUN and M0.G IN_PROGRESS.

- Task1 RED: focused budget regressions produced 12 failures / 9 passes before source edits (`fix-red-budget.log`), including accepted budgets3/5, environment overrides, bypassed settings and invalid consumed counters. GREEN: all21 new regressions plus13 existing guardrail/provider tests passed (`fix-green-budget.log`, 34 total). Four production files changed only as planned; code validation pending full suite.

- Task1 RED: `tests/unit/test_llm_call_budget.py` produced 12 failed / 9 passing controls before any production edit; constructor/environment >2, bypassed settings and malformed counters reproduced the missing checks. [RED log](fix-red-budget.log).
- Task1 GREEN: minimum settings/client ceiling and malformed-counter rejection implemented; UTC/import-only changes resolve Ruff. New regression file plus existing guardrails: 34 passed. [GREEN log](fix-green-budget.log). Required Ruff including the new test exits0. No provider calls.
- Task1: COMPLETE subject to final whole-change review. Task2: IN_PROGRESS, fresh suite/runtime/package receipts are recorded under `fix-*`; original `peer-*` measurements remain untouched.

- First implementation verification: all 96 tests, 11 contract/smoke tests, configured mypy, Ruff and scanner passed; independent runtime38/38 and clean installed ASGI passed. Those pre-review results are preserved under `fix-before-review/`. Fresh-context reviewer found one residual Important defect: `min(NaN,2)` preserves NaN when an unvalidated settings copy contains it, allowing used2 to reach the stub SDK. No real provider call occurred. The one review-fix pass adds a failing nonfinite copied-budget regression, rejects malformed copied budgets before min, and reruns source-bound verification.

## Remediation RED/GREEN and review-fix ledger

- Task1 RED: `tests/unit/test_llm_call_budget.py` produced 12 failed / 9 passed before production changes; failures were constructor/environment over-budget acceptance, copied-budget bypass, and invalid consumed-counter handling. [RED](fix-red-budget.log).
- Initial GREEN: settings/client hard cap plus two style changes produced 34 passing budget/provider-guardrail tests. [GREEN](fix-green-budget.log). Initial full verification then passed 96 tests and clean Ruff, with prior receipts preserved in `fix-before-review/`.
- One fresh-context read-only review found a residual copied NaN budget bypass; no other material finding was reported. [Review and resolution](fix-code-review.md). No reviewer file/index/HEAD mutation or live provider call occurred.
- Review-fix RED: 4 nonfinite copied-budget cases produced 3 failures / 1 control pass. Added validation of copied configured budgets as positive integers before computing min. Final focused GREEN: 38 passing tests, including all 25 new budget cases and 13 existing provider/guardrail tests. [RED](fix-red-review-budget.log), [GREEN](fix-green-reviewed-budget.log).
- Task1 implementation is complete subject to final task2 full verification and evidence integrity. Current source hashes are pinned in `fix-check-results.json`; `HEAD` alone is insufficient because source edits are uncommitted.
- Final validation uses new `fix-*` outputs. Historical `peer-*` failed checks/measurements remain unchanged; their inventory includes earlier mutable report/spec/plan versions, so the final handoff separately verifies immutable historical evidence and publishes a new current inventory.

## Remediation final verification and handoff

- Final Task1 source verification: all 38 focused budget/provider-guardrail tests pass after the reviewed NaN correction. The 25 new budget cases plus existing tests give 100 passing full-suite tests (58.16 seconds; subprocess wall60.829 seconds); contract/smoke has 11 passes (24.69 seconds). Required Ruff, configured mypy (76 files), pip check and source secret scanner all exit0. [Current command receipt](fix-check-results.json).
- Independent runtime: 38/38 assertions pass with 0 live provider calls and zero spend. Clean COPY-context wheel build/install and installed-package ASGI pass; runtime, package and suite receipts share the same five source/test SHA256 values. [Runtime](fix-runtime-receipt.json), [package](fix-package-results.json).
- Later Docker observation differs from the old audit: version/info commands now succeed (engine29.6.2). No image build or container run is inferred or performed. Existing data/rights/UI/scientific and hosting boundaries remain documented.
- Task1 COMPLETE for its authorized repairs; Task2 verification and review performed. The material reviewer finding was fixed in one RED/GREEN pass; no new reviewer round or human sign-off is claimed. Final report/layout/link/hash checks are recorded by [fix-handoff.json](fix-handoff.json).
- `finishing-a-development-branch/SKILL.md` 7.0.1 was read to check integration boundaries. The authorized endpoint is local fixes and a decision-ready report; its menu/merge/push/cleanup flow is not applied because no further integration was requested. The current branch and uncommitted changes stay available for the owner; no commit or push is claimed.
- Current recommendation changes from the preserved earlier HOLD report to technical PASS within the defined local CPU/offline foundation after verified fixes. Formal G0 remains NOT_RUN and M0.G remains IN_PROGRESS until the owner's decision. Historical peer evidence stays intact; the new fix inventory owns current report/source hashes.

- Publication integration: path-scoped stash retained as recovery, topic branch created at ad7eb92f. Stash apply returned1 for the milestone-index conflict; resolved by preserving the fetched-main index and updating only G0, retaining exactly one M3.1/M6.1 row. Settings merged automatically with optional dense-index fields preserved. Git stash changed the new test to CRLF; restored its original LF bytes and checked the pre-stash SHA256. [Git integration receipt](publish-git-integration.json).

- Extended the repository's existing .gitattributes -text convention to the measured G0 health/client/new-test files. Other measured G0 files and all report evidence were already covered. This preserves source SHA256 identity across Git checkouts without changing source behavior; staged blob bytes will be checked against publication source hashes before commit.

- Updated-main results: 38 focused tests,11 contract/smoke and38 runtime assertions PASS; required Ruff/pip/source scan PASS. Full pytest FAIL at collection (exit2); mypy FAIL with4 errors across80 files (exit1). The canonical report now recommends HOLD for updated-tree integration, explicitly retaining the earlier100-test repair PASS as dated evidence. Publication will be draft only; the source repair is not labeled a new regression.

- Precommit staging verified supported secret patterns across all staged text, including logs, with zero findings. Initial byte comparison exposed Git automatic line-ending normalization for health/client; explicit -text attributes plus path-scoped renormalization of the index restored staged bytes to the tested SHA256 values. No working source content changed. Upstream M6.1 identity is checked as canonical Git content, accounting for its existing automatic checkout line endings.

- Before commit, normalized only the measured health/client source files to their existing Git LF representation to avoid whole-file line-ending churn in the PR; the -text attributes now preserve these measured bytes. Earlier publication results are retained under publish-before-line-ending-normalization/. Revalidation below pins the final normalized source; original raw data/evidence bytes are unaffected.

- Published source/evidence commit `7abcd6e5635134395eedbcb8c8055957b351ca55` with a conventional fix(g0) subject; normal `git push --set-upstream origin fix/g0-call-budget-and-lint` exited0 and remote ref equaled the local commit. Created [draft PR #3](https://github.com/khuonglaptri3/TikTok_AI_Engine_/pull/3) into main, OPEN/draft. [GitHub receipt](publish-github-receipt.json), [push log](publish-push.log). No force push, main push, merge or G0 approval.
- A documentation-only follow-up persists actual publication receipts and current hashes. Product source is unchanged from the publication test/runtime SHA256 map; its final remote ref is verified after push without attempting a circular self-commit receipt.

- User-authorized PR3 integration completed: source commit `af5be92bf48433688c47c97b03ecaccc5d8fcb5b`, merge commit `eb43b0df3d46007b7550de8f4314dc2dbca9c51f`, merged_at `2026-11-18T10:45:57Z`. [GitHub PR3](https://github.com/khuonglaptri3/TikTok_AI_Engine_/pull/3). Local main was fast-forwarded by fetch while the topic branch was checked out, then switched to the identical merged tree; no old main checkout removed preserved data. Formal G0 remains NOT_RUN and scientific M6.1 remains IN_PROGRESS.

- Post-merge verification on actual main `eb43b0df3d46007b7550de8f4314dc2dbca9c51f`: 120 passed in 58.09s, exit0; committed source hashes match the full premerge suite/runtime/package map. [Main test receipt](../../M6.1/evidence/main-verification.json). No production source is changed by the final evidence-only PR.
