# TikTok_AI_Engine_ — CPU resources and conditional deployment

- Revision date: 2026-11-17 (Asia/Saigon).
- Team: Trần Đình Khương and Nguyễn Việt Nguyên; equal estimated delivery, evaluation, integration and reciprocal review effort under the [authoritative milestone plan](TikTok_AI_Engine_Milestone.md).
- Accepted operating assumption: local CPU, offline, typed FastAPI and one ASGI-mounted Gradio `/demo/`. **No public host or live provider profile is accepted by this document.**
- Requirement and reporting rules: [AGENTS.md](../../AGENTS.md); [audit baseline](../reports/tasks/docs-refactor-feasibility-2026-11-17/README.md); [current recovery evidence](../reports/tasks/core-recovery-and-two-person-plan-2026-11-17/README.md).

## 1. Local development and shared reproducibility

Use Python 3.11+ compatible source and a declared dependency profile. Record the actual Python, package lock/resolution, OS, CPU model/core count, RAM, storage and code revision with every fresh verification. Each contributor must reproduce the other's key checks; the allocation already includes this work. Profile installation and commands against the current `pyproject.toml` and root [Quickstart](../../README.md), not old pass claims.

The API/demo imports must match the installed dependency profile. The image source/package build must include the required `apps`, `packages` and `pipelines` source. A wheel/source-context build is not an actual Docker-engine image run; record each separately. The recovery task repairs the audited packaging defects; until its evidence is integrated, do not call the container path verified.

| Component | Required core profile | Conditional experiment / resource decision |
| --- | --- | --- |
| Data and analytics | PyArrow/Pandas over verified immutable Parquet; descriptive cohort counts/quantiles | DuckDB only if a measured query/memory need justifies it |
| Retrieval | Local pickle-free BM25 CSR and lexical phrase/aspect reranking | One CPU embedding model and populated dense/Qdrant pilot only after parity and held-out comparison |
| Script drafting | Explicit `offline_grounded`, zero external calls, qualified creative directions and structural checks | Eligible owner Gemini free-tier project only after current model/project/quota check; never a paid fallback |
| Comment/aspect diagnostics | Observable rule/lexicon baseline; preserve source spans, unknowns and insufficient evidence | Independently annotated real comments/aspects before automated filtering or accuracy claims; model agreement alone is not gold |
| Audio | No historical audio assumed; source text retrieval remains usable | Pilot audio only, CPU ASR/prosody with measured throughput, boundary error and RAM; optional dependencies stay isolated |
| API/demo | One Uvicorn/FastAPI process with ASGI-mounted Gradio `/demo/`; no account/session product | Local Docker optional; public host requires the separate G6 eligibility/resource decision |

Qdrant, Redis, ASR and crawling are optional infrastructure or dependencies. Neither a reachable adapter nor a fixture demonstrates populated hybrid retrieval or a working live worker. Core offline analytics/search/drafting must not require their daemons, external credentials or network access. Existing frozen 21 ms retrieval is historical weak-label evaluation evidence; it is not this revision's current latency promise.

## 2. Preserved data, generated artifacts and rights

Preserve all original local raw/interim/legacy bytes and never re-crawl historical TikTok videos. The audit corroborated 37,837 upstream data files / 1,475,677,482 logical bytes at pinned revision `f142e5656a220f94f8024de168b0832754b3bd9e`; the prior 37,840 owner-copy inventory used a different scope and remains separately qualified. Recovery must inventory actual paths, bytes and SHA256, record which existing files were untouched, and avoid claiming an old inventory comparison that is unavailable.

| Asset | Storage / Git treatment | Reproducibility and disclosure requirement |
| --- | --- | --- |
| Source, tests, task plans/reports and small evaluation receipts | Git-tracked where allowed by repository rules | Pin source revision, record actual commands/environments and preserve historical evaluation versions |
| Historical raw/interim/processed/transcript/legacy payloads | Local-only, gitignored; retain owners' original copies | Pinned source/owner provenance and input inventories; parse/filter acceptance is not speech accuracy |
| Gold snapshot | `data/corpus/<new-id>/`; heavy Parquet local-only | Reject output collisions; stage all tables, validate keys/schema/hash and publish only complete snapshots; parent/input/code lineage |
| BM25/dense artifacts | `artifacts/indexes/<version>/`, heavy binaries local-only | Bind to corpus/input hashes, model/tokenizer version, query/qrel revision and actual build receipt |
| Fresh capture | `data/raw_incremental/`, local-only | 120-day operational cutoff/as-of, historical-ID exclusion, bounded requested/success/failure records, audio/comment coverage and original source IDs |
| Human annotation | Local evidence; publish only permitted/redacted summaries | Guidelines, sample/partition provenance, two-person judgments, disagreements/adjudication and uncertainty |
| Provider secrets | Solely gitignored `.env` | Never log keys or commit them; run `python3 scripts/check_secrets.py` before any commit |

Source access does not establish a redistribution license. The audit found no upstream root dataset license; resolve terms before shipping raw text/audio/comments, derived examples or a public artifact containing them. Public deployment also requires minimizing personal data and checking what its logs/caches expose. This is a specific unresolved release input, not an assumption that the repository's MIT declaration licenses upstream data.

Follow the current root Quickstart for fresh snapshot IDs and rebuild commands. Do not rerun historical commands against an already published output path. A missing asset must produce a bounded readiness/error state rather than a live-route synthetic replacement. Local storage requirements are measured after recovery; the approximate historical 1.50 GB claim excludes new Gold/index copies, package/model caches and audio, so it is not a full disk budget.

## 3. Bounded capacity and quality measurements

The two-person plan budgets 94 estimated points / 47 person-days each, including review, annotation, integration and gate work. Actual availability and CPU throughput remain unknown. The relative W1–W12+ windows are indicative, and the whole multimodal research scope is not promised in eight weeks.

| Pilot or check | Bound / provisional acceptance | Required measurements |
| --- | --- | --- |
| Historical analytics | 100 fixed requests, concurrency 1; warm p95 <= 250 ms excluding artifact load | Hardware, cold/warm p50/p95, support counts and cohort/observation dates |
| Historical BM25 | 40 independently authored queries (20 dev / 20 locked test), blinded pooled judgments; 100 warm requests, p95 <= 500 ms | Conventional Recall@10, Precision@10, MRR/nDCG, per-query results, qrel completeness, uncertainty and corpus/index/query/code hashes |
| Fresh capture | <= 5 creators / 50 candidates / 30 successes / 60 audio minutes / 1,000 comments / one two-hour capture session | Yield, skip/failure reasons, metadata/audio/comment coverage, wall time and storage; minimum 5 real transcribed searchable videos for the vertical slice |
| Early transcription | <= 10 videos / 20 audio minutes before accepting searchability | CPU ASR model, wall/audio real-time factor, peak RAM, actual transcript coverage and source resolution |
| Audio evaluation | <= 60 captured audio minutes; <= 20 reference minutes / >= 50 utterances; <= 4 CPU hours / <= 8 GiB peak RAM | CER/WER with tokenization, median/p95 boundary errors, interval bounds; target median <= 1 s / p95 <= 3 s or abstain from precise timing |
| Comment labels | <= 300 comments, minimum 150 for a quality gate, double annotation and video/thread holdout | Observable label definitions, agreement, class precision/recall/F1, bootstrap uncertainty and filter sensitivity |
| ABSA labels | <= 200 units across >= 10 videos, minimum 120 units, double annotation and video-disjoint holdout | Aspect presence/polarity, source-span validity, per-aspect coverage and before/after-filter discrepancy |
| Dense experiment | <= 5,000 records, one CPU model, corpus/query parity; warm p95 <= 1,000 ms / <= 8 GiB peak RAM | Build time, model/index/cache bytes, quality differences/uncertainty; retain BM25 if no justified gain |
| Integrated offline demo | 30 held-out questions and 30 timing repetitions, concurrency 1; request p95 <= 5 s excluding startup | Source/temporal/claim coverage, no-answer behavior, per-stage and total latency, artifact-load/cold-start time |

These are prospective pilot limits/thresholds from the plan, not observed throughput or calibrated accuracy. The milestone plan has the complete sample/quality criteria. Publish failed targets and reduce the sample/model/features or extend the schedule; never silently promote fixture results to live acceptance. Additional collection/model batches need an explicit measured bound after G3. Estimate audio work as audio duration × observed real-time factor, then add retry, review, annotation and integration effort.

Retain `StageTimer` measurements in milliseconds: domain/filter/retrieval/fusion/rerank/synthesis/guardrail and total where executed. Separate artifact startup, network/provider wait and offline computation; do not attribute an omitted stage a measured zero. Track successful requests and failures separately, with repetition count and warm/cold state. Historical engagement supports retrospective associations; no real-time forecast or causal viral uplift is accepted from a single capture.

## 4. Zero-spend provider contract

Authorized provider/GPU/hosting spend is **USD 0**. Offline operation needs no key and remains a sufficient release path. Optional online synthesis uses only the owner's currently eligible Gemini free-tier API project and a model explicitly confirmed eligible immediately before use. Model availability, retirement and project quota can change; the former fixed model/15 RPM settings are configuration values, not guaranteed entitlements.

Enforce <= 2 LLM calls per turn, a conservative sliding-window RPM limiter below the actual project quota, bounded timeout/retry and explicit `ProviderKeyMissingError`, `QuotaBlockedError` and provider-unavailable handling. Missing key must not crash offline analytics/search. Missing eligible free quota/model must fail closed or return an explicitly requested offline draft; never silently enable billing, paid fallback, account upgrades or paid GPU. No live LLM call or expenditure is evidenced by this documentation rewrite.

## 5. Public hosting remains a measured candidate decision

The audit recorded time-sensitive hosting/provider restrictions against official documentation on 2026-11-17; see its [external evidence and links](../reports/tasks/docs-refactor-feasibility-2026-11-17/evidence/external-and-runtime-review.md). This guide does not assert that an ordinary Gradio/Docker host is currently free. No host is selected, deployed or accepted. Local execution remains available when no eligible host fits.

M6.G must record a candidate comparison and actual small-profile measurement before any public release:

| Candidate evidence | Pass condition | Current state |
| --- | --- | --- |
| Official current eligibility/terms | Genuinely free account/tier; no paid prerequisite, add-on, overage or automatic upgrade; record check date and direct official links | NOT_RUN |
| Resource/storage fit | Measured artifact/model/image bytes, RAM peak and disk/cache fit within stated limits; no assumed persistent disk | NOT_RUN |
| Sleep, cold start and quotas | Document suspension/eviction, idle sleep, cold-start time, CPU/RAM/network/build/request limits and expected availability honestly | NOT_RUN |
| Artifact rights/privacy | Source reuse/redistribution and personal-data exposure resolved for the actual hosted profile | BLOCKED pending evidence |
| Runtime and cost controls | Offline core works on candidate, bounded errors/readiness visible, no paid fallback or billing/overage path | NOT_RUN |
| Acceptance | Both contributors review measured evidence; owner approves any public publish separately | NOT_RUN |

If a candidate cannot fit the full corpus, a smaller permitted immutable demonstration snapshot requires its own provenance and qualified coverage; it is not silently equivalent to the whole historical corpus. A host failure blocks public hosting only. Do not mark a local AI core incomplete merely because public hosting is unavailable, and do not call a local smoke check a deployed service.

## 6. Provenance and operational references

The exact prior resource guide is preserved in the recovery task's [source archive](../reports/tasks/core-recovery-and-two-person-plan-2026-11-17/evidence/prior-resources-and-deployment.md), with [preservation hashes](../reports/tasks/core-recovery-and-two-person-plan-2026-11-17/evidence/prior-plan-preservation.json). New documentation is dated; frozen measurements and historical reports remain historical.

- [FastAPI response models](https://fastapi.tiangolo.com/tutorial/response-model/)
- [Gradio mounting in FastAPI](https://www.gradio.app/docs/gradio/mount_gradio_app)
- [Qdrant hybrid queries](https://qdrant.tech/documentation/concepts/hybrid-queries/)
- [Current milestone gates and task owners](TikTok_AI_Engine_Milestone.md)

References identify implementation documentation; they do not certify current provider/hosting eligibility. Check official service terms at the decision point and retain the dated evidence in M6.G.
