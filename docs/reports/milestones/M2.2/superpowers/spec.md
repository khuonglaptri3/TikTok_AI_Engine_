# M2.2 — Specification: Corrected BM25 Evaluation, Query Intent Guardrails & Pooled Relevance Pilot

- **Task ID:** `M2.2`
- **Primary Owner:** Trần Đình Khương (`K`)
- **Peer Reviewer:** Nguyễn Việt Nguyên (`N`)
- **Requirement Source:** [TikTok_AI_Engine_Milestone.md](../../../../planning/TikTok_AI_Engine_Milestone.md) (`M2.2`)
- **Date:** 2026-11-19 (Asia/Saigon)

## 1. Purpose & Historical Preservation Boundaries

Establish a reproducible, honest lexical retrieval evaluation and guardrail baseline over the taxonomy-corrected Gold snapshot (`data/corpus/20261118_taxonomy_fix_v1`, `21,748` transcribed videos out of `70,996` total videos) ahead of Gate `G2` (`M2.G`) and the `M6.1` dense/hybrid comparison:

1. **Immutable Historical Preservation:** Preserve `artifacts/benchmarks/retrieval_v1.json`, `artifacts/benchmarks/retrieval_v2.json`, `artifacts/indexes/bm25-v2/`, and `data/evaluation/v1/queries.jsonl` (`16` keyword-derived weak-label regression queries) byte-for-byte untouched.
2. **Updated Sparse Index (`bm25-v3`):** Build a new immutable index at `artifacts/indexes/bm25-v3/` bound to `corpus_snapshot_id = "20261118_taxonomy_fix_v1"` so disambiguated cities, districts, dishes (eliminated substring `"ốc"` false positives), and occasions (`[]` instead of forced `"an_vat_xe_chieu"`) are reflected in `rag_document` indexing.
3. **Query Intent & No-Answer Abstention Layer:** Prevent fabricated support on out-of-corpus / no-answer queries, handle decomposed `NFD` Vietnamese Unicode, expand regional/culinary synonyms, and respect Vietnamese negation cues (`"không cay"`, `"không mắm tôm"`, `"không hành"`) at `USD 0` CPU cost (`0` LLM calls).
4. **40-Query Disjoint Pilot & Pooled Judgment Framework:** Construct `20` frozen `dev` queries (`10` `K` + `10` `N`) and `20` locked `test` queries (`10` `K` + `10` `N`), generate blinded top-10 candidate pools across `bm25` and `bm25_reranked`, record evidence-backed draft relevance judgments with explicit AI-assisted provenance, and compute pooled `Recall@10`, `Precision@10`, `MRR@10`, `nDCG@10`, no-answer abstention rates, paired bootstrap 95% confidence intervals, and `100`-request warm CPU latency (`p95 <= 500 ms`).

## 2. Architecture & Component Contracts

### 2.1 Data Contract Extension (`packages/data_contracts/retrieval.py`)
Add two optional backward-compatible fields to `RetrievalResponse`:
- `insufficient_evidence: bool = False` — `True` when retrieval abstains (`items == []`) because no candidate satisfies specific query anchors or non-relaxable dish/entity evidence.
- `abstain_reason: str | None = None` — human-readable bounded explanation when `insufficient_evidence` is `True` (`None` otherwise).

All existing callers constructing or consuming `RetrievalResponse` without these fields remain 100% compatible.

### 2.2 Query Intent Analysis & Retrieval Guardrails (`packages/retrieval/query_intent.py`, `scorer.py`, `service.py`)
1. **Unicode Normalization:** Normalize every incoming query to `NFC` (`unicodedata.normalize("NFC", query)`) before tokenization, synonym expansion, negation parsing, or reranking so `NFD` decomposed diacritics produce identical rankings to `NFC`.
2. **Vietnamese Negation Parsing (`parse_query_intent`):**
   - Detect negation markers (`không`, `chẳng`, `đừng`, `kiêng`, `dị ứng`, `tránh`, `ghét`, `né`, `bỏ`, `trừ`) and extract negated 1–3 token culinary/attribute spans up to punctuation or conjunction boundaries (`nhưng`, `mà`, `ở`, `tại`, `cho`, `với`, `giá`).
   - Exclude negated tokens/bigrams from positive BM25 query scoring so `"bún đậu không mắm tôm"` searches positive `"bún đậu"` without boosting `"mắm tôm"`.
   - In `EvidenceReranker.rerank()`, subtract a bounded penalty (`0.25` per matched negated term, capped at `0.50`) when a candidate's `caption`, `dishes`, or `transcript` contains the negated term without also matching the explicit negated phrase (e.g., `"không cay"`, `"không mắm tôm"`).
3. **Curated Vietnamese F&B Synonym Expansion:**
   - Map positive regional/culinary terms to canonical equivalents (e.g., `sài gòn ↔ hồ chí minh`, `heo ↔ lợn`, `tàu hũ ↔ đậu hũ / tào phớ`, `nước lèo ↔ nước dùng`, `lai rai ↔ nhậu`, `healthy ↔ ăn kiêng / ít calo / giữ dáng`, `mì gói ↔ mì tôm`, `bánh mì que ↔ bánh mì cay hải phòng`, `trà đá ↔ trà chanh`, `quán cóc ↔ vỉa hè`) by appending matched synonym tokens at attenuated lexical weight (or expanded BM25 query string) without overwriting original tokens.
4. **Specific Anchor Extraction & No-Answer Abstention (`insufficient_evidence`):**
   - Separate generic F&B/search boilerplate tokens (`review`, `quán`, `nhà`, `hàng`, `ăn`, `uống`, `ngon`, `rẻ`, `đẹp`, `nổi`, `tiếng`, `chỗ`, `nào`, `ở`, `tại`, `đâu`, `công`, `thức`, `cách`, `làm`, `nấu`, `món`, `hướng`, `dẫn`, `cho`, `người`, `mình`, `bạn`, `bè`, `gia`, `đình`, `sinh`, `viên`, `chuẩn`, `vị`, `siêu`, `đậm`, `đà`, `bữa`, `sáng`, `trưa`, `chiều`, `tối`, `đêm`, `khuya`, `vỉa`, `hè`, `bình`, `dân`, `cao`, `cấp`, `sang`, `chảnh`, `mukbang`, `vlog`, and standalone geographic location names) from **specific culinary/dish/ingredient/venue anchors**.
   - **Out-of-Corpus Anchor Rule:** If a query contains specific culinary/entity anchors and **any explicit rare foreign/exotic dish anchor is completely absent from `BM25Index.vocab` (with no in-vocab synonym)** — or **zero** positive anchor tokens appear in `BM25Index.vocab` — abstain immediately (`items=[]`, `insufficient_evidence=True`, `abstain_reason="no_corpus_match_for_query_anchors"`).
   - **Candidate Anchor Verification & Filter Discipline:** After retrieving candidates, verify that each retained card matches at least one specific positive anchor token/phrase (or expanded synonym) in its normalized `caption`, `poi_name`, `dishes`, `food_category`, or `transcript`. Filter out boilerplate-only matches (e.g., matching only `"công thức nấu"` or song lyrics matching `"sài gòn"` with zero culinary/anchor overlap when specific anchors exist). Furthermore, when an explicit geographic filter (`city_norm` or `region`) yields zero anchor-matching documents in that location, do **not** silently substitute videos from another city as fabricated support; abstain with `items=[]` and `insufficient_evidence=True`.
5. **Dev-Only Tuning Boundary:** All synonym entries, boilerplate word sets, negation rules, and abstention conditions are developed and validated exclusively against unit tests and `dev_queries.jsonl` (`20` queries). `test_queries.jsonl` (`20` queries) is frozen prior to test execution and never used to tune weights, lexicons, or thresholds.

## 3. 40-Query Pilot Design & Pooled Judgment Protocol (`data/evaluation/v2_pilot/`)

### 3.1 Query Split & Phenomena Coverage
- **Files:**
  - `data/evaluation/v2_pilot/dev_queries.jsonl`: `20` queries (`d_k01..d_k10` authored for `K`, `d_n01..d_n10` drafted for `N`).
  - `data/evaluation/v2_pilot/test_queries.jsonl`: `20` locked test queries (`t_k01..t_k10` authored for `K`, `t_n01..t_n10` drafted for `N`).
  - Disjoint query text and intent across `dev` and `test` (`0` duplicate queries).
- **Per-Split Stratification (`20` queries per split):**
  - `synonym`: `4` queries (regional/colloquial Vietnamese F&B terms).
  - `unicode_nfd`: `3` queries (stored/submitted with `NFD` combining diacritics to test end-to-end Unicode normalization).
  - `negation`: `3` queries (explicit dietary/ingredient exclusions).
  - `filtered`: `6` queries (combining dish/topic queries with `city_norm`, `video_format`, `food_category`, `price_tier`, or `occasion` filters).
  - `no_answer`: `4` queries (`expect_no_answer: true` — dishes, exotic ingredients, or dish-location combinations verified absent from the `21,748` transcribed videos).

### 3.2 Blinded Top-10 Pooling & Honest Provenance
- Pool the union of top-10 retrieved `video_id`s from `bm25` (`rerank=False`) and `bm25_reranked` (`rerank=True`) on `bm25-v3` for every query; for `no_answer` queries where the guarded service abstains (`items=[]`), also inspect raw unguarded BM25 top-5 candidates in a separate verification table (`no_answer_raw_audit.csv`) to confirm that abstention did not suppress a genuinely relevant corpus video.
- Shuffle each query's pooled candidates using deterministic seed `20261119` with rank and system origin hidden in `data/evaluation/v2_pilot/blinded_pool.csv`.
- **Relevance Scale:**
  - `1`: Video's spoken transcript/caption/metadata genuinely addresses the requested dish/topic, satisfies explicit location/category filters, and does not violate explicit negation constraints.
  - `0`: Non-relevant dish/topic, boilerplate/song-lyric match, wrong location for location-specific query, or directly contradicts a negated constraint.
  - `U`: Uncertain / ambiguous transcript excerpt where relevance cannot be verified from available text; reported in completeness/uncertainty statistics and NOT counted as a verified positive (`1`) unless adjudicated.
- **Provenance Qualification (`AGENTS.md` Section 4):** Initial columns `K_rel_draft`, `N_rel_draft`, and `adjudicated_rel_draft` are populated via transcript-inspected AI-assisted drafting with per-row `evidence_note` excerpts, accompanied by explicit boolean columns `K_human_verified` (`False`) and `N_human_verified` (`False`). All benchmark JSONs and `M2.2/README.md` MUST declare `label_source = "ai_assisted_pooled_draft_pending_human_K_N_signoff"` and keep task status **`IN_PROGRESS`** until both `K` and `N` confirm/adjudicate the pool.

## 4. Metric Definitions, Latency Budget & Acceptance Criteria

### 4.1 Metrics (`pipelines/benchmark_retrieval/pilot_m2_2.py`)
1. **Answerable Queries (`expect_no_answer == false`, `16` dev / `16` test):**
   - `pooled_recall_at_10` = `|Retrieved@10 ∩ Relevant_Pool| / |Relevant_Pool|` for queries with `|Relevant_Pool| >= 1` (queries with `|Relevant_Pool| == 0` are counted under `zero_relevant_pool_count` and reported separately rather than silently dropped without disclosure). Explicitly labeled **pooled recall**, not exhaustive corpus recall.
   - `precision_at_10` = `|Retrieved@10 ∩ Relevant_Pool| / 10`.
   - `mrr_at_10` = `1 / rank_first_hit` within top 10 (`0.0` if no hit).
   - `ndcg_at_10` = `DCG@10 / IDCG@10` using binary relevance and `ideal_hits = min(|Relevant_Pool|, 10)`.
   - **Uncertainty:** Paired bootstrap 95% confidence intervals (`1,000` resamples, `seed=42`) on `mrr_at_10`, `ndcg_at_10`, `pooled_recall_at_10`, and `precision_at_10` for `bm25`, `bm25_reranked`, and `delta = bm25_reranked - bm25`, plus completeness/uncertainty counts (`U` rate, pool size per query).
2. **No-Answer Queries (`expect_no_answer == true`, `4` dev / `4` test):**
   - `no_answer_abstention_rate`: proportion returning `items == []` and `insufficient_evidence == True`.
   - `fabricated_support_count`: count of `no_answer` queries returning `len(items) > 0` (`target == 0`).
3. **Warm CPU Latency (`100` warm requests, `concurrency = 1`):**
   - Measure `1` cold request + `100` warm requests cycling deterministically across the locked test queries for both `bm25` and `bm25_reranked`, recording `p50_ms`, `p95_ms`, `mean_ms`, hardware specs, and OS peak memory (`provisional warm p95 <= 500 ms`).

### 4.2 Acceptance Checklist
- Hand-calculated unit tests in `tests/unit/test_retrieval_metrics.py` and `tests/unit/test_query_intent_and_abstention.py` pass via TDD (`RED -> GREEN`), covering `Recall@10`, `Precision@10`, `MRR@10`, `nDCG@10`, `NFD` Unicode parity, regional synonyms, negation demotion, no-answer abstention, and bootstrap CIs.
- Existing 16-query weak-label regression (`tests/eval/test_retrieval_benchmark.py`) and the full project `pytest`, `mypy` (`Windows` + `Linux` static targets), `ruff`, and `scripts/check_secrets.py` suites pass (`0` errors, `0` leaks).
- Disjoint frozen `dev` (`20`) and `test` (`20`) query files, `blinded_pool.csv`, `qrels_pooled_draft.jsonl`, per-query results, and immutable receipt `artifacts/benchmarks/retrieval_v3_pilot.json` exist with full SHA256 provenance.
- Provisional locked-test targets (`MRR@10 >= 0.60`, `nDCG@10 >= 0.50` on answerable queries, `0` fabricated support on `no_answer` queries, warm CPU `p95 <= 500 ms`) are evaluated and reported honestly without tuning on `test` or forcing a reranking win.
- Task status remains `IN_PROGRESS` pending human `K` & `N` verification/adjudication of `blinded_pool.csv` and `N` peer review.
