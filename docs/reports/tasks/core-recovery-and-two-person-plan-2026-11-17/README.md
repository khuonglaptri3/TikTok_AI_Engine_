# Core recovery and balanced two-person plan

- Status: COMPLETE
- Execution date: 2026-11-17 (Asia/Saigon)
- Requirement source: owner approval of the [audit follow-up](../docs-refactor-feasibility-2026-11-17/README.md), followed by the explicit two-person/equal-allocation instruction.
- Repository version: `main`, baseline `cdbc6ed9ccad11db437aa66c68638cf018701fe5`, with the reviewed recovery changes uncommitted.
- Specification: [spec.md](superpowers/spec.md)
- Execution plan: [plan.md](superpowers/plan.md)

## Conclusion

The authorized recovery and balanced-plan task is **COMPLETE**. All 37,840 selected historical files (1,504,284,701 bytes) are restored and independently verified. The rebuilt CPU core passes **57/57 project tests**, configured mypy for 75 source files, both package-source builds and the recovered-corpus API/Gradio probe, with **zero provider calls**. The active plan allocates **94 effort points to each contributor**, including reciprocal review and integration. Bundle/link/provenance/hash checks pass; no milestone gate is claimed.

## Work performed

- Preserved the existing audit and archived superseded planning documents. Recovery uses the pinned upstream archive without historical TikTok recrawling or importing legacy application code.
- Integrated snapshot staging/collision checks, required manifest coverage, multimodal carry-forward, explicit transcript/comment enrichment and parent-manifest lineage. Sparse comment updates retain omitted observed fields.
- Removed arbitrary fallback citations and unsupported firsthand template claims. Empty, uncited and mistimed drafts cannot pass structural checks; estimated timing uses `max(2 seconds, 5%)`. Structural acceptance does not establish claim-level factual grounding.
- Corrected standard Recall@10, exposed Precision@10 and label-cardinality ceilings, and added versioned query/corpus/index/code receipts. The legacy benchmark remains historical evidence.
- Made Gradio a base dependency and included pipelines in the Docker source context. Both source wheel builds pass; no actual container run is claimed.
- Rewrote the active plan for two equal contributors, with reciprocal reviews, bounded acquisition/annotation pilots, conditional multimodal gates and a CPU/offline baseline. The root overview remains intact with updated Quickstart and capability wording.
- Resolved all three Important findings from the final independent review in one TDD pass: source excerpts now survive draft shortening and only their IDs are cited; repeated same-video records retain distinct enrichment; initial and existing comments use the same keyed sparse-update normalization.

## Recovered core and measurements

Gold snapshot `20261117_recovered_v1` contains **264 creators, 70,996 unique videos, 21,748 accepted transcripts and 23,448 POI-bearing rows**, covering 2023-11-25 through 2025-03-19. Its video table has 49 columns; the generated tables' schema/counts/keys, creator joins, manifest checksums and index membership were verified. BM25 `bm25-v2` indexes 21,748 documents with 391,043 terms and 9,464,226 postings. The original two-file local baseline and historical benchmark remain intact. Source restoration proves the selected pinned inventory; the unavailable original owner-copy inventory was not independently reconstructed by assertion.

The new [benchmark receipt](../../../../artifacts/benchmarks/retrieval_v2.json) binds queries, corpus, index and implementation bytes. These are 16 frozen keyword/metadata weak-label queries, with a macro Recall@10 ceiling of **0.2948**; they are not independently judged relevance data.

| Configuration | Recall@10 | Precision@10 | MRR@10 | nDCG@10 | p95 (ms) |
| --- | ---: | ---: | ---: | ---: | ---: |
| BM25 + viral boost | 0.1837 | 0.6000 | 0.8875 | 0.6962 | 37.04 |
| Same + phrase reranking | 0.1901 | 0.6438 | 0.8127 | 0.7083 | 86.73 |

Reranking improved recall/nDCG while reducing MRR on this set. These standard recall values are not directly comparable with the older capped-denominator result. The original `retrieval_v1.json` is preserved as historical evidence; no positive gate or universal reranking advantage is inferred.

The CPU probe used Windows 11, Python 3.12.14 and a 12-logical-CPU Intel system, with sequential ASGI requests. App construction took 10,759.211 ms excluding module import. One observed request took 294.266 ms for niche analytics (283.22 ms internal), 691.255 ms for retrieval (685.96 ms internal) and 1,212.189 ms for the offline draft (1,209.81 ms internal). The hybrid-mode request spent 672.73 ms in its optional dense stage; a populated dense index/quality comparison remains future work. These single observations do not establish a p95 service budget. Every reported stage timing and actual source-resolving output is retained in the probe receipts.

`/health/ready` and `/demo/` returned 200. The offline draft passed structure/source-ID/timing checks at **44.9 seconds for a 45-second target** and remains `creative_draft` / `grounding_verified=false`. Missing key returned 503 `PROVIDER_KEY_MISSING`; a non-F&B brief returned 422 `UNSUPPORTED_DOMAIN`. No provider call or hosting deployment occurred.

## Outputs

| File | Purpose |
| --- | --- |
| [Workflow ledger](evidence/workflow.md) | Actual authorization, skills, progress, and verification provenance. |
| [Restoration record](evidence/restore-review.md) | Pinned historical input mapping, preservation method and limitations. |
| [Input verification](evidence/restore-verification.json) | Exhaustive reread of every selected file and preservation of original files. |
| [Integration manifest](evidence/integration-manifest.json) | Before/worktree/integrated SHA256 values for the 32 copied source/test files. |
| [Snapshot review](evidence/snapshot-review.md) | Earlier independent findings and the scope of that review. |
| [Final independent review](evidence/final-independent-review.md) | Three reproduced findings, their required fixes and all review boundaries. |
| [Metric/package record](evidence/metrics-packaging.md) | Original RED/GREEN observations, metric examples and packaging limits. |
| [Allocation](evidence/two-person-allocation.json) | Exact 94/94 point allocation, ownership, review and dependencies. |
| [Plan verification](evidence/plan-rewrite-verification.json) | Fourteen checks of allocation, archives, links and task traceability. |
| [Recovered core verification](evidence/recovered-core-verification.json) | Gold/index integrity, runtime module paths, hardware and actual endpoint/stage timings. |
| [Actual API outputs](evidence/recovered-api-outputs.json) | Returned readiness, benchmark, evidence cards and qualified offline draft. |
| [Full suite](evidence/final-full-suite.log) | Final 57-test project result after all review fixes and artifact builds. |
| [Build logs](evidence/recovered-gold-build.log) / [index](evidence/recovered-index-build.log) / [benchmark](evidence/recovered-benchmark-build.log) | Actual offline artifact-generation commands/results. |
| [Handoff verification](evidence/handoff-verification.json) / [final SHA256 manifest](evidence/final-sha256.json) | Canonical layout, current report/index, local links and final artifact/provenance hashes. |

The canonical [specification](superpowers/spec.md) and [plan](superpowers/plan.md) were created on 2026-11-17 before implementation under the owner's existing execution authorization. Resumption amendments are dated in the ledger; prior observations are not represented as new measurements.

## Verification

| Check | Result | Scope / evidence |
| --- | --- | --- |
| Restored input inventory and preservation | PASS: 37,840 files / 1,504,284,701 bytes | [Independent verification](evidence/restore-verification.json), all selected files gitignored, original files unchanged. |
| Focused snapshot, script and metric regressions after review fixes | PASS: 42 tests | [Review RED](evidence/final-review-red.log) / [GREEN](evidence/final-review-green.log); original RED logs remain in evidence. |
| Configured `mypy packages apps pipelines` | PASS: 75 source files | [Type check](evidence/core-final-mypy.log). |
| Root and Docker COPY-context wheel builds | PASS | [Package check](evidence/package-final.log); Docker engine was not used. |
| Scoped Ruff | PASS | [Final lint](evidence/scoped-lint-final.log); initial two import-order findings were corrected. |
| Two-person plan verification | PASS: 14 checks | [Verification](evidence/plan-rewrite-verification.json), K=94 / N=94 points. |
| Final project `python -m pytest` | PASS: 57 tests, 78.33 seconds | [Final suite](evidence/final-full-suite.log), includes API/demo, corpus, ingestion, guardrails and metrics. |
| Actual recovered-corpus API/Gradio probe | PASS; zero provider calls | [Probe](evidence/recovered-core-verification.json) and [outputs](evidence/recovered-api-outputs.json); verifies checkout module paths. |
| Secret scanner | PASS: zero leaks | [Scanner](evidence/final-secret-check.log). |
| Full suite before regenerated artifacts | FAIL (intermediate): 44 passed / 5 failed | [Intermediate observation](evidence/resumed-suite-before-data.log); all five missing-data failures are resolved by the final 57-test run. |
| Final bundle, links, receipt provenance and byte hashes | PASS | [Handoff result](evidence/handoff-verification.json) and [SHA256 manifest](evidence/final-sha256.json); rechecked after final status reconciliation. |
| `git diff --check` | PASS | [Output](evidence/final-diff-check.log); only informational LF/CRLF warnings. |

The first queued build failed on PyPI DNS before pipeline execution; offline cached resolution then succeeded. The first detailed probe imported an installed wheel and resolved data under site-packages; the evidence script was corrected to insert/assert current checkout modules, and the later probe passed. Both failures remain preserved in [the build log](evidence/gold-initial-network-failure.log) and [the probe log](evidence/core-probe-import-path-failure.log). Neither is presented as a successful pipeline observation.

## Open issues

| Issue | Impact | Follow-up / responsible task |
| --- | --- | --- |
| Frozen query labels are keyword/metadata-derived | Correct metrics do not establish independent relevance quality | M2.2 human-judged pilot. |
| Structural validation cannot verify factual claims | Drafts require claim/source review before factual use | M2.3 held-out claim audit. |
| Live collector, audio alignment and independently labeled trust diagnostics remain unaccepted | Synthetic/manual demonstrations do not prove fresh collection or real-world accuracy | M3–M6 gates. |
| Source rights, live free-tier eligibility and hosting fit unresolved | No public data redistribution or deployment acceptance | Conditional G1/G6 follow-up; local/offline scope retained. |
| Some inherited Gold caveat text uses approximate transcript counts/date ranges | Structured rebuilt counts/date bounds above are authoritative for this run; semantic annotation quality is unverified | M1.1 qualified data-card/lineage audit. |
| Docker engine/image and browser interactions were not run | Source-package and in-process ASGI checks have bounded scope | Reproduce an actual container/browser run before claiming those environments accepted. |

## Acceptance and handoff

| Task criterion | Result | Evidence |
| --- | --- | --- |
| Recover pinned historical sources and preserve original bytes | Met | Exhaustive [restoration verification](evidence/restore-verification.json). |
| Immutable publication, multimodal continuity and explicit keyed enrichment | Met for tested application behavior | Snapshot RED/GREEN tests and final full suite; no filesystem-enforced immutability claim. |
| Reject unsupported citation attachment, empty/uncited/mistimed structural passes | Met | Review regressions and actual 44.9-second creative draft; no entailment guarantee. |
| Correct standard metrics and publish provenance-bound result | Met | Hand-calculated regressions, `retrieval_v2` receipt and preserved legacy result. |
| Installable source profile and real-corpus CPU API/demo | Met within declared source/ASGI scope | Wheel builds, 57 tests, actual probe and zero provider calls. |
| Equal two-person plan with reciprocal review and bounded future gates | Met | 24 allocation rows, 94/94 points, 14-check verification and independent arithmetic review. |
| Final local integration, review and bundle/hash integrity | Met | Independent review/fix pass, report/index agreement and the final handoff checker. |

Final task status: **COMPLETE for the authorized recovery scope**. The source changes are integrated into the owner's main checkout and remain uncommitted. The externally managed interrupted worktree is preserved. G0–G6 remain **NOT_RUN**: the new human-evaluation, acquisition, multimodal and hosting criteria require their own work and evidence. Use the [active plan](../../../planning/TikTok_AI_Engine_Milestone.md) for the next two-person tasks, not this recovery completion as a substitute for gate acceptance.
