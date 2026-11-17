# Team kickoff and authorized repository publication specification

- Created: 2026-11-17 (Asia/Saigon), before publication edits or commit/push.
- Authorization: the owner explicitly requested pushing the completed work and writing a description so the two contributors can begin. This supersedes the earlier recovery task's no-commit/no-push execution boundary for this publication only.
- Source: [completed recovery](../../core-recovery-and-two-person-plan-2026-11-17/README.md) and the [active two-person plan](../../../../planning/TikTok_AI_Engine_Milestone.md).
- Baseline: local `main` and fetched `origin/main` both at `cdbc6ed9ccad11db437aa66c68638cf018701fe5`; existing reviewed source, audit, recovery records and local generated artifacts remain uncommitted.

## Required outcome

Publish the reviewed recovery source, its reports and small reproducibility receipts to the existing private `khuonglaptri3/TikTok_AI_Engine_` repository on `main`, using a normal fast-forward push. Provide an English kickoff description explaining the verified baseline, local setup, first reciprocal tasks, dependencies and gates. Include a clear commit description and a concise repository About description.

## Constraints and acceptance

- Preserve all historical raw/interim/legacy files, local Gold Parquet/index binaries and `.env`; none is staged or uploaded. Keep small manifests, benchmark receipts and audit inventories available for review.
- Preserve checksum-bound original bytes across Git storage/checkout. Investigation already confirmed `core.autocrlf=true` changes source bytes through the clean filter; use scoped attributes for receipt-bound files rather than silently rewriting historical measurements.
- Rerun the whole project suite and secret scanner before committing. Verify staged file scope, no oversized file, no raw data/key, all applicable receipt hashes and a clean diff. No product behavior change is planned.
- Keep the previous recovery/audit records dated to their execution. A new publication receipt identifies this handoff; an older all-workspace hash manifest is a historical snapshot, not a claim about later kickoff edits.
- Preserve 94/94 estimated effort, reciprocal review, zero provider spend, the existing module/demo scope and G0–G6 NOT_RUN. No collaborator invitation, issue notification, live crawl, provider call, hosting deployment or forced push.
- Completion requires remote `main` matching local HEAD, the requested description published, and a concrete linked kickoff report. A failed authentication/network/protection check is reported honestly; it is not push success.

## Deliverables

This bundle contains exactly `README.md`, `evidence/` and `superpowers/`, with exactly `spec.md` and `plan.md` under planning. Its README is the current kickoff narrative. Evidence holds actual workflow, verification, staged-byte inventory, the exact commit description and publication receipts.
