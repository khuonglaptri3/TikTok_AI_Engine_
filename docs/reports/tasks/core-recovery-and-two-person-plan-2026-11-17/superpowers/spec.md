# Core recovery and balanced two-person delivery specification

- Created: 2026-11-17 (Asia/Saigon), before implementation.
- Authorization: the owner accepted the audit's recovery-first sequence and said to execute it and rewrite the plan for the owner and Nguyên. The owner then explicitly required equal allocation and instructed continuation after reconnection.
- Team: Trần Đình Khương and Nguyễn Việt Nguyên ([NguyenVietNguyen2612](https://github.com/NguyenVietNguyen2612)). Profile identity was checked; no skill level or availability is inferred from the profile.
- Baseline: `cdbc6ed9ccad11db437aa66c68638cf018701fe5`, plus the existing uncommitted audit bundle. Preserve that audit and unrelated work.
- Requirement source: [completed audit](../../docs-refactor-feasibility-2026-11-17/README.md).

## Approved approach and boundaries

Implement the historical CPU demonstration first: recover source assets, fix proven data-integrity/validation/metric/packaging defects, regenerate verified artifacts, and run the existing API/Gradio flow. Plan later acquisition, human annotation, and multimodal work as gated future tasks; do not pretend new labels, live crawl results, or paid deployment exist. The owner already selected this sequence; no repeated implementation approval is required.

Options considered in the prior audit were a narrow reproducible historical core and immediate expansion of the entire multimodal stack. The owner authorized the recovery-first core. Existing Python/FastAPI/Gradio/BM25 components are retained; new infrastructure is conditional on measured need.

## Required outcomes

1. Recover upstream historical data from pinned revision `f142e5656a220f94f8024de168b0832754b3bd9e` without TikTok recrawling. Never overwrite existing original files with different content. Preserve source provenance and verification inventories; avoid importing legacy code/secrets into active source.
2. Reject snapshot output collisions, publish complete snapshots safely, preserve all base multimodal tables across new batches/replay, and permit explicit same-video transcript/comment enrichment without duplicating video identity.
3. Reject empty/uncited/mistimed script validation; never fabricate a citation association. Keep creative drafts qualified and replace unsupported firsthand factual claims in offline templates. No claim-level entailment accuracy is promised by structural checks.
4. Correct standard Recall@10, preserve the old benchmark as historical evidence, produce a new correctly defined result with corpus/index/query provenance, and distinguish weak-label regression from independent relevance evaluation.
5. Make base/demo dependencies and container source packaging consistent; verify real-corpus offline API/Gradio behavior on CPU, with zero live LLM spend.
6. Rewrite the active milestone plan for two equal contributors, with balanced estimated effort, primary owner and peer reviewer, parallel work, dependencies, concrete acceptance, truthful statuses, a near-term core and conditional future multimodal gates. Equal points/days are estimates, not measured equal hours. Do not contact or invite Nguyên.
7. Align AGENTS scope, resources, refactor implementation guidance, targeted README setup instructions, reports and navigation with the two-person plan. Preserve the overall root overview and historical reports; archive superseded plan text in evidence.

## Acceptance and verification

- Meaningful regressions are written and observed failing before their production fixes. Record RED/GREEN commands and outputs.
- Source restoration and generated Gold/index artifacts are checked for completeness/rows/schema/hashes; all original files remain unmodified.
- Run the entire project pytest suite, project-configured mypy, secret scanner, package/image-source build check, and ASGI demo smoke; report exact results and environment limitations.
- New snapshots retain keyed data across A, B, replay, empty batch and enrichment, reject existing outputs, and leave the base byte-identical.
- Correct metric examples are hand-checkable. New frozen results cannot claim human ground truth or current trends.
- The plan has a verifiable 50/50 estimated allocation, visible reviews/integration work for both people, all old gate claims reconciled, and no future task marked done without evidence.
- Final independent review and bundle/link/hash checks precede completion. No commit, push, collaborator invitation, live synthesis, or hosting deployment is required.
