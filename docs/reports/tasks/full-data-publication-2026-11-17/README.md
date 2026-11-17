# Full historical data and runtime artifact publication

- Status: IN_PROGRESS
- Execution date: 2026-11-17 (Asia/Saigon)
- Requirement source: the owner's explicit instruction to push all data, superseding the earlier local-only publication choice.
- Baseline: private `khuonglaptri3/TikTok_AI_Engine_`, `main` at `2e927154abacebf747a08a87b02ec705bd94558c`.
- Specification: [spec.md](superpowers/spec.md)
- Execution plan: [plan.md](superpowers/plan.md)

## Conclusion

The upload inventory contains **37,849 files / 1,593,622,816 logical bytes** across `data/` and the available BM25 runtime artifacts. This includes all 37,840 pinned historical files plus existing manifests, evaluation queries, Gold Parquet and four BM25 files. All are being published directly through ordinary Git in the existing private repository. No Git LFS purchase, paid storage or separate data host is used.

The largest file is `data/interim/final_raw_videos.csv` at 75,850,189 bytes. Original local data are not edited, moved or deleted; scoped `-text` attributes preserve exact bytes. `.env` and caches remain excluded. Completion depends on the exact staged blob/checksum inventory and remote verification below.

## Work performed and clone behavior

- Removed only the data/index/enrichment Gitignore exclusions under the owner's explicit authorization.
- Added byte-preservation rules for the full data/runtime directories, retaining the existing evidence/source rules.
- Inventoried every regular file; the upload has no symlink or secret-file candidate. A dedicated credential-pattern and SHA256/Git blob scan covers actual candidate contents, including data skipped by the ordinary source-only scanner.
- Completed that scan for all 37,849 files in 214.977 seconds: zero credential findings, and all 37,840 historical files match both their archive-derived SHA256 and pinned Git blob identity. Eight read workers changed no original data.
- Updated current setup/kickoff guidance. The intended completed clone supplies default Gold/BM25 files, so the full project suite/demo no longer requires a separate local data transfer. Existing snapshot IDs remain immutable; independent rebuilds still need new output IDs.
- Kept dated prior publication receipts as history. Their original raw-data exclusion was correct for those commits; this task explicitly supersedes that decision. The 94/94 effort allocation and G0–G6 NOT_RUN remain unchanged.

## Outputs and verification

| File | Purpose |
| --- | --- |
| [Workflow](evidence/workflow.md) | Authorization, skills, actual commands/results and publication scope. |
| [Upload inventory](evidence/upload-inventory.json) | Complete candidate path/size list and largest files. |
| [Upload verifier](evidence/verify-data-upload.py) | Credential-safe hashing, pinned historical comparisons and exact staged tree verification. |
| [Per-file hashes](evidence/upload-file-hashes.json) | Every actual upload file's size, SHA256 and Git blob ID; 37,840 historical matches and zero credential-pattern findings. |
| [Hash/secret scan log](evidence/data-hash-and-secret-scan.log) | Actual progress and successful complete scan. |
| [Fresh full suite](evidence/pytest-pre-upload.log) | PASS: 57 project tests in 71.34 seconds. |
| [Commit description](evidence/commit-message.txt) | Exact data-publication subject/body. |
| [Staged verification](evidence/staged-data-verification.json) | Complete Git index path/blob equality against the scanned upload inventory, generated after staging. |
| [Source secret scanner](evidence/secrets-pre-commit.log) | Mandatory source/evidence scan in addition to the full data-content credential scan. |
| [Document verification](evidence/document-verification.json) | Canonical layout and current navigation checks. |

Content-hash/credential checks and the full suite pass. Staged verification, mandatory pre-commit source scanner and remote publication results are recorded as they finish. A prepared inventory alone is not upload success.

## Open issues and handoff

Publication remains **IN_PROGRESS** until remote/local commit equality and complete remote path/blob coverage are verified. Clone supplies the data once the upload completes; source rights and later scientific/acquisition/hosting gates are not silently reclassified by this private data transfer.
