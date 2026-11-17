# Full data publication workflow

## Authorization and process

On 2026-11-17 the owner explicitly instructed uploading all data after clarification that the first code publication excluded it. This task changes that publication decision; no repeated approval is requested. The existing private repository and normal `main` push are the destination. Local originals, secret files and private visibility remain protected.

Read/applied Superpowers 7.0.1 from `C:/Users/lanph/.codex/plugins/cache/openai-curated-remote/superpowers/7.0.1/skills/`: `using-superpowers/SKILL.md`, `writing-plans/SKILL.md`, and `verification-before-completion/SKILL.md`; the previously read finishing workflow applies to the authorized normal push. Canonical spec/plan were created before changing Gitignore/attributes or staging data. No new product feature or autonomous subagent work is involved.

## Observed baseline and decision

- Local/remote main start at `2e927154abacebf747a08a87b02ec705bd94558c`.
- The pinned source inventory contains 37,840 historical files / 1,504,284,701 bytes. Its largest file is `data/interim/final_raw_videos.csv`, 75,850,189 bytes; the next largest are 67,215,794 and 67,042,750 bytes. Runtime artifact sizes are inventoried next.
- Ruling: use normal Git with explicit `-text` for data/runtime artifacts; no Git LFS or external host is required for the observed historical sizes. No paid feature or quota purchase is authorized or used. If any actual runtime file exceeds the regular Git server limit, preserve it and report the specific limitation rather than dropping it.
- The previous local-only choice is superseded by this direct owner instruction. Dated earlier reports/commit receipts retain their original meaning; current setup guidance is updated for the new data-containing clone.

## Execution and verification

Actual file inventory, credential scan, staging/hash checks, tests and remote publication results are recorded below as execution proceeds.

- Actual inventory: 37,849 regular files / 1,593,622,816 bytes, maximum 75,850,189 bytes; no candidate exceeds 100 MiB. This includes all current data files and the four existing BM25 artifacts. No enrichment directory was present to omit.
- Gitignore now permits the explicitly requested data/runtime paths; `.env`, tool caches and unrelated legacy application archives remain ignored. `data/**`, `artifacts/indexes/**` and `artifacts/enrichment/**` receive `-text` byte preservation. No original content is edited.
- The initial sequential read-only checksum scan was intentionally stopped after 15,000 files to reduce filesystem latency; its progress is retained in [data-scan-sequential-interrupted.log](data-scan-sequential-interrupted.log). No data file was written or staged by that interrupted scan. The restarted scan uses eight independent read workers, deterministic output order and the same pinned SHA256/blob/credential checks for every file; no subagents were spawned.
- Fresh full pytest passed 57 tests in 71.34 seconds ([pytest-pre-upload.log](pytest-pre-upload.log)). No application logic changed for this upload. The current kickoff/Quickstart now explain data-containing clones and preserve the immutable-snapshot rebuild rule.
- The restarted complete scan passed in 214.977 seconds: all 37,849 candidates hashed and credential-scanned, no findings; all 37,840 pinned historical entries matched SHA256 and original Git blob SHA1. [upload-file-hashes.json](upload-file-hashes.json) preserves actual hashes/bytes. Only after this PASS did Git staging start, using the exact inventoried pathspec and temporary Windows filesystem-cache option; global Git settings remain unchanged.
