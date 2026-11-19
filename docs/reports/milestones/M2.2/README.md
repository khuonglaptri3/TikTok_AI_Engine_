# M2.2 — Corrected BM25 Evaluation, Query Intent Guardrails & Pooled Relevance Pilot

- Status: IN_PROGRESS (Primary `K` engineering, `bm25-v3` index build, `40`-query disjoint `dev`/`locked_test` benchmark, `N`'s bounded `gemini-3.1-flash-lite` `408`-row check, and `K`'s `408`-row full-transcript human audit & owner `Q1`–`Q6` adjudication with `K_human_verified = True` complete; awaiting `N`'s independent human sign-off `N_human_verified` on `blinded_pool.csv` and `N` peer review)
- Execution date: 2026-11-19 (Asia/Saigon)
- Requirement source: [TikTok_AI_Engine_Milestone.md](../../../planning/TikTok_AI_Engine_Milestone.md) (`M2.2`)
- Repository version: `feat/k-m2.2-m2.3-m3.2-deliverables` (rebased onto `main` @ `f130d4b5`)
- Primary owner: Trần Đình Khương (`K`) · Peer reviewer: Nguyễn Việt Nguyên (`N`)
- Specification: [spec.md](superpowers/spec.md)
- Execution plan: [plan.md](superpowers/plan.md)

## Conclusion

Built immutable sparse index **`artifacts/indexes/bm25-v3/`** (`21,748` transcribed documents, `vocab_size = 390,943`) over the taxonomy-corrected snapshot `data/corpus/20261118_taxonomy_fix_v1`, added a `USD 0` CPU-offline Vietnamese query-intent & abstention layer (`packages/retrieval/query_intent.py`, `scorer.py`, `service.py`), preserved historical `retrieval_v1.json`, `retrieval_v2.json`, `bm25-v2/`, `data/evaluation/v1/queries.jsonl` (`16` weak-label regression queries), [retrieval_v3_pilot.json](../../../../artifacts/benchmarks/retrieval_v3_pilot.json), and [retrieval_v3_1_pilot.json](../../../../artifacts/benchmarks/retrieval_v3_1_pilot.json) byte-for-byte untouched, recorded `N`'s bounded `gemini-3.1-flash-lite` check ([nguyen_llm_pool_audit.csv](evidence/nguyen_llm_pool_audit.csv)), and completed **`K`'s full untruncated transcript audit across all `408` pooled candidates + `40` `no_answer` candidates** ([khuong_408_full_transcript_audit.jsonl](evidence/khuong_408_full_transcript_audit.jsonl), [khuong_q1_q6_adjudication.json](evidence/khuong_q1_q6_adjudication.json)), emitting [retrieval_v3_2_k_verified_pilot.json](../../../../artifacts/benchmarks/retrieval_v3_2_k_verified_pilot.json).

Inspecting full untruncated transcripts from `fact_videos.parquet` (`354/408 = 86.8%` had exceeded the `1,000`-character excerpt cutoff in the initial blinded pass) resolved `25` objective late-transcript cases (including true positives hidden past character `1,000` such as `t_n02_s05`, `t_n04_s02/s07/s11`, `t_n05_s10`, `t_k08_s12`, `t_n08_s04`, and late negation/method violations such as `d_k05_s12`, `t_n05_s12`, `t_k03_s13`) alongside owner Trần Đình Khương (`K`)'s explicit adjudication of `6` borderline rule clusters (`Q1`–`Q6`). `K_human_verified` is now `True` across all `408` rows while `N_rel_draft` and `N_human_verified = False` remain untouched (`raw_agreement = 87.01%`, $\kappa = 0.7723$; `label_source = "ai_assisted_pooled_draft_pending_human_K_N_signoff"` until `N` completes independent human sign-off).

On the untuned **`locked_test`** split in [retrieval_v3_2_k_verified_pilot.json](../../../../artifacts/benchmarks/retrieval_v3_2_k_verified_pilot.json) (`16` answerable + `4` `no_answer` queries):
- **Answerable Relevance (`14` positive-pool queries with `0` false abstentions; all-`16` answerable denominator including sparse/uncertain `t_k04`, `t_k07` also reported):**
  - `bm25`: **`MRR@10 = 0.7976`** (`95% CI [0.6429, 0.9286]`; all-`16` **`0.6979 >= 0.60`**), **`nDCG@10 = 0.7819`** (`[0.6864, 0.8628]`; all-`16` **`0.6842 >= 0.50`**), `Pooled Recall@10 = 0.8889`, `Precision@10 = 0.5071`.
  - `bm25_reranked`: **`MRR@10 = 0.8571`** (`95% CI [0.6429, 1.0000]`; all-`16` **`0.7500 >= 0.60`**), **`nDCG@10 = 0.7178`** (`[0.5503, 0.8546]`; all-`16` **`0.6281 >= 0.50`**), `Pooled Recall@10 = 0.7017`, `Precision@10 = 0.4643` (lifting `negation` `MRR@10` from `0.4167` to `1.0000` and `synonym` `nDCG@10` from `0.8411` to `0.9001`, while plain `bm25` retains higher `pooled_recall_at_10` on `unicode_nfd` / `filtered`; paired `delta_MRR@10 = +0.0595 [-0.0833, +0.2262]`, `delta_nDCG@10 = -0.0641 [-0.2106, +0.0552]`).
- **No-Answer & False-Abstention Guardrails:** **`4/4 = 100%` abstention (`0` fabricated support)** on both `dev` and `locked_test` (verified against all `40` full untruncated transcripts in [no_answer_raw_audit.csv](../../../../data/evaluation/v2_pilot/no_answer_raw_audit.csv)) and **`0 / 16` (`0.0%`) false abstentions** on answerable queries across both splits.
- **100-Request Warm CPU Latency (`concurrency = 1`, Linux, `peak_rss_mib = 887.11 MiB`):** `bm25` `warm p50 = 8.61 ms`, **`warm p95 = 18.89 ms <= 500 ms`**; `bm25_reranked` `warm p50 = 21.17 ms`, **`warm p95 = 30.16 ms <= 500 ms`**.

Per `AGENTS.md` Section 4, task `M2.2` remains **`IN_PROGRESS`** until Nguyễn Việt Nguyên (`N`) independently verifies/signs off `N_human_verified` on [blinded_pool.csv](../../../../data/evaluation/v2_pilot/blinded_pool.csv) and completes reciprocal peer review.

## Summary of Measured Results (`retrieval_v3_2_k_verified_pilot.json`)

| Split & Configuration | Pos-Pool (`All-16`) | False Abstain | Pooled Recall@10 | Precision@10 | MRR@10 (`All-16`) | nDCG@10 (`All-16`) | No-Answer Abstain (`Fab`) | Warm p50 / p95 (`100` req) |
| --- | --- | ---: | ---: | ---: | --- | --- | --- | --- |
| `dev` — `bm25` | `15` (`16`; `d_k07`) | `0` | `0.8057` | `0.4733` | `0.7633` (`0.7156`) | `0.7151` (`0.6704`) | `4/4 = 100%` (`0`) | — |
| `dev` — `bm25_reranked` | `15` (`16`; `d_k07`) | `0` | `0.8175` | `0.4533` | `0.8233` (`0.7719`) | `0.7369` (`0.6909`) | `4/4 = 100%` (`0`) | — |
| `locked_test` — `bm25` | `14` (`16`; `t_k04, t_k07`) | `0` | `0.8889` | `0.5071` | **`0.7976`** (`0.6979`) | **`0.7819`** (`0.6842`) | **`4/4 = 100%` (`0`)** | `8.61 ms` / **`18.89 ms`** |
| `locked_test` — `bm25_reranked` | `14` (`16`; `t_k04, t_k07`) | `0` | `0.7017` | `0.4643` | **`0.8571`** (`0.7500`) | **`0.7178`** (`0.6281`) | **`4/4 = 100%` (`0`)** | `21.17 ms` / **`30.16 ms`** |

## Work performed

- **Contract & Query Intent Guardrails ([retrieval.py](../../../../packages/data_contracts/retrieval.py), [query_intent.py](../../../../packages/retrieval/query_intent.py), [scorer.py](../../../../packages/retrieval/rerank/scorer.py), [service.py](../../../../packages/retrieval/service.py)):** Added backward-compatible `insufficient_evidence` / `abstain_reason` fields, `NFC` query normalization across `bm25`/`dense`/`hybrid_rrf`, multi-negation cursor extraction (`1–3` tokens, `(?<!ăn\s)kiêng` diet protection, `ghét`/`bỏ`/`trừ`, all-negated abstention), word-boundary reranker negation penalty with `0..2`-token dietary accommodation exemption, bidirectional F&B/regional synonym expansion, strict `city_norm`/`region` filter preservation, and core-dish-aware OOV/observed-anchor abstention (`14/14` unit tests in [test_query_intent_and_abstention.py](../../../../tests/unit/test_query_intent_and_abstention.py)).
- **Immutable `bm25-v3` & Pooled Metric Runner ([pilot_m2_2.py](../../../../pipelines/benchmark_retrieval/pilot_m2_2.py), [test_retrieval_metrics.py](../../../../tests/unit/test_retrieval_metrics.py)):** Built `artifacts/indexes/bm25-v3/` on `20261118_taxonomy_fix_v1` and verified hand-calculated `pooled_recall_at_10`, `precision_at_10`, `mrr_at_10`, `ndcg_at_10`, `answerable_abstained_count`, all-`16` answerable macro denominators, `U`-uncertainty tracking (`4.74%` dev, `8.63%` test), and single-system + paired bootstrap 95% CIs (`10/10` unit tests).
- **40-Query Disjoint Pilot, Physically Blinded Dual-Pass Pooling & Code Review (`data/evaluation/v2_pilot/`):** Authored `20` `dev` and `20` `locked_test` queries, extracted `408` rank-stripped shuffled candidate pairs, ran two independent blinded passes (`raw_agreement = 94.85%`, $\kappa = 0.9109$), completed a fresh-context Senior Code Review ([code-review.md](evidence/code-review.md)) with TDD `RED -> GREEN` fixes for all `6` Critical/Important items, and emitted [retrieval_v3_1_pilot.json](../../../../artifacts/benchmarks/retrieval_v3_1_pilot.json) while preserving [retrieval_v3_pilot.json](../../../../artifacts/benchmarks/retrieval_v3_pilot.json) untouched.
- **Bounded `N` LLM Pool Verification (`2026-11-19`, `<= 14 RPM` per contributor override):** Ran [verify_pool_with_gemini.py](evidence/verify_pool_with_gemini.py) (`gemini-3.1-flash-lite`, `34` batches x `12` rows) over all `408` rows of `blinded_pool.csv` against full transcripts (`20261118_taxonomy_fix_v1`), recording [nguyen_llm_pool_audit.csv](evidence/nguyen_llm_pool_audit.csv) and [nguyen_llm_pool_summary.json](evidence/nguyen_llm_pool_summary.json) without modifying human verification flags.
- **`K` 408-Row Full-Transcript Human Audit & Owner `Q1`–`Q6` Sign-Off (`2026-11-19`):** Joined all `408` blinded candidate rows and `40` raw `no_answer` rows against `fact_videos.parquet` (`354/408` full transcripts exceeded the prior `1,000`-char excerpt limit), audited 100% of full transcripts in [khuong_408_full_transcript_audit.jsonl](evidence/khuong_408_full_transcript_audit.jsonl), recorded owner `K`'s explicit rulings on all `6` hard-case clusters in [khuong_q1_q6_adjudication.json](evidence/khuong_q1_q6_adjudication.json), updated `K_human_verified = True` (`N_human_verified = False` preserved untouched), and emitted immutable receipt [retrieval_v3_2_k_verified_pilot.json](../../../../artifacts/benchmarks/retrieval_v3_2_k_verified_pilot.json).

## Outputs

| File | Purpose |
| --- | --- |
| [workflow.md](evidence/workflow.md), [code-review.md](evidence/code-review.md) | Superpowers TDD/blinding ledger, rulings, `N` LLM audit & `K` full-transcript sign-off provenance, and Senior Code Review |
| [khuong_408_full_transcript_audit.jsonl](evidence/khuong_408_full_transcript_audit.jsonl), [khuong_q1_q6_adjudication.json](evidence/khuong_q1_q6_adjudication.json) | Complete `408`-row full-transcript audit log and owner `K` adjudication of `Q1`–`Q6` hard-case clusters |
| [verify_pool_with_gemini.py](evidence/verify_pool_with_gemini.py), [nguyen_llm_pool_audit.csv](evidence/nguyen_llm_pool_audit.csv), [nguyen_llm_pool_summary.json](evidence/nguyen_llm_pool_summary.json) | `N`'s bounded `<= 14 RPM` `gemini-3.1-flash-lite` check over all `408` pool rows |
| [relevance_guidelines.md](evidence/relevance_guidelines.md) | Ternary (`1`/`0`/`U`) coding guidelines for blinded pooled evaluation |
| [judgments_K_dev.jsonl](evidence/judgments_K_dev.jsonl), [judgments_K_test.jsonl](evidence/judgments_K_test.jsonl), [judgments_N_dev.jsonl](evidence/judgments_N_dev.jsonl), [judgments_N_test.jsonl](evidence/judgments_N_test.jsonl) | Preserved initial truncated-pass blinded outputs consumed alongside `K` overrides in [build_m2_2_pool_and_judgments.py](evidence/build_m2_2_pool_and_judgments.py) |
| [pool_agreement_and_disagreements.json](evidence/pool_agreement_and_disagreements.json), [adjudication_overrides.json](evidence/adjudication_overrides.json) | Agreement (`87.01%` `K`-full vs `N`-draft, $\kappa = 0.7723$; initial draft `94.85%`) and itemized diffs |
| [dev_queries.jsonl](../../../../data/evaluation/v2_pilot/dev_queries.jsonl), [test_queries.jsonl](../../../../data/evaluation/v2_pilot/test_queries.jsonl) | Disjoint frozen `20`-dev and `20`-locked-test queries (including `NFD` Unicode queries) |
| [blinded_pool.csv](../../../../data/evaluation/v2_pilot/blinded_pool.csv), [qrels_pooled_draft.jsonl](../../../../data/evaluation/v2_pilot/qrels_pooled_draft.jsonl), [no_answer_raw_audit.csv](../../../../data/evaluation/v2_pilot/no_answer_raw_audit.csv) | `408` blinded pooled rows (`K_human_verified=True`, `N_human_verified=False`) and `40`-row full-transcript `no_answer` audit |
| [retrieval_v3_pilot.json](../../../../artifacts/benchmarks/retrieval_v3_pilot.json), [retrieval_v3_1_pilot.json](../../../../artifacts/benchmarks/retrieval_v3_1_pilot.json), [retrieval_v3_2_k_verified_pilot.json](../../../../artifacts/benchmarks/retrieval_v3_2_k_verified_pilot.json) | Initial, post-code-review, and post-`K`-full-transcript-signoff immutable benchmark receipts with SHA256 provenance |
| [pytest-k-signoff-linux.log](evidence/pytest-k-signoff-linux.log), [pilot-benchmark-v3-2-k-verified.log](evidence/pilot-benchmark-v3-2-k-verified.log) | Linux `139`-test suite (`35.60s`) and `v3_2` benchmark execution logs |

## Verification

| Check | Result | Scope / evidence |
| --- | --- | --- |
| `python3 -m pytest -v` | PASS (`139 passed` at `M2.2` sign-off; full rebased suite verified below) | All contract, smoke, eval (`v1`), retrieval, dense parity, guardrail, and continuity tests; [pytest-k-signoff-linux.log](evidence/pytest-k-signoff-linux.log) |
| `mypy` (`Windows` & `--platform linux` `83` files; `anaconda3` Linux check) | PASS on `M2.2` code (`83/83` on pinned `.venv`; `1` pre-existing numpy `Any` stub issue in untouched `dense/encoder.py` under `anaconda3`) | [mypy-windows.log](evidence/mypy-windows.log), [mypy-linux-target.log](evidence/mypy-linux-target.log), [mypy-k-signoff-linux.log](evidence/mypy-k-signoff-linux.log) |
| `python3 scripts/check_secrets.py` | PASS (`0` leaks) | Workspace secret scan |
| `python3 -m pipelines.benchmark_retrieval.pilot_m2_2` (`retrieval_v3_2_k_verified_pilot`) | PASS (`MRR@10 = 0.8571`, `nDCG@10 = 0.7178`, `p95 = 30.16 ms`) | Untuned locked test evaluation & `100`-warm-request CPU benchmark; [retrieval_v3_2_k_verified_pilot.json](../../../../artifacts/benchmarks/retrieval_v3_2_k_verified_pilot.json) |

## Open issues

| Issue | Impact | Follow-up / responsible task |
| --- | --- | --- |
| `N`'s independent human sign-off (`N_human_verified`) on `blinded_pool.csv` (`53` `K`-full vs `N`-truncated-draft diffs) and `N` peer review pending | `K`'s verified full-transcript pass (`K_human_verified=True`) and `N`'s LLM check do not substitute for two-human completion | `N` inspects/confirms `N_human_verified` on `blinded_pool.csv` (`408` rows), reconciles diffs with `K`, and reviews `M2.2` before closing `M2.2` and unblocking `M2.G` / `M6.1` |
| `3` queries (`d_k07`, `t_k04`, `t_k07`) have `0` verified `1`s in top-10 pool (`t_k04` has `9` `U`s under `Q1`; `t_k07` lacks Hanoi egg-coffee transcripts) | Both positive-pool (`14/16`: `MRR@10 = 0.8571`, `nDCG@10 = 0.7178`) and all-answerable (`16/16`: `MRR@10 = 0.7500 >= 0.60`, `nDCG@10 = 0.6281 >= 0.50`) denominators are recorded directly in `retrieval_v3_2_k_verified_pilot.json` | Retain dual-denominator reporting in `M2.G` and `M6.1` |

## Acceptance and handoff

| Task criterion | Result | Evidence |
| --- | --- | --- |
| Preserve `retrieval_v1.json`, `retrieval_v2.json`, `bm25-v2`, `16` weak-label regressions, and prior `v3`/`v3_1` receipts | Met (`0` bytes mutated) | [test_retrieval_benchmark.py](../../../../tests/eval/test_retrieval_benchmark.py), [pytest-k-signoff-linux.log](evidence/pytest-k-signoff-linux.log) |
| Hand-calculated metric tests, disjoint frozen `20 dev` / `20 test`, and SHA256 receipts | Met | [test_retrieval_metrics.py](../../../../tests/unit/test_retrieval_metrics.py), [retrieval_v3_2_k_verified_pilot.json](../../../../artifacts/benchmarks/retrieval_v3_2_k_verified_pilot.json) |
| Provisional test `MRR@10 >= 0.60`, `nDCG@10 >= 0.50`, `0` no-answer fabrication, warm `p95 <= 500 ms` | Met (`0.8571` / `0.7500`, `0.7178` / `0.6281`, `0` fabricated, `30.16 ms`) | [retrieval_v3_2_k_verified_pilot.json](../../../../artifacts/benchmarks/retrieval_v3_2_k_verified_pilot.json) |
| `K` & `N` pool sign-off and `N` peer review | Partial (`K_human_verified = True` complete on all `408` rows; awaiting `N_human_verified` & `N` peer review) | [blinded_pool.csv](../../../../data/evaluation/v2_pilot/blinded_pool.csv), [khuong_q1_q6_adjudication.json](evidence/khuong_q1_q6_adjudication.json) |

Final task status: **`IN_PROGRESS`** (`K`'s engineering, `bm25-v3`, `408`-row full-transcript audit, and `Q1`–`Q6` sign-off complete; handed over to `N` for `N_human_verified` confirmation and reciprocal peer review).
