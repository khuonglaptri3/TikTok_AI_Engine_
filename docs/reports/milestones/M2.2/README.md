# M2.2 — Corrected BM25 Evaluation, Query Intent Guardrails & Pooled Relevance Pilot

- Status: IN_PROGRESS (Primary `K` engineering, `bm25-v3` index build, `40`-query disjoint `dev`/`locked_test` benchmark, blinded dual-pass candidate pool inspection, whole-branch code review & TDD fix pass, `100`-request CPU latency verification, and `N`'s bounded `gemini-3.1-flash-lite` `408`-row verification pass complete; awaiting human `K` & `N` resolution on `109` LLM-flagged pool disagreements / sign-off on `blinded_pool.csv`)
- Execution date: 2026-11-19 (Asia/Saigon)
- Requirement source: [TikTok_AI_Engine_Milestone.md](../../../planning/TikTok_AI_Engine_Milestone.md) (`M2.2`)
- Repository version: `feat/m2.2-bm25-pilot-and-gate-closures` (branched from `main` @ `e050d7d5bbcf90e310bbfd144407086d82479341`)
- Primary owner: Trần Đình Khương (`K`) · Peer reviewer: Nguyễn Việt Nguyên (`N`)
- Specification: [spec.md](superpowers/spec.md)
- Execution plan: [plan.md](superpowers/plan.md)

## Conclusion

Built immutable sparse index **`artifacts/indexes/bm25-v3/`** (`21,748` transcribed documents, `vocab_size = 390,943`) over the taxonomy-corrected snapshot `data/corpus/20261118_taxonomy_fix_v1`, added a `USD 0` CPU-offline Vietnamese query-intent & abstention layer (`packages/retrieval/query_intent.py`, `scorer.py`, `service.py`), preserved historical `retrieval_v1.json`, `retrieval_v2.json`, `bm25-v2/`, and `data/evaluation/v1/queries.jsonl` (`16` weak-label regression queries) byte-for-byte untouched, and evaluated `40` disjoint pilot queries (`20` `dev` + `20` `locked_test`) in immutable receipts [retrieval_v3_pilot.json](../../../../artifacts/benchmarks/retrieval_v3_pilot.json) (initial) and [retrieval_v3_1_pilot.json](../../../../artifacts/benchmarks/retrieval_v3_1_pilot.json) (post-code-review).

On the untuned **`locked_test`** split in `retrieval_v3_1_pilot.json` (`16` answerable + `4` `no_answer` queries; `408` blinded candidate pairs judged across two independent blinded AI draft passes with `94.85%` overall raw agreement and ternary Cohen's $\kappa = 0.9109$, explicitly qualified as `ai_assisted_pooled_draft_pending_human_K_N_signoff`):
- **Answerable Relevance (`14` positive-pool queries with `0` false abstentions; all-`16` answerable denominator including sparse/uncertain `t_k04`, `t_k07` also reported):**
  - `bm25`: **`MRR@10 = 0.7440`** (`95% CI [0.5891, 0.8929]`; all-`16` **`0.6510 >= 0.60`**), **`nDCG@10 = 0.7438`** (`[0.6348, 0.8447]`; all-`16` **`0.6508 >= 0.50`**), `Pooled Recall@10 = 0.8717`, `Precision@10 = 0.4214`.
  - `bm25_reranked`: **`MRR@10 = 0.8036`** (`95% CI [0.6071, 1.0000]`; all-`16` **`0.7031 >= 0.60`**), **`nDCG@10 = 0.7475`** (`[0.5747, 0.9001]`; all-`16` **`0.6541 >= 0.50`**), `Pooled Recall@10 = 0.7809`, `Precision@10 = 0.4286` (lifting `negation` `MRR@10` from `0.4167` to `1.0000` and `synonym` `nDCG@10` from `0.8224` to `0.9223`; paired `delta_MRR@10 = +0.0595 [-0.0952, +0.2381]`, `delta_nDCG@10 = +0.0037 [-0.1408, +0.1470]`).
- **No-Answer & False-Abstention Guardrails:** **`4/4 = 100%` abstention (`0` fabricated support)** on both `dev` and `locked_test` (verified against `40` raw unguarded BM25 top-5 candidates in [no_answer_raw_audit.csv](../../../../data/evaluation/v2_pilot/no_answer_raw_audit.csv)) and **`0 / 16` (`0.0%`) false abstentions** on answerable queries across both splits.
- **100-Request Warm CPU Latency (`concurrency = 1`, Windows 11, `12` logical CPUs):** `bm25` `warm p50 = 7.68 ms`, **`warm p95 = 15.53 ms <= 500 ms`**; `bm25_reranked` `warm p50 = 18.09 ms`, **`warm p95 = 29.70 ms <= 500 ms`** (`peak_rss_mib = 1,015.18 MiB`).

All `139/139` project `pytest` tests, `83`-file Windows & Linux `mypy`, `ruff`, and `scripts/check_secrets.py` pass. Per `AGENTS.md` Section 4, task `M2.2` remains **`IN_PROGRESS`** until human contributors `K` and `N` verify/sign off [blinded_pool.csv](../../../../data/evaluation/v2_pilot/blinded_pool.csv) (`K_human_verified`, `N_human_verified`) and `N` completes reciprocal peer review.

## Summary of Measured Results (`retrieval_v3_1_pilot.json`)

| Split & Configuration | Pos-Pool (`All-16`) | False Abstain | Pooled Recall@10 | Precision@10 | MRR@10 (`All-16`) | nDCG@10 (`All-16`) | No-Answer Abstain (`Fab`) | Warm p50 / p95 (`100` req) |
| --- | --- | ---: | ---: | ---: | --- | --- | --- | --- |
| `dev` — `bm25` | `15` (`16`; `d_k07`) | `0` | `0.8094` | `0.4533` | `0.8500` (`0.7969`) | `0.7493` (`0.7025`) | `4/4 = 100%` (`0`) | — |
| `dev` — `bm25_reranked` | `15` (`16`; `d_k07`) | `0` | `0.8473` | `0.4400` | `0.8833` (`0.8281`) | `0.7726` (`0.7243`) | `4/4 = 100%` (`0`) | — |
| `locked_test` — `bm25` | `14` (`16`; `t_k04, t_k07`) | `0` | `0.8717` | `0.4214` | **`0.7440`** (`0.6510`) | **`0.7438`** (`0.6508`) | **`4/4 = 100%` (`0`)** | `7.68 ms` / **`15.53 ms`** |
| `locked_test` — `bm25_reranked` | `14` (`16`; `t_k04, t_k07`) | `0` | `0.7809` | `0.4286` | **`0.8036`** (`0.7031`) | **`0.7475`** (`0.6541`) | **`4/4 = 100%` (`0`)** | `18.09 ms` / **`29.70 ms`** |

## Work performed

- **Contract & Query Intent Guardrails ([retrieval.py](../../../../packages/data_contracts/retrieval.py), [query_intent.py](../../../../packages/retrieval/query_intent.py), [scorer.py](../../../../packages/retrieval/rerank/scorer.py), [service.py](../../../../packages/retrieval/service.py)):** Added backward-compatible `insufficient_evidence` / `abstain_reason` fields, `NFC` query normalization across `bm25`/`dense`/`hybrid_rrf`, multi-negation cursor extraction (`1–3` tokens, `(?<!ăn\s)kiêng` diet protection, `ghét`/`bỏ`/`trừ`, all-negated abstention), word-boundary reranker negation penalty with `0..2`-token dietary accommodation exemption, bidirectional F&B/regional synonym expansion, strict `city_norm`/`region` filter preservation, and core-dish-aware OOV/observed-anchor abstention (`14/14` unit tests in [test_query_intent_and_abstention.py](../../../../tests/unit/test_query_intent_and_abstention.py)).
- **Immutable `bm25-v3` & Pooled Metric Runner ([pilot_m2_2.py](../../../../pipelines/benchmark_retrieval/pilot_m2_2.py), [test_retrieval_metrics.py](../../../../tests/unit/test_retrieval_metrics.py)):** Built `artifacts/indexes/bm25-v3/` on `20261118_taxonomy_fix_v1` and verified hand-calculated `pooled_recall_at_10`, `precision_at_10`, `mrr_at_10`, `ndcg_at_10`, `answerable_abstained_count`, all-`16` answerable macro denominators, `U`-uncertainty tracking (`9.00%` dev, `11.17%` test), and single-system + paired bootstrap 95% CIs (`10/10` unit tests).
- **40-Query Disjoint Pilot, Physically Blinded Dual-Pass Pooling & Code Review (`data/evaluation/v2_pilot/`):** Authored `20` `dev` and `20` `locked_test` queries, extracted `408` rank-stripped shuffled candidate pairs, ran two independent blinded passes (`raw_agreement = 94.85%`, $\kappa = 0.9109$), adjudicated all `21` disagreements from full transcripts, completed a fresh-context Senior Code Review ([code-review.md](evidence/code-review.md)) with TDD `RED -> GREEN` fixes for all `6` Critical/Important items, and emitted [retrieval_v3_1_pilot.json](../../../../artifacts/benchmarks/retrieval_v3_1_pilot.json) while preserving [retrieval_v3_pilot.json](../../../../artifacts/benchmarks/retrieval_v3_pilot.json) untouched.
- **Bounded LLM Pool Verification (`2026-11-19`, `<= 14 RPM` per contributor override):** Ran [verify_pool_with_gemini.py](evidence/verify_pool_with_gemini.py) (`gemini-3.1-flash-lite`, `34` batches x `12` rows) over all `408` rows of `blinded_pool.csv` against full transcripts (`20261118_taxonomy_fix_v1`). Recorded `299/408` (`73.28%`, $\kappa = 0.5297$; `dev = 69.67%`, `locked_test = 77.16%`) agreement with `adjudicated_rel` and `109` disagreement rows in [nguyen_llm_pool_audit.csv](evidence/nguyen_llm_pool_audit.csv) and [nguyen_llm_pool_summary.json](evidence/nguyen_llm_pool_summary.json) while keeping `K_human_verified=False` and `N_human_verified=False` untouched.

## Outputs

| File | Purpose |
| --- | --- |
| [workflow.md](evidence/workflow.md), [code-review.md](evidence/code-review.md) | Superpowers TDD/blinding ledger, rulings, deferred minors, and fresh-context Senior Code Review |
| [relevance_guidelines.md](evidence/relevance_guidelines.md) | Ternary (`1`/`0`/`U`) coding guidelines for blinded pooled evaluation |
| [judgments_K_dev.jsonl](evidence/judgments_K_dev.jsonl), [judgments_K_test.jsonl](evidence/judgments_K_test.jsonl), [judgments_N_dev.jsonl](evidence/judgments_N_dev.jsonl), [judgments_N_test.jsonl](evidence/judgments_N_test.jsonl) | Repo-local raw blinded pass outputs reproducing `blinded_pool.csv` via [build_m2_2_pool_and_judgments.py](evidence/build_m2_2_pool_and_judgments.py) |
| [pool_agreement_and_disagreements.json](evidence/pool_agreement_and_disagreements.json), [adjudication_overrides.json](evidence/adjudication_overrides.json) | Inter-annotator agreement (`94.85%`, $\kappa = 0.9109$) and full-transcript adjudication of `21` items |
| [dev_queries.jsonl](../../../../data/evaluation/v2_pilot/dev_queries.jsonl), [test_queries.jsonl](../../../../data/evaluation/v2_pilot/test_queries.jsonl) | Disjoint frozen `20`-dev and `20`-locked-test queries (including `NFD` Unicode queries) |
| [blinded_pool.csv](../../../../data/evaluation/v2_pilot/blinded_pool.csv), [qrels_pooled_draft.jsonl](../../../../data/evaluation/v2_pilot/qrels_pooled_draft.jsonl), [no_answer_raw_audit.csv](../../../../data/evaluation/v2_pilot/no_answer_raw_audit.csv) | `408` blinded pooled rows, draft qrels (`K_human_verified=False`, `N_human_verified=False`), and `40`-row unguarded `no_answer` audit |
| [verify_pool_with_gemini.py](evidence/verify_pool_with_gemini.py), [nguyen_llm_pool_audit.csv](evidence/nguyen_llm_pool_audit.csv), [nguyen_llm_pool_summary.json](evidence/nguyen_llm_pool_summary.json) | Bounded `<= 14 RPM` `gemini-3.1-flash-lite` independent check over all `408` pool rows (`299/408 = 73.28%` agreement, $\kappa = 0.5297$, `109` disagreements) |
| [retrieval_v3_pilot.json](../../../../artifacts/benchmarks/retrieval_v3_pilot.json), [retrieval_v3_1_pilot.json](../../../../artifacts/benchmarks/retrieval_v3_1_pilot.json) | Initial and post-review immutable benchmark receipts with SHA256 provenance, CIs, and `100`-req latency |
| [red-task1-query-intent.log](evidence/red-task1-query-intent.log), [green-task1-query-intent.log](evidence/green-task1-query-intent.log), [red-task2-metrics.log](evidence/red-task2-metrics.log), [green-task2-metrics.log](evidence/green-task2-metrics.log), [red-review-fixes.log](evidence/red-review-fixes.log), [green-review-fixes.log](evidence/green-review-fixes.log) | TDD RED and GREEN test logs across Tasks 1, 2, and the post-review fix pass |
| [pytest-full.log](evidence/pytest-full.log), [mypy-windows.log](evidence/mypy-windows.log), [mypy-linux-target.log](evidence/mypy-linux-target.log), [ruff.log](evidence/ruff.log), [pilot-benchmark-v3-1.log](evidence/pilot-benchmark-v3-1.log) | Full `139`-test suite, Windows/Linux `mypy` (`83` files), Ruff, and `v3_1` benchmark logs |

## Verification

| Check | Result | Scope / evidence |
| --- | --- | --- |
| `pytest -v` | PASS (`139 passed in 25.28s`) | All contract, smoke, eval (`v1`), retrieval, dense parity, guardrail, and continuity tests; [pytest-full.log](evidence/pytest-full.log) |
| `mypy` (Windows & `--platform linux`) | PASS (`83` source files) | [mypy-windows.log](evidence/mypy-windows.log), [mypy-linux-target.log](evidence/mypy-linux-target.log) |
| `ruff check` & `scripts/check_secrets.py` | PASS (`0` issues, `0` leaks) | [ruff.log](evidence/ruff.log) |
| `python -m pipelines.benchmark_retrieval.pilot_m2_2` (`retrieval_v3_1_pilot`) | PASS (`MRR@10 = 0.8036`, `nDCG@10 = 0.7475`, `p95 = 29.70 ms`) | Untuned locked test evaluation & `100`-warm-request CPU benchmark; [retrieval_v3_1_pilot.json](../../../../artifacts/benchmarks/retrieval_v3_1_pilot.json) |

## Open issues

| Issue | Impact | Follow-up / responsible task |
| --- | --- | --- |
| Human `K` & `N` sign-off on `blinded_pool.csv` and `N` peer review pending | AI-assisted blinded draft labels do not substitute for two-human verification | `K` and `N` inspect/confirm `blinded_pool.csv` (`408` rows) and `N` reviews `M2.2` before closing `M2.2` and unblocking `M2.G` / `M6.1` |
| `3` queries (`d_k07`, `t_k04`, `t_k07`) had `0` verified `1`s in top-10 pool (`t_k04` had `8` `U`s because `phở bò` transcripts omit scallion presence; `t_k07` lacked Hanoi egg-coffee transcripts) | Both positive-pool (`14/16`: `MRR@10 = 0.8036`, `nDCG@10 = 0.7475`) and all-answerable (`16/16`: `MRR@10 = 0.7031 >= 0.60`, `nDCG@10 = 0.6541 >= 0.50`) denominators are recorded directly in `retrieval_v3_1_pilot.json` | Retain dual-denominator reporting in `M2.G` and `M6.1` |

## Acceptance and handoff

| Task criterion | Result | Evidence |
| --- | --- | --- |
| Preserve `retrieval_v1.json`, `retrieval_v2.json`, `bm25-v2`, and `16` weak-label regressions | Met | [test_retrieval_benchmark.py](../../../../tests/eval/test_retrieval_benchmark.py), [pytest-full.log](evidence/pytest-full.log) |
| Hand-calculated metric tests, disjoint frozen `20 dev` / `20 test`, and SHA256 receipts | Met | [test_retrieval_metrics.py](../../../../tests/unit/test_retrieval_metrics.py), [retrieval_v3_1_pilot.json](../../../../artifacts/benchmarks/retrieval_v3_1_pilot.json) |
| Provisional test `MRR@10 >= 0.60`, `nDCG@10 >= 0.50`, `0` no-answer fabrication, warm `p95 <= 500 ms` | Met on draft qrels (`0.8036` / `0.7031`, `0.7475` / `0.6541`, `0` fabricated, `29.70 ms`) | [retrieval_v3_1_pilot.json](../../../../artifacts/benchmarks/retrieval_v3_1_pilot.json) |
| Human `K` & `N` pool sign-off and `N` peer review | Pending human sign-off | [blinded_pool.csv](../../../../data/evaluation/v2_pilot/blinded_pool.csv) |

Final task status: **`IN_PROGRESS`** (all code, index `bm25-v3`, `40`-query pilot, blinded draft pool, code-review TDD fixes, and latency checks complete; awaiting human `K` & `N` pool confirmation and `N` peer review).
