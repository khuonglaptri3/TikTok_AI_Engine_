# Current data progress: historical core available; fresh stream absent

Fresh verification on 2026-11-18 at `c3348e93d66ad4eeba133c1d05752d26da18d774` confirms the historical chain is available: **37,840 preserved source files → 70,996 Gold video rows → 21,748 BM25 documents**. All checked bytes, fetched remote Git blobs, Gold counts/keys/joins, and retrieval provenance match. The fresh rolling stream and independent evaluation labels have not been supplied in the inspected checkout. This audit does not change milestone or gate acceptance.

## Verified stage and availability

| Layer | Fresh observation | Meaning / remaining work |
| --- | --- | --- |
| Preserved historical sources | 37,840 unique files; 1,504,284,701 logical bytes; all archive-derived SHA256 and pinned Git blob checks pass | Restoration is already complete for the selected pinned inventory. Do not restore or recrawl it again. This does not independently reconstruct the unavailable original owner-copy inventory. |
| Published data and runtime artifacts | 37,849 files; 1,593,622,816 logical bytes; exact local and fetched `origin/main` path/blob/size equality | Data publication is present in the fetched Git tree. The older publication report's `IN_PROGRESS` narrative is stale; this audit does not edit that historical report. No separate clone was performed. |
| Active Gold snapshot | `20261117_recovered_v1`: 264 creators; 70,996 unique video IDs; 49 video columns; all creator joins resolve | Physical schema, manifest size/count/SHA256, unique/non-null keys, date bounds and declared subsets pass. Semantic taxonomy and annotation quality still require their planned audits. |
| Historical coverage | 2023-11-25 through 2025-03-19; 21,748 accepted transcripts; 23,448 POI-bearing rows; 5,798 commerce-tagged rows | This is a historical cohort. It does not establish current trends, venue attendance or transcription accuracy. |
| BM25 v2 | 21,748 unique documents; 391,043 terms; 9,464,226 postings | Membership exactly equals Gold's nonempty transcript-eligible documents. The other Gold rows remain metadata-only for this index. CSR arrays, parameters, receipt and stored hashes pass. |
| Retrieval evaluation | 16 frozen weak-label queries; every labeled ID resolves to Gold and the index; corpus/query/index/code hashes match `retrieval_v2` | These are lexical/metadata-derived labels, not human relevance judgments. Previous quality/latency numbers were not rerun or represented as new measurements. |
| Fresh raw stream | `data/raw_incremental/` is absent; zero fresh files | No real 120-day capture batch, capture receipt or fresh transcript-to-search pilot is present. |
| Fresh audio | Zero fresh audio files | Four historical `.m4a` files, totaling 4,133,681 bytes, are preserved under `data/raw/` and belong to the verified restoration manifest. They do not establish a fresh 64 kbps MP3 stream or a complete aligned voice dataset; decoding, bitrate and duration were not evaluated. |
| Voice/comment/ABSA snapshots | No `fact_voice_segments.parquet`, `fact_comments.parquet` or `fact_absa_reviews.parquet` in either actual corpus directory | Implemented ingestion behavior and test fixtures do not establish real modality availability. Metadata `comment_count` is not comment text. |
| Independent labels | One actual evaluation file: `data/evaluation/v1/queries.jsonl`; no label/annotation/judgment/qrels-named candidate file in the inventoried data/runtime scope | No independent human relevance, audio-boundary, observable comment-noise or aspect-sentiment evaluation set was found. This says nothing about unpublished teammate files. |

The legacy `20261116_v1` directory contains its old manifest but neither declared Parquet table. The active recovered snapshot contains both tables and passes every check; the legacy directory is not evidence that the recovered data need rebuilding.

## Verification and provenance

The [aggregate verification receipt](data-verification.json) records the observed commits, input-manifest SHA256 values, full schemas, counts, all checks and scope limitations. A fresh one-pass content scan covered every file in the later publication inventory with eight read workers; it completed the integrity/structure audit in **161.733 seconds**, with **zero failures**. Both pre-existing files recorded before restoration retain their SHA256. The restoration manifest, Gold manifest and four recovered builder/index implementation hashes also match the previous recovery receipt.

The remote comparison uses the freshly fetched `origin/main` tree at the same commit as `HEAD`, with no missing paths, extra paths, size differences or blob differences. It follows the owner's later authorization to track data; the earlier verifier's `gitignored` assertion was intentionally not used. No restoration, Gold/index rebuild, crawl, audio/model processing, provider request, paid service, commit or push was run.

Process skills read for this delegated audit were `using-superpowers`, `writing-plans` and `verification-before-completion`, from the installed Superpowers `7.0.1` package. The dispatched-subagent exception in `using-superpowers` applies. Work follows the parent's existing [specification](../superpowers/spec.md) and [investigation plan](../superpowers/plan.md); this is execution of the delegated check, not a newly approved implementation plan.

Earlier context remains available in the [completed recovery report](../../core-recovery-and-two-person-plan-2026-11-17/README.md) and [publication report](../../full-data-publication-2026-11-17/README.md). Their dated measurements were not substituted for this scan. The active [milestone plan](../../../../../docs/planning/TikTok_AI_Engine_Milestone.md) retains G0–G6 as `NOT_RUN`; scientific and acquisition acceptance requires separate evidence.

## Recommended next data assignments

| Contributor | Next bounded task | Review and handoff |
| --- | --- | --- |
| Nguyễn Việt Nguyên | Continue M1.1: trace field sources/unknown handling and prepare the planned 120-record stratified taxonomy audit, including 30 records reviewed by both contributors. Independently check the existing M1.2 build/receipt. | Publish sample denominators, disagreements and observed errors; request Khương's review. Do not infer semantic correctness from matching hashes. |
| Trần Đình Khương | Continue M1.2 acceptance using the existing recovered snapshot and linked source/build receipts; reconcile canonical task evidence and source-rights limitations without overwriting snapshot IDs or repeating recovery. Review Nguyên's taxonomy audit. | Supply the preserved inventory, count/schema checks and provenance for reciprocal review. Jointly prepare the later independent relevance pilot under M2.2. |

Fresh acquisition remains M3.2/M3.3 work after the required prior reviews/gates. The plan's capped real-data pilot must produce actual metadata/audio/comment receipts and searchable fresh transcripts before audio, comment filtering or ABSA quality can be accepted. Existing historical data and synthetic fixtures cannot close that gap.
