# Team kickoff — verified CPU baseline and first reciprocal tasks

- Status: IN_PROGRESS
- Execution date: 2026-11-17 (Asia/Saigon)
- Requirement source: owner request to push the completed recovery and write a description so the team can begin.
- Repository: private `khuonglaptri3/TikTok_AI_Engine_`, target branch `main`; publication receipt follows verification.
- Specification: [spec.md](superpowers/spec.md)
- Execution plan: [plan.md](superpowers/plan.md)

## Conclusion

Start from the recovered historical CPU core: descriptive niche analytics, Vietnamese BM25 evidence retrieval, qualified script drafts, typed AI APIs and one Gradio demo at `/demo/`. The previous [recovery report](../core-recovery-and-two-person-plan-2026-11-17/README.md) records **57 passing tests**, verified 37,840-file input restoration, new Gold/BM25 artifacts and zero provider calls. This publication reruns checks before committing; its actual results and remote commit are recorded below.

**Trần Đình Khương and Nguyễn Việt Nguyên share 94 estimated effort points each**, including implementation, evaluation, integration and reciprocal review. Use the [active milestone plan](../../../planning/TikTok_AI_Engine_Milestone.md) as the work allocation and acceptance authority. Recovery completion does not pass G0–G6; independent relevance/claim evaluation, fresh acquisition, audio and calibrated trust diagnostics remain future work.

## Project description

TikTok_AI_Engine_ is a Vietnamese food-and-beverage AI project for creators and viewers. It turns preserved historical video metadata and transcripts into descriptive niche benchmarks, retrieves attributable examples, and produces clearly qualified script drafts through local CPU APIs and a lightweight Gradio interface. Comment-pattern and aspect-sentiment tools are heuristic demonstrations pending independent labels. The two-person roadmap prioritizes reproducibility and human evaluation before expanding to bounded fresh data and multimodal experiments.

The repository About description is: “Vietnamese F&B TikTok AI: verified historical analytics, BM25 retrieval, cited script drafts, and a CPU Gradio demo. Two-person roadmap for evaluated multimodal diagnostics.”

## Start here

1. Read this kickoff, the [recovery conclusions](../core-recovery-and-two-person-plan-2026-11-17/README.md), [work allocation](../../../planning/TikTok_AI_Engine_Milestone.md) and [resource constraints](../../../planning/TikTok_AI_Engine_Resources_and_Deployment.md).
2. Clone/pull `main`, install Python 3.11+ (the recorded environment uses 3.12), and verify the source-only baseline. Python/venv commands below use Windows PowerShell; activate the equivalent environment on other systems.

```powershell
git clone https://github.com/khuonglaptri3/TikTok_AI_Engine_.git
cd TikTok_AI_Engine_
py -3.12 -m venv .venv
.\.venv\Scripts\Activate.ps1
python -m pip install '.[dev]'
if (-not (Test-Path -LiteralPath '.env')) { Copy-Item -LiteralPath '.env.example' -Destination '.env' }
python scripts/check_secrets.py
python -m mypy packages apps pipelines
python -m pytest tests/unit/test_snapshot_continuity.py tests/unit/test_script_guardrails.py tests/unit/test_offline_draft.py tests/unit/test_retrieval_metrics.py tests/eval/test_retrieval_benchmark.py
```

The focused command uses synthetic temporary fixtures and committed receipts; it previously passed 42 tests without the heavy historical dataset. Record the result from each contributor's machine. No Gemini key is needed for these checks or offline drafting. The repository remains private, so each contributor needs repository access managed by the owner; this task sends no invitations.

3. For the complete data-backed suite/demo, arrange permitted local transfer of the preserved input tree, matching Gold Parquet and `bm25-v2` index from the verified owner copy. Verify against the [input inventory](../core-recovery-and-two-person-plan-2026-11-17/evidence/restore-input-manifest.json), committed Gold manifest and benchmark receipt. The dataset, Parquet, index binaries and `.env` are intentionally outside Git. Do not replace an existing differing original. Never re-crawl historical TikTok videos.

```powershell
# After permitted local artifact transfer into the recorded default paths:
python -c "from pathlib import Path; from packages.analytics import load_verified_corpus; m, c, v = load_verified_corpus(Path('data/corpus/20261117_recovered_v1')); print(m.snapshot_id, len(c), len(v))"
python scripts/dev.py test
python scripts/dev.py run-demo
```

Expected recorded default counts are 264 creators and 70,996 videos, with 21,748 indexed transcripts. Open `http://127.0.0.1:8000/demo/`. Choose `offline_grounded` for zero-provider script generation. The complete suite previously passed 57 tests on the owner machine; a new clone without local assets cannot reproduce those data-backed tests yet.

For independent rebuilding, use the pipeline CLIs with **new snapshot/index/benchmark output IDs** and matching API environment settings. A committed manifest already occupies the recorded snapshot directory, and the immutable builder rejects existing destinations. Several data-backed unit checks currently use the default `AppSettings()` paths, so arbitrary environment overrides do not redirect every test. Restore the matching default artifacts for an exact full-suite reproduction; do not delete the committed manifest or rewrite a trusted snapshot to force a build. Keep new build receipts in the owning task. Historical recovery helpers write their own evidence directory and must not be rerun in place to overwrite archived records.

## First working cycle

| Contributor | First delivery | Reciprocal check / concrete output |
| --- | --- | --- |
| Nguyễn Việt Nguyên | Lead M0.2 contract/settings boundary revalidation: malformed/missing/unknown values, error payloads, finite timings in `ms`. Start with controlled fixtures. | Khương reviews the change and reproduces its key tests. Nguyên publishes an actual M0.2 spec/plan, tests, command results and unresolved boundaries when that task begins. |
| Trần Đình Khương | Reconcile M0.1 recovery provenance/rights gaps and M0.3 source/API/demo reproduction using the completed recovery evidence. Prepare a reviewable reproduction checklist rather than rerunning historical collection. | Nguyên independently verifies the input/artifact receipts and installation/demo checks on his machine. Record actual results before requesting G0 review. |
| Both | Agree shared contract versions, immutable input IDs, actual availability and review windows. Use separate task branches; preserve the approved equal total allocation. | Review each other's output before integration; nobody closes their own gate alone. Report blockers with evidence instead of synthetic replacement results. |

Then follow the dependency graph: Nguyên leads the M1.1 taxonomy/lineage sample after the contract baseline; Khương leads M1.2 after its listed prerequisites. Both review the overlapping annotation sample. Prepare the independently authored relevance/claim pilots in M2; a keyword-derived benchmark or model agreement is not human ground truth. Do not begin the live M3.3 pilot before its G2/worker/ingestion prerequisites. Create each milestone's exact report bundle only when its work actually starts.

Each reviewable task provides its spec, checkable plan, implementation/data changes, actual commands/results, source/artifact hashes, limitations and the receiving next task. The [milestone report index](../../milestones/README.md) owns milestone status; this publication neither completes those tasks nor changes a gate.

## Work performed

- Prepared publication of the reviewed source fixes, completed audit/recovery reports and small reproducibility receipts.
- Reproduced Git clean-filter changes for 53 checksum-bound files, then added scoped `-text` attributes. The post-change probe preserves all 129 Git-bound checked files byte-for-byte. Some previously unchanged files will appear in the commit solely because their measured CRLF bytes are now retained.
- Added this kickoff, the exact commit description and navigation. Original recovery/audit evidence remains dated to the earlier execution; its whole-workspace hash snapshot is not silently rewritten to include these later navigation changes.

## Outputs and verification

| Output | Purpose / current result |
| --- | --- |
| [Workflow](evidence/workflow.md) | Actual authorization, skill usage, decisions and publication results. |
| [Commit description](evidence/commit-message.txt) | Exact subject/body supplied to Git. |
| [Byte-filter RED](evidence/byte-filter-before.json) / [GREEN](evidence/byte-filter-after.json) | Actual Git boundary reproduction and byte-preservation proof. |
| [Publication verifier](evidence/verify-publication.py) | Checks immutable prior bindings, actual staged blobs and raw/binary/secret exclusions. |
| [Fresh full suite](evidence/pytest-pre-push.log) | PASS: 57 tests in 65.74 seconds before publication. |
| [Fresh type check](evidence/mypy-pre-push.log) | PASS: configured mypy, 75 source files. |
| [Document checks](evidence/document-verification.json) | Canonical layout and local navigation checked before publication. |
| [Secret scan](evidence/secrets-pre-commit.log) | PASS: zero leaked keys; rerun before each commit. |
| [Staged-file inventory](evidence/staged-files.json) | Exact Git blob/working-byte comparison, sizes and exclusion checks; excludes its own self-reference. |
| [Source diff check](evidence/source-diff-check.log) | PASS with CRLF recognized and immutable raw evidence excluded from whitespace rewriting. |

The fresh suite, type check, secret scan, document checks and staged-byte checks pass. Remote commit and repository-description results are recorded as publication finishes. The final remote receipt, not preparation of this page, proves push success.

## Open issues and handoff

Raw data/runtime artifacts still require permitted local transfer or independent rebuilding; they are not supplied by a Git clone. Human relevance/claim judgments, source rights and future multimodal/hosting gates remain unresolved under their owning tasks. Estimated equal work does not establish actual capacity or equal hours.

Publication status remains **IN_PROGRESS** until the commit, normal remote push and description update are verified. The deliverable for beginning work is this linked kickoff plus the unchanged authoritative milestone allocation.
