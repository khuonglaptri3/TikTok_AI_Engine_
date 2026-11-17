# Core recovery and two-person plan implementation plan

> **For agentic workers:** Apply `superpowers:executing-plans` with TDD for production fixes and isolated read-only/data-restoration/documentation assistance. Preserve the owner's existing execution authorization. The specification is binding; record deviations in the workflow ledger.

**Goal:** Deliver a reproducible, corrected offline historical core and an equally allocated plan for Khương and Nguyên.

**Architecture:** Retain immutable Gold snapshots, BM25, typed FastAPI, and one Gradio demo. Share a staged snapshot publisher across historical/incremental builders; keep provenance-bound evaluation distinct from independent scientific validation.

**Tech Stack:** Python 3.11+, pandas/PyArrow/SciPy, Pydantic, FastAPI, Gradio, pytest, mypy, Git; CPU and no provider calls.

**Spec:** [spec.md](spec.md)

## Global constraints

- Preserve all original data, previous audit evidence and unrelated edits; no historical TikTok recrawl.
- Provider/GPU spend USD 0; no live Gemini calls, automatic paid fallback, publication, invitation, commit or push.
- Task bundle has exactly README.md, evidence/, superpowers/; canonical spec/plan remain in superpowers/.
- Reports/authored documentation English. Root README remains the overall project overview.
- Owner and Nguyên receive equal estimated total effort and peer-review responsibilities; do not infer expertise from GitHub.

## Review focus

- Failed publication, collisions and same-input/output paths must leave trusted snapshots intact.
- Two successive batches, empty/replayed batches and same-video enrichment must preserve all data identities.
- Available source IDs do not establish factual support; do not auto-attach IDs to unsupported dialogue.
- Correct recall may be much lower than historical mislabeled values; no gate result is preordained.
- Recovery checksum equality, API startup and balanced task totals must be observed, not asserted from documentation.

## Tasks

- [x] 1. Set up isolated implementation workspace, preserve pending audit, and restore pinned source data with an integrity record. Files: task evidence and local-only data. Expected: required historical inputs present and verified; no original overwrite.
- [x] 2. Add failing snapshot/continuity/enrichment tests; fix shared publication and converter. Files: packages/common snapshot helper, pipelines/build_gold_corpus/builder.py, pipelines/ingest_incremental_to_gold/converter.py, tests/unit. Expected: regressions fail before fixes, then pass; base/source bytes unchanged.
- [x] 3. Add failing script-validation cases; fix guardrails and evidence-aware offline drafting. Files: packages/llm/guardrails/verifier.py, packages/script_engine/service.py, relevant contracts/presentation if necessary, tests/unit. Expected: no fabricated ID, empty/mistimed/missing-required-content outputs cannot pass; ordinary supported draft succeeds.
- [x] 4. Add hand-calculated metric regression; correct and version evaluation/receipts. Files: pipelines/benchmark_retrieval, tests/eval, artifacts/benchmarks. Expected: correct Recall@10 denominator and matching query/corpus/index receipts; original artifact retained in historical evidence.
- [x] 5. Fix package/container profile and defaults, rebuild historical Gold/index in new paths, run full CPU offline integration. Files: pyproject.toml, infra/docker/Dockerfile.api, setup commands, local-only artifacts. Expected: package builds, API/demo smoke and full pytest/mypy pass, no provider operation.
- [x] 6. Rewrite balanced two-person milestone plan and aligned policy/resources/refactor guidance; archive prior plans. Files: docs/planning/*, AGENTS.md, ReFactor_structure/04_IMPLEMENTATION_PLAN.md, targeted root README. Expected: equal summed effort, owner/reviewer for every task, bounded future gates and truthful status.
- [x] 7. Integrate reviewed changes into the owner's checkout; independently review, resolve findings, run final verification and publish the task report/navigation locally. Expected: honest results, intact prior audit/data, valid bundle/links/hashes, no commit/push/deployment.

## Pre-flight and authorization

Tasks 2 and 3 are independent code domains; task 4 depends on the artifact paths from task 5 but its metric fix is independent. Task 6 consumes the observed task results before final status reconciliation. Data recovery and draft documentation can proceed separately from code without shared writes. The existing audit and the owner's explicit 'do it' supply the agreed design/approach and execution authorization; defaults selected by the implementer are documented rather than attributed to the owner.

## Resumed execution — 2026-11-17

- Continue the existing isolated `bf1f` worktree; canonical planning/evidence stay in the owner's checkout. Preserve its pending documentation edits.
- Task 2 remaining regression: `test_incremental_manifest_binds_parent_snapshot_bytes` must publish `parent_snapshot_id` and `parent_manifest_sha256`. Add optional backward-compatible fields to `CorpusManifest`, populate them from the verified base, and run snapshot regressions followed by the project suite.
- Task 3 consistency check: a 100-token beat at 2 units/second is 50 seconds and must fail a 45-second request under the active `max(2 seconds, 5%)` tolerance. Observe this regression failing, align the verifier, and rerun structural/offline draft checks.
- Reconcile restored input verification, rebuild Gold/index in new directories, run the corrected benchmark and real-corpus ASGI smoke, then finish tasks 5–7. Existing RED/GREEN evidence is retained and distinguished from fresh verification.
- Final independent review requires one fix pass: regression-test empty/multiple-source offline citations and retain attributed excerpts through shortening; coalesce repeated video records before ingestion (later explicitly supplied fields win, omitted values remain, distinct comments survive); normalize duplicate comment IDs for initial and existing videos using the same sparse-field rules. Re-run focused tests and the full suite after fixes. No second independent review is required by the execution skill.
