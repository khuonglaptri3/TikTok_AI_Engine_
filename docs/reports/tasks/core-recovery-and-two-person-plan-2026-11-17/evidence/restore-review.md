# Historical input recovery evidence

- Execution date: 2026-11-17 (Asia/Saigon).
- Status: COMPLETE for pinned input restoration and exhaustive byte-preservation verification. Gold/index/API acceptance is recorded separately by the owning recovery task.
- Source: `TrggTin/21KHDL-TikTok-Analytics`, pinned revision `f142e5656a220f94f8024de168b0832754b3bd9e`.
- Authorization: the owner's approved recovery-first scope, delegated by the primary implementer under the task specification and plan. This assistance changes historical data and task evidence only.

## Scope and mapping

The untruncated GitHub recursive tree contains 37,837 blobs under `data/`, totaling 1,475,677,482 logical bytes. Every one is selected for byte-preserving restoration to the same repository-relative path. Three legacy app tables add 28,607,219 bytes:

| Upstream source | Local destination |
| --- | --- |
| `src/app/trend_analysis/data/final_location_food_data.parquet` | `data/legacy_app_data/trend_analysis/final_location_food_data.parquet` |
| `src/app/video_analysis/data/content_analyse.csv` | `data/legacy_app_data/video_analysis/content_analyse.csv` |
| `src/app/video_analysis/data/preprocessed_video.parquet` | `data/legacy_app_data/video_analysis/preprocessed_video.parquet` |

The combined selected inventory is 37,840 files and 1,504,284,701 logical bytes. This inclusion rule matches the documented historical file count numerically. It does not independently verify the owner's original local file inventory or establish that every original historical file was represented upstream.

The builder requires the mapped trend-analysis table at the stated local path. The two video-analysis tables are preserved as legacy data assets without importing the associated application code.

## Integrity and preservation method

1. Fetch the recursive tree for the pinned revision, require `truncated: false`, and retain each selected source path, byte size and expected Git blob SHA1 in [restore-source-tree.json](restore-source-tree.json).
2. Cache the codeload ZIP outside the repository. Only selected data entries can be written to the workspace; no downloaded upstream Python, notebooks or configuration code is executed.
3. Validate each destination against the resolved local `data/` root, reject traversal or case-insensitive collisions, reject selected symlinks, and check archive-entry sizes against the tree.
4. For every selected source, calculate the Git blob SHA1 using `blob <size>\0<payload>` and compare it with the pinned tree. Compute the source SHA256, create a missing local file exclusively, and reread the destination for both Git blob SHA1 and SHA256 verification. Existing destinations with different bytes cause a failure and are never overwritten.
5. Hash the preexisting local data files before and after recovery. Keep the archive checksum, source-to-destination mapping and full installed input manifest in task evidence.

Expected per-file SHA256 values are computed from archive bytes after their Git blob SHA1 matches the pinned tree. They are not represented as an independently published upstream SHA256 manifest. ZIP CRC checks occur when each selected entry is read.

## Observed final result

The resumed restoration finished on 2026-11-17 at 05:46:23 UTC (12:46:23 Asia/Saigon): **37,840 selected files / 1,504,284,701 bytes**. The resumed run created 32,319 missing selected files and preserved 5,521 already identical selected files. Its pre-resume preservation inventory also includes the original manifest and frozen query file; no existing differing destination was overwritten. The original two-file pre-restoration inventory remains intact in `restore-existing-before.json`; a separate resume inventory records the interrupted installation state.

An independent exhaustive reread finished at 05:55:45 UTC, taking 557.457 seconds: **PASS** for every selected file's size, pinned Git blob SHA1 and archive-derived SHA256. All 37,840 selected files are gitignored. Both original pre-restoration files remained byte-identical, and the cleaned-video CSV also matched the independently recorded prior-audit SHA256. This verifies the selected pinned inventory and preservation of actual preexisting files; it does not recover an unavailable owner-original inventory by assertion.

## Actual workflow provenance

The delegated assistant read these installed skill sources:

- `C:/Users/lanph/.codex/plugins/cache/openai-curated-remote/superpowers/7.0.1/skills/using-superpowers/SKILL.md`: read; its dispatched-subagent exemption applies.
- `C:/Users/lanph/.codex/plugins/cache/openai-curated-remote/superpowers/7.0.1/skills/executing-plans/SKILL.md`: read to align with the authorized parent plan. The primary implementer owns inline production implementation, TDD, overall ledger, integration and final review. This isolated data-restoration delegation does not claim to execute those production-code phases.
- `C:/Users/lanph/.codex/plugins/cache/openai-curated-remote/superpowers/7.0.1/skills/verification-before-completion/SKILL.md`: read and applied to the data-integrity completion claim.

The assistant also read repository `AGENTS.md`, the task [specification](../superpowers/spec.md), the task [plan](../superpowers/plan.md), and the prior audit's upstream data review and metadata. Both canonical planning files already existed before this restoration began. This record describes actual present work and makes no retroactive workflow claim about the earlier corpus.

Ruling: restore historical inputs directly into the original workspace while production edits proceed in the primary implementer's isolated worktree. The task plan and delegation explicitly authorize that separation, and heavy data are gitignored. A second worktree would duplicate or hide these local inputs rather than isolate code changes.

Initial direct Python network attempts failed once on DNS resolution and once on TCP connection timeout. The GitHub recursive-tree cURL request succeeded after two connection-timeout retries. The archive cURL request then began transferring successfully. No proxy environment variables were configured. These transient transport failures did not change local historical data.

## Evidence

| File | Purpose |
| --- | --- |
| [restore-upstream-data.py](restore-upstream-data.py) | Narrow restoration helper; not product code |
| [restore-source-tree.json](restore-source-tree.json) | Pinned Git source inventory and destination mapping |
| [restore-progress.jsonl](restore-progress.jsonl) | Timestamped progress events that survive reconnection |
| [restore-summary.json](restore-summary.json) | Actual completion counts, groups and preservation checks |
| [restore-input-manifest.json](restore-input-manifest.json) | Every selected source/destination path, size, Git blob SHA1 and SHA256 |
| [restore-existing-before.json](restore-existing-before.json) | Original two-file pre-restoration preservation baseline |
| [restore-resume-existing-before.json](restore-resume-existing-before.json) | Separate pre-resume inventory; does not replace the original baseline |
| [restore-verification.json](restore-verification.json) | Independent exhaustive verification, Gitignore and original-file results |
| [restore-final-verification.log](restore-final-verification.log) | Fresh verification progress and observed summary |

## Limits

No historical TikTok recrawling, provider operation, paid spend, Gold or index generation, upstream code execution, commit, push or publication is part of this recovery. Source availability and successful byte restoration do not settle missing licenses, collection permissions, annotation quality, waveform coverage or viewer-comment label gaps identified by the prior audit.
