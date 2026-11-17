# Full data publication plan

> Execute the owner's explicit upload request natively. No extra permission or branch-choice gate is needed.

**Goal:** Make a normal clone contain the preserved dataset and runnable Gold/BM25 artifacts.

**Spec:** [spec.md](spec.md)

**Approach:** Remove only the relevant Gitignore exclusions, preserve all data/artifact bytes through scoped attributes, and stage actual files without modifying originals. Use the pinned restoration manifest plus independent Git tree/remote verification as acceptance evidence.

- [x] Inventory every current data/index/enrichment file and maximum size; reject unsafe/symlink or credential-bearing candidates without exposing values.
- [x] Add scoped byte-preservation attributes and permit the requested directories in Git. Keep `.env` and caches excluded.
- [ ] Stage all inventoried paths, verify Git blob IDs/bytes and pinned historical checksums, and check generated corpus/index receipts. Capture actual counts and logical bytes.
- [ ] Run the full project pytest command and mandatory secret scanner. Update current README/kickoff navigation and this task's report/provenance to reflect the new clone behavior.
- [ ] Commit and push normally to private `origin/main`, verify remote commit/tree completeness and update final results. A small documentation-only follow-up may publish the receipt of the named data commit without self-referencing its own hash.

## Boundaries

This is data publication, not a new acquisition or AI feature. Existing independent code review remains the source-change review; no new product code or scientific gate is claimed. Earlier local-only reports remain dated records, with this new publication explicitly superseding that choice.
