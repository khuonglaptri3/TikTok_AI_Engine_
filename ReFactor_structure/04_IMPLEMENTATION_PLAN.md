# Recovery-first two-person execution companion

> **For agentic workers:** Use `superpowers:executing-plans` or the explicitly selected reviewed execution method. Read the task's canonical specification/plan before implementation. Preserve existing authorization; no new approval is needed for already authorized routine recovery/fixes.

- Revision: 2026-11-17 (Asia/Saigon).
- Authoritative scope, allocation and gates: [active milestone plan](../docs/planning/TikTok_AI_Engine_Milestone.md).
- Contributors: Trần Đình Khương (K) and Nguyễn Việt Nguyên (N); 94 estimated points / 47 person-days each, including reciprocal review/integration/gates. No skill tiers are inferred from the public profile.
- Current activity: [authorized recovery task](../docs/reports/tasks/core-recovery-and-two-person-plan-2026-11-17/README.md), with its [specification](../docs/reports/tasks/core-recovery-and-two-person-plan-2026-11-17/superpowers/spec.md) and [implementation plan](../docs/reports/tasks/core-recovery-and-two-person-plan-2026-11-17/superpowers/plan.md).

**Goal:** Reproduce and correct the historical CPU analytics/BM25/script/API/Gradio core first, then decide bounded fresh-data and multimodal experiments from observed evidence.

**Architecture:** Immutable provenance-bound Gold snapshots feed typed domain packages, reproducible CLI pipelines, FastAPI and one ASGI-mounted Gradio `/demo/`. Local BM25 and offline drafting are the baseline. Audio, dense indexes, live providers and public hosting are conditional capabilities with their own acceptance evidence.

**Tech stack:** Python 3.11+, Pydantic v2, pandas/PyArrow/SciPy, FastAPI/Gradio, pytest and project-configured mypy; optional crawling/ASR/dense dependencies only when used.

**Spec:** The current recovery specification governs present fixes. Each later task creates its own `docs/reports/milestones/<ID>/superpowers/spec.md` and `plan.md` at task start. Legacy [architecture text](03_AI_ENGINEER_ARCHITECTURE_SPEC.md) remains historical design context where it disagrees with the active plan.

## Global constraints

- Preserve original local raw/interim/legacy bytes; no historical TikTok recrawl. Distinguish pinned upstream inventory from the unverified earlier owner-copy scope.
- Use a new output ID, reject collisions, validate complete table/schema/hash sets before publication and retain parent/input/code lineage. Never rewrite a published base snapshot.
- USD 0 provider/GPU/hosting spend; offline default, <= 2 optional free-tier LLM calls per turn, actual project-aware sliding-window rate limit, bounded typed failures and no paid fallback.
- Never replace live outputs with authored fixtures or call a source ID proof of claim support. Present historical descriptive summaries, source-supported facts and creative directions accurately.
- Preserve prior reports/raw evidence. Store each started task's single current report with sibling `evidence/` and `superpowers/{spec.md,plan.md}`; no empty future bundles or backdated provenance.
- This companion does not claim any unchecked item below is implemented or accepted. Existing code and the prior checked plan are historical inputs, not a reason to skip current verification.

## Review focus

1. Repeated ingestion, replay, empty batches and same-video enrichment must retain every base multimodal table and leave originals unchanged.
2. Empty/uncited/mistimed drafts, no-answer requests and invalid citations must fail or abstain; arbitrary evidence associations and unsupported firsthand assertions must not pass.
3. Conventional Recall@10, independent query judgments and exact corpus/index/query receipts must remain distinct from weak-label frozen regression.
4. Fresh capture requires a real invoked worker and transcript-before-search dependency; cutoff helpers and synthetic fixture success are insufficient.
5. Unknown aspects/intent, estimated timestamp provenance and resource/provider/host limits must remain visible; missing data cannot become neutral sentiment or hidden-intent truth.

## Execution waves

The authoritative task table defines exact K/N effort and dependencies. W1 starts after verified checkouts and actual capacity agreement; W1–W12+ are indicative windows. The complete research scope is not an eight-week commitment. Every owner submits evidence for the other contributor's review and reproduction; release integration waits for that review.

### Wave 1 — recover inputs and foundation (M0/M1; indicative W1–W2)

**Owners/review:** K leads M0.1/M0.3/M1.2, N leads M0.2/M1.1; gate owners/reviewers are in the active plan.

**Files and interfaces:** `packages/common/`, `packages/data_contracts/`, `packages/taxonomy/`, `pipelines/build_gold_corpus/`, `pyproject.toml`, `infra/docker/Dockerfile.api`, `apps/api/`, `apps/demo/`; source/input inventories and a new verified snapshot are the outputs consumed by M2.

- [ ] Inventory every pre-existing original by relative path/size/SHA256; recover missing permitted assets from pinned revision `f142e5656a220f94f8024de168b0832754b3bd9e` without overwriting different content. Record missing/failed/source-license evidence.
- [ ] Reproduce the snapshot collision/publication and packaging defects with meaningful failing checks before production changes. Revalidate contract bounds, taxonomy unknowns and nonfinite-value handling.
- [ ] Implement minimal fixes; build a new immutable Gold output and verify complete tables/schema/keys/counts/hashes, original-byte preservation and per-field lineage. Do not force unverified old counts to match.
- [ ] Reproduce clean install/import, source/package build and actual ASGI API/Gradio behavior with no provider call. Record whether Docker-engine execution is available separately.
- [ ] Review the 120-record taxonomy/lineage sample, publish G0/G1 evidence and decisions under the actual task bundles. Link the existing M0.1 historical report rather than pretending it was newly executed.

### Wave 2 — correct and accept the historical core (M2; indicative W2–W4)

**Owners/review:** N leads M2.1/M2.3, K leads M2.2; other contributor reviews each.

**Files and interfaces:** `packages/analytics/`, `packages/retrieval/`, `packages/llm/guardrails/verifier.py`, `packages/script_engine/`, `pipelines/benchmark_retrieval/`, `tests/unit/`, `tests/eval/`, `data/evaluation/` and versioned evaluation receipts; consumes the verified M1 snapshot and produces the G2 accepted local demonstration.

- [ ] Observe hand-checkable metric regressions fail; correct Recall@10's denominator to all relevant documents and preserve the old artifact as historical evidence. Keep rankings/qrels/query/index/corpus/code provenance.
- [ ] Observe empty/uncited/mistimed/no-evidence script cases fail before guardrail fixes; remove arbitrary fallback citations and unsupported firsthand claims. Test supported ordinary drafts and no-answer behavior after the fixes.
- [ ] Independently author/freeze 40 queries (20 development / 20 locked test), blind pooled relevance judgments, adjudicate disagreement and record missing judgments. Each person authors half and both contribute review.
- [ ] Measure analytics/BM25 current latency with hardware, 100 warm requests and concurrency 1; report thresholds and failure honestly. Qualify historical cohorts and support counts rather than claiming causal optimization/current trends.
- [ ] Double-review 30 scripts for factual source support and creative-direction separation; structural citation/timeline checks remain separate from entailment evidence.
- [ ] Run full pytest, configured mypy, secret scanner, clean package/source check and recovered-corpus API/demo smoke. Record exact outcomes and G2 acceptance; a passing historical core closes no fresh-data/trust gate automatically.

The current recovery task can supply dated fixes/rebuild evidence to these tasks. Independent human judgments and per-task acceptance remain future work unless actually performed; automated synthetic tests do not replace them.

### Wave 3 — safe ingest and one real vertical slice (M3; indicative W5–W6)

**Owners/review:** N leads M3.1/M3.3, K leads M3.2; M3.3 has equal pilot/integration effort. Repairs may start early; real pilot acceptance waits for G2 and safe ingest.

**Files and interfaces:** `pipelines/ingest_incremental_to_gold/`, `pipelines/crawl_incremental/`, `packages/data_contracts/multimodal.py`, `tests/unit/test_incremental_absa_seeding.py` and new focused tests; consumes base snapshot/historical-ID set and produces a new snapshot with available modal tables plus real capture receipts.

- [ ] First observe A/B/replay/empty/enrichment retention checks fail; fix keyed merge/deduplication across video, voice, comment and ABSA tables and safe new-output publication. Verify unchanged base bytes.
- [ ] Implement an invoked live worker with bounded discovery/retries/resume and per-item success/failure provenance; keep fixture mode explicitly labeled. Test as-of 120-day cutoff and historical-ID exclusion.
- [ ] Pilot at most 5 creators / 50 candidates / 30 successes / 60 audio minutes / 1,000 comments / one two-hour capture session. No successful yield is guaranteed.
- [ ] Transcribe at most 10 videos / 20 audio minutes before asserting searchability. Verify at least 5 real fresh transcribed videos resolve through search, or record BLOCKED/insufficient yield without authored replacements.
- [ ] Measure capture/audio/comment coverage, wall time, disk/RAM, ASR real-time factor and annotation minutes; G3 decides any further bounded workload. Do not expand collection automatically.

### Wave 4 — independently evaluate audio and diagnostics (M4/M5; indicative W6–W9)

**Owners/review:** K leads M4.1/M5.2, N leads M4.2/M5.1; independent reference/annotation/review work is budgeted for both.

**Files and interfaces:** audio adapters/pipelines when begun, `packages/data_contracts/multimodal.py`, `packages/seeding/`, `packages/absa/`, corresponding API/presentation tests and task-local annotation/evaluation evidence; consumes real pilot audio/comments and produces qualified timestamp/observable-pattern/aspect evidence.

- [ ] Validate `0 <= start < end <= duration` and provenance before indexing. Evaluate <= 60 audio minutes with <= 20 reference minutes / >= 50 utterances; record CER/WER, boundary error, real-time factor and peak RAM/disk. Keep interpolated historical offsets visibly estimated.
- [ ] Replace hidden-intent sponsorship claims with observed disclosure/commerce flags and qualified promotional-language indicators. Review the bounded 100-text sample; hidden-intent supervised training stays deferred without verified labels.
- [ ] Double-annotate <= 300 real comments (minimum 150 for gate), use thread/video holdouts and evaluate observable duplicate/contact/noise classes. Do not call repeated praise proof of bots or paid seeding.
- [ ] Double-annotate <= 200 ABSA text units across >= 10 videos (minimum 120), freeze video-disjoint partitions and retain source IDs/spans/aspect support. Missing aspect is unknown; unsupported comparisons abstain.
- [ ] Report precision/recall/F1, uncertainty, agreement, before/after-filter discrepancies and threshold sensitivity against the exact plan criteria; G4/G5 accept only supported features and visibly limit unaccepted ones.

### Wave 5 — measure optional complexity and release (M6; indicative W9–W12+)

**Owners/review:** N leads M6.1/M6.G, K leads M6.2; other person reviews/integrates each.

**Files and interfaces:** `packages/retrieval/dense/`, `packages/retrieval/fusion/`, indexing CLI if a populated pilot is justified, typed Q&A contracts/routes and `apps/demo/`; final accepted backend may remain BM25. Canonical M6 reports contain release measurements and decisions.

- [ ] Pilot one CPU embedding model on <= 5,000 records with corpus/filter/query parity; compare populated BM25/dense/RRF runs on frozen independent queries. Record quality differences/uncertainty, build/index/model cost and latency/RAM. Retain the simpler baseline if extra complexity is unjustified.
- [ ] Integrate accepted evidence into one API/demo and double-review 30 held-out questions including >= 10 insufficient-evidence cases. Verify source resolution, fact support/coverage, temporal provenance, no fabricated offsets and bounded abstention.
- [ ] Measure total/per-stage offline latency separately from artifact startup or optional provider time. Run all current project checks and validate reports, links, hashes, unresolved issues and task/index status consistency.
- [ ] Assess public hosting separately against current official genuinely-free eligibility, no-billing/overage/upgrade path, rights/privacy, measured RAM/disk/cold-start fit and sleep/quota limits. No candidate accepted means public hosting BLOCKED; local release remains valid within its accepted scope.
- [ ] Record G6's actual accepted feature set and exclusions. Provider eligibility/quota is checked immediately before any optional live free-tier run; no publication/spend is authorized by this companion alone.

## Verification and status discipline

Use test-driven development for substantive behavior fixes: write meaningful regression, observe RED, implement minimal fix, observe GREEN and run appropriate broader checks. Documentation-only edits use direct arithmetic/link/layout/source-preservation checks; no mirrored implementation tests are needed. Apply `verification-before-completion` before any success claim. No commit/push/deployment is required for the current recovery task; follow its explicit boundaries.

The old fully checked refactor plan is preserved byte-for-byte as [historical source](../docs/reports/tasks/core-recovery-and-two-person-plan-2026-11-17/evidence/prior-refactor-implementation-plan.md), with [hashes](../docs/reports/tasks/core-recovery-and-two-person-plan-2026-11-17/evidence/prior-plan-preservation.json). Its prior counts, dense/neural completion language and checks are not new acceptance evidence. The active milestone plan controls IDs, owners/reviewers, exact effort, bounded samples, prospective thresholds and truthful statuses.
