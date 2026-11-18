# M0.G (G0) — Execution Plan

## Owner-selected integration repair and merge — 2026-11-18

Follow [M6.1's repair plan](../../M6.1/superpowers/plan.md), revalidate G0 on the final integrated source, update the report/index and PR3 to reflect current passing results, and merge through the PR after checks and review. Record actual GitHub merge/main verification separately from formal G0 acceptance. The user's latest instruction explicitly supersedes the earlier draft-only publication boundary; no additional merge permission is required.

## GitHub publication plan — 2026-11-18

**Goal:** Publish the reviewed G0 repair on a distinct branch and PR after checking the repository's actual branch workflow.
**Spec:** [spec.md](spec.md), GitHub publication addendum.
**Execution:** `finishing-a-development-branch` and `verification-before-completion`; the user has selected publication, so no redundant integration menu is required.

- [x] Inspect remote branches, open PRs and repository conventions. Record that classic Gitflow's `develop` is absent; retain the existing `main` + topic PR workflow.
- [x] Preserve an exact authorized-path inventory and source/evidence hashes; stash only the authorized G0 paths if needed. Create `fix/g0-call-budget-and-lint` at freshly fetched `origin/main`, apply the saved changes, and preserve independent M3.1/M6.1 changes and index rows.
- [x] Run full pytest, contract/smoke, configured mypy, required Ruff including the new test, source secret scan, pip check and asserting G0 runtime probe. Expected: exit0 and source-hash-bound results; no paid/provider operations.
- Integration finding: required checks were executed; updated-main full pytest exits2 during collection and mypy exits1 due to M6.1's unchanged Unix-only `resource` usage. Record FAIL rather than weakening the checks. Publication proceeds as an explicitly draft PR with the integration blocker visible; no merge or G0 acceptance is claimed.
- [x] Finalize the report and publication evidence for this source tree. Stage only the explicit G0 source/test/report paths, inspect staged contents and run the secret scanner before committing. Expected: conventional fix commit with no historical data changes or unrelated logs.
- [x] Push the new branch normally and create a reviewable PR into `main` with validation and G0 decision scope. Record actual Git/PR receipts; do not merge the PR or mark G0 PASS.
- [x] Persist publication receipts and refreshed artifact hashes in a documentation follow-up if needed, recheck scanner/source identity, push normally, and verify the remote head/PR base/mergeability and preserved unrelated files.

Incoming remote changes require integrated verification but not acceptance or redesign of M3.1/M6.1. The final report identifies the source revision/hashes and distinguishes source validation from the owner's gate decision.

## Authorized remediation implementation plan — 2026-11-18

> For agentic workers: execute this bounded repair natively with `superpowers:executing-plans`, `test-driven-development`, and `verification-before-completion`. Existing owner authorization covers both fixes and local verification; gate approval remains the owner's decision.

**Goal:** Resolve the two recorded G0 acceptance gaps without widening project scope.
**Architecture:** Validate budgets at settings boundaries and apply an independent client ceiling before rate limiting or SDK work. Preserve all earlier review results and write new `fix-*` receipts in the same evidence directory.
**Tech stack:** Python 3.12, Pydantic, pytest, Ruff, configured mypy, uv offline packages, FastAPI/Gradio.
**Spec:** [spec.md](spec.md), owner-authorized fixes addendum.

### Global constraints and review focus

CPU/offline, zero paid spend, no original data mutation, no secret values in logs, no gate approval. Focus regression coverage on constructor/environment budgets above2, unvalidated settings copies, stricter budget1, consumed counters that could bypass validation, and existing missing-key/deadline behavior. SDK stubs replace external I/O only; the settings, client and limiter stay real.

### Task 1: Hard call ceiling and clean lint

**Files:** modify `packages/common/settings/__init__.py`, `packages/llm/clients/gemini.py`, `apps/api/app/routers/health.py`, `packages/retrieval/sparse/bm25.py`; create `tests/unit/test_llm_call_budget.py`.
**Interfaces:** keep `AppSettings.max_llm_calls_per_turn` and `BoundedGeminiClient.generate_structured_json(prompt, turn_calls_used=0)`; return parsed JSON on eligible requests and raise bounded errors otherwise.

- [x] Archive the current G0 report; record baseline source hashes and the authorization in `evidence/workflow.md` before implementation.
- [x] Write regressions for settings/environment budgets >2, a bypassed settings copy, consumed counter >=2, invalid consumed counters, and budget1/eligible-call controls. Run the focused file before source edits. Expected: failures expose current policy bypasses; no live SDK calls.
- [x] Set the settings ceiling to2; cap the effective client budget at2 and reject invalid consumed counters before RPM/SDK work. Apply only the two identified Ruff corrections.
- [x] Run the focused regressions, existing provider/guardrail tests and required scoped Ruff including the new test. Expected: all pass. Preserve RED/GREEN outputs and exact source hashes in `fix-*` receipts.

### Task 2: Revalidate and hand off for owner decision

**Files:** current `README.md`, `superpowers/spec.md`, `superpowers/plan.md`, `evidence/workflow.md`, new `evidence/fix-*` artifacts, and the milestone index.
**Interfaces:** previous `peer-*` files remain historical review evidence. New checks use distinct filenames and pin the uncommitted source changes by SHA256.

- [x] Run full pytest, contract/smoke, configured mypy, pip check, secret scan and required Ruff. Expected: exit0 for every required check, no exclusions for Ruff.
- [x] Re-run the independent runtime and clean-wheel/installed-ASGI checks into `fix-*` outputs, preserving the original failed receipts. Expected: all policy/runtime assertions and installation checks pass; Docker absence remains an explicit boundary.
- [x] Obtain one fresh-context read-only code review under `requesting-code-review`; address material findings within these two repairs and retain the review outcome.
- [x] Update the decision-ready report/index, validate exact layout/links, preserved files and source scope, and regenerate an accurate SHA256 inventory. Expected: both issues resolved, evidence integrity passes, owner decision still pending.

The durable native execution ledger is `../evidence/workflow.md`, per repository storage rules. Windows-native command/receipt runners replace the skill's Bash scratch wrappers; no Bash wrapper execution or unrequested commit/push is claimed. The worktree preference is already supplied by the owner's local-checkout request, and the implementation stays in that checkout.

## Independent local review plan — added 2026-11-18

**Goal:** Give the owner a reproducible G0 recommendation after the requested local synchronization.
**Architecture:** Preserve the existing contributor evidence, run independent bounded CPU/offline checks against the synchronized revision, and update the canonical G0 report without approving the gate.
**Tech stack:** Git, local Python, pytest, configured mypy, Ruff, Poetry build backend, FastAPI/Gradio ASGI, Parquet/BM25.
**Spec:** [spec.md](spec.md), including the owner-authorized local review addendum.
**Execution:** Native audit in the requested checkout. Existing authorization covers synchronization and evaluation; no product implementation is planned. Workflow and results live in `../evidence/workflow.md` and `peer-*` artifacts.

### Constraints and review focus

Preserve original data and unrelated files; no secret values in evidence; no provider/crawler calls; retain `G0 = NOT_RUN` for owner decision. Specifically check stale/non-asserting receipts, provider missing-key behavior, redaction regressions, manifest/source mismatches, and installation/runtime boundaries. These are evaluation probes, not new product behavior.

### Review tasks

- [x] Synchronize safely with `origin/main`; record before/after SHAs, branch, exit codes and hashes of pre-existing untracked logs. Expected: fast-forward, no unrelated changes.
- [x] Archive the original report and inspect M0.1–M0.3, G0 probe, actual environment and dependency profile. Record any limitations rather than changing acceptance retroactively.
- [x] Run source secret scan, `python -m pip check`, configured `python -m mypy packages apps pipelines`, scoped Ruff, `python -m pytest tests/contract tests/smoke -v` and `python -m pytest -v`, each with credentials blanked and full output saved. Expected: required checks exit 0; any Ruff failure is explicitly classified.
- [x] Independently load and checksum both historical snapshots and BM25, verify actual ASGI valid/invalid requests, citation/source membership, finite nonnegative `ms` timings, missing-key and redaction behavior with explicit assertions. Expected: all mandatory assertions pass with zero provider calls and no source artifact changes.
- [x] Reproduce a source wheel build and package/import checks without credentials; probe Docker availability with a timeout. Record the exact tested installation scope and any unexecuted container/clean-install checks.
- [x] Write the decision-ready report, preserve historical contributor results, update the index description while retaining IN_PROGRESS, and record blockers or a bounded PASS recommendation for the owner.
- [x] Verify English authored prose, exact bundle layout, both planning links, local report links, source mutation scope, preserved-log hashes and evidence SHA256 inventory; run final secret scan. Expected: valid report/evidence and unchanged formal gate status.

## Original contributor execution plan

1. Verify current git revision (`git rev-parse HEAD`), clean working tree, and completion status of `M0.1`, `M0.2`, and `M0.3`.
2. Run and archive fresh G0 verification checks on the recorded environment:
   - Environment & packaging probe (`python --version`, `pip check`, `import apps, packages, pipelines`, `docker --version` / daemon check).
   - Secret scan (`python scripts/check_secrets.py`).
   - Static checks (`ruff check`, `mypy packages apps pipelines`).
   - Contract, smoke, and full `pytest` suites (`pytest tests/contract tests/smoke -v`, `pytest -v`).
   - ASGI in-process readiness probe (`/health/live`, `/health/ready`, `/demo/`).
3. Record all results, exact revision, hardware/Python environment, and explicit limitations (upstream terms, semantic limits, Docker daemon status, `M0.3-UI-*` notes) into `evidence/g0_verification_receipt.json`, `evidence/workflow.md`, and `M0.G/README.md`.
4. Update `docs/reports/milestones/README.md` with the `M0.G` row and run final pre-handoff `scripts/check_secrets.py`.

Review tasks describe completed investigation, not passing product acceptance: G0-REV-1 and G0-REV-2 remain unresolved, and the owner decision is pending. Final artifact integrity is recorded in `../evidence/peer-handoff.json`.

Remediation outcome (2026-11-18): both G0-REV-1 and G0-REV-2 are resolved in the source-hash-pinned local tree; all required checks are green. The earlier unresolved/HOLD wording is retained as dated review history. Current formal gate status remains NOT_RUN for owner decision.

Publication outcome: source/evidence commit 7abcd6e5635134395eedbcb8c8055957b351ca55 was pushed and draft PR #3 opened against main. A documentation-only receipt follow-up is included in the publication handoff; final remote identity is checked after its push outside that self-referential commit. Current full-suite/mypy failures remain explicitly reported and G0 remains NOT_RUN.
