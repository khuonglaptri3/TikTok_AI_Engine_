# Full data publication specification

- Created: 2026-11-17 (Asia/Saigon), before changing publication exclusions or staging data.
- Authorization: the owner's latest explicit request is to push all data. This overrides the earlier local-only publication choice for this data upload. Preserve private repository visibility, original bytes and secret hygiene.
- Baseline: `main` / `origin/main` at `2e927154abacebf747a08a87b02ec705bd94558c`.
- Requirement source: direct owner instruction, [verified recovery](../../core-recovery-and-two-person-plan-2026-11-17/README.md) and [previous publication](../../team-kickoff-and-push-2026-11-17/README.md).

## Outcome and acceptance

Upload every current regular file under `data/`, plus existing runtime artifacts under `artifacts/indexes/` and `artifacts/enrichment/`, to the existing private GitHub repository using normal Git. The known largest historical file is 75,850,189 bytes, so no Git LFS storage, paid quota or external data host is needed. Inventory actual runtime artifacts before staging; never omit a file silently.

- Original local data and existing Gold/index bytes remain unchanged. Git must store exact bytes (`-text`) so pinned Git blob SHA1 and SHA256 evidence remains meaningful.
- Never stage `.env`, credentials, caches or unrelated archive/application files. Scan the upload candidates for credential patterns without printing credentials.
- Verify every data/index file's staged Git blob against actual bytes and all historical rows against the pinned inventory. Validate source/corpus/index receipts and run the current full project suite before publication.
- Update current setup/kickoff guidance to explain that cloning now supplies the data/artifacts. Preserve dated earlier observations as historical; retain 94/94 allocation and G0–G6 NOT_RUN.
- Use a normal push to `main`; no force/history rewrite, invitation, live collection, provider call, hosting or paid service.
- Completion requires remote/local commit equality and a remote tree containing the complete data/artifact path inventory. Record actual counts, logical bytes, hashes, commands and any Git warnings.

## Artifacts

This task has exactly `README.md`, `evidence/`, and `superpowers/` at its root; planning contains exactly `spec.md` and `plan.md`. The README is its current results narrative. All machine manifests, logs and workflow provenance belong in evidence.
