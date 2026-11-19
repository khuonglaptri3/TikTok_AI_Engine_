# M2.2 — Workflow Provenance & Execution Ledger

- **Plan:** `docs/reports/milestones/M2.2/superpowers/plan.md`
- **Spec:** `docs/reports/milestones/M2.2/superpowers/spec.md`
- **Date:** 2026-11-19 (Asia/Saigon)
- **Primary Owner:** Trần Đình Khương (`K`) · **Peer Reviewer:** Nguyễn Việt Nguyên (`N`)
- **Base Revision:** `main` @ `e050d7d5bbcf90e310bbfd144407086d82479341`

## Setup & Pre-flight Ledger
- **Skills read & applied:** `using-superpowers`, `brainstorming`, `writing-plans`, `executing-plans`, `using-git-worktrees`, `test-driven-development`, `requesting-code-review`, `verification-before-completion`.
- **Execution mode:** Native inline execution selected by project owner (`2026-11-19T01:58:02+07:00`) with a fresh-context subagent code review at the end.
- **Ruling (Workspace isolation):** Use topic branch `feat/m2.2-bm25-pilot-and-gate-closures` in the active checkout rather than creating `.worktrees/` — avoids duplicating `37,849` data/index files (`1.59 GB`) on Windows disk and preserves in-progress `M0.G`/`M1.G`/`M3.1`/`M2.2` files while protecting `main` — cost if wrong: switching back to `main` requires stashing or committing on the topic branch first.
- **Ruling (Execution ledger):** Persist the execution ledger in `docs/reports/milestones/M2.2/evidence/workflow.md` per `AGENTS.md` Section 7 rather than `.superpowers/sdd/` Bash scratch scripts (`Windows` PowerShell harness) — cost if wrong: none, durable repo provenance is stronger.
- **Pre-flight interface check:**
  - Task 1 produces `RetrievalResponse.insufficient_evidence` / `abstain_reason`, `parse_query_intent`, and updated `HybridRetrievalService.search` / `EvidenceReranker.rerank` -> consumed by Task 2 (`pilot_m2_2.py`) and Task 3 (`build_m2_2_pool_and_judgments.py` & `retrieval_v3_pilot.json`). Signatures match 100%.
  - Task 2 produces `compute_pooled_query_metrics`, `evaluate_pilot_split`, `paired_bootstrap_ci`, `measure_warm_latency`, and CLI `pipelines.benchmark_retrieval.pilot_m2_2` -> consumed by Task 3 & Task 4. Signatures match 100%.

## Task Execution Ledger
- **Task 1 (`query_intent.py`, `scorer.py`, `service.py`, `retrieval.py`):**
  - RED: `tests/unit/test_query_intent_and_abstention.py` -> `7 failed, 1 passed` ([red-task1-query-intent.log](red-task1-query-intent.log)).
  - GREEN: `27 passed in 17.39s` across `test_query_intent_and_abstention.py`, `test_retrieval_benchmark.py`, `test_dense_hybrid_retrieval.py`, `test_analytics_and_retrieval.py`, and `test_retrieval_metrics.py` ([green-task1-query-intent.log](green-task1-query-intent.log)). Task 1: complete.
- **Task 2 (`pilot_m2_2.py`, `test_retrieval_metrics.py`):**
  - **Ruling:** `plan.md` referenced `get_process_peak_rss_mb` whereas `packages/common/resources.py` exports `get_peak_rss_mib()` — used `get_peak_rss_mib()` — cost if wrong: none, matches canonical helper.
  - RED: `tests/unit/test_retrieval_metrics.py` -> `3 failed, 5 passed` ([red-task2-metrics.log](red-task2-metrics.log)).
  - GREEN: `8 passed in 1.89s` ([green-task2-metrics.log](green-task2-metrics.log)). Task 2: complete.
- **Task 3 (`bm25-v3` & 40-query pilot):**
  - Built `artifacts/indexes/bm25-v3/` over `data/corpus/20261118_taxonomy_fix_v1` (`21,748` docs, `vocab_size = 390,943`, `postings_count = 9,469,556`, [bm25-v3-build.log](bm25-v3-build.log)).
  - Authored disjoint frozen `dev_queries.jsonl` (`20` queries) and `test_queries.jsonl` (`20` locked test queries) via [write_v2_pilot_queries.py](write_v2_pilot_queries.py) prior to inspecting `bm25-v3` outputs.
  - Dev-only validation (`0` peeking on `test_queries.jsonl`) surfaced two edge cases (`xôi thịt kho` with spurious legacy `dishes=['bún đậu']` tag and a Christmas cake shaped like a reindeer matching bare `'tuần lộc'`); added two TDD `RED -> GREEN` regressions to `tests/unit/test_query_intent_and_abstention.py` (`10/10` pass) and tiered full-anchor matches ahead of partial-word matches so `test_dense_hybrid_retrieval.py` parity (`133/133` full suite) passes unchanged.
  - **Ruling (Blinded dual-pass annotation):** Physically moved `pool_provenance_map.json` outside the workspace while 4 isolated fresh-context subagents (`K_dev`, `N_dev`, `K_test`, `N_test`) independently judged all `408` shuffled candidate pairs (`blinded_candidates_only.jsonl`) against [relevance_guidelines.md](relevance_guidelines.md) (`raw_agreement = 94.85%`, `387/408`, ternary Cohen's $\kappa = 0.9109$, `21` disagreements). Inspected full untruncated transcripts in [disagreed_full_transcripts.txt](disagreed_full_transcripts.txt) while still blinded to system origin to record [adjudication_overrides.json](adjudication_overrides.json), then emitted `data/evaluation/v2_pilot/blinded_pool.csv`, `no_answer_raw_audit.csv`, `qrels_pooled_draft.jsonl`, and immutable `artifacts/benchmarks/retrieval_v3_pilot.json` ([pilot-benchmark.log](pilot-benchmark.log)) with `label_source = "ai_assisted_pooled_draft_pending_human_K_N_signoff"` — cost if wrong: human `K` & `N` reviewers override draft cells in `blinded_pool.csv` before closing `M2.2`. Task 3: complete.
- **Task 4 (Full verification, whole-branch code review, single TDD fix pass & reporting):**
  - Initial pre-review suite: `133 passed in 30.46s`, `83`-file Windows & Linux `mypy`, `ruff`, and `check_secrets.py` clean.
  - Dispatched fresh-context read-only Senior Code Reviewer (`da40c1a5-9157-412c-8f09-b37e32096248`, `gemini-4-carbon-high`) against `spec.md`, `plan.md` Review Focus, and `workflow.md` rulings; verdict `With fixes` (`2` Critical, `4` Important, `3` Minor, `2` Declined to judge) saved in [code-review.md](code-review.md).
  - Executed single post-review TDD fix pass ([red-review-fixes.log](red-review-fixes.log) -> [green-review-fixes.log](green-review-fixes.log)):
    - `Final: fixed Critical #1 (multi-negation cursor, 3-token negation, ăn-kiêng guard, ghét/bỏ/trừ markers, and all-negated query abstention) — test_multi_negation_three_token_negation_and_all_negated_abstention RED→GREEN, suite 139/139`
    - `Final: fixed Critical #2 (repo-local blinded judgment files in evidence/ without machine-specific SCRATCH_DIR path) — test_pool_builder_script_uses_repo_local_evidence_without_machine_paths RED→GREEN, suite 139/139`
    - `Final: fixed Important #3 (in-vocab core dish + OOV shop/brand query does not false-abstain and early OOV check precedes bm25.search) — test_in_vocab_dish_with_oov_venue_name_does_not_false_abstain_while_exotic_dish_abstains RED→GREEN, suite 139/139`
    - `Final: fixed Important #4 (word-boundary negation match and 0..2-token dietary accommodation exemption in EvidenceReranker) — test_reranker_negation_uses_word_boundaries_and_exempts_dietary_accommodation RED→GREEN, suite 139/139`
    - `Final: fixed Important #5 (answerable false-abstention tracking, all-16 answerable macro metrics, and single-system bootstrap 95% CIs in pilot_m2_2.py) — test_pilot_split_tracks_false_abstention_all_answerable_and_per_query_abstention & test_pilot_paired_bootstrap_ci_is_deterministic RED→GREEN, suite 139/139`
    - `Final: fixed Important #6 (NFC/positive query normalization and OOV/anchor abstention parity across dense and hybrid_rrf modes) — test_dense_and_hybrid_rrf_enforce_query_normalization_and_no_answer_abstention RED→GREEN, suite 139/139`
    - `Final: Ruling: AppSettings default paths (packages/common/settings/__init__.py:43-46) remaining pointed at 20261117_recovered_v1 / bm25-v2 / retrieval_v2.json — callers of default /demo/ and smoke tests keep the M0.G-accepted baseline while M2.2 remains IN_PROGRESS awaiting human K & N pool sign-off and M2.G cutover — cost if wrong: /demo/ uses bm25-v2 unless TIKTOK_CORPUS_DIR and TIKTOK_BM25_INDEX_DIR are set or M2.G switches defaults.`
    - `Final: Ruling: Lexical breadth on unindexed multi-word dishes outside COMMON_DISH_KEYWORDS (e.g., t_n04 "trà mãng cầu" admitting generic "trà" videos into tier_1) — BM25 IDF still ranks exact phrase matches ahead while preserving untuned locked_test integrity without post-hoc keyword fitting ahead of M6.1 dense/hybrid comparison — cost if wrong: slightly lower reranked nDCG@10 on uncatalogued compound dishes (locked_test bm25_reranked nDCG@10 = 0.7475 >= 0.50).`
    - `Final: minor (deferred): pilot_m2_2.py dev/test disjointness guard omits NFC normalization and query_id collision check (current 40 v2_pilot queries already verified disjoint under NFC).`
    - `Final: minor (deferred): packages/data_contracts/retrieval.py CRLF line-ending diff noise without git diff -w and shared branch working tree across M0.G/M1.G/M3.1/M2.2.`
    - `Final: minor (deferred): spec.md:62 names column adjudicated_rel_draft whereas CSV, JSONL qrels, and pilot_m2_2.py consistently use adjudicated_rel.`
  - Preserved `artifacts/benchmarks/retrieval_v3_pilot.json` untouched on disk, audited the `23` post-fix top-10 pool shifts (`0` missed positives), and emitted immutable post-review receipt `artifacts/benchmarks/retrieval_v3_1_pilot.json` ([pilot-benchmark-v3-1.log](pilot-benchmark-v3-1.log)).
  - Final full `pytest -v`: `139 passed in 25.28s` ([pytest-full.log](pytest-full.log)).
  - Final `mypy` Windows & `--platform linux`: `Success: no issues found in 83 source files` ([mypy-windows.log](mypy-windows.log), [mypy-linux-target.log](mypy-linux-target.log)).
  - Final `ruff check` & `scripts/check_secrets.py`: `All checks passed!` ([ruff.log](ruff.log)), `PASS: Zero secret leaks detected across workspace.`

## Follow-up `N` LLM Pool Verification (`2026-11-19`, `feat/m2.2-m2.3-llm-audit`)
- Per contributor override (`<= 15 RPM`), executed `verify_pool_with_gemini.py --batch-size 12 --max-rpm 14` (`gemini-3.1-flash-lite`, `34` batches, `408/408` rows).
- Raw agreement vs `adjudicated_rel`: `299/408` (`73.28%`, `dev=69.67%`, `locked_test=77.16%`, ternary $\kappa = 0.5297`); `109` disagreement slots exported to `nguyen_llm_pool_summary.json`. `K_human_verified=False` and `N_human_verified=False` in `blinded_pool.csv` remain untouched.
