# Whole-Branch Code Review: `M2.2` (`feat/m2.2-bm25-pilot-and-gate-closures`)

- **Reviewer:** Fresh-Context Read-Only Senior Code Reviewer (`da40c1a5-9157-412c-8f09-b37e32096248`, `gemini-4-carbon-high`)
- **Reviewed Base:** `main` @ `e050d7d5bbcf90e310bbfd144407086d82479341`
- **Date:** 2026-11-19 (Asia/Saigon)
- **Initial Verdict:** `With fixes` (2 Critical, 4 Important, 3 Minor, 2 Declined to judge)

## 1. Strengths
- **Immutable historical preservation & cryptographic provenance (`pipelines/benchmark_retrieval/pilot_m2_2.py:372-379, 436-457, 478`, `artifacts/benchmarks/retrieval_v3_pilot.json:30-63`):** `bm25-v3` (`21,748` transcribed videos over `20261118_taxonomy_fix_v1`) and `retrieval_v3_pilot.json` fail closed on collision (`open("x")`) and bind verified SHA256 digests across the Gold manifest, Parquet files, BM25 CSR artifacts, `dev`/`test` query files, draft qrels, and retrieval code. Verified `0` byte changes to `retrieval_v1.json`, `retrieval_v2.json`, `bm25-v2/`, `data/evaluation/v1/queries.jsonl`, and Gold snapshots, plus `0` secret leaks (`scripts/check_secrets.py`) and `0` broken markdown links across `docs/reports/milestones/M2.2/`.
- **Scientific honesty, dev/locked-test hygiene & provenance qualification (`docs/reports/milestones/M2.2/README.md:3, 15-22, 66-67`, `artifacts/benchmarks/retrieval_v3_pilot.json:13-22, 2134-2163`):** Properly keeps `M2.2 = IN_PROGRESS` with `label_source = "ai_assisted_pooled_draft_pending_human_K_N_signoff"` and `K_human_verified=False` / `N_human_verified=False` across all `408` pooled rows; qualifies recall as `pooled_recall_at_10`; honestly reports the `locked_test` `nDCG@10` delta (`-0.0118`, 95% CI `[-0.1462, +0.1120]`) without peeking/tuning on `locked_test`; and transparently reports both `14/16` (`MRR@10 = 0.7679`) and `16/16` (`MRR@10 = 0.6719`) denominators for zero-pool queries (`t_k04`, `t_k07`).
- **Strict geographic filter discipline & `NFC` normalization (`packages/retrieval/service.py:135-157, 178-193, 210-217`, `packages/retrieval/query_intent.py:142`, `tests/unit/test_query_intent_and_abstention.py:167-180, 212-227`):** Prevents `_resolve_candidate_pool` and lexical fallback from relaxing `city_norm`/`region` into fabricated cross-city matches while preserving broad city browse queries (`!intent.has_specific_anchors`), and normalizes `NFD` combining diacritics to `NFC` prior to tokenization.
- **Blinded pooling & raw `no_answer` audit (`docs/reports/milestones/M2.2/evidence/extract_blinded_pool.py:49-53, 94-113`, `data/evaluation/v2_pilot/no_answer_raw_audit.csv:1-41`):** Deterministic rank/origin-stripped candidate shuffling (`seed=20261119`), written ternary (`1`/`0`/`U`) guidelines, full-transcript disagreement adjudication (`adjudication_overrides.json`), and a 40-row unguarded raw BM25 top-5 audit confirming `0` suppressed relevant videos across all `8` `no_answer` queries.
- **Backward-compatible contract & low CPU latency (`packages/data_contracts/retrieval.py:57-58`, `artifacts/benchmarks/retrieval_v3_pilot.json:2166-2190`):** Optional `insufficient_evidence` and `abstain_reason` defaults preserve full caller compatibility, achieving `15.39 ms` (`bm25`) and `26.55 ms` (`bm25_reranked`) 100-request warm CPU `p95` (`<= 500 ms` budget).

---

## 2. Issues

### Critical

1. **Greedy regex cursor advancement breaks multi-negation queries, 3-token negated terms, and truly all-negated queries (`packages/retrieval/query_intent.py:97-102, 157-191`, `packages/retrieval/service.py:200, 331`, `tests/unit/test_query_intent_and_abstention.py:245-248`)**
   - `_NEG_MARKER_RE.finditer(q_nfc)` advances past `match.end()` even when breaking early at `_NEG_STOP_BOUNDARIES` or `len(kept) == 2`, skipping subsequent negations (`"không cay không mắm tôm"` -> `positive_query='không mắm tôm'`), truncating 3-token negations (`"không nước cốt dừa"` -> leaves `"dừa"` positive), omitting `ghét|bỏ|trừ` from `spec.md:30`, and falling back to `intent.normalized_query` when `positive_query == ""` in `service.py:200, 331`.

2. **Hardcoded machine-specific `.gemini` scratch path and uncommitted upstream draft files break reproducibility of `build_m2_2_pool_and_judgments.py` (`docs/reports/milestones/M2.2/evidence/build_m2_2_pool_and_judgments.py:12, 35-36`)**
   - Hardcodes `SCRATCH_DIR` pointing outside the repo for `judgments_{K,N}_{dev,test}.jsonl`.

### Important

3. **Unconditional all-group OOV check causes false abstention (`items=[]`) whenever a valid dish query also contains any OOV shop name, street, creator handle, or typo (`packages/retrieval/query_intent.py:268-283`, `packages/retrieval/service.py:202-227, 278`)**
   - `check_vocab_anchor_support()` abstains if *any* group in `intent.anchor_groups` is OOV even when a specific multi-word `explicit_dishes` / culinary synonym group is supported in `vocab`, and runs after `bm25.search()`.

4. **Raw substring check (`neg in full_doc`) and narrow exemption in `EvidenceReranker` misfire on Vietnamese syllable substrings and `"không ăn được ..."` (`packages/retrieval/rerank/scorer.py:91-94`)**
   - `neg in full_doc` penalizes `"các"`/`"cách"` on `"cá"` and `"thành"`/`"nhánh"` on `"hành"`, while missing `"không ăn được mắm tôm"`, `"không có hành"`, `"không cho hành"`.

5. **`evaluate_pilot_split` omits answerable false-abstention tracking and single-system bootstrap 95% CIs (`pipelines/benchmark_retrieval/pilot_m2_2.py:174-257, 351-358`)**
   - Omits `answerable_abstained_count`, `mrr_at_10_all_answerable` / `ndcg_at_10_all_answerable`, `per_query` `insufficient_evidence`/`abstain_reason`, and single-system 95% CIs (`ci95_a`, `ci95_b`).

6. **Dense and `hybrid_rrf` (when dense is active) bypass `NFC`/positive query normalization and candidate anchor/abstention guards (`packages/retrieval/service.py:243, 277`)**
   - Passes raw `request.query` to `_encode_dense_query()` and restricts OOV/anchor verification to `effective_mode == "bm25"`.

### Minor

7. **`dev`/`test` disjointness check in `pilot_m2_2.py:384-387` does not normalize `NFC` or check `query_id` overlap.**
8. **Full-file CRLF/LF diff churn in `packages/data_contracts/retrieval.py` and multi-task working tree.**
9. **Schema key naming drift between `spec.md:62` (`adjudicated_rel_draft`) and qrels implementation (`adjudicated_rel`).**

---

## 3. Declined to judge
- **`AppSettings` default paths (`packages/common/settings/__init__.py:43-46`) remaining pointed at `20261117_recovered_v1` / `bm25-v2` / `retrieval_v2.json`.**
- **Lexical breadth on unindexed multi-word dishes outside `COMMON_DISH_KEYWORDS` (e.g., `t_n04` `"trà mãng cầu"` admitting generic `"trà"` videos into `tier_1`).**

---

## 4. Assessment
**Ready:** `With fixes`
