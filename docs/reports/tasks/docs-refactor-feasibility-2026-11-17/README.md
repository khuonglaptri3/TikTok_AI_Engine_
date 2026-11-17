# Documentation, architecture, and data feasibility audit

- Status: COMPLETE
- Execution date: 2026-11-17 (Asia/Saigon)
- Requirement source: owner request to assess `docs/` and `ReFactor_structure/`; owner-supplied data source [TrggTin/21KHDL-TikTok-Analytics](https://github.com/TrggTin/21KHDL-TikTok-Analytics).
- Repository version: `main`, `cdbc6ed9ccad11db437aa66c68638cf018701fe5`; audit changes are uncommitted documentation/evidence only.
- Specification: [spec.md](superpowers/spec.md)
- Execution plan: [plan.md](superpowers/plan.md)

## Conclusion

**A CPU-based historical analytics, BM25 retrieval, script-drafting API, and simple Gradio demonstration is feasible for one AI Engineer. The complete multimodal trust system is not yet validated or ready to deploy.** The modular architecture is broadly sound, but several correctness defects and unsupported scientific claims must be resolved before accepting the broader completion labels.

Fresh verification produced **15 passing and 5 failing existing tests**, with all five failures requiring historical raw/Gold data absent from this checkout. Type checking passed for 74 source files. Controlled temporary fixtures independently reproduced multimodal data loss across successive ingests, snapshot overwrite, fabricated citation associations, and false-positive script validation. These are actual defects; the missing local corpus is a separate availability limitation.

The upstream source genuinely contains a substantial historical F&B dataset. Its metadata CSV has 70,996 unique video IDs and 264 authors, covering November 2023 to March 2025. Engagement observations come from a single March 2025 capture. This supports retrospective descriptive analysis and text retrieval, but does not establish present trends, causal viral improvement, undisclosed sponsorship, coordinated seeding, or verified diner experience. Those distinctions are essential to a defensible demonstration.

## Work performed

- Reviewed all **15 original documents**: nine under `docs/` and six under `ReFactor_structure/`; compared relevant code, contracts, tests, and frozen artifacts.
- Inspected the upstream repository at pinned revision `f142e5656a220f94f8024de168b0832754b3bd9e`, its complete tree metadata, selected schemas/notebooks, and bounded aggregate metadata checks. No historical TikTok video was recrawled.
- Built the package with demo/dev extras in an ephemeral uv environment, ran the full existing tests and type checker, and reproduced boundary defects with synthetic temporary data. No product code or owner data was changed.
- Checked current Gemini model/quota and hosting conditions against official documentation. No live LLM request, paid service, public deployment, or spending was initiated.

## Priority findings

Severity reflects the consequence for correctness or acceptance, not evidence that a historical run was fabricated. Detailed reports contain exact source file/line references and qualifications.

| Priority | Finding and consequence | Required follow-up / evidence |
| --- | --- | --- |
| HIGH | **Incremental Sink B loses prior batches.** A then B preserves both videos, but only B's voice/comment/ABSA rows. Replaying A produces empty Sink B tables. Later transcription/comment enrichment of existing video IDs is skipped. | Preserve/deduplicate every base table and support explicit enrichment updates before M3.3. [Controlled results](evidence/runtime-probes.json), [R6](evidence/refactor-review.md#r6--high-repeated-incremental-ingestion-loses-prior-sink-b-rows). |
| HIGH | **Snapshots are not immutable.** Builders accept existing output directories; the converter accepts its base as output and rewrites it with a new matching manifest. SHA256 checks alone do not prevent replacement. | Reject published output collisions and verify complete artifacts before atomic publication under a new ID. Record parent/input/code provenance. [R5](evidence/refactor-review.md#r5--high-immutable-snapshots-can-be-overwritten-by-the-documented-command), [runtime evidence](evidence/runtime-probes.json). |
| HIGH | **Grounding and duration validation can falsely pass.** Uncited text is assigned an arbitrary retrieved source ID; empty scripts pass; a 3-second script targeting 300 seconds passes. Offline templates also assert firsthand freshness/quality without source support. | Separate source existence, coverage, claim support, creative suggestions, and timing; fail on missing required content. [D06](evidence/docs-review.md#d06---high-citation-id-membership-is-insufficient-to-establish-grounded-scripts), [controlled results](evidence/runtime-probes.json). |
| HIGH | **Reported Recall@10 is mislabeled and relevance is weakly defined.** The denominator is `min(relevant_count,10)`, not all relevant documents. The 16-query benchmark derives relevance from keyword/metadata rules, and evaluates BM25 variants only. | Correct/version the metric; use independent held-out judgments and record per-query results. The current qrels imply a theoretical conventional macro Recall@10 ceiling of 0.294768, so the reported 0.7094 is a different metric. [D01-D02](evidence/docs-review.md#d01---high-the-reported-recall10-is-a-different-metric). |
| HIGH | **The current checkout cannot reproduce the real-corpus application.** Raw/interim/processed/transcript inputs, Gold Parquet files, and the BM25 index are absent; a manifest and frozen JSON are present. | Restore permitted preserved inputs/artifacts from the pinned source or owner's copy, then verify hashes and rerun data-dependent checks. Do not recrawl old videos. [Upstream/data review](evidence/upstream-data-review.md), [pytest output](evidence/pytest-full.log). |
| HIGH | **Dense/neural retrieval and live collection remain incomplete.** The index builder creates BM25 only; the reranker is lexical/rule-based. The crawler CLI emits authored demo data or a readiness message, not an invoked live collection worker. | Reconcile active capability/status claims. Implement and measure the missing paths before accepting their criteria. Resolve M3.3's transcript-before-search dependency. [R3](evidence/refactor-review.md#r3--high-checked-neural-retrieval-completion-describes-capabilities-not-implemented), [D07](evidence/docs-review.md#d07---high-m32-completion-and-the-m33-freshness-dependency-exceed-the-implemented-collector). |
| HIGH | **Trust targets exceed observable labels.** `is_ad` and shop flags do not label undisclosed sponsorship. Duplicate text does not prove bots/seeding; nonfiltered commenters are not verified diners. Missing ABSA aspects are treated as neutral and exact source-span citations are absent. | Use observable, qualified indicators; preserve unknowns, source IDs/spans, aspect support, and independently annotated evaluation. Defer hidden-intent classification unless genuine ground truth exists. [D03-D05](evidence/docs-review.md#d03---high-disclosed-ad-and-e-commerce-flags-do-not-label-undisclosed-sponsorship). |
| HIGH | **Deployment and zero-spend assumptions need correction.** Default Gemini model eligibility/deprecation is time-sensitive; 15 RPM is not a guaranteed project quota. New ordinary HF CPU Gradio/Docker Spaces require a paid plan under current documentation. No hosting profile has been measured and accepted. | Verify a current eligible free model/project and fail closed; select and resource-test a genuinely free hosting profile with no billing/overage path. [Current official sources and qualifications](evidence/external-and-runtime-review.md#external-conditions). |
| HIGH | **Packaging blocks the documented container path.** The Dockerfile omits the `pipelines` package required by Poetry. Base install also lacks Gradio despite unconditional imports in the API. Both failures were reproduced separately. | Align image source/package/dependency profiles before a real image/deployment smoke check. [Packaging/import evidence](evidence/external-and-runtime-review.md#local-root-causes-and-fresh-verification). |
| MEDIUM | **Historical association, extraction, and completion claims are too strong.** Engagement snapshots and selected transcripts do not establish optimal duration, current trends, causality, accurate speech, physical venue presence, or calibrated trust. Several completed tasks have no separate report/acceptance trail. | Retain explicit statistical caveats; qualify weak labels and observations; add current, dated acceptance evidence without backdating records. [D08-D12](evidence/docs-review.md#d08---medium-descriptive-historical-statistics-must-not-become-causal-or-optimal-content-claims). |

## Data suitability

| Asset or claim | What this audit established | Suitable use / limitation |
| --- | --- | --- |
| Historical video metadata | Upstream CSV: 70,996 rows, 70,996 unique IDs, 264 authors; video dates 2023-11-25 to 2025-03-19. | Historical cohort summaries, filtering, creator-relative engagement descriptors. Creator-selected, not a representative TikTok population sample. |
| Engagement | Upstream `collectTime` values form one short capture on 2025-03-19; the local Gold mapping drops that field. | Snapshot associations; no repeated outcome trajectory or fixed exposure horizon. Retain observation time to distinguish video age and later capture batches. |
| Corpus size/preservation | Pinned upstream `data/` tree: 37,837 files, 1,475,677,482 logical bytes. Local reports claim 37,840 preserved files; no source preservation manifest/payload is available here. | Approximate historical scale corroborated; exact owner-copy preservation remains unverified because inventory scopes differ. |
| Transcripts and annotations | 23,122 upstream transcript JSON files; local manifest claims 21,748 accepted transcripts. Existing annotations are machine-derived/filtered, not human ground truth. | A plausible text RAG corpus once locally rebuilt and checked. Accepted transcript count and semantic/audio accuracy were not freshly verified. |
| POI and taxonomy | Upstream contains raw POI fields and derived location/food annotations. Gold's 49 fields are a local transformation contract. | Useful weak metadata with per-field lineage and unknowns; a platform POI tag is not proof of physical presence. |
| Audio/comments/intent labels | No complete aligned historical audio/comment corpus or verified sponsorship/seeding ground truth was established. | Prosody and viewer-vs-creator trust require new, bounded fresh-data capture and independent labels; do not infer absent modalities from metadata. |
| Reuse terms | GitHub license metadata is null and no root dataset license was found. | Source access is verified; public redistribution/reuse terms remain unresolved. The current project's MIT declaration does not establish an upstream dataset license. |

Detailed source revision, file/schema references, sampling bounds, and checked counts are in the [upstream review](evidence/upstream-data-review.md) and [metadata record](evidence/upstream-metadata.json).

## Implementation feasibility and sequence

| Layer | Judgment for one engineer / CPU / USD 0 | Acceptance condition |
| --- | --- | --- |
| Gold metadata, taxonomy, niche statistics | Feasible local baseline. Pandas is reasonable at this scale; DuckDB is an optional measured choice. | Available inputs, safe snapshots, schema/lineage checks, sampled annotation accuracy, descriptive wording and support counts. |
| BM25 plus heuristic reranking | Feasible; existing implementation is substantial. | Recover/build the real index, correct metrics, independent query judgments, measured current latency. |
| Script drafting, typed API, Gradio | Feasible local demonstration. Offline drafting can avoid provider spend. | Supported factual claims, visibly creative directions, correct validation and bounded provider errors, real-data smoke check. |
| Fresh metadata/audio/comments and dual-sink ingest | Conditional; utilities and fixtures exist, complete live path is unfinished. | Safe repeated ingestion and a bounded real capture-to-transcript-to-search pilot, with success rates and failures. |
| ASR/prosody and timestamp citations | Conditional on fresh aligned audio and measured CPU throughput. | Audio-derived vs interpolated provenance; temporal bounds, ASR/boundary error, memory and real-time-factor measurements. |
| Seeding/ABSA | Feasible as qualified research baselines; current trust accuracy is unverified. | Independent real-data annotation, precision/recall or aspect F1, uncertainty, missing-aspect handling, source spans, filter sensitivity. |
| Undisclosed sponsorship | Current proposed supervised target is not supported. | Revised observable target or independently verified ground truth; more features alone do not resolve the target mismatch. |
| Neural hybrid retrieval / timestamped Q&A / public hosting | Possible later, not accepted by this audit. | Versioned populated dense indexes, held-out gain over simpler baselines, end-to-end citations, and a measured genuinely free deployment profile. |

Recommended order within the existing plan:

1. Re-establish M0/M1 evidence: recover historical inputs and Gold/index assets, verify lineage and hashes, resolve source reuse terms, and distinguish historical assertions from new checks.
2. Address the destructive-ingestion, snapshot, script-validation, and packaging defects before expanding data volume or public exposure.
3. Re-evaluate M2 against correct metrics and independent relevance/grounding judgments. Accept a truthful local historical analytics/BM25/API/Gradio demonstration first.
4. Treat M3.3 as a bounded acquisition feasibility gate, with a complete capture-to-transcript-to-index path and measured comment/audio coverage. A four-month window alone does not bound the number of videos or compute workload.
5. Measure fresh-audio throughput and annotate/evaluate ABSA and suspicious-comment patterns before adding richer trust claims. Resolve the M4.2 target mismatch explicitly.
6. Add dense retrieval and final hosting only when held-out usefulness, CPU/memory cost, and no-spend eligibility are demonstrated.

The eight-week window is an unvalidated capacity assumption. A narrow demonstrator is plausible; the current documents do not provide cohort size, audio hours, annotation effort, throughput, or deployment capacity sufficient to promise the full research scope in that window.

## Outputs

| File | Purpose |
| --- | --- |
| [document-inventory.json](evidence/document-inventory.json) | Paths and SHA256 hashes for all 15 original requested documents. |
| [docs-review.md](evidence/docs-review.md) | Active scope, scientific validity, evaluation, reporting, and schedule findings. |
| [refactor-review.md](evidence/refactor-review.md) | All six refactor documents compared with implementation. |
| [upstream-data-review.md](evidence/upstream-data-review.md) | Pinned upstream data inspection and module suitability. |
| [upstream-metadata.json](evidence/upstream-metadata.json) | Aggregate tree/schema/count evidence and bounded inspection details. |
| [external-and-runtime-review.md](evidence/external-and-runtime-review.md) | Official provider/host conditions, packaging failures, and runtime qualifications. |
| [pytest-full.log](evidence/pytest-full.log), [mypy.log](evidence/mypy.log) | Full existing-suite and type-checker output. |
| [base-install-import.log](evidence/base-install-import.log), [docker-context-build.log](evidence/docker-context-build.log) | Controlled installation/image-source packaging reproductions. |
| [runtime-probes.py](evidence/runtime-probes.py), [runtime-probes.json](evidence/runtime-probes.json) | Reproducible synthetic defect probes and resolved runtime versions. |
| [workflow.md](evidence/workflow.md) | Actual authorization, skill usage, adaptations, and execution provenance. |
| [report-review.md](evidence/report-review.md) | Fresh independent report review; no Critical/Important corrections, one wording correction applied. |
| [verify-audit.py](evidence/verify-audit.py) | Reproducible final layout, link, source-integrity, status, hash, and secret checks. |
| [verification.json](evidence/verification.json) | Final layout, local-link, secret, navigation, and source-integrity checks. |
| [artifact-hashes.json](evidence/artifact-hashes.json) | Audit artifact SHA256 hashes; excludes itself and the final verification record to avoid circular hashes. |

## Planning and verification

The [specification](superpowers/spec.md) and [plan](superpowers/plan.md) were created on 2026-11-17 before substantive investigation. The owner's audit request authorized execution and report writing. The process record distinguishes applied investigation skills from implementation skills read only for applicability. No code/TDD implementation, branch integration, commit, or product deployment is claimed.

| Check | Result | Scope / evidence |
| --- | --- | --- |
| Original-document coverage | PASS | 15 files inventoried and independently reviewed; [inventory](evidence/document-inventory.json). |
| Full existing pytest | FAIL | 15 passed, 5 failed; failures need missing original/Gold inputs. [Output](evidence/pytest-full.log). |
| Project-configured mypy | PASS | 74 source files; [output](evidence/mypy.log). |
| Product correctness probes | Defects reproduced | Synthetic fixtures, not live data or model-accuracy tests. [Results](evidence/runtime-probes.json). |
| Base import / Docker COPY-set package build | FAIL / FAIL | Missing optional Gradio / required `pipelines`; actual container execution NOT_RUN. [Evidence](evidence/external-and-runtime-review.md). |
| Real-corpus latency/model accuracy, live capture, public hosting | NOT_RUN | Missing local artifacts and no live operation within audit scope. Frozen numbers remain historical. |
| Secret check and report integrity | PASS | Fresh scanner plus layout, links, status, source integrity, and artifact hashes; [final verification record](evidence/verification.json). |
| Independent report review | PASS with minor wording correction applied | No Critical/Important factual corrections. [Review](evidence/report-review.md). |

## Open issues and acceptance

All priority findings above remain open for implementation or evidence repair. This audit changes no existing milestone status and passes no gate. Exact original preservation, full-corpus runtime, live provider eligibility, real-data trust accuracy, and free-host fit remain unverified. Existing source documents are preserved apart from the authorized report-navigation link; any source-document link issues found during verification are recorded rather than silently rewritten.

| Audit acceptance criterion | Result | Evidence |
| --- | --- | --- |
| Inventory and review both requested directories | Met | 15 original documents in the [inventory](evidence/document-inventory.json), covered by the two document reviews. |
| Evidence-backed findings with consequences and follow-up | Met | Priority table and independent [report review](evidence/report-review.md). |
| Module-level scientific and CPU/zero-spend feasibility | Met | Feasibility matrix, scientific review, and [provider/hosting qualifications](evidence/external-and-runtime-review.md). |
| Pinned upstream data inspection without replacing originals | Met | [Upstream review](evidence/upstream-data-review.md) and aggregate/schema metadata. |
| Bounded checks with truthful results | Met | Actual failing/passing logs and controlled defect reproductions; no live operation is claimed. |
| Validated report, planning, provenance, and navigation | Met | [Workflow](evidence/workflow.md), [verification](evidence/verification.json), and [hash manifest](evidence/artifact-hashes.json). |

The audit task is **COMPLETE**. Product implementation, fixes, data restoration, and milestone/gate acceptance remain open as described above. The handoff is an assessed scope and prioritized evidence-backed follow-up, not a declaration that the project is complete or publicly deployable.
