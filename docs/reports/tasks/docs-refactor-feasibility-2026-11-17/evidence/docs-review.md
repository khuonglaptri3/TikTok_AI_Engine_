# Documentation and scientific feasibility review

- Review date: 2026-11-17, Asia/Saigon.
- Scope: all nine original files under `docs/`, excluding this newly authored audit bundle; selected implementation, contracts, tests, evaluation queries, and frozen benchmark needed to assess the documents.
- Authorization and boundaries: the parent investigator's [specification](../superpowers/spec.md) and [plan](../superpowers/plan.md); read-only investigation, with this evidence document as the only assigned write. No provider call, network crawl, data mutation, installation, or milestone-status change.
- Process provenance: read `C:/Users/lanph/.codex/plugins/cache/openai-curated-remote/superpowers/7.0.1/skills/using-superpowers/SKILL.md`; its subagent instruction delegates execution workflow to the assigned task. Read and applied the evidence-before-claims rule from the same package's `verification-before-completion/SKILL.md`. Source inspection and a bounded PowerShell calculation support this review; no runtime pytest/mypy success is claimed here.

## Conclusion

The historical analytics, lexical retrieval, typed API, and a simple demonstration are a coherent feasible core. The documents already acknowledge important limitations of the creator sample and engagement snapshot. They do not yet justify scientific claims about optimal content, undisclosed sponsorship, coordinated seeding, actual diner consensus, or exact historical timestamps. A useful prototype can be delivered by narrowing those claims and establishing independent evaluation before extending the multimodal stack.

The most urgent issues are the nonstandard metric called `Recall@10`, insufficiently independent retrieval judgments, a sponsorship target unsupported by the proposed labels, synthetic-only evidence for the incremental collector and trust modules, and completion claims that exceed the available report trail. Frozen benchmarks are historical measurements, not current runtime verification.

## Reviewed documentation

| Original file | Classification and review result |
| --- | --- |
| `docs/planning/TikTok_AI_Engine_Milestone.md` | Active scope and status authority; fully read. Contains important explicit limitations and gates, but also unsupported acceptance assumptions and incomplete task traceability. |
| `docs/planning/TikTok_AI_Engine_Resources_and_Deployment.md` | Active execution profile; fully read. Its latency is a frozen lexical measurement; it does not specify a complete hosting or multimodal throughput budget. |
| `docs/data-cards/tiktok_fnb_corpus_v1.md` | Active historical data card; fully read. Correctly documents creator selection, one engagement snapshot, and transcript selection; completeness and annotation accuracy remain distinct from checksums. |
| `docs/reports/milestones/README.md` | Current report index; fully read. Contains only M0.1 despite many separately completed/in-progress tasks in the plan. |
| `docs/reports/milestones/M0.1/README.md` | Historical completion report; fully read. Aggregates M0.1-M3.2 implementation and reports historical verification without raw logs or a preservation inventory. |
| `docs/reports/milestones/M0.1/superpowers/spec.md` | Existing M0.1 scope record; fully read. Scope is much wider than the named legacy-audit task in the active plan. |
| `docs/reports/milestones/M0.1/superpowers/plan.md` | Existing M0.1 execution record; fully read. Includes multiple later milestones' implementations under M0.1. |
| `docs/reports/milestones/M0.1/evidence/workflow.md` | Historical provenance assertion; fully read. Ten lines record pass claims, with no exact skill paths/version, command logs, environment, commit SHA, original-file checksums, or check output. |
| `docs/reports/Case_Study/README.md` | Empty study index; fully read. No case-study result is implied. |

## Findings

### D01 - HIGH: the reported Recall@10 is a different metric

**Evidence:** `pipelines/benchmark_retrieval/__main__.py:105-107` divides top-10 relevant hits by `min(number_of_relevant_documents, 10)`. Conventional recall divides by the full number of relevant documents. The frozen artifact reports `recall_at_10=0.7094` at `artifacts/benchmarks/retrieval_v1.json:18`, and the active plan repeats it at `docs/planning/TikTok_AI_Engine_Milestone.md:23,113`.

**Bounded fresh calculation:** PowerShell parsed all 16 lines of `data/evaluation/v1/queries.jsonl` without exposing document identities. Relevant-set sizes are `1011, 1, 179, 12, 62, 67, 138, 15, 112, 215, 272, 46, 33, 231, 4, 320`. The mean of `min(10, count)/count` is `0.294768`. Thus even a perfect top-10 ranking could not obtain conventional macro Recall@10 above about 0.295 on these qrels. The reported 0.7094 cannot be interpreted as conventional recall. No corrected actual recall was computed because the frozen artifact has no per-query rankings/hits.

**Consequence:** the metric name overstates corpus coverage and is not comparable with standard retrieval results. This does not invalidate the separately computed reciprocal-rank values.

**Next step:** retain the existing artifact as historical evidence, assign this formula an explicit custom name if retained, calculate true Recall@10 alongside Precision@10/MRR/nDCG, and preserve per-query rankings, judgments, and metric definitions in a new versioned evaluation artifact.

### D02 - HIGH: retrieval judgments and acceptance tests do not establish independent generalization

**Evidence:** `pipelines/benchmark_retrieval/__main__.py:17-18` describes its generated queries as independent, but `:29-60` defines 16 topic queries and obtains relevance from keyword containment in the same indexed captions/transcripts plus category/city metadata. No human adjudication, dev/test split, query provenance, or qrel exhaustiveness is recorded in `data/evaluation/v1/queries.jsonl`. `tests/eval/test_retrieval_benchmark.py:8-18` reads a saved JSON artifact rather than executing search and accepts `MRR>=0.50`, `nDCG>=0.35`, `p95<=2000ms`; active G2 requires `MRR>=0.75` at `docs/planning/TikTok_AI_Engine_Milestone.md:209`, and M2.2 names the precise 21ms result as verified by that test at `:113`.

The frozen comparison itself is mixed: reranking changes MRR from `0.8875` to `0.8127`, nDCG from `0.6962` to `0.7083`, and p95 from `8.5` to `21.0ms` (`artifacts/benchmarks/retrieval_v1.json:8-22`). It supports a small nDCG improvement and a lower MRR on this weakly labeled sample, not a universal reranking improvement. It contains no dense or actual hybrid run; `_evaluate_run` forces `mode="bm25"` at `pipelines/benchmark_retrieval/__main__.py:92-98`.

**Consequence:** lexical matching is partly evaluated against lexical relevance rules. This is weak-label circularity, not evidence of deliberate train/test leakage; there is insufficient provenance to establish whether these queries were also used for tuning. A passing frozen-artifact test cannot verify current code, quality on synonyms/negation, or present CPU latency.

**Next step:** freeze independently authored dev and held-out queries, pool results across retrieval methods for blinded human relevance judgments, cover Vietnamese synonyms/accents/negation/filter failure/no-answer cases, report per-query paired differences and uncertainty, and align executable gates with the documented targets. Repeat latency with hardware, warm/cold state, repetition count, and concurrency recorded. Do not require hybrid to win as a predetermined scientific result.

### D03 - HIGH: disclosed-ad and e-commerce flags do not label undisclosed sponsorship

**Evidence:** `docs/planning/TikTok_AI_Engine_Milestone.md:159-165` proposes a supervised undisclosed-PR detector trained on `is_ad=True` and `is_ec_video=True` historical examples, with prosody and lexical features. These flags describe disclosure/commerce, not sponsorship that was deliberately undisclosed. The current heuristic sets `undisclosed_pr_risk=1.0` whenever either flag is true at `packages/absa/analyzer.py:245-259`. Historical data lack the audio/prosody required by M4.1 (`docs/reports/milestones/M0.1/README.md:42`; active plan `:155` assigns audio processing to fresh videos), so the proposed historical-label/prosody training join also lacks a documented source.

**Consequence:** held-out creator splitting alone cannot repair target mismatch or establish probability calibration for undisclosed sponsorship. Treating all unflagged videos as negative would add unverified negative labels; shop content also includes a different domain from restaurant reviews. The current 0-1 heuristic is not an empirically calibrated probability and paradoxically gives maximum *undisclosed* risk to disclosed ads.

**Next step:** separate factual disclosure indicators from a clearly labeled promotional-language heuristic. Either rename the supervised task to prediction of observed platform flags with explicit proxy limitations, or obtain an independently verified sponsorship dataset with unknown labels retained as unknown. Train lexical-only historical baselines separately from any future audio model. Use creator/time/venue grouping, exclude label-derived features, evaluate relevant false-positive costs and calibration, and refrain from asserting hidden commercial intent.

### D04 - HIGH: seeding intent and viewer truth exceed the observable data and current algorithm

**Evidence:** the plan promises bot/seeding clustering and a manually audited comment slice (`docs/planning/TikTok_AI_Engine_Milestone.md:169-175`), but current decisions are URL/contact matches, empty/emoji text, pairwise shingle similarity, and four canned-praise phrases (`packages/seeding/detector.py:8-19,47-99`). The input contract has no comment time or cross-thread history (`packages/data_contracts/multimodal.py:16-23`), so temporal bursts or coordinated networks cannot be evaluated from the stored representation. The unit example is four authored comments selected to match the rules (`tests/unit/test_incremental_absa_seeding.py:41-71`); it is not an annotated TikTok benchmark.

**Consequence:** duplication/spam indicators can be useful, but do not establish bots, payment, or coordinated seeding. Organic repeated praise, jokes, emojis, and contact information can be misclassified. Filtering positive-looking comments can systematically reduce viewer sentiment and increase `pr_hype_gap`; the downstream trust score is therefore not an independent validation of the filter. Nonfiltered commenters are not thereby verified restaurant visitors.

**Next step:** expose evidence-based labels such as duplicate/contact/noise indicators, preserve originals and rule reasons, and keep unknown intent explicit. Audit independently sampled real comments with annotation guidelines, disagreements, and per-class precision/recall. Report the sentiment gap both before and after filtering, with sensitivity to the threshold. Add time/network evidence only if the intended coordination task and collection protocol require it.

### D05 - HIGH: the ABSA gap conflates missing aspects with neutral sentiment and lacks required citations

**Evidence:** the plan's M5.2 acceptance requires exact comment/utterance citations (`docs/planning/TikTok_AI_Engine_Milestone.md:177-183`). `score_text_aspects` applies a single clause polarity to every matched aspect, assigns unmatched sentiment to taste, and returns `0.0` for empty aspect buckets (`packages/absa/analyzer.py:179-216`). `analyze_koc_vs_viewer_absa` averages all four aspect scores for each group regardless of aspect coverage (`:227-243`). `AbsaComparisonRecord` contains strings for pain points, but no comment ID, utterance ID, source offset, or aspect observation count (`packages/data_contracts/multimodal.py:100-110`); ingestion drops those identities too (`pipelines/ingest_incremental_to_gold/converter.py:272-288`).

**Consequence:** a taste-only creator score of +1 and a service-only viewer score of -1 produce a cross-aspect gap even though the two groups discuss different things. No comments produces zero gap by copying the creator mean, which is absence of evidence rather than agreement. Matching an entire clause distributes one aspect's polarity to others. The current records cannot meet exact-citation acceptance, and the gap is not evidence of deception, poor food hygiene, or actual diner consensus.

**Next step:** represent absent/uncertain aspects separately from observed neutral sentiment; retain source spans and IDs, per-aspect support, and language/negation context. Compare only appropriately supported overlapping aspects, show an insufficient-evidence state, and report intervals/sensitivity. Build a separately adjudicated Vietnamese F&B aspect-span/polarity test set, macro/per-aspect F1 and agreement, then evaluate the downstream gap independently. Gemini agreement alone must not become the gold truth.

### D06 - HIGH: citation-ID membership is insufficient to establish grounded scripts

**Evidence:** M2.3 accepts stripping hallucinated IDs and cliché checking (`docs/planning/TikTok_AI_Engine_Milestone.md:115-121`); the M0.1 report describes a Citation-Grounded Script Engine (`docs/reports/milestones/M0.1/README.md:12`). The guardrail only tests cited-ID membership; when no citation survives, it attaches an arbitrary available ID (`packages/llm/guardrails/verifier.py:37,50-63`). It reports a citation ratio of 1.0 when there are no submitted citations but available evidence exists (`:82`), and does not check textual entailment. The offline template asserts fresh ingredients, firsthand tasting, reasonable price, and favorable quality independent of source support (`packages/script_engine/service.py:120-144`), while attaching available video IDs (`:177-201`).

**Consequence:** a real video ID may accompany an unsupported claim; attaching a fallback ID can make unsupported dialogue appear sourced. Existing tests can confirm structural citation integrity and bounded behavior, not factual grounding or genuine firsthand experience.

**Next step:** distinguish suggested creative directions from source-supported factual statements. Require an exact supporting excerpt per factual claim, keep unsupported beats explicitly uncited or remove them, and report citation coverage separately from source validity and entailment precision. Audit claims against source excerpts rather than counting IDs. Keep creative staging suggestions visibly separate from historical evidence.

### D07 - HIGH: M3.2 completion and the M3.3 freshness dependency exceed the implemented collector

**Evidence:** M3.2 is `COMPLETE` and claims audio/comments collection plus resumable manifests (`docs/planning/TikTok_AI_Engine_Milestone.md:133-139`). Its CLI builds authored demo records when `--seed-demo-batch` is used (`pipelines/crawl_incremental/__main__.py:18-92,115-133`); otherwise it only prints `ready_for_live_crawl` and tells the operator to invoke a worker (`:135-146`). No live discovery/comment collector is invoked. `write_incremental_batch` rewrites one JSONL file (`pipelines/crawl_incremental/crawler_service.py:82-90`), which is not a resumable crawl protocol. The window helper itself is usefully tested, but this does not demonstrate a working collector.

M3.3 requires fresh videos searchable at once (`docs/planning/TikTok_AI_Engine_Milestone.md:141-147`), while Whisper is a later M4.1 dependency (`:151-157`). Fresh records default to empty transcript (`packages/data_contracts/multimodal.py:56`), and both index construction and serving only include transcribed rows (`pipelines/build_dense_sparse_index/__main__.py:18`; `packages/retrieval/service.py:37`).

**Consequence:** the plan currently treats collector implementation as a completed prerequisite. Metadata-plus-audio rows alone cannot enter the existing RAG path; synthetic demo records already include authored transcripts and segments, masking that dependency.

**Next step:** distinguish cutoff utilities, offline fixtures, live worker implementation, and successful bounded capture as separate deliverables. Pilot a capped real cohort with failures and comment coverage recorded before estimating the full capture. Move transcript generation before searchability acceptance, or explicitly support metadata-only retrieval with its own evaluation. Require resumable/idempotent capture and repeated-ingestion verification before calling the stream operational.

### D08 - MEDIUM: descriptive historical statistics must not become causal or optimal-content claims

**Evidence:** the data card explicitly identifies the creator-centric sample, single March-April 2025 engagement snapshot, and selected transcripts (`docs/data-cards/tiktok_fnb_corpus_v1.md:23-26`). Yet the script output calls the duration IQR optimal (`packages/script_engine/service.py:210-211`), and the refactor architecture asks why videos won and specifies an optimal hashtag IQR (`ReFactor_structure/03_AI_ENGINEER_ARCHITECTURE_SPEC.md:20,199`; `ReFactor_structure/04_IMPLEMENTATION_PLAN.md:80`). Actual analytics calculate descriptive quantiles and rank posting hours by median snapshot views, with some cells having only two observations (`packages/analytics/engine.py:171-177,197-221,240-250`).

**Consequence:** creator size, topic, video age/exposure, seasonality, selective transcription, and unmeasured platform distribution can explain associations. Creator-normalized plays do not control those factors. Full-sample duration/hashtag IQRs are common historical practices, not estimates of an optimal intervention. Late-2026 trend claims cannot come from 2023-2025 observations; even fresh cumulative counts have unequal exposure ages.

**Next step:** label outputs as historical descriptive benchmarks, expose observation window, support counts and uncertainty, and abstain on sparse slices. Distinguish the selected transcript subset from the metadata cohort. If predictive experiments are later added, use an as-of timestamp, creator/time holdouts, fixed prediction horizons, and exclude target/outcome-derived features. A claim of causal uplift needs a separate experimental design; it is not required for this demonstration.

### D09 - MEDIUM: timestamp provenance is a good start, but accuracy and physical bounds are untested

**Evidence:** M4.1 calls Whisper segments exact and plans historical `wps_estimated` backfill (`docs/planning/TikTok_AI_Engine_Milestone.md:155-157`); M6.2 demands zero fabricated timestamps (`:201`). Current segment creation trusts supplied segment boundaries or cumulatively estimates sentence time from whitespace-token count (`pipelines/ingest_incremental_to_gold/converter.py:46-92`). `RawWhisperSegment` and `VoiceSegmentRecord` only bound start/end individually to nonnegative values (`packages/data_contracts/multimodal.py:8-13,61-73`), with no end-after-start, monotonicity, or video-duration constraint. The synthetic fixture simply asserts a supplied record becomes `whisper_exact` (`tests/unit/test_incremental_absa_seeding.py:165-170,193-195`).

**Consequence:** supplying a timestamp field does not establish audio alignment. Estimated historical offsets cannot support exact playback claims, and an ASR segment boundary is an estimate requiring error evaluation. Current schemas also allow impossible ranges. Whitespace counts in Vietnamese generally count syllable-like units and total video duration includes silence, so the measure is not a validated speech articulation rate.

**Next step:** preserve estimated-versus-audio-derived provenance visibly in APIs/UI; validate temporal invariants and duration bounds; measure manual boundary error and ASR error on a small audio sample; and define citation correctness/coverage separately. Keep estimated historical timestamps out of any exact-audio claim. Choose tolerances before evaluating.

### D10 - MEDIUM: report provenance is too thin to reproduce completed-task claims

**Evidence:** the active plan independently marks M0.2, M0.3, M1.1, M1.2, M2.1-M2.3, M3.1, M3.2 complete and M5.1-M5.2 in progress (`docs/planning/TikTok_AI_Engine_Milestone.md:23,47-61,73-87,99-121,125-139,169-183`). Only M0.1 appears in the report index (`docs/reports/milestones/README.md:5-7`). M0.1 describes itself as M0.1-M3.2 baseline initialization and points only to `main`, not a commit SHA (`docs/reports/milestones/M0.1/README.md:5-6`). Its only in-directory evidence file is a short pass-claim narrative (`evidence/workflow.md:4-9`). SHA256 entries cover two derived Gold tables (`data/corpus/20261116_v1/manifest.json:11-25`), not the 37,840 original source files whose preservation is asserted (`docs/reports/milestones/M0.1/README.md:50`).

**Consequence:** a reviewer cannot independently reproduce the original-file preservation comparison, original runtime environment, strict-typecheck result, or per-task acceptance from these artifacts. Derived-file checksums protect the current derived artifact against unrecorded changes; they do not establish original-file preservation, correct annotations, or physical POI accuracy. This audit does not infer that the historical work failed; it identifies absent supporting evidence. In this checkout `data/` contains only corpus manifests and evaluation assets, so the historical heavy-data claim cannot be reverified by this reviewer.

**Next step:** retain historical assertions as historical. Add a dated verification activity at a fixed revision with actual command output/environment and available input hashes; do not backdate provenance. Give each actually started milestone its own canonical spec/plan/report and index row, or explicitly reconcile scope into the task model. Record unavailable original inventories as an unresolved evidence gap rather than inventing retrospective hashes.

### D11 - MEDIUM: transcript validation and POI restoration are stronger claims than implemented checks support

**Evidence:** the data card calls 21,748 transcripts validated speech and calls restored POIs official GPS (`docs/data-cards/tiktok_fnb_corpus_v1.md:8-9,19`). Transcript acceptance tests only minimum string length and a refusal-prefix denylist (`pipelines/build_gold_corpus/builder.py:120-125`), then merges legacy annotations (`:374-405`). No audio reference transcription, word/character error measurement, or factual-accuracy audit is recorded. Restored fields are POI name/address/city/category, not latitude/longitude (`:356-362`).

**Consequence:** these are successfully parsed/filtered transcripts and restored platform POI metadata; neither checksum verification nor the platform check-in label establishes accurate spoken content or actual physical presence. Legacy LLM summaries and location guesses may propagate into retrieval evidence and labels.

**Next step:** use qualified terms such as parse/filter-accepted transcript and restored TikTok POI metadata. Preserve per-field source lineage, manually audit a stratified subset of transcript/location/taxonomy outputs, and publish coverage/error/unknown rates. Reserve audio accuracy claims for the fresh audio cohort where reference assessment is possible without historical recrawling.

### D12 - MEDIUM: the eight-week plan has no bounded workload or complete evaluation/gate tasks

**Evidence:** one engineer is assigned eight working weeks (`docs/planning/TikTok_AI_Engine_Milestone.md:5-6`), but the fresh creator/video/comment/audio cohort size and capture success threshold are unspecified (`:141-147`), CPU Whisper plus historical backfill has two allocated days (`:151-157`), and sponsorship training/calibration has two days (`:159-165`). Manual comment evaluation is required but no sample size/annotation task is budgeted (`:175`); ABSA has no minimum F1/sample criterion (`:177-183`). M5.1b and M5.2b are mentioned but not defined (`:172,180`). G2-G6 list task IDs (`:209-213`) without the detailed task/window definitions present for M0.G/M1.G. The resources guide specifies tools but no audio-hours, CPU real-time factor, model RAM/disk, annotation effort, or end-to-end latency target (`docs/planning/TikTok_AI_Engine_Resources_and_Deployment.md:6-18`).

**Consequence:** the calendar is an intention, not a substantiated capacity estimate. No data in the documents justifies treating the entire live multimodal/research release as achievable on schedule. A narrow CPU demonstration remains plausible; collecting and validating multiple independent trust targets is the larger uncertainty. Empirical hybrid superiority cannot be guaranteed in advance.

**Next step:** first record a bounded pilot's capture success, comment coverage, audio minutes, ASR/embedding throughput, memory/disk peak, and annotation time. Estimate batch work as audio-hours times measured real-time factor plus review/retry cost. Define exact evaluation populations, quality thresholds, abstention policies, and release criteria; explicitly schedule labeling and gates. Prioritize the verified historical core and one fresh vertical slice, and defer hidden-intent sponsorship claims and extra model infrastructure until the data and independent evaluation justify them.

## Module-level feasibility and proposed sequence

| Module | Feasibility assessment | Minimum next evidence |
| --- | --- | --- |
| Immutable Gold metadata and taxonomy | Coherent CPU implementation pattern; historical claimed counts need accessible inputs and a fresh fixed-revision verification. | Original/derived lineage and hashes, schema/count checks, sampled label accuracy. |
| Niche Micro-Benchmarks | Feasible as descriptive historical summaries. | Sample counts, cohort window/coverage, uncertainty, non-causal output wording. |
| BM25 and phrase reranking | Plausible low-cost baseline; existing frozen report is lexical-only and uses weak relevance labels. | Correct metrics, held-out manually judged queries, paired baseline comparison, current runtime measurement. |
| Script API and Gradio | Useful local demonstration scope. | Claim-level source support, unsupported-claim behavior, bounded provider errors, smoke/integration checks at the audited revision. |
| Fresh incremental multimodal stream | Requires live collector implementation and a capped acquisition feasibility pilot. | Non-synthetic capture manifest, retry/resume/idempotency results, audio/comment coverage, transcript-before-indexing path. |
| ASR and prosody | Feasible to investigate on a bounded fresh-audio sample; throughput and quality unmeasured. | CPU real-time factor, RAM/disk, ASR and boundary error; prosody validated as a measured signal rather than intent detector. |
| Seeding and ABSA | Reasonable research baselines when presented as pattern indicators and sentiment estimates. | Independent labels, missing-aspect handling, source spans, filter sensitivity, calibrated uncertainty/abstention. |
| Undisclosed sponsorship | Current supervised target is not supported by the proposed labels. | Revised observable target or independently verified sponsorship ground truth; otherwise defer. |
| Timestamped dense/hybrid Q&A | Possible later integration, currently unvalidated. | Versioned dense indexes, corpus/index parity, fixed held-out ranking/grounding tests, temporal validity and end-to-end resource measurements. |

Recommended order: (1) reproduce the historical core and correct scientific wording/metrics; (2) independently evaluate retrieval and claim grounding; (3) implement and measure one capped fresh capture-to-transcript-to-search path; (4) annotate/evaluate ABSA and suspicious-comment patterns; (5) add audio timing and dense retrieval only when the measured budget supports them. Sponsorship intent requires a separate data decision, not another heuristic threshold.

## Verification scope and limitations

- Fresh source inspection: all nine original `docs/` files were read completely with numbered UTF-8 output. Relevant selected code/contracts/tests were inspected with exact references above.
- Fresh bounded computation: PowerShell `ConvertFrom-Json` read the existing 16 qrels and calculated only relevant-set sizes and the theoretical conventional Recall@10 ceiling (`0.294768`). This is a metric-definition check, not a new search benchmark.
- Existing frozen artifact: evaluated at `2026-11-16T08:13:30.101678+00:00`, as recorded in `artifacts/benchmarks/retrieval_v1.json:4`; all its performance values remain historical claims of that artifact.
- Runtime model accuracy, real live collection, current pytest/mypy, historical original-file preservation, and precise CPU performance were not independently established by this sub-review. Parent audit verification and upstream inspection are separate evidence sources.
- The checkout has no original heavy source datasets visible under `data/` during this review. No missing-data result is presented as evidence that the owner's separate preserved copy was deleted.
- No existing code, datasets, planning status, or original reports were changed. This review recommends future work; documentation completion does not pass any milestone gate.
