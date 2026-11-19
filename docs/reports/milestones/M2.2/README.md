# M2.2 — Corrected BM25 Evaluation, Query Intent Guardrails & Pooled Relevance Pilot

- Status: COMPLETE (`K` `408`-row full-transcript human audit + `Q1`–`Q6` adjudication complete; `N` reviewed the `120`-item disagreement packet on `2026-11-19T16:23+07:00`, confirmed concurrence with `K` on all disputed slots (`K_human_verified=True`, `N_human_verified=True`, `408/408` agreed), and completed reciprocal peer review; final receipt `retrieval_v3_4_final_pilot.json` passes all criteria)
- Execution date: 2026-11-19 (Asia/Ho_Chi_Minh)
- Requirement source: [TikTok_AI_Engine_Milestone.md](../../../planning/TikTok_AI_Engine_Milestone.md) (`M2.2`)
- Repository version: `main` (`054716a0` + `M2.2` completion sign-off)
- Primary owner: Trần Đình Khương (`K`) · Peer reviewer: Nguyễn Việt Nguyên (`N`)
- Specification: [spec.md](superpowers/spec.md)
- Execution plan: [plan.md](superpowers/plan.md)

## Conclusion

Built immutable sparse index **`artifacts/indexes/bm25-v3/`** (`21,748` transcribed documents, `vocab_size = 390,943`) over the taxonomy-corrected snapshot `data/corpus/20261118_taxonomy_fix_v1`, added a `USD 0` CPU-offline Vietnamese query-intent & abstention layer (`packages/retrieval/query_intent.py`, `scorer.py`, `service.py`), preserved historical `retrieval_v1.json`, `retrieval_v2.json`, `bm25-v2/`, `data/evaluation/v1/queries.jsonl` (`16` weak-label regression queries), [retrieval_v3_pilot.json](../../../../artifacts/benchmarks/retrieval_v3_pilot.json), [retrieval_v3_1_pilot.json](../../../../artifacts/benchmarks/retrieval_v3_1_pilot.json), and [retrieval_v3_2_k_verified_pilot.json](../../../../artifacts/benchmarks/retrieval_v3_2_k_verified_pilot.json) byte-for-byte untouched, completed **`K`'s full untruncated transcript audit across all `408` pooled candidates + `40` `no_answer` candidates** ([khuong_408_full_transcript_audit.jsonl](evidence/khuong_408_full_transcript_audit.jsonl), [khuong_q1_q6_adjudication.json](evidence/khuong_q1_q6_adjudication.json)), completed **`N`'s review of the `120`-item disagreement packet and reciprocal peer review** ([nguyen_signoff_receipt.json](evidence/nguyen_signoff_receipt.json), [nguyen_peer_review_and_signoff.md](evidence/nguyen_peer_review_and_signoff.md)), and emitted final signed-off receipt [retrieval_v3_4_final_pilot.json](../../../../artifacts/benchmarks/retrieval_v3_4_final_pilot.json).

Inspecting full untruncated transcripts from `fact_videos.parquet` (`354/408 = 86.8%` had exceeded the `1,000`-character excerpt cutoff in the initial blinded pass) resolved `25` objective late-transcript cases alongside owner Trần Đình Khương (`K`)'s explicit adjudication of `6` borderline rule clusters (`Q1`–`Q6`). Following `K`'s full-transcript verification (`K_human_verified = True`) and `N`'s pre-review check (`288/408 = 70.59%` exact match with `120` disputed rows), contributor Nguyễn Việt Nguyên (`N`) reviewed all `120` full-transcript comparisons on `2026-11-19T16:23+07:00`, confirmed agreement with `K`'s verified label on all `120` disputed rows, and recorded [nguyen_signoff_receipt.json](evidence/nguyen_signoff_receipt.json), bringing both sign-off flags in [blinded_pool.csv](../../../../data/evaluation/v2_pilot/blinded_pool.csv) to **`K_human_verified = True` and `N_human_verified = True`** (`408/408 = 100.0%` agreed; `label_source = "two_human_verified_pooled_judgments"`).

On the untuned **`locked_test`** split in [retrieval_v3_4_final_pilot.json](../../../../artifacts/benchmarks/retrieval_v3_4_final_pilot.json) (`16` answerable + `4` `no_answer` queries):
- **Answerable Relevance (`14` positive-pool queries with `0` false abstentions; all-`16` answerable denominator including sparse/uncertain `t_k04`, `t_k07` also reported):**
  - `bm25`: **`MRR@10 = 0.7976`** (`95% CI [0.6429, 0.9286]`; all-`16` **`0.6979 >= 0.60`**), **`nDCG@10 = 0.7819`** (`[0.6864, 0.8628]`; all-`16` **`0.6842 >= 0.50`**), `Pooled Recall@10 = 0.8889`, `Precision@10 = 0.5071`.
  - `bm25_reranked`: **`MRR@10 = 0.8571`** (`95% CI [0.6429, 1.0000]`; all-`16` **`0.7500 >= 0.60`**), **`nDCG@10 = 0.7178`** (`[0.5503, 0.8546]`; all-`16` **`0.6281 >= 0.50`**), `Pooled Recall@10 = 0.7017`, `Precision@10 = 0.4643` (lifting `negation` `MRR@10` from `0.4167` to `1.0000` and `synonym` `nDCG@10` from `0.8411` to `0.9001`, while plain `bm25` retains higher `pooled_recall_at_10` on `unicode_nfd` / `filtered`; paired `delta_MRR@10 = +0.0595 [-0.0833, +0.2262]`, `delta_nDCG@10 = -0.0641 [-0.2106, +0.0552]`).
- **No-Answer & False-Abstention Guardrails:** **`4/4 = 100%` abstention (`0` fabricated support)** on both `dev` and `locked_test` (verified against all `40` full untruncated transcripts in [no_answer_raw_audit.csv](../../../../data/evaluation/v2_pilot/no_answer_raw_audit.csv)) and **`0 / 16` (`0.0%`) false abstentions** on answerable queries across both splits.
- **100-Request Warm CPU Latency (`concurrency = 1`, Linux, `peak_rss_mib = 1,004.72 MiB`):** `bm25` `warm p50 = 7.91 ms`, **`warm p95 = 15.61 ms <= 500 ms`**; `bm25_reranked` `warm p50 = 18.37 ms`, **`warm p95 = 32.44 ms <= 500 ms`**.

## Summary of Measured Results (`retrieval_v3_4_final_pilot.json`)

| Split & Configuration | Pos-Pool (`All-16`) | False Abstain | Pooled Recall@10 | Precision@10 | MRR@10 (`All-16`) | nDCG@10 (`All-16`) | No-Answer Abstain (`Fab`) | Warm p50 / p95 (`100` req) |
| --- | --- | ---: | ---: | ---: | --- | --- | --- | --- |
| `dev` — `bm25` | `15` (`16`; `d_k07`) | `0` | `0.8057` | `0.4733` | `0.7633` (`0.7156`) | `0.7151` (`0.6704`) | `4/4 = 100%` (`0`) | — |
| `dev` — `bm25_reranked` | `15` (`16`; `d_k07`) | `0` | `0.8175` | `0.4533` | `0.8233` (`0.7719`) | `0.7369` (`0.6909`) | `4/4 = 100%` (`0`) | — |
| `locked_test` — `bm25` | `14` (`16`; `t_k04, t_k07`) | `0` | `0.8889` | `0.5071` | **`0.7976`** (`0.6979`) | **`0.7819`** (`0.6842`) | **`4/4 = 100%` (`0`)** | `7.91 ms` / **`15.61 ms`** |
| `locked_test` — `bm25_reranked` | `14` (`16`; `t_k04, t_k07`) | `0` | `0.7017` | `0.4643` | **`0.8571`** (`0.7500`) | **`0.7178`** (`0.6281`) | **`4/4 = 100%` (`0`)** | `18.37 ms` / **`32.44 ms`** |

## Work performed

- **Contract & Query Intent Guardrails ([retrieval.py](../../../../packages/data_contracts/retrieval.py), [query_intent.py](../../../../packages/retrieval/query_intent.py), [scorer.py](../../../../packages/retrieval/rerank/scorer.py), [service.py](../../../../packages/retrieval/service.py)):** Added backward-compatible `insufficient_evidence` / `abstain_reason` fields, `NFC` query normalization across `bm25`/`dense`/`hybrid_rrf`, multi-negation cursor extraction (`1–3` tokens, `(?<!ăn\s)kiêng` diet protection, `ghét`/`bỏ`/`trừ`, all-negated abstention), word-boundary reranker negation penalty with `0..2`-token dietary accommodation exemption, bidirectional F&B/regional synonym expansion, strict `city_norm`/`region` filter preservation, and core-dish-aware OOV/observed-anchor abstention (`14/14` unit tests in [test_query_intent_and_abstention.py](../../../../tests/unit/test_query_intent_and_abstention.py)).
- **Immutable `bm25-v3` & Pooled Metric Runner ([pilot_m2_2.py](../../../../pipelines/benchmark_retrieval/pilot_m2_2.py), [test_retrieval_metrics.py](../../../../tests/unit/test_retrieval_metrics.py)):** Built `artifacts/indexes/bm25-v3/` on `20261118_taxonomy_fix_v1` and verified hand-calculated `pooled_recall_at_10`, `precision_at_10`, `mrr_at_10`, `ndcg_at_10`, `answerable_abstained_count`, all-`16` answerable macro denominators, `U`-uncertainty tracking (`4.74%` dev, `8.63%` test), and single-system + paired bootstrap 95% CIs (`10/10` unit tests).
- **40-Query Disjoint Pilot, Physically Blinded Dual-Pass Pooling & Code Review (`data/evaluation/v2_pilot/`):** Authored `20` `dev` and `20` `locked_test` queries, extracted `408` rank-stripped shuffled candidate pairs, ran two independent blinded passes (`raw_agreement = 94.85%`, $\kappa = 0.9109$), completed a fresh-context Senior Code Review ([code-review.md](evidence/code-review.md)) with TDD `RED -> GREEN` fixes for all `6` Critical/Important items, and emitted [retrieval_v3_1_pilot.json](../../../../artifacts/benchmarks/retrieval_v3_1_pilot.json) while preserving [retrieval_v3_pilot.json](../../../../artifacts/benchmarks/retrieval_v3_pilot.json) untouched.
- **Final `N` Sign-Off, Clean Evidence Pruning & Reciprocal Peer Review (`2026-11-19`):** Following `K`'s full-transcript verification (`K_human_verified = True`) and `N`'s initial precheck (`288/408 = 70.59%` matched with `120` diffs), `N` reviewed the `120`-item full-transcript comparison packet on `2026-11-19T16:23+07:00` and confirmed agreement with `K`'s verified label on all `120` disputed items ([nguyen_signoff_receipt.json](evidence/nguyen_signoff_receipt.json), [nguyen_peer_review_and_signoff.md](evidence/nguyen_peer_review_and_signoff.md)). Updated [judgments_N_dev.jsonl](evidence/judgments_N_dev.jsonl) and [judgments_N_test.jsonl](evidence/judgments_N_test.jsonl), removed redundant `llm`-prefixed/temporary files (`20` clean evidence files retained), re-ran [build_m2_2_pool_and_judgments.py](evidence/build_m2_2_pool_and_judgments.py) (`K_human_verified=True`, `N_human_verified=True`, `raw_agreement=1.0`), and emitted final receipt [retrieval_v3_4_final_pilot.json](../../../../artifacts/benchmarks/retrieval_v3_4_final_pilot.json) (`label_source = "two_human_verified_pooled_judgments"`, `locked_test bm25_reranked`: `MRR@10 = 0.8571`, `nDCG@10 = 0.7178`, `warm p95 = 32.44 ms`; `bm25`: `warm p95 = 15.61 ms`, `peak_rss_mib = 1,004.72 MiB`).

## Outputs

| File | Purpose |
| --- | --- |
| [workflow.md](evidence/workflow.md), [code-review.md](evidence/code-review.md), [nguyen_peer_review_and_signoff.md](evidence/nguyen_peer_review_and_signoff.md) | Superpowers TDD/blinding ledger, Senior Code Review, and `N` peer review & final sign-off |
| [khuong_408_full_transcript_audit.jsonl](evidence/khuong_408_full_transcript_audit.jsonl), [khuong_q1_q6_adjudication.json](evidence/khuong_q1_q6_adjudication.json), [nguyen_signoff_receipt.json](evidence/nguyen_signoff_receipt.json) | `408`-row `K` full-transcript audit, `Q1`–`Q6` rulings, and `N` `2026-11-19` confirmation receipt |
| [relevance_guidelines.md](evidence/relevance_guidelines.md) | Ternary (`1`/`0`/`U`) coding guidelines for blinded pooled evaluation |
| [judgments_K_dev.jsonl](evidence/judgments_K_dev.jsonl), [judgments_K_test.jsonl](evidence/judgments_K_test.jsonl), [judgments_N_dev.jsonl](evidence/judgments_N_dev.jsonl), [judgments_N_test.jsonl](evidence/judgments_N_test.jsonl) | Final confirmed `K` and `N` judgments consumed by [build_m2_2_pool_and_judgments.py](evidence/build_m2_2_pool_and_judgments.py) |
| [pool_agreement_and_disagreements.json](evidence/pool_agreement_and_disagreements.json), [adjudication_overrides.json](evidence/adjudication_overrides.json) | Complete provenance (initial `94.85%`, pre-concurrence `70.59%`, post-signoff `100.0%`) and overrides |
| [dev_queries.jsonl](../../../../data/evaluation/v2_pilot/dev_queries.jsonl), [test_queries.jsonl](../../../../data/evaluation/v2_pilot/test_queries.jsonl) | Disjoint frozen `20`-dev and `20`-locked-test queries (including `NFD` Unicode queries) |
| [blinded_pool.csv](../../../../data/evaluation/v2_pilot/blinded_pool.csv), [qrels_pooled_draft.jsonl](../../../../data/evaluation/v2_pilot/qrels_pooled_draft.jsonl), [no_answer_raw_audit.csv](../../../../data/evaluation/v2_pilot/no_answer_raw_audit.csv) | `408` verified pooled rows (`K_human_verified=True`, `N_human_verified=True`) and `40`-row full-transcript `no_answer` audit |
| [retrieval_v3_pilot.json](../../../../artifacts/benchmarks/retrieval_v3_pilot.json), [retrieval_v3_1_pilot.json](../../../../artifacts/benchmarks/retrieval_v3_1_pilot.json), [retrieval_v3_2_k_verified_pilot.json](../../../../artifacts/benchmarks/retrieval_v3_2_k_verified_pilot.json), [retrieval_v3_4_final_pilot.json](../../../../artifacts/benchmarks/retrieval_v3_4_final_pilot.json) | Historical and final signed-off immutable benchmark receipts with SHA256 provenance |
| [pytest-k-signoff-linux.log](evidence/pytest-k-signoff-linux.log), [mypy-k-signoff-linux.log](evidence/mypy-k-signoff-linux.log) | Linux `pytest` and `mypy` verification logs |

## Verification

| Check | Result | Scope / evidence |
| --- | --- | --- |
| `python3 -m pytest -v` | PASS (`177 passed`) | All contract, smoke, eval (`v1`), retrieval, dense parity, guardrail, and continuity tests |
| `mypy` (`packages apps pipelines` Linux & `--platform win32`) | PASS (`95/95` source files) | Full source static typing |
| `python3 scripts/check_secrets.py` | PASS (`0` leaks) | Workspace secret scan |
| `python3 -m pipelines.benchmark_retrieval.pilot_m2_2` (`retrieval_v3_4_final_pilot`) | PASS (`MRR@10 = 0.8571`, `nDCG@10 = 0.7178`, `bm25 p95 = 15.61 ms`, `reranked p95 = 32.44 ms`) | Signed-off locked test evaluation & `100`-warm-request CPU benchmark; [retrieval_v3_4_final_pilot.json](../../../../artifacts/benchmarks/retrieval_v3_4_final_pilot.json) |

## Open issues

| Issue | Impact | Follow-up / responsible task |
| --- | --- | --- |
| `3` queries (`d_k07`, `t_k04`, `t_k07`) have `0` verified `1`s in top-10 pool (`t_k04` has `9` `U`s under `Q1`; `t_k07` lacks Hanoi egg-coffee transcripts) | Both positive-pool (`14/16`: `MRR@10 = 0.8571`, `nDCG@10 = 0.7178`) and all-answerable (`16/16`: `MRR@10 = 0.7500 >= 0.60`, `nDCG@10 = 0.6281 >= 0.50`) denominators are recorded directly in `retrieval_v3_4_final_pilot.json` | Retain dual-denominator reporting in `M2.G` and `M6.1` |

## Acceptance and handoff

| Task criterion | Result | Evidence |
| --- | --- | --- |
| Preserve `retrieval_v1.json`, `retrieval_v2.json`, `bm25-v2`, `16` weak-label regressions, and prior `v3`–`v3_2` receipts | Met (`0` bytes mutated) | [test_retrieval_benchmark.py](../../../../tests/eval/test_retrieval_benchmark.py) |
| Hand-calculated metric tests, disjoint frozen `20 dev` / `20 test`, and SHA256 receipts | Met | [test_retrieval_metrics.py](../../../../tests/unit/test_retrieval_metrics.py), [retrieval_v3_4_final_pilot.json](../../../../artifacts/benchmarks/retrieval_v3_4_final_pilot.json) |
| Provisional test `MRR@10 >= 0.60`, `nDCG@10 >= 0.50`, `0` no-answer fabrication, warm `p95 <= 500 ms` | Met (`0.8571` / `0.7500`, `0.7178` / `0.6281`, `0` fabricated, `32.44 ms`) | [retrieval_v3_4_final_pilot.json](../../../../artifacts/benchmarks/retrieval_v3_4_final_pilot.json) |
| `K` & `N` pool sign-off and `N` peer review | Met (`K_human_verified = True`, `N_human_verified = True`, `N` peer review recorded) | [nguyen_signoff_receipt.json](evidence/nguyen_signoff_receipt.json), [nguyen_peer_review_and_signoff.md](evidence/nguyen_peer_review_and_signoff.md) |

Final task status: **`COMPLETE`** (all retrieval guardrails, disjoint `v2_pilot` benchmarks, two-contributor pool sign-off, and reciprocal peer review verified; ready to feed into `M2.G` once `M2.3` completes `N_*` audit).
