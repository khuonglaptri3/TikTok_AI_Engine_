# TikTok_AI_Engine_ — AI engineering milestone plan

- Revision: DUAL_STREAM_FNB_INTELLIGENCE_2026_11_16; M0–M2 historical Gold corpus, Niche Micro-Benchmarks, Vietnamese BM25/RRF retrieval, and Grounded Script Engine baseline verified; M3–M6 4-month multimodal incremental stream scaffolded.
- Delivery: Typed AI domain packages, reproducible offline CLI pipelines, FastAPI endpoints, and one lightweight ASGI-mounted Gradio demonstration UI (`/demo/`).
- Owner: Trần Đình Khương; one AI Engineer; no additional contributor is assumed.
- Reference window: 16 November 2026 to 08 January 2027, 8 working weeks.

[Resources & Deployment](TikTok_AI_Engine_Resources_and_Deployment.md) · [Milestone Reports](../reports/milestones/README.md) · [Case Studies](../reports/Case_Study/README.md) · [Data Card](../data-cards/tiktok_fnb_corpus_v1.md)

## 1. Active scope

Implement and evaluate an end-to-end Vietnamese TikTok Food & Beverage (F&B) AI Engine unifying **Creator-Side Viral Content Intelligence** and **Consumer-Side Review Trust & Multimodal ABSA**:

1. **Historical Macro Intelligence (`1.50 GB`, `70,996` videos, `2023-11` to `2025-03`):** Immutable Gold Parquet corpus (`dim_creators` + `fact_videos` with `23,448` recovered official TikTok GPS POIs and `21,748` clean Vietnamese transcripts), Columnar Niche Micro-Benchmarking, Vietnamese NFC Hybrid Retrieval (`BM25 CSR + Qdrant Dense + RRF + Phrase/Aspect Reranking`), and Citation-Grounded Script Synthesis with deterministic `mm:ss` pacing guardrails.
2. **Rolling 4-Month Incremental Multimodal Stream (`data/raw_incremental/`):** Never re-crawl historical videos. Collect only the latest 4-month window (`Metadata + 64kbps .mp3 Audio + Top Viewer Comments`) and process through a **Dual-Sink Normalization Pipeline** that:
   - **Sink A (Corpus Continuity):** Converts fresh 4-month videos into the canonical 49-column `fact_videos` schema to keep RAG and Niche Benchmarks current.
   - **Sink B (Multimodal Trust Modules):** Populates `fact_voice_segments` (`Whisper` word/segment timestamps + `Librosa` prosody), `fact_comments` (`Seeding & Spam Clustering`), and `fact_absa_reviews` (`4-Aspect KOC Voice vs. Clean Viewer Comment Sentiment` + `PR Hype Gap` + `Undisclosed Sponsorship Risk`).

User authentication, role workspaces, merchant billing CRUD, automated ad-buying actions, and paid GPU/API plans are excluded. Online LLM orchestration is capped at `USD 0` using only the owner's Gemini Free-Tier API (`<= 2` calls per turn, sliding-window RPM limiter, explicit `offline_grounded` `$0` fallback).

## 2. Current status and stage windows

M0.1–M0.3: COMPLETE; M1.1–M1.2: COMPLETE (`70,996` clean videos, `264` creators, `23,448` GPS POIs, `21,748` speech transcripts verified by SHA256 `manifest.json`). M2.1–M2.3: COMPLETE (`391,042`-term NFC BM25 CSR index, frozen `retrieval_v1.json` benchmark at `Recall@10 = 0.7094`, `MRR@10 = 0.8127`, `nDCG@10 = 0.7083`, `p95 = 21.0 ms`, and Grounded Script Engine + Gradio `/demo/`). M3.1–M3.2 contracts, seeding cleanser, 4-aspect ABSA baseline, and Dual-Sink 4-month incremental pipelines are implemented and unit-tested; live 4-month crawl execution (`M3.3`) and Qdrant dense/Whisper batch runs (`M4`–`M6`) remain `NOT_STARTED` for upcoming milestones. Gates `G0`–`G6` remain explicit review checkpoints.

| Stage | AI result | Start window | End window |
| --- | --- | --- | --- |
| M0 | Legacy audit, secret hygiene, canonical contracts and API/demo foundation | 16/11/2026 | 18/11/2026 |
| M1 | Unified Historical Gold Corpus (`71K` videos, `23.4K` GPS POIs) & F&B Taxonomy | 19/11/2026 | 23/11/2026 |
| M2 | Columnar Niche Micro-Benchmarks, Vietnamese Hybrid RAG & Grounded Script Engine | 24/11/2026 | 30/11/2026 |
| M3 | Rolling 4-Month Incremental Crawler (`Audio + Comments`) & Dual-Sink Lakehouse | 01/12/2026 | 08/12/2026 |
| M4 | Whisper Segment Timestamps, Librosa Voice Prosody & Undisclosed PR Detector | 09/12/2026 | 16/12/2026 |
| M5 | Comment Seeding Cleanser & 4-Aspect KOC-vs-Viewer ABSA Intelligence | 17/12/2026 | 24/12/2026 |
| M6 | Timestamped Multimodal Voice RAG on Qdrant & End-to-End Verification Release | 28/12/2026 | 08/01/2027 |

## 3. Task definitions

### M0 — Legacy audit, secret hygiene, canonical contracts and API/demo foundation

#### M0.1 — Audit legacy repository, sanitize secrets and preserve 1.50 GB dataset
- Window: 16/11/2026; allocation 0.5 day(s).
- Dependency: START. Owner: Trần Đình Khương, AI Engineer.
- Status: COMPLETE. See [M0.1 report](../reports/milestones/M0.1/README.md).
- Work: Audit legacy coursework limitations, purge all hardcoded API keys, archive legacy code non-destructively, and verify 100% preservation of all `37,840` data files (`1.50 GB`).
- Output: Architecture audit (`ReFactor_structure/`), `scripts/check_secrets.py`, preserved `data/` & `archive/legacy_coursework/`.
- Acceptance: Zero hardcoded keys across workspace; zero original data files deleted or mutated.

#### M0.2 — Lock canonical Pydantic v2 contracts and bounded settings
- Window: 16/11/2026; allocation 0.5 day(s).
- Dependency: M0.1. Owner: Trần Đình Khương, AI Engineer.
- Status: COMPLETE.
- Work: Define strict Pydantic v2 schemas (`corpus`, `query`, `analytics`, `retrieval`, `script`, `multimodal`, `errors`), `.env` loader (`AppSettings`), `StageTimer`, and domain exceptions.
- Output: `packages/common/` and `packages/data_contracts/`.
- Acceptance: Contract tests validate schema invariants, bounds, and fail-closed error payloads.

#### M0.3 — Set up FastAPI boundary and ASGI-mounted Gradio `/demo/` workspace
- Window: 16/11/2026; allocation 0.5 day(s).
- Dependency: M0.2. Owner: Trần Đình Khương, AI Engineer.
- Status: COMPLETE.
- Work: Build single-port FastAPI service (`/health/live`, `/health/ready`, `/api/v1/*`) and mount thin Gradio 6 UI at `/demo/` calling FastAPI via in-process ASGI transport.
- Output: `apps/api/`, `apps/demo/`, `tests/smoke/test_api_and_demo.py`.
- Acceptance: Smoke suite exercises health, readiness, valid/invalid requests, and `/demo/` HTTP 200 without external network dependency.

#### M0.G — G0: foundation, secret hygiene and contract gate review
- Window: 18/11/2026; allocation 0.5 day(s).
- Dependency: M0.3. Owner: Trần Đình Khương, AI Engineer.
- Status: NOT_RUN.
- Work: Formal gate audit of M0.1–M0.3 deliverables and remaining effort re-estimation.
- Output: `docs/reports/milestones/M0.G/README.md`.
- Acceptance: `check_secrets.py`, `mypy`, and contract/smoke suites pass cleanly.

### M1 — Unified Historical Gold Corpus & Vietnamese F&B Taxonomy

#### M1.1 — Implement 6-axis Vietnamese F&B Taxonomy and GPS POI location resolver
- Window: 19/11/2026; allocation 1.0 day(s).
- Dependency: M0.2. Owner: Trần Đình Khương, AI Engineer.
- Status: COMPLETE.
- Work: Implement GPS POI priority resolver (fixing dish-name vs. district collisions such as *"Bún đậu Hà Nội ở Quận 7"* -> `hồ chí minh`), 5 video formats, 8 food categories, 6 price tiers, 8 occasions, and script anatomy extractor (`hook_text`, `body_beats`, `cta_text`).
- Output: `packages/taxonomy/`.
- Acceptance: Unit tests verify location disambiguation, zero-division guards, and script anatomy extraction.

#### M1.2 — Build immutable Historical Gold Parquet snapshot (`20261116_v1`)
- Window: 20/11/2026; allocation 1.0 day(s).
- Dependency: M1.1. Owner: Trần Đình Khương, AI Engineer.
- Status: COMPLETE.
- Work: Non-destructively join `cleaned_video_info.parquet` (`70,996` rows), `cleaned_user_info.parquet` (`264` creators), `final_raw_videos.csv` (`23,448` GPS POIs, `5,798` `is_ec_video`), `23,122` transcript JSONs (`strict=False` + LLM-refusal filtering -> `21,748` valid speech transcripts), and legacy food/content tables.
- Output: `pipelines/build_gold_corpus/`, `data/corpus/20261116_v1/{dim_creators.parquet, fact_videos.parquet, manifest.json}`.
- Acceptance: Startup loader verifies SHA256 checksums fail-closed; exact row/column counts match `manifest.json`.

#### M1.G — G1: historical Gold corpus and taxonomy provenance gate
- Window: 23/11/2026; allocation 0.5 day(s).
- Dependency: M1.2. Owner: Trần Đình Khương, AI Engineer.
- Status: NOT_RUN.
- Work: Audit Gold corpus distributions, location coverage, and caveats documentation.
- Output: `docs/reports/milestones/M1.G/README.md`.
- Acceptance: Reproducible Gold snapshot build and verified data card.

### M2 — Columnar Niche Micro-Benchmarks, Hybrid RAG & Grounded Script Engine

#### M2.1 — Build Columnar Niche Micro-Benchmark Engine
- Window: 24/11/2026; allocation 1.0 day(s).
- Dependency: M1.2. Owner: Trần Đình Khương, AI Engineer.
- Status: COMPLETE.
- Work: Compute empirical niche medians & IQRs (`median_plays`, `duration_q25..q75`, `median_word_per_second`, hashtag IQR, top posting hours, top GPS POI venues) with transparent filter relaxation.
- Output: `packages/analytics/engine.py`, `POST /api/v1/analytics/niche-benchmark`.
- Acceptance: Sub-50ms columnar slice aggregation with valid IQR ordering and per-stage `timings_ms`.

#### M2.2 — Build Vietnamese NFC BM25 CSR Index, Qdrant Adapter, RRF & Reranker
- Window: 25/11/2026 to 26/11/2026; allocation 1.5 day(s).
- Dependency: M1.2. Owner: Trần Đình Khương, AI Engineer.
- Status: COMPLETE (BM25 + Viral Boost + Phrase/Aspect Reranker verified; live Docker Qdrant dense indexing deferred to M6.1).
- Work: Build pickle-free CSR Okapi BM25 over `391,042` NFC Vietnamese unigrams/bigrams (`21,748` videos), creator-normalized `viral_multiplier` log-boost, field-aware phrase/aspect reranker, and frozen retrieval evaluation harness.
- Output: `packages/retrieval/`, `pipelines/build_dense_sparse_index/`, `pipelines/benchmark_retrieval/`, `artifacts/benchmarks/retrieval_v1.json`.
- Acceptance: `Recall@10 = 0.7094`, `MRR@10 = 0.8127`, `nDCG@10 = 0.7083`, `p95 = 21.0 ms` verified by `tests/eval/test_retrieval_benchmark.py`.

#### M2.3 — Build Bounded Grounded Script Engine & Timeline/Cliché Guardrails
- Window: 27/11/2026 to 30/11/2026; allocation 1.5 day(s).
- Dependency: M2.1, M2.2. Owner: Trần Đình Khương, AI Engineer.
- Status: COMPLETE.
- Work: Implement sliding-window RPM `BoundedGeminiClient` (`gemini_free`) + `$0` deterministic `offline_grounded` blueprint synthesizer, exact `mm:ss` beat timeline recalculator from niche `word_per_second`, citation validator, and anti-cliché filter.
- Output: `packages/llm/`, `packages/script_engine/`, `POST /api/v1/script/generate`.
- Acceptance: Hallucinated `video_id` citations are stripped, cliché filler phrases are flagged, and missing `GEMINI_API_KEY` returns typed `503 PROVIDER_KEY_MISSING`.

### M3 — Rolling 4-Month Incremental Crawler & Dual-Sink Lakehouse

#### M3.1 — Define multimodal Star Schema contracts & Dual-Sink converter
- Window: 01/12/2026 to 02/12/2026; allocation 1.5 day(s).
- Dependency: M1.2. Owner: Trần Đình Khương, AI Engineer.
- Status: COMPLETE (scaffold & unit tests verified).
- Work: Define `RawIncrementalVideoRecord`, `VoiceSegmentRecord` (`fact_voice_segments`), `CommentRecord` (`fact_comments`), and `AbsaComparisonRecord` (`fact_absa_reviews`); implement `pipelines/ingest_incremental_to_gold/` converting fresh 4-month crawls simultaneously into canonical 49-column `fact_videos` AND multimodal trust tables.
- Output: `packages/data_contracts/multimodal.py`, `pipelines/ingest_incremental_to_gold/`.
- Acceptance: Fresh incremental batch appends cleanly to `fact_videos.parquet` without mutating historical `data/` files and emits SHA256-verified multimodal tables.

#### M3.2 — Implement Rolling 4-Month Incremental Crawler (`Metadata + 64kbps Audio + Comments`)
- Window: 03/12/2026 to 04/12/2026; allocation 1.5 day(s).
- Dependency: M3.1. Owner: Trần Đình Khương, AI Engineer.
- Status: COMPLETE (CLI & cutoff filter implemented; live network crawl scheduled in M3.3).
- Work: Build `pipelines/crawl_incremental/` enforcing a strict `120-day` rolling cutoff (`create_time >= now - 120d`) and skipping any `video_id` already present in the historical `70,996` corpus; extract `yt-dlp` audio-only `.mp3` (`~500 KB`) and top viewer comments into `data/raw_incremental/`.
- Output: `pipelines/crawl_incremental/`.
- Acceptance: Historical videos older than 4 months are strictly skipped; incremental batches persist resumable JSONL manifests.

#### M3.3 — Execute 4-month fresh F&B cohort capture & build Gold Corpus `v2`
- Window: 07/12/2026 to 08/12/2026; allocation 1.5 day(s).
- Dependency: M3.2. Owner: Trần Đình Khương, AI Engineer.
- Status: NOT_STARTED.
- Work: Run `pipelines.crawl_incremental` across active Vietnamese F&B creators for the past 4 months, execute `pipelines.ingest_incremental_to_gold`, and rebuild BM25/Qdrant indexes over combined historical + fresh corpus.
- Output: `data/corpus/<v2-snapshot>/` and M3.3 ingestion report.
- Acceptance: Zero historical re-crawling; fresh 4-month videos searchable in RAG Script Engine and populated in `fact_comments`.

### M4 — Whisper Segment Timestamps, Librosa Voice Prosody & Undisclosed PR Detector

#### M4.1 — CPU Whisper segment timestamping & Librosa voice prosody extraction
- Window: 09/12/2026 to 11/12/2026; allocation 2.0 day(s).
- Dependency: M3.3. Owner: Trần Đình Khương, AI Engineer.
- Status: NOT_STARTED.
- Work: Run `faster-whisper` (`int8` CPU) on 4-month `.mp3` audio for exact `start_sec..end_sec` utterance segments alongside `Librosa` (`pitch_std`, `energy_cv`, `pause_ratio`); backfill sentence-level `wps_estimated` segments for the `21,748` historical transcripts.
- Output: Populated `fact_voice_segments.parquet` (`whisper_exact` + `wps_estimated`).
- Acceptance: Every indexed utterance resolves to `[video_id, start_sec, end_sec, timestamp_source]`.

#### M4.2 — Supervised Undisclosed Sponsorship / PR Detector (`4,779` `is_ad` labels)
- Window: 14/12/2026 to 16/12/2026; allocation 2.0 day(s).
- Dependency: M4.1. Owner: Trần Đình Khương, AI Engineer.
- Status: NOT_STARTED.
- Work: Train and calibrate a lightweight CPU classifier using the `4,779` `is_ad=True` and `5,798` `is_ec_video=True` historical disclosures plus prosody/lexical features to score `undisclosed_pr_risk` on unlabelled restaurant reviews.
- Output: Model card, evaluation metrics (`ROC-AUC`, `PR-AUC`, `Brier`), and `packages/absa/` integration.
- Acceptance: Held-out creator-split evaluation reported honestly without data leakage.

### M5 — Comment Seeding Cleanser & 4-Aspect KOC-vs-Viewer ABSA Intelligence

#### M5.1 — Comment Seeding & Bot Clustering Cleanser
- Window: 17/12/2026 to 18/12/2026; allocation 1.5 day(s).
- Dependency: M3.1. Owner: Trần Đình Khương, AI Engineer.
- Status: IN_PROGRESS (lexical/shingle baseline + API live in `packages/seeding/`; ONNX `BGE-M3` dense clustering upgrade in M5.1b).
- Work: Detect template seeding bursts, phone/link spam, and semantic near-duplicate comments (`is_seeding`, `seeding_reason`, `cluster_id`).
- Output: `packages/seeding/`, `fact_comments.parquet` cleansing metrics.
- Acceptance: Precision/Recall evaluated on manually audited Vietnamese TikTok comment slice.

#### M5.2 — 4-Aspect F&B ABSA (`Taste`, `Price`, `Hygiene`, `Service`) & `PR Hype Gap`
- Window: 21/12/2026 to 24/12/2026; allocation 2.5 day(s).
- Dependency: M5.1. Owner: Trần Đình Khương, AI Engineer.
- Status: IN_PROGRESS (lexicon baseline + `/api/v1/trust/audit-video` + Gradio Tab 4 live; batched Gemini Flash structured calibration in M5.2b).
- Work: Score KOC spoken transcript vs. non-seeding viewer comments across 4 F&B aspects, compute `pr_hype_gap`, and feed negative viewer pain-points back into `GroundedScriptEngine`.
- Output: `packages/absa/`, `fact_absa_reviews.parquet`, frozen ABSA Macro-F1 evaluation.
- Acceptance: `PR Hype Gap` highlights KOC-vs-viewer discrepancies with exact comment/utterance citations.

### M6 — Timestamped Multimodal Voice RAG on Qdrant & End-to-End Release

#### M6.1 — Populate Docker Qdrant Hybrid Collections (`utterance_segments` + `clean_reviews`)
- Window: 28/12/2026 to 31/12/2026; allocation 2.5 day(s).
- Dependency: M4.1, M5.2. Owner: Trần Đình Khương, AI Engineer.
- Status: NOT_STARTED.
- Work: Index dense (`multilingual-e5-base` / `BGE-M3`) + sparse vectors into Qdrant with payload filters (`city_norm`, `food_category`, `price_tier`, `is_seeding=False`) and benchmark `BM25` vs `Dense` vs `Hybrid RRF`.
- Output: Qdrant indexing pipeline and `retrieval_v2.json` benchmark report.
- Acceptance: Hybrid retrieval outperforms standalone BM25 on semantic/synonym Vietnamese F&B queries.

#### M6.2 — Timestamped Voice & Review Q&A Assistant + Final Gate `G6`
- Window: 04/01/2027 to 08/01/2027; allocation 3.0 day(s).
- Dependency: M6.1. Owner: Trần Đình Khương, AI Engineer.
- Status: NOT_STARTED.
- Work: Serve grounded diner/creator Q&A returning `[🎬 @handle | mm:ss-mm:ss]` citations alongside clean viewer consensus; complete reproducible release bundle and `M6.G` gate review.
- Output: `/api/v1/chat/timestamped-rag`, updated Gradio `/demo/`, and `M6.G` report.
- Acceptance: Citation completeness `>= 95%`, zero fabricated timestamps, `$0` Free-Tier compliance verified.

## 4. AI acceptance gates

| Gate | Acceptance | Task |
| --- | --- | --- |
| G0 | Secret hygiene (`0` leaks), strict Pydantic contracts, single-port FastAPI + Gradio `/demo/` smoke verified. | M0.G |
| G1 | `1.50 GB` upstream preservation, `70,996`-row SHA256 Gold corpus, and GPS POI disambiguation verified. | M1.G |
| G2 | Niche Micro-Benchmarks, Vietnamese BM25/RRF retrieval (`MRR@10 >= 0.75`), and Grounded Script Guardrails verified. | M2.G |
| G3 | Rolling 4-month incremental capture appends cleanly to Gold corpus without re-crawling historical videos. | M3.G |
| G4 | Utterance timestamps (`whisper_exact` + `wps_estimated`) and Undisclosed PR Detector calibrated on held-out creators. | M4.G |
| G5 | Comment Seeding Cleanser and 4-aspect KOC-vs-Viewer ABSA (`PR Hype Gap`) verified on audited F&B benchmarks. | M5.G |
| G6 | Qdrant Hybrid Timestamped Voice RAG, full test pyramid, and `$0` Free-Tier demonstration bundle verified. | M6.G |

## 5. AI capability traceability

| Capability | Active tasks | Expected evidence |
| --- | --- | --- |
| Foundation & Secret Hygiene | M0.1, M0.2, M0.3 | `check_secrets.py`, Pydantic v2 contracts, ASGI smoke tests |
| Historical Gold Lakehouse | M1.1, M1.2 | `20261116_v1/manifest.json`, `23,448` GPS POIs, `21,748` transcripts |
| Niche Analytics & Script RAG | M2.1, M2.2, M2.3 | `retrieval_v1.json`, `mm:ss` pacing guardrails, cited scripts |
| 4-Month Dual-Sink Ingestion | M3.1, M3.2, M3.3 | `pipelines/crawl_incremental/`, `pipelines/ingest_incremental_to_gold/` |
| Voice Prosody & PR Detection | M4.1, M4.2 | `fact_voice_segments.parquet`, `is_ad` calibrated classifier |
| Seeding & KOC-vs-Viewer ABSA | M5.1, M5.2 | `packages/seeding/`, `packages/absa/`, `POST /api/v1/trust/audit-video` |
| Timestamped Multimodal RAG | M6.1, M6.2 | Qdrant hybrid collections, `[mm:ss]` grounded citations |

## 6. Planning decisions

| Decision | Current rule |
| --- | --- |
| Scope | One AI Engineer implements and demonstrates AI modules; no CRUD accounts, login, or backend handoff docs. |
| Historical Data (`1.50 GB`) | Strictly read-only, never re-crawled, gitignored from remote, served via SHA256-verified Gold Parquet snapshots. |
| Fresh Data (`4-Month Window`) | Crawl only `create_time >= now - 120 days`; normalize into both `fact_videos` (for RAG) and multimodal trust tables. |
| Cost & Secrets | `USD 0` spend cap; `GEMINI_API_KEY` in `.env` only; `<= 2` LLM calls/turn; deterministic `$0` offline modes always available. |
| Reporting | Every started milestone task follows `AGENTS.md` (`docs/reports/milestones/<TASK-ID>/{README.md, evidence/, superpowers/}`) in English. |
