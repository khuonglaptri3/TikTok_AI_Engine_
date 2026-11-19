# M0.G (G0) — Foundation Decision Specification

- **Task ID:** `M0.G` (Gate `G0`)

## Owner formal G0 PASS decision — 2026-11-18

On `2026-11-18T21:26:08+07:00`, the project owner (`Trần Đình Khương`, `K`) explicitly approved **`G0 = PASS` (`M0.G = COMPLETE`)** based on the verified post-merge `main` results (`e050d7d5bbcf90e310bbfd144407086d82479341`, incorporating merged PR #3 `eb43b0df3d46007b7550de8f4314dc2dbca9c51f` with `120/120` passing tests, `81`-file Windows/Linux `mypy`, clean Ruff, `38/38` runtime assertions, clean wheel/installed ASGI checks, and `0` secret leaks).

- Archive the pre-decision `M0.G/README.md` byte-for-byte to `evidence/report-before-owner-pass-decision.md`.
- Record the formal gate decision receipt in `evidence/owner-gate-decision-receipt.json` and append provenance to `evidence/workflow.md`.
- Update `M0.G/README.md`, `docs/reports/milestones/README.md`, and `docs/planning/TikTok_AI_Engine_Milestone.md` so `M0.G` is `COMPLETE` and `G0` is `PASS`.
- Explicit scope boundary: `G0 = PASS` approves only the local CPU/offline foundation (`M0.1`–`M0.3`). It does **not** approve `G1`–`G6`, close `M2.3`/`M3.1`/`M6.1`, establish upstream dataset redistribution rights, verify Docker container execution, or imply live Gemini entitlement or public hosting eligibility.

## Authorized integration repair and PR merge — 2026-11-18

The owner now explicitly authorizes fixing the M6.1 Windows blocker, updating/readying PR3 and merging the completed work into main after verification. The implementation plan and resource-measurement criteria are owned by [M6.1's spec](../../M6.1/superpowers/spec.md) and [plan](../../M6.1/superpowers/plan.md). G0 reports must reflect fresh integrated results without rewriting previous failed evidence or automatically setting formal G0 PASS.

## Owner-authorized GitHub publication — 2026-11-18

The owner requested pushing the verified G0 repairs and checking Gitflow compliance. Publish the existing authorized source/tests/report evidence on a new bounded fix branch, with a reviewable pull request; preserve the owner's pending G0 decision.

- Current remote convention is `main` plus topic branches/PRs; `develop` is absent. Describe this as GitHub flow rather than claiming classic Gitflow. Do not introduce integration/release branches, branch protections or direct pushes to `main` as an unrequested repository migration.
- Use `fix/g0-call-budget-and-lint`, based on freshly fetched `origin/main` (`ad7eb92f76cddbfa8526bb16d53f8d7f8db30810` at initial inspection). Preserve incoming M3.1/M6.1 code and index/report rows without approving those milestones.
- Carry only the G0 source, new regression tests, canonical report/spec/plan/evidence and G0 index update. The three unrelated untracked publication logs and any pre-existing stashes remain untouched.
- Extend the existing `.gitattributes` byte-preservation convention to the three measured G0 source/test files not already covered (`health.py`, `gemini.py`, `test_llm_call_budget.py`), so committed bytes match their recorded SHA256 values across checkouts. This changes line-ending attributes, not source behavior.
- A path-scoped temporary stash may preserve these authorized changes while switching to the fresh base; apply it without discarding its recovery copy until the integrated code is verified/committed.
- Re-run required full/contract/smoke/type/lint/secret/dependency checks plus G0 runtime assertions on the updated tree. Record new source hashes and distinguish integrated results from earlier 100-test measurements.
- Create conventional commits and a PR against `main`; no force push, PR merge, tag/release, deployment, live provider call or formal G0 PASS is authorized by publication alone.
- Updated-main inspection found an upstream Windows portability blocker in unchanged M6.1 files: the full suite fails collection on `import resource`, and mypy reports four missing Unix resource attributes. Preserve those actual failures and publish a **draft** PR for review under the owner's push authorization. Do not represent publication as integration readiness or expand this repair into M6.1 implementation without authorization.
- Preserve original dated `peer-*`/`fix-*` verification receipts. Store publication-specific planning, Git/command receipts and fresh verification under `evidence/publish-*`, update the current report/index and generate current SHA256 checks before each commit.

## Owner-authorized fixes — 2026-11-18

The owner's follow-up instruction, "fix 2 diem do di", authorizes resolving `G0-REV-1` (LLM hard ceiling) and `G0-REV-2` (clean Ruff) in this existing local checkout. This is prospective implementation scope; the earlier review and failed measurements remain archived evidence.

- Settings accept only budgets 1 or 2, including values loaded from the environment. Default remains 2. Out-of-policy budgets fail validation rather than being silently accepted.
- The Gemini client independently caps the effective budget at 2, even if an unvalidated model copy supplies a higher configured value. A consumed-call count of 2 must raise `QuotaBlockedError` before RPM accounting or the SDK. A configured budget of 1 must remain stricter.
- Invalid copied client budgets, including non-finite values, must fail closed before RPM/SDK work.
- Invalid consumed-call counts must fail closed before the SDK: negative, boolean, fractional or non-finite counters cannot bypass the exhausted-budget check. Retain the existing public method and explicit domain-error behavior.
- Preserve missing-key behavior, offline mode, timeout/RPM behavior, and zero paid fallback. External SDK calls are replaced only in controlled tests; no real provider/crawler calls are authorized for validation.
- Fix exactly the Ruff I001 import ordering in `apps/api/app/routers/health.py` and UP017 UTC usage in `packages/retrieval/sparse/bm25.py`; add no behavior unrelated to the findings.
- Acceptance: observed RED then GREEN regression tests, full project tests, configured mypy, required scoped Ruff (including the new test), secret scanner, independent runtime assertions and clean wheel/installed ASGI validation pass against recorded source hashes.
- Preserve data, all prior peer receipts and unrelated local changes. Update the canonical report/index and evidence hashes. Keep `M0.G = IN_PROGRESS` and `G0 = NOT_RUN` until the owner decides; passing code checks is a recommendation, not human approval.
- **Independent review addendum:** 2026-11-18 (Asia/Saigon), requested by the project owner after the original evidence assembly. This addendum is prospective for the local review; it does not backdate the original work.

## Owner-authorized local review

Synchronize the current local branch with fetched `origin/main`, independently assess the foundation gate, and prepare a recommendation for the owner's decision. The original spec and plan already exist on the fetched revision and are read before synchronization; this addendum and the detailed review plan are recorded before evaluation commands.

- Work in the existing checkout requested by the owner; preserve unrelated untracked files and original historical/Gold/index bytes. Merge only `origin/main`, using fast-forward if possible. M3.1 is outside this G0 review.
- Evaluate the pinned synchronized source, prerequisite evidence, declared installation/package profile, configured mypy, secret scan, contract/smoke/full tests, real-corpus ASGI routes, bounded errors, source resolution and finite `ms` timings.
- Recheck the two fixed M0.2 redaction cases using synthetic markers. Inspect the existing G0 probe for assertions and evidence integrity; a zero exit alone must not be treated as endpoint acceptance.
- CPU/offline only, with provider credentials blanked in child processes; zero live provider/crawler operations and zero paid spend.
- Preserve the original contributor report and receipts. Store new commands, exit codes, timing, environment, checks, hashes and review findings under `evidence/` with `peer-` names.
- Keep `M0.G` IN_PROGRESS and formal `G0` NOT_RUN pending the owner's explicit decision, even if all independent technical checks pass. An AI-assisted review is not a fabricated human sign-off.
- Final report must distinguish blockers, accepted scope boundaries, lower-priority follow-ups, historical receipts and new measurements. Validate report layout, relative links, index status and evidence hashes before handoff.
- **Primary Owner:** Nguyễn Việt Nguyên (`N`)
- **Peer Reviewer:** Trần Đình Khương (`K`)
- **Requirement Source:** [TikTok_AI_Engine_Milestone.md](../../../../planning/TikTok_AI_Engine_Milestone.md) (`M0.G`)
- **Date:** 2026-11-18 (Asia/Ho_Chi_Minh)

## Scope

Assemble, verify, and record the **G0 foundation gate decision** across `M0.1`, `M0.2`, and `M0.3` on the synchronized `main` revision (`1ff574fe`).

## Gate Acceptance Criteria (`M0.G`)

1. **Upstream task completion:** Verify `M0.1`, `M0.2`, and `M0.3` reports and evidence bundles are marked `COMPLETE` and match the milestone index (`docs/reports/milestones/README.md`) and plan (`TikTok_AI_Engine_Milestone.md`).
2. **Automated checks on recorded revision & environment:**
   - `scripts/check_secrets.py` exits `0` (`Zero secret leaks detected`).
   - `mypy packages apps pipelines` passes with `0` issues.
   - `ruff check` passes cleanly on core foundation packages (`packages/`, `apps/`, `tests/contract/`, `tests/smoke/`).
   - Executable contract and smoke tests (`tests/contract/test_data_contracts.py`, `tests/smoke/test_api_and_demo.py`) plus the full `pytest` suite pass with `0` provider calls (`USD 0`).
   - Dependency integrity (`pip check`), editable/package import verification, and `Docker` engine availability status are explicitly recorded (distinguishing source-package verification from an actual Docker container run when unavailable).
3. **Explicit limitations & bounded claims:** Record all unresolved dataset licensing, semantic/ASR/POI ground-truth limits, UI `422` formatting rough edges (`M0.3-UI-1..3`), and Docker daemon boundaries; infer no live provider quota or public hosting eligibility.
4. **Two-person gate review:** Publish `M0.G/README.md`, `evidence/workflow.md`, and machine-readable receipt for independent review by Trần Đình Khương (`K`) before setting `G0` to `PASS`.
