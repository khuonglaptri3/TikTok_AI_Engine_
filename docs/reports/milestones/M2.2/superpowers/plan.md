# M2.2 Corrected BM25 Evaluation & Pooled Relevance Pilot Implementation Plan

> **For agentic workers:** REQUIRED SUB-SKILL: Use superpowers:subagent-driven-development (recommended) or superpowers:executing-plans to implement this plan task-by-task. Steps use checkbox (`- [ ]`) syntax for tracking.

**Goal:** Build immutable `bm25-v3` on `20261118_taxonomy_fix_v1`, add CPU-offline Vietnamese query-intent guardrails (`NFC` Unicode, synonyms, negation, no-answer abstention), evaluate disjoint `20 dev` / `20 locked test` pooled queries with paired bootstrap uncertainty and `100`-request warm CPU latency, and publish `M2.2` evidence honestly.

**Architecture:** Introduce a focused `packages/retrieval/query_intent.py` analyzer consumed by `HybridRetrievalService` and `EvidenceReranker`, preserving existing CSR `BM25Index` speed (`< 30 ms`) and backward-compatible `RetrievalResponse` contracts. Add a standalone pooled-evaluation module `pipelines/benchmark_retrieval/pilot_m2_2.py` while keeping `pipelines/benchmark_retrieval/__main__.py`, `retrieval_v1.json`, `retrieval_v2.json`, and `bm25-v2` untouched.

**Tech Stack:** Python 3.12, NumPy, SciPy CSR, Pandas, PyArrow, Pydantic v2, pytest, mypy, Ruff (`USD 0`, `0` LLM calls).

**Spec:** [spec.md](spec.md)

## Global Constraints

- Preserve `artifacts/benchmarks/retrieval_v1.json`, `artifacts/benchmarks/retrieval_v2.json`, `artifacts/indexes/bm25-v2/`, `data/evaluation/v1/queries.jsonl`, and both Gold Parquet snapshots byte-for-byte untouched.
- Zero live LLM/provider calls and `USD 0` spend across indexing, retrieval, and benchmarking.
- Tune lexicons/weights strictly on unit fixtures and `dev_queries.jsonl` (`20` queries); never tune on locked `test_queries.jsonl` (`20` queries) or force a reranking win.
- Qualify recall over pooled top-10 candidates as `pooled_recall_at_10` (not exhaustive `21,748`-document recall) and label draft judgments `ai_assisted_pooled_draft_pending_human_K_N_signoff`, keeping `M2.2 = IN_PROGRESS` until `K` and `N` complete human sign-off.
- Provisional locked-test targets: answerable `MRR@10 >= 0.60`, `nDCG@10 >= 0.50`, `fabricated_support_count == 0` on `no_answer` queries, and `100`-request warm CPU `p95 <= 500 ms` at `concurrency = 1`.

## Review Focus

- Broad browse queries containing only boilerplate + location (`"review quán ăn ngon ở Sài Gòn"`, zero specific dish anchors) must return matching location videos rather than falsely abstaining with `insufficient_evidence=True`.
- Queries whose tokens are all negated (`"không cay không dầu mỡ"`) must not pass an empty string crash into BM25 or raise validation errors; handle empty positive queries safely.
- Decomposed `NFD` Vietnamese combining marks in both positive and negated spans (`"bu\u0301n đâ\u0323u không mă\u0301m tôm"`) must normalize to `NFC` prior to regex word splitting so combining marks never fragment tokens.
- Answerable queries whose pooled candidates all receive `0` or `U` (`|Relevant_Pool| == 0`) must not raise `ZeroDivisionError`; record `zero_relevant_pool_count` and evaluate `mrr_at_10 = 0.0`, `ndcg_at_10 = 0.0`, `precision_at_10 = 0.0`.
- Existing callers (`GroundedScriptEngine`, `/demo/`, `M6.1` parity tests, and `16`-query weak-label regression) must pass unchanged without breaking on `insufficient_evidence` or over-aggressive abstention.

---

### Task 1: Retrieval Contract, `QueryIntentAnalyzer`, Negation Reranking & No-Answer Abstention

**Files:**
- Modify: `packages/data_contracts/retrieval.py`
- Create: `packages/retrieval/query_intent.py`
- Modify: `packages/retrieval/rerank/scorer.py`
- Modify: `packages/retrieval/service.py`
- Modify: `packages/retrieval/__init__.py`
- Test: `tests/unit/test_query_intent_and_abstention.py`

**Interfaces:**
- Consumes: `tokenize_vietnamese(text: str, include_bigrams: bool = True) -> list[str]`, `BM25Index.vocab: dict[str, int]`
- Produces:
  - `RetrievalResponse.insufficient_evidence: bool = False`, `RetrievalResponse.abstain_reason: str | None = None`
  - `QueryIntent` dataclass (`normalized_query: str`, `positive_query: str`, `expanded_bm25_query: str`, `anchor_groups: list[tuple[str, ...]]`, `negated_terms: tuple[str, ...]`, `has_specific_anchors: bool`)
  - `parse_query_intent(query: str) -> QueryIntent`
  - `EvidenceReranker.rerank(..., negated_terms: tuple[str, ...] = ()) -> list[tuple[str, float, float]]`

- [x] **Step 1: Write failing unit tests in `tests/unit/test_query_intent_and_abstention.py`**

Cover all 7 cases:
1. `test_retrieval_response_defaults_remain_backward_compatible`: `insufficient_evidence is False` and `abstain_reason is None` when omitted.
2. `test_nfd_and_nfc_queries_produce_identical_intent_and_ranking`: `"bu\u0301n bo\u0300 kh\u00f4ng ha\u0300nh"` matches `"bún bò không hành"` identically.
3. `test_negation_excludes_positive_boost_and_demotes_violating_doc`: on a fixture corpus with `"Bún đậu mắm tôm đậm đặc"` vs `"Bún đậu chấm nước mắm cho người không ăn mắm tôm"`, query `"bún đậu không mắm tôm"` ranks the non-`mắm tôm` video `#1`.
4. `test_regional_and_culinary_synonym_expansion_recovers_match`: query `"tàu hũ đá Sài Gòn"` retrieves `"Chè đậu hũ mát lạnh Hồ Chí Minh"`.
5. `test_out_of_corpus_exotic_dish_abstains_without_fabricated_support`: queries `"công thức nấu thịt kangaroo hầm rượu vang"` and `"sushi cá nóc fugu chuẩn Nhật"` return `items == []`, `insufficient_evidence is True`, and non-empty `abstain_reason`.
6. `test_broad_location_query_and_all_negated_query_do_not_crash_or_false_abstain`: `"review quán ăn ngon ở Hồ Chí Minh"` (`city_norm="hồ chí minh"`) returns matching city videos (`insufficient_evidence is False`), and `"không cay không dầu mỡ"` returns cleanly without exception.
7. `test_strict_city_filter_with_absent_dish_abstains_instead_of_cross_city_fabrication`: querying `"bánh cóng Sóc Trăng"` with `city_norm="đà lạt"` where only `"hồ chí minh"` has `"bánh cóng"` returns `items == []` and `insufficient_evidence is True` rather than substituting HCMC videos.

- [x] **Step 2: Run focused test file to verify RED**

Run: `uv run --offline --no-project --with-editable ".[demo,dev]" --python 3.12 python -m pytest tests/unit/test_query_intent_and_abstention.py -v`
Expected: FAIL (`ModuleNotFoundError: No module named 'packages.retrieval.query_intent'`).

- [x] **Step 3: Implement contract fields, `query_intent.py`, reranker negation penalty, and service abstention guard**

Implement `insufficient_evidence` / `abstain_reason` in `packages/data_contracts/retrieval.py`, `parse_query_intent` + candidate/vocab anchor check helpers in `packages/retrieval/query_intent.py`, optional `negated_terms` penalty (`0.25` per violated negated term, capped at `0.50`) in `packages/retrieval/rerank/scorer.py`, and BM25/service integration in `packages/retrieval/service.py` (preserving `mode="dense"` and `restrict_to_df=True` parity behavior for `M6.1`).

- [x] **Step 4: Run focused tests and full existing suite to verify GREEN**

Run: `uv run --offline --no-project --with-editable ".[demo,dev]" --python 3.12 python -m pytest tests/unit/test_query_intent_and_abstention.py tests/eval/test_retrieval_benchmark.py tests/unit/test_dense_hybrid_retrieval.py -v`
Expected: PASS with `0` regressions.

---

### Task 2: Pooled Evaluation Metrics, Paired Bootstrap CIs & Pilot Runner

**Files:**
- Create: `pipelines/benchmark_retrieval/pilot_m2_2.py`
- Modify: `tests/unit/test_retrieval_metrics.py`

**Interfaces:**
- Consumes: `HybridRetrievalService`, `RetrievalRequest`, `NicheQueryFilter`, `packages.common.resources.get_process_peak_rss_mb`
- Produces:
  - `compute_pooled_query_metrics(retrieved_ids: list[str], relevant_ids: set[str], k: int = 10) -> dict[str, float]`
  - `evaluate_pilot_split(service: HybridRetrievalService, queries: list[dict[str, Any]], qrels: dict[str, dict[str, str]], *, rerank: bool, k: int = 10) -> dict[str, Any]`
  - `paired_bootstrap_ci(vals_a: list[float], vals_b: list[float], *, n_boot: int = 1000, seed: int = 42) -> dict[str, float]`
  - `measure_warm_latency(service: HybridRetrievalService, queries: list[dict[str, Any]], *, rerank: bool, n_warm: int = 100, k: int = 10) -> dict[str, float]`

- [x] **Step 1: Add failing hand-calculated metric, zero-pool, `U`-uncertainty, `no_answer`, and bootstrap tests to `tests/unit/test_retrieval_metrics.py`**

Assert exact hand-calculated values:
- `retrieved_ids = ["v1", "v_irrel", "v2"]`, `relevant_ids = {"v1", "v2", "v3", "v4"}`, `k = 10`: `pooled_recall_at_10 == 0.5`, `precision_at_10 == 0.2`, `mrr_at_10 == 1.0`, `ndcg_at_10 == round((1.0 + 1.0 / math.log2(4)) / (1.0 + 1.0 / math.log2(3) + 1.0 / math.log2(4) + 1.0 / math.log2(5)), 6)`.
- `|Relevant_Pool| == 0` answerable query increments `zero_relevant_pool_count` without `ZeroDivisionError`, and `"U"` judgments increment `uncertain_judgment_count` without counting as verified positives.
- `expect_no_answer=True` queries compute `no_answer_abstention_rate == 1.0` and `fabricated_support_count == 0` when `items == []` and `insufficient_evidence is True`, and increment `fabricated_support_count` when non-empty items are returned.
- `paired_bootstrap_ci` with `seed=42` returns deterministic `mean_a`, `mean_b`, `mean_diff`, `ci95_low`, `ci95_high`.

- [x] **Step 2: Run `tests/unit/test_retrieval_metrics.py` to verify RED**

Run: `uv run --offline --no-project --with-editable ".[demo,dev]" --python 3.12 python -m pytest tests/unit/test_retrieval_metrics.py -v`
Expected: FAIL (`ModuleNotFoundError: No module named 'pipelines.benchmark_retrieval.pilot_m2_2'`).

- [x] **Step 3: Implement `pipelines/benchmark_retrieval/pilot_m2_2.py`**

Implement pooled metric functions, `U` completeness accounting, `no_answer` abstention accounting, deterministic paired bootstrap CIs, `1` cold + `100` warm CPU latency runner with `get_peak_rss_mib()`, and CLI entrypoint writing immutable `artifacts/benchmarks/retrieval_v3_pilot.json` (`FileExistsError` on collision) with corpus/index/query/qrels/code SHA256 receipts.

- [x] **Step 4: Run `tests/unit/test_retrieval_metrics.py` to verify GREEN**

Run: `uv run --offline --no-project --with-editable ".[demo,dev]" --python 3.12 python -m pytest tests/unit/test_retrieval_metrics.py -v`
Expected: PASS.

---

### Task 3: Immutable `bm25-v3`, Frozen 40-Query Set (`dev` + `locked test`), Blinded Pooling & Pilot Benchmark

**Files:**
- Create: `artifacts/indexes/bm25-v3/` (`bm25-receipt.json`, `bm25_csr.npz`, `video_ids.json`, `vocab.json`)
- Create: `data/evaluation/v2_pilot/dev_queries.jsonl`
- Create: `data/evaluation/v2_pilot/test_queries.jsonl`
- Create: `data/evaluation/v2_pilot/blinded_pool.csv`
- Create: `data/evaluation/v2_pilot/no_answer_raw_audit.csv`
- Create: `data/evaluation/v2_pilot/qrels_pooled_draft.jsonl`
- Create: `docs/reports/milestones/M2.2/evidence/build_m2_2_pool_and_judgments.py`
- Create: `artifacts/benchmarks/retrieval_v3_pilot.json`

**Interfaces:**
- Consumes: `pipelines.build_dense_sparse_index`, `pipelines.benchmark_retrieval.pilot_m2_2`, `data/corpus/20261118_taxonomy_fix_v1`
- Produces: immutable `bm25-v3` index, frozen `20 dev` + `20 locked test` queries, blinded candidate pool + draft qrels (`K_human_verified=False`, `N_human_verified=False`), and `retrieval_v3_pilot.json`.

- [x] **Step 1: Build `artifacts/indexes/bm25-v3` over `data/corpus/20261118_taxonomy_fix_v1`**

Run: `uv run --offline --no-project --with-editable ".[demo,dev]" --python 3.12 python -m pipelines.build_dense_sparse_index --corpus data/corpus/20261118_taxonomy_fix_v1 --output artifacts/indexes/bm25-v3`
Expected: `bm25-receipt.json` reports `corpus_snapshot_id == "20261118_taxonomy_fix_v1"` and `document_count == 21748`; `bm25-v2` bytes remain untouched.

- [x] **Step 2: Author `dev_queries.jsonl` (`20` queries) and freeze `test_queries.jsonl` (`20` queries)**

Author `10 K` + `10 N` queries per split (`4 synonym, 3 unicode_nfd, 3 negation, 6 filtered, 4 no_answer`), ensuring zero overlap between `dev` and `test`. Inspect `dev_queries.jsonl` behavior ONLY if lexicon refinements are needed before touching `test_queries.jsonl`.

- [x] **Step 3: Generate blinded top-10 candidate pool (`seed=20261119`), `no_answer_raw_audit.csv`, and evidence-inspected draft qrels**

Run `build_m2_2_pool_and_judgments.py` to pool unique top-10 hits from `bm25` and `bm25_reranked`, shuffle blind order per query, inspect full `caption` + `transcript` + metadata of every pooled video (`and raw unguarded top-5 for no_answer queries`), and write `blinded_pool.csv`, `no_answer_raw_audit.csv`, and `qrels_pooled_draft.jsonl` with explicit `ai_assisted_pooled_draft_pending_human_K_N_signoff` provenance.

- [x] **Step 4: Execute `pilot_m2_2.py` to produce `artifacts/benchmarks/retrieval_v3_pilot.json` and per-query CSV/JSON evidence**

Run: `uv run --offline --no-project --with-editable ".[demo,dev]" --python 3.12 python -m pipelines.benchmark_retrieval.pilot_m2_2 --corpus data/corpus/20261118_taxonomy_fix_v1 --bm25 artifacts/indexes/bm25-v3 --dev-queries data/evaluation/v2_pilot/dev_queries.jsonl --test-queries data/evaluation/v2_pilot/test_queries.jsonl --qrels data/evaluation/v2_pilot/qrels_pooled_draft.jsonl --output artifacts/benchmarks/retrieval_v3_pilot.json`
Expected: exits `0`, records `dev` and locked `test` metrics, paired bootstrap 95% CIs, `no_answer` abstention audit, and `100`-request warm CPU latency (`p95 <= 500 ms`).

---

### Task 4: Full Regression Verification, `M2.2` Report Bundle & Milestone Index

**Files:**
- Modify: `.gitattributes` (add `-text` preservation for new measured `M2.2` files/benchmarks)
- Create: `docs/reports/milestones/M2.2/evidence/workflow.md`
- Create: `docs/reports/milestones/M2.2/README.md`
- Modify: `docs/reports/milestones/README.md`

**Interfaces:**
- Consumes: `artifacts/benchmarks/retrieval_v3_pilot.json` and all Task 1–3 logs/receipts.
- Produces: complete `M2.2` milestone report bundle (`IN_PROGRESS` pending human `K` & `N` pool sign-off and `N` peer review) and updated milestone index row.

- [x] **Step 1: Run full project pytest, mypy (Windows & Linux static targets), Ruff, and secret scanner**

Run:
- `pytest -v`
- `mypy packages apps pipelines` and `mypy --platform linux packages apps pipelines`
- `ruff check packages apps pipelines tests/unit/test_query_intent_and_abstention.py tests/unit/test_retrieval_metrics.py docs/reports/milestones/M2.2/evidence/build_m2_2_pool_and_judgments.py`
- `python scripts/check_secrets.py`
Expected: `0` failures, `0` type errors, `0` lint violations, `0` secret leaks, and `0` byte changes to `retrieval_v1.json`, `retrieval_v2.json`, `bm25-v2`, or Gold snapshots.

- [x] **Step 2: Author `M2.2/evidence/workflow.md`, `M2.2/README.md`, and update `docs/reports/milestones/README.md`**

Report `dev` vs locked `test` results, weak-label (`v1`/`v2`) vs pooled pilot (`v3`) comparison, no-answer abstention count, 100-request CPU `p50`/`p95` latency, `U` uncertainty count, and explicit `IN_PROGRESS` boundary pending human `K` & `N` pool verification. Verify top-level layout (`README.md`, `evidence/`, `superpowers/`) and all relative markdown links.
