# Team kickoff and repository publication plan

> Execute natively in the existing checkout. The owner explicitly selected commit/push; do not ask for another branch menu or design approval.

**Goal:** Publish the verified recovery and an actionable, equally shared kickoff.

**Spec:** [spec.md](spec.md)

**Approach:** Retain the completed application and measured receipts. Add a bounded kickoff report and scoped Git attributes so the stored blobs match the measured bytes. Commit reviewed sources/evidence and verify a normal push to the synchronized remote.

## Steps and verification

- [x] Inspect branch/remotes/pending scope and fetch origin. Expected: `main`, existing private owner repository, zero ahead/behind at the recorded baseline.
- [x] Record the Git line-ending failure with real clean-filter byte comparisons. Add attributes limited to checksum-bound files/evidence and observe those comparisons pass, including unchanged receipt-bound source files.
- [x] Write the English kickoff, exact commit message, workflow and navigation. Map first work to the approved owner/reviewer rows; explain data is local and generated binaries are rebuilt rather than fetched from Git.
- [x] Run the full pytest command, configured mypy, secret scanner and document/index/receipt checks. Preserve actual output; no new product tests or provider calls are required for documentation/Git configuration.
- [ ] Stage an explicit reviewed scope, verify Git blobs against working bytes and receipt-bound expectations, confirm raw/Parquet/index/.env exclusions, and inspect the complete staged diff. Commit using the exact body file after a fresh zero-leak check.
- [ ] Push `HEAD:main` without force; compare remote/local IDs. Publish the short repository description. Record actual URLs/results and finish the report/index without falsely changing milestone gates.

## Publication and evidence ordering

The kickoff narrative is prepared and verified before the remote mutation. Commit/push receipt metadata may require a small follow-up documentation commit so its evidence is itself published. Every commit gets the mandated secret scan. A receipt names the commit it proves, rather than attempting to embed a commit's own hash into itself.
