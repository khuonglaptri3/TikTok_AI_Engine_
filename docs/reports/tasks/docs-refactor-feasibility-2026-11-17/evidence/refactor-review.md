# Refactor proposal: independent architecture and feasibility review

- Review date: 2026-11-17, Asia/Saigon.
- Repository revision inspected: `cdbc6ed`; source was read from the current shared working tree.
- Scope: all six Markdown files in `ReFactor_structure/`, compared with the relevant implementation, manifest, benchmark, contracts, and active milestone plan.
- Method: read-only source inspection, bounded file-presence and JSON-cardinality checks, and primary-source verification of metric/model definitions. No crawling, provider calls, model downloads, data changes, or implementation changes were performed by this reviewer.
- Planning: [audit specification](../superpowers/spec.md), [audit plan](../superpowers/plan.md). Root investigator owns audit verification and workflow provenance.

## Conclusion

The proposed modular Python architecture is suitable for a local, single-engineer demonstration of historical F&B retrieval, descriptive niche statistics, and evidence-assisted script drafting. Immutable Parquet, typed APIs, BM25, explicit provider errors, and one ASGI-mounted Gradio UI are sensible choices. These architectural choices do not establish scientific validity or a working dense/multimodal system.

The proposal contains stronger claims than its evidence supports. Its checked implementation plan overstates neural retrieval completion; its benchmark mislabels a capped hit fraction as recall; and its citation guardrail can manufacture a source association while reporting a pass. Historical engagement does not establish the cause of video success or an optimal production strategy. The current local checkout also lacks the Parquet files and BM25 index required to run its corpus-dependent application. The later incremental implementation contains an additional data-continuity defect: the second ingest drops the first ingest's multimodal rows from the new snapshot.

This review does not change existing milestone statuses. Source-supported defects should be resolved and acceptance evidence rebuilt before those statuses are used as a readiness claim.

## Document coverage and interpretation

| File | Assessment |
| --- | --- |
| `ReFactor_structure/README.md` | Read in full. Useful navigation; its present-tense description needs to distinguish historical audit, target architecture, implemented baseline, and deferred modules. |
| `00_OVERVIEW_AND_CURRENT_STATE.md` | Read in full. Detailed historical inventory and app description; exact counts, historical performance assertions, and legacy defects require the original dataset/revision for fresh reproduction. They are source claims rather than new measurements from this review. |
| `01_LIMITATIONS_AND_BUGS_AUDIT.md` | Read in full. Identifies valuable issues: missing POI fields, imputation, label imbalance, biased sampling, missing extraction ground truth, inconsistent metrics, and unsafe key storage. Many cited paths now refer to archived coursework, not active application code. |
| `02_DATA_AND_RAG_REFACTOR_PROPOSAL.md` | Read in full. Good motivation for merging data and context retrieval; scientific overclaims and obsolete paths/stack alternatives need qualification. |
| `03_AI_ENGINEER_ARCHITECTURE_SPEC.md` | Read in full. Dated draft target; separates core packages and transport well, but some planned behavior is absent or differs materially in code. |
| `04_IMPLEMENTATION_PLAN.md` | Read in full. All steps are checked; completion labels exceed the current neural retrieval, immutable-publication, grounding, and evaluation evidence. |

## Prioritized findings

### R1 — High: the reported Recall@10 uses the wrong denominator

- Claim: `ReFactor_structure/03_AI_ENGINEER_ARCHITECTURE_SPEC.md:202` promises retrieval Recall@10; checked benchmark completion appears at `04_IMPLEMENTATION_PLAN.md:82`.
- Evidence: `pipelines/benchmark_retrieval/__main__.py:105-107` divides hits by `min(len(relevant), k)` and stores it as `recall_at_10` at line 128. For queries with at least ten relevant items this equals precision at ten, assuming ten results, rather than recall over all relevant items. The official [scikit-learn recall definition](https://scikit-learn.org/stable/modules/generated/sklearn.metrics.recall_score.html) uses all actual positives in the denominator (retrieved relevant plus missed relevant).
- Fresh bounded check: the committed query file contains 16 queries; `q01` has 1,011 relevant IDs. Ten hits would produce `1.0` in the current implementation, while ordinary Recall@10 would be `10/1011`, approximately `0.00989`.
- Consequence: the frozen `0.7094` value is not interpretable as ordinary Recall@10. Thresholds and reports repeating that label cannot serve as recall acceptance evidence. MRR/nDCG have a separate relevance-quality limitation in R2.
- Correction: implement ordinary recall or give the existing capped metric an explicit nonstandard name and formula; report precision separately. Recompute and version results, without silently replacing the historical artifact or backdating its meaning.
- Confidence: directly established by source and JSON cardinalities; no model inference was run.

### R2 — High: the evaluation does not validate semantic hybrid retrieval

- Evidence: `pipelines/benchmark_retrieval/__main__.py:29-68` defines 16 queries and constructs relevance labels through exact keyword containment plus the same derived city/format/category fields used by the system. The runner requests only `mode="bm25"` at line 94. `artifacts/benchmarks/retrieval_v1.json:7-23` contains only BM25 with viral boosting, with and without the heuristic reranker. The query file has no judge, rubric, split, or disagreement fields.
- Consequence: this is a useful weak-label regression check for lexical/metadata behavior, not independent evidence that dense search, RRF, a Cross-Encoder, synonyms, full brief satisfaction, or generation grounding work. For example, a query may mention price and occasion while its qrels check only a dish substring and city. The existing artifact shows reranking MRR falling from `0.8875` to `0.8127`; it does not support an unqualified claim that every quality measure improved.
- Correction: retain and label this regression set; add separately judged queries and pooled candidates, semantic paraphrases, hard negatives, unsupported/no-answer cases, and creator/time separation where needed. Freeze tuning and held-out evaluation sets; compare actual BM25, dense, RRF, and neural reranker configurations only after their indexes exist. Record corpus, index, qrels, model, configuration, and code hashes plus hardware and warm/cold timing conditions.
- Confidence: source and artifact inspection. The reviewer did not independently judge all 16 queries.

### R3 — High: checked neural retrieval completion describes capabilities not implemented

- Claims: `03_AI_ENGINEER_ARCHITECTURE_SPEC.md:20`, `:72-74`, and `:88-90` specify dense embeddings, Qdrant, Cross-Encoder reranking, and comparisons. `04_IMPLEMENTATION_PLAN.md:81` checks off a phrase/overlap plus optional Cross-Encoder implementation.
- Evidence: `pipelines/build_dense_sparse_index/__main__.py:12-24` builds and saves only BM25. `packages/retrieval/rerank/scorer.py:30-88` computes token overlap, phrase/dish/context bonuses, anatomy completeness, and viral signals; it never loads a Cross-Encoder. `packages/retrieval/service.py:131-140` can encode a query, but there is no corresponding document-embedding/collection-population path in this builder. `pyproject.toml:22-48` does not declare `sentence-transformers` or a neural retrieval extra.
- Consequence: a Qdrant HTTP adapter and fusion function are useful scaffolding, but do not make the installed project a populated neural hybrid system. Setting a reranker model name does not activate a neural reranker.
- Correction: state the verified baseline as BM25 plus heuristic reranking. Add a bounded offline embedding/index job with model revision, prefixes, truncation/chunking, dimensions, normalization, IDs, payloads, and receipts. Implement a neural reranker only if an independent CPU benchmark shows useful improvement. Dense/heuristic/neural modes must be distinguishable in returned module status.
- Feasibility qualification: the author's [multilingual E5 model card](https://huggingface.co/intfloat/multilingual-e5-base) lists approximately 0.3B parameters, requires query/passage prefixes for retrieval, and limits input to 512 tokens. CPU operation is possible, but cold load, peak memory, document truncation, batch throughput, and query latency need measurement; the `21 ms` heuristic benchmark cannot predict these costs.
- Confidence: source inspection plus model-author documentation accessed 2026-11-17.

### R4 — High: citation validation can attach unsupported citations and pass

- Claim: `03_AI_ENGINEER_ARCHITECTURE_SPEC.md:75` proposes offset/quote provenance verification; line 201 describes synthesis grounded strictly in retrieved anatomy.
- Evidence: `packages/llm/guardrails/verifier.py:37` selects an arbitrary valid evidence ID from a set; lines 62-63 attach it when a beat has no surviving citations. Line 82 reports a citation ratio of `1.0` when no citations were submitted if any evidence exists. Lines 87-94 make duration mismatch a warning while `passed` checks only cliches and citation-ID ratio. No entailment, quoted span, or source offset is checked.
- Consequence: a cited ID can be real while the associated dialogue is unsupported. Empty or badly timed output can receive a positive grounding-style pass. This breaks the stated meaning of a verified evidence-based script and makes an ID-validity score inadequate as a grounding score.
- Correction: do not invent source associations. Separate ID existence, citation coverage, claim support, anatomy provenance, schema validity, and duration compliance. Require evidence spans or explicit creative-suggestion labels and a human-reviewed grounding evaluation. Define exactly which failed criteria prevent an overall pass.
- Controlled verification: the root's [runtime probes](runtime-probes.json) confirmed that uncited arbitrary text receives an injected retrieved ID, `valid_citations_ratio=1`, and `passed=true`; a three-second estimate for a 300-second target passes; an empty script also passes.
- Confidence: source inspection and root-controlled runtime reproduction, using synthetic fixtures rather than a provider or the missing historical corpus.

### R5 — High: immutable snapshots can be overwritten by the documented command

- Claim: `04_IMPLEMENTATION_PLAN.md:15-18` requires preservation and integrity; line 66 documents rebuilding into the named `20261116_v1` snapshot. `03_AI_ENGINEER_ARCHITECTURE_SPEC.md:100` calls snapshots immutable and line 187 requests a Git commit in the manifest.
- Evidence: `pipelines/build_gold_corpus/builder.py:189` accepts an existing output directory; lines 320, 527, and 566 overwrite the two Parquet files and manifest. No output-collision rejection or atomic publication appears. `packages/data_contracts/corpus.py:16-29` records output checksums but has no source-input hashes, build code revision, transformation configuration, or parent snapshot lineage.
- Consequence: reusing a snapshot ID can change its content and regenerate matching checksums. A checksum detects unexpected differences against a trusted manifest; it does not enforce immutable publication or authenticate the provenance of a replacement manifest.
- Correction: refuse existing published output, build in a temporary directory, validate, then publish atomically under a new ID. Record original-input hashes, code/config versions, schema version, and parent lineage. Protect raw inputs independently from generated snapshots and check exact inventory hashes for preservation, rather than relying on a minimum total byte count (`04_IMPLEMENTATION_PLAN.md:38`).
- Controlled verification: the root's [runtime probes](runtime-probes.json) confirmed that the incremental converter accepts `output_dir=base`, changes the manifest, and therefore can overwrite the base snapshot. The historical builder collision issue is directly established by its write paths. No owner data snapshot was modified during this review.

### R6 — High: repeated incremental ingestion loses prior Sink B rows

- Requirement: the later active plan requires continuing both the fact-video corpus and multimodal tables (`docs/planning/TikTok_AI_Engine_Milestone.md:15-17` and `:125-147`). This is an integration finding in the code that extends the refactor, rather than an original promise in the historical draft.
- Evidence: `pipelines/ingest_incremental_to_gold/converter.py:104` loads only base creators/videos. Voice/comment/ABSA arrays are reset at lines 121-123. Duplicate video IDs are skipped before processing either sink at lines 126-127. Lines 302-310 construct the three multimodal tables from this batch only, and lines 312-323 publish all five tables.
- Consequence: base -> batch A -> batch B retains A+B in `fact_videos` but retains only B in voice/comments/ABSA. Replaying a processed video or an empty batch produces empty Sink B tables in the next snapshot. Existing video IDs also cannot receive later ASR/comments through this route. Historical raw files may survive, but the advertised current snapshot loses downstream continuity.
- Correction: carry forward all base tables with stable keyed deduplication and versioned enrichment updates, or publish immutable partitions with explicit snapshot lineage. Test at least two different successive batches, idempotent replay, an empty batch, and same-video enrichment. Reject existing output destinations as in R5.
- Additional limitation: `converter.py:114-116` loads old creator medians, and lines 234-254 create one-row baselines only for new creators. Existing creator aggregates are not recomputed when new videos arrive. Define an explicit baseline/cohort version rather than describing these values as continuously updated without qualification.
- Controlled verification: the root's [runtime probes](runtime-probes.json) reproduced A -> v2 with one row in each Sink B table; B -> v3 grew fact-video rows from two to three while retaining only one row per Sink B table; replaying A produced zero Sink B rows. These are controlled synthetic tests, not live-data measurements.
- Confidence: complete source flow and root-controlled fixture results.

### R7 — High: a relative engagement outlier cannot prove the script caused success

- Claim: `02_DATA_AND_RAG_REFACTOR_PROPOSAL.md:49` says an `8x` creator-normalized video proves an effective script/opening; `03_AI_ENGINEER_ARCHITECTURE_SPEC.md:20` asks why the videos won. Lines 199-201 describe optimal hashtag ranges and grounded production advice. `packages/script_engine/service.py:211` labels the observed duration IQR as optimal.
- Evidence: the formula divides snapshot plays by creator median plays; it does not measure script quality, paid distribution, exposure time, audience size at posting, recommendation traffic, visual quality, or causal effects. The manifest itself acknowledges a creator-centric cohort and single-snapshot engagement observations. The analytics implementation at `packages/analytics/engine.py:243-248` computes ordinary duration and hashtag percentiles over the matched slice, not an estimated optimum.
- Consequence: the formula is a useful descriptive outlier/ranking feature, but the claimed explanation or optimization does not follow. Older videos have had different exposure periods; the transcription subset was selected for high performance, further limiting representativeness.
- Correction: use terms such as historical creator-relative outperformance, observed niche distribution, and associated posting hours. Show dates, creator count, sample count, missingness, uncertainty, and relaxed filters. Separate creative suggestions from source-observed facts. Causal uplift or best posting policy would require a different study and is outside the current owner scope.
- Confidence: mathematical consequence of the stated metric and observational design, not a fresh effect-size measurement.

### R8 — Medium: structural duration/format filters are relaxed despite the architecture contract

- Claim: `03_AI_ENGINEER_ARCHITECTURE_SPEC.md:200` makes duration and format strict, while treating occasion, price, and city as soft. The earlier audit specifically identifies long source videos for short script requests as a problem (`01_LIMITATIONS_AND_BUGS_AUDIT.md:27`).
- Evidence: `packages/retrieval/service.py:111` drops duration first, then can eventually drop format. Lines 162-166 issue an entirely unfiltered lexical search when filtered lexical hits are empty. `packages/analytics/engine.py:122` uses the same duration-first relaxation order, while retrieval relaxes when fewer than a minimum candidate count and analytics relaxes only at zero matches.
- Consequence: a fifteen-second brief can again use much longer sources. The statistics and retrieved examples may describe different relaxed populations, even though the script flow presents a shared niche evidence pack. Returned relaxation names partially disclose behavior but do not make it conform to the strict contract.
- Correction: define and share one filter policy; preserve explicitly strict fields or return insufficient evidence. Show the final population and each relaxation in the UI and generated response. If duration is deliberately soft, amend the contract and evaluate that choice rather than treating it as already fixed.
- Confidence: direct source comparison.

### R9 — Medium: new context/anatomy labels are weak extraction, not verified ground truth

- Claim: `02_DATA_AND_RAG_REFACTOR_PROPOSAL.md:16` suggests full transcript and deep labels for approximately 22,500 rows; lines 28-38 describe LLM batch relabeling and a hook representing the first 3-5 seconds. The architecture carries these fields into evidence cards.
- Evidence: `packages/taxonomy/rule_extractor.py:80-81` assigns afternoon-snacking occasion even when there is no occasion evidence. Lines 103-115 use first/last text sentences as hook/CTA, which do not establish timing or rhetorical function. `pipelines/enrich_taxonomy_batch/__main__.py:32` only selects unspecified-price rows; lines 55-67 ask for price/persona and append raw output to a checkpoint. It does not populate occasion/anatomy or merge validated results into a new Gold snapshot. The local manifest reports 21,748 transcripts, rather than the draft's approximately 22,516.
- Consequence: defaults create artificial context frequencies and potentially misleading filters. Untimed transcripts cannot prove a 3-5 second hook. A resumable checkpoint is not a completed, validated enriched corpus.
- Correction: preserve unknown labels; add extractor/version/source/confidence fields; distinguish human labels, historical LLM outputs, rules, and inferred defaults. Audit a stratified sample for each field. Label source opening text separately from acoustically timed hooks, and merge schema-validated enrichment only through new snapshot publication.
- Confidence: code inspection and manifest reading; no extraction-accuracy measurement was performed.

### R10 — Medium: current architecture status, readiness, and receipts differ from the draft

- Claims: `03_AI_ENGINEER_ARCHITECTURE_SPEC.md:68` and `:199` specify DuckDB; line 197 requires readiness to check DuckDB, Qdrant, and Redis with typed 503 failures; line 202 promises receipt-verified evaluation. `04_IMPLEMENTATION_PLAN.md:51-97` checks the baseline tasks as complete.
- Evidence: `packages/analytics/engine.py:64-65` loads pandas DataFrames and computes statistics with pandas/NumPy. `/health/ready` (`apps/api/app/routers/health.py:22-38`) always returns `status="ready"` after checking optional Qdrant readiness, with no Redis test. `apps/api/app/dependencies.py:30-34` serves the benchmark JSON without receipt/corpus/index hash checks. The active milestone plan is more candid at `:110`, deferring live dense indexing to M6, and identifies 21,748 transcripts at `:14`.
- Consequence: pandas is a viable small-corpus implementation choice; the problem is an inconsistent contract and readiness claim, not a requirement to replace working pandas with DuckDB. A stale evaluation JSON can be displayed next to a different runtime snapshot/index.
- Correction: designate one authoritative current architecture/status document and mark earlier alternatives as superseded. State actual implementations explicitly, define readiness per capability/profile, and bind frozen evaluations to immutable runtime artifacts.
- Confidence: source comparison; no Docker runtime was launched.

### R11 — High for immediate reproducibility: the runtime data and index are absent locally

- Evidence: a fresh `Get-ChildItem -Force data/corpus/20261116_v1` returned only `manifest.json`. The manifest lists `dim_creators.parquet` and `fact_videos.parquet`, but neither file was present. `artifacts/indexes/` was absent. `apps/api/app/dependencies.py:43-50` loads both verified corpus and index at startup, before app construction completes (`apps/api/app/main.py:28`).
- Consequence: the current checkout cannot reproduce the claimed real-corpus demo or rerun data-dependent checks from install commands alone. A historical manifest or frozen benchmark does not prove the data is present today. This finding does not show that the owner's original local corpus was deleted elsewhere.
- Correction: locate the preserved owner dataset/Gold files, verify against the trusted preservation and snapshot manifests, and document a reproducible rehydration path. Obtain missing historical assets from the identified upstream revision or an existing preserved copy; do not recrawl old TikTok videos. Keep availability, license, and immutable checks separate.
- Confidence: fresh local filesystem check. Root investigator verifies upstream asset accessibility and full test outcomes.

## Module feasibility for one engineer, CPU, and zero paid spend

The assessments below are engineering judgments, not measured completion times or performance guarantees.

| Module | Current evidence | Feasibility and boundary | Required condition before acceptance |
| --- | --- | --- | --- |
| Historical data preservation and Gold merge | Builder, manifest format, and detailed historical inventory exist; required local tables are absent. | High for recovering available owner/upstream inputs; blocked locally until assets are present. | Verify raw inventory and Gold hashes; reject snapshot overwrite; record source/build lineage. |
| Taxonomy and POI normalization | Finite regex/dictionary rules and legacy labels. | High for a weak-label baseline; partial for broad Vietnamese locations and context. A platform POI tag is useful provenance, not independently verified physical truth. | Preserve unknowns and audit field accuracy; normalize timezone and administrative-location semantics explicitly. |
| Descriptive niche statistics | Pandas/NumPy engine, filters, timings. | High locally for approximately 71K metadata rows. DuckDB is optional until measured need. | Sufficient creator/sample support, dates, missingness, shared filters, and association-only wording. |
| BM25 retrieval and heuristic reranking | Explicit sparse index/search/rerank code, frozen 16-query artifact. | High as a CPU baseline; current index must be restored/rebuilt. | Correct metric names, independent relevance labels, receipt matching, and real-corpus quality checks. |
| Dense embeddings, Qdrant, RRF | Query encoder and HTTP adapter exist; document indexing absent. | Conditional. Batch locally, prebuild offline, measure CPU memory and latency; avoid putting heavyweight downloads on first request. | Populated index with model/config hashes, correct prefixes/chunking, mode-specific benchmarks, honest degraded status. |
| Neural Cross-Encoder | Model name in settings; heuristic scorer implementation. | Conditional and optional for the demonstration. | Declare dependencies, cap candidates, demonstrate held-out gain over the simpler reranker under CPU latency budget. |
| Gemini script drafting | Single synthesis call in current service, explicit offline mode and typed key/quota errors. | Conditional on a usable free-tier owner key; quota availability cannot be guaranteed by application settings. | Root provider review; request/token/time budgets, strict output validation, supported citations, explicit draft/creative status. |
| Shooting advice | Generic templates and synthesized text; no implemented visual extraction in this refactor. | High as clearly labeled creative guidance; unsupported as evidence of actual reference camera techniques. | Separate source-observed text facts from proposed filming directions; visual claims require new legitimate visual evidence. |
| FastAPI and Gradio demonstration | Typed routes, error handler, ASGI mounting and in-process HTTP calls present. | High after local corpus/index recovery. | Real-data startup/smoke checks, capability-specific readiness, no unsupported pass badges. |
| Rolling dual-sink ingestion | Converter publishes five tables and unit fixture for one batch. | Feasible after continuity defects are fixed; a live 4-month stream remains separate work. | Two-batch/replay/enrichment tests, all-table lineage, immutable output, updated creator statistics/cohort policy. |
| Voice timing/prosody | Later active milestones depend on audio/Whisper work; original refactor has text only. | Conditional on obtaining fresh audio and a measured CPU workload. | Distinguish ASR estimates and WPS interpolation from observed acoustic timing; do not claim historical prosody from transcripts. |
| Seeding/ABSA/trust | Later heuristic scaffolds exist; not part of this draft's original corpus evidence. | Feasible as auditable text baselines on new comments; unsupported as validated bot intent, diner experience, or hidden sponsorship truth. | Manual domain labels, uncertainty/abstention, missing-aspect handling, creator-separated evaluation; root scientific review covers details. |
| Airflow/Redis/three-service deployment | Cron/Airflow proposed; Redis/Qdrant Compose provided. | Optional operational complexity for one engineer. Local batch CLIs and one service are a practical first acceptance target. | Introduce services only for measured retrieval or concurrency needs; root hosting review must validate free-tier limits independently. |

## Recommended order

1. Recover and verify the preserved inputs and current Gold/index artifacts; establish exact schema, date, license, and lineage contracts.
2. Fix immutable publication and multi-batch continuity, then verify all five tables and replay behavior with fixtures before collecting a larger stream.
3. Correct metric semantics and create a modest independently judged evaluation set before tuning further retrieval/ranking features.
4. Accept a truthful local baseline: descriptive analytics, BM25 plus heuristic ranking, typed API, one Gradio demonstration, and explicit creative script drafting.
5. Strengthen grounding/schema/duration/provider enforcement and rebuild frozen evaluation receipts.
6. Add bounded dense indexing and optional neural reranking only after measuring gain and CPU cost. Expand fresh-data ABSA/prosody one evaluated module at a time; do not infer these modalities from missing historical inputs.

## Verification provenance and limits

This reviewer read `superpowers/7.0.1/skills/using-superpowers/SKILL.md` (whose dispatched-subagent clause exempts an independently dispatched worker from its main orchestration workflow) and `verification-before-completion/SKILL.md`, plus repository `AGENTS.md` and the root audit's pre-existing spec/plan. The review followed the bounded investigation task; it did not execute an implementation/TDD workflow or claim prior work followed one.

Fresh commands used PowerShell with `login:false`, UTF-8 content reads, `rg` source searches, numbered source extracts, Git revision inspection, direct directory listings, and `ConvertFrom-Json` cardinality checks. The initial `rg --files` requests for `artifacts/indexes` returned a missing-directory error, which was retained as an availability finding rather than treated as a passing check. A wildcard search under `data/evaluation/v1/*` failed because of Windows argument handling; the query file was subsequently read directly and all 16 rows counted successfully. No test, benchmark, provider, or crawl was run by this reviewer. The root separately ran [controlled fixture probes](runtime-probes.json), which corroborate R4-R6; these must be distinguished from corpus-dependent/full-environment test outcomes in the root report.

Primary external references accessed 2026-11-17: [scikit-learn recall definition](https://scikit-learn.org/stable/modules/generated/sklearn.metrics.recall_score.html) and [the model author's multilingual E5 card](https://huggingface.co/intfloat/multilingual-e5-base). Exact historical dataset claims in the six reviewed documents remain historical claims unless corroborated by the root's upstream/data review.
