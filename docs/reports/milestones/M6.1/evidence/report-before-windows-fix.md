# M6.1 — CPU Dense & Hybrid Retrieval Pilot (Text-Only Spike)

- Status: IN_PROGRESS (`N`'s text-only CPU dense index, Qdrant upsert adapter, `HybridRetrievalService` parity integration, 100-request CPU latency/RAM benchmark, and paired bootstrap comparison complete; awaiting `M2.2` frozen human-judged qrels, conditional multimodal evaluation after `M4.G`/`M5.G`, and `K` peer review)
- Execution date: 2026-11-18 (Asia/Ho_Chi_Minh)
- Requirement source: [TikTok_AI_Engine_Milestone.md](../../../planning/TikTok_AI_Engine_Milestone.md) (`M6.1`)
- Repository version: `feat/m6.1-dense-hybrid-spike` (branched from `main` @ `c6c36131`)
- Primary owner: Nguyễn Việt Nguyên (`N`) · Peer reviewer: Trần Đình Khương (`K`)
- Specification: [spec.md](superpowers/spec.md)
- Execution plan: [plan.md](superpowers/plan.md)

## Conclusion

Implemented the pluggable CPU dense embedding stack ([encoder.py](../../../../packages/retrieval/dense/encoder.py), [local_index.py](../../../../packages/retrieval/dense/local_index.py), [qdrant_adapter.py](../../../../packages/retrieval/dense/qdrant_adapter.py), [service.py](../../../../packages/retrieval/service.py)) and built a populated versioned index (`artifacts/indexes/dense-svd-v1/`, `5,000` eligible documents, `128`-dim `tfidf_svd_vn_128d_v1`, `14,898,224` bytes, build time `19.418 s`, build peak RSS `1,547.24 MiB`) against `data/corpus/20261117_recovered_v1`.

Across `100` warm CPU requests (`concurrency = 1`, `4` logical CPUs, `15.33 GB` RAM) on the identical `5,000`-record slice (`restrict_to_df=True`), all backends stay well under the `1,000 ms` latency and `8 GiB` RAM ceilings: `bm25` `p95 = 2.90 ms`, `dense` `p95 = 6.42 ms`, `hybrid_rrf` `p95 = 8.41 ms`, `hybrid_rrf_reranked` `p95 = 28.54 ms`, evaluation peak RSS `798.89 MiB`. On the `15` available weak-label `v1` queries overlapping this `5,000`-record slice, `bm25` + reranking achieves higher `MRR@10` (`0.8356` vs `0.7911`) and `nDCG@10` (`0.7150` vs `0.6963`) while `hybrid_rrf_reranked` edges `Recall@10` (`0.3819` vs `0.3803`). Per `M6.1` decision rules, **`BM25` remains the recommended production default** until frozen human-judged synonym/semantic queries from `M2.2` demonstrate a justified hybrid gain. All `81/81` pytest tests, strict `mypy` (`80` source files), `ruff`, and `check_secrets.py` (`0` leaks) pass.

## Measured parity & latency results (`5,000`-record slice)

| Configuration | Recall@10 | Precision@10 | MRR@10 | nDCG@10 | Warm p50 (100 req) | Warm p95 (100 req) |
| --- | ---: | ---: | ---: | ---: | ---: | ---: |
| `bm25` | `0.3470` | `0.5267` | `0.7874` | `0.6723` | `2.58 ms` | `2.90 ms` |
| `bm25_reranked` | `0.3803` | `0.5667` | `0.8356` | `0.7150` | — | — |
| `dense` (`tfidf_svd_vn_128d_v1`) | `0.3517` | `0.4800` | `0.6541` | `0.5979` | `5.97 ms` | `6.42 ms` |
| `hybrid_rrf` | `0.3735` | `0.5333` | `0.7500` | `0.6370` | `7.73 ms` | `8.41 ms` |
| `hybrid_rrf_reranked` | `0.3819` | `0.5667` | `0.7911` | `0.6963` | `24.27 ms` | `28.54 ms` |

- **Paired bootstrap 95% CIs (`1,000` resamples, `n = 15` queries):**
  - `dense - bm25`: `delta_MRR@10 = -0.1333` (`[-0.2504, -0.0222]`), `delta_nDCG@10 = -0.0744` (`[-0.1729, +0.0155]`).
  - `hybrid_rrf - bm25`: `delta_MRR@10 = -0.0374` (`[-0.1741, +0.0926]`), `delta_nDCG@10 = -0.0353` (`[-0.1124, +0.0342]`).
  - `hybrid_rrf_reranked - bm25_reranked`: `delta_MRR@10 = -0.0444` (`[-0.1511, +0.0444]`), `delta_nDCG@10 = -0.0187` (`[-0.0790, +0.0346]`).

## Work performed

- **Pluggable CPU dense encoders ([encoder.py](../../../../packages/retrieval/dense/encoder.py)):** Added `DenseTextEncoder` protocol, offline zero-dependency `TruncatedSvdDenseEncoder`, optional `FastEmbedEncoder` / `SentenceTransformerEncoder` (`intfloat/multilingual-e5-small` E5 prefixes), and `load_saved_encoder`.
- **Populated local dense index & Qdrant upsert ([local_index.py](../../../../packages/retrieval/dense/local_index.py), [qdrant_adapter.py](../../../../packages/retrieval/dense/qdrant_adapter.py)):** Added pickle-free `LocalDenseIndex` with SHA256 fail-closed loading and exact `allowed_video_ids` cosine filtering, plus `ensure_collection` and `upsert_vectors` on `QdrantDenseAdapter`.
- **Hybrid service & env wiring ([service.py](../../../../packages/retrieval/service.py), [settings](../../../../packages/common/settings/__init__.py), [dependencies.py](../../../../apps/api/app/dependencies.py)):** Wired optional `dense_dir` (`TIKTOK_RAG_DENSE_INDEX_DIR`, default `None`) and `restrict_to_df` parity pool enforcement.
- **CLIs & pilot ([dense.py](../../../../pipelines/build_dense_sparse_index/dense.py), [dense_hybrid_pilot.py](../../../../pipelines/benchmark_retrieval/dense_hybrid_pilot.py)):** Enforced `max_records <= 5000`, generated `artifacts/indexes/dense-svd-v1/`, and recorded paired bootstrap + 100-request latency measurements in [m6_1_dense_hybrid_spike.json](../../../../artifacts/benchmarks/m6_1_dense_hybrid_spike.json).
- **TDD suite ([test_dense_hybrid_retrieval.py](../../../../tests/unit/test_dense_hybrid_retrieval.py)):** Added `6` unit tests covering SVD roundtrip, filtered search & SHA256 corruption, mocked Qdrant REST creation/upsert, local `bm25`/`dense`/`hybrid_rrf` parity, `5,000` cap, bootstrap CI, and env wiring.

## Outputs

| File | Purpose |
| --- | --- |
| [workflow.md](evidence/workflow.md) | Skill/process provenance, decisions, and command receipts |
| [m6_1_dense_hybrid_spike.json](../../../../artifacts/benchmarks/m6_1_dense_hybrid_spike.json) | Complete paired parity, bootstrap CI, RAM, build time, and 100-req CPU latency receipt |
| [dense-receipt.json](../../../../artifacts/indexes/dense-svd-v1/dense-receipt.json) | SHA256 manifest for populated `5,000`-record dense index (`14,898,224` bytes) |
| [red-m6_1-tests.log](evidence/red-m6_1-tests.log) | TDD RED import failure prior to implementation |
| [green-m6_1-tests.log](evidence/green-m6_1-tests.log) | Post-fix `test_dense_hybrid_retrieval.py` output (`6 passed in 1.07s`) |
| [ruff.log](evidence/ruff.log) | Scoped Ruff output (`All checks passed!`) |
| [mypy.log](evidence/mypy.log) | Strict project-wide mypy check (`80 source files`) |
| [pytest-full.log](evidence/pytest-full.log) | Full pytest suite (`81 passed in 17.03s`) |
| [check-secrets.log](evidence/check-secrets.log) | Workspace secret scan (`0` leaks) |

## Verification

| Check | Result | Scope / evidence |
| --- | --- | --- |
| `.venv/bin/python -m pipelines.build_dense_sparse_index.dense --corpus data/corpus/20261117_recovered_v1 --output artifacts/indexes/dense-svd-v1 --max-records 5000 --dimension 128` | PASS (`19.418 s`, `1,547.24 MiB` peak) | Built populated `5,000`-doc dense index (`14,898,224` B); [dense-receipt.json](../../../../artifacts/indexes/dense-svd-v1/dense-receipt.json) |
| `.venv/bin/python -m pipelines.benchmark_retrieval.dense_hybrid_pilot` | PASS (`p95 <= 28.54 ms <= 1000 ms`, `798.89 MiB <= 8 GiB`) | Exact `5,000`-doc parity (`bm25`, `dense`, `hybrid_rrf`), paired bootstrap CIs, 100 warm reqs; [m6_1_dense_hybrid_spike.json](../../../../artifacts/benchmarks/m6_1_dense_hybrid_spike.json) |
| `.venv/bin/python -m pytest tests/unit/test_dense_hybrid_retrieval.py -v` | PASS (`6 passed`) | Encoder, `LocalDenseIndex`, Qdrant upsert, `bm25`/`dense`/`hybrid_rrf` parity, cap, CI; [green-m6_1-tests.log](evidence/green-m6_1-tests.log) |
| `.venv/bin/python -m ruff check ...` | PASS | Lint & style checks on touched modules; [ruff.log](evidence/ruff.log) |
| `.venv/bin/python -m mypy packages apps pipelines` | PASS (`80 source files`) | Full strict static typing; [mypy.log](evidence/mypy.log) |
| `.venv/bin/python -m pytest -v` | PASS (`81 passed in 17.03s`) | Full repository suite; [pytest-full.log](evidence/pytest-full.log) |
| `.venv/bin/python scripts/check_secrets.py` | PASS (`0` leaks) | Workspace secret scan; [check-secrets.log](evidence/check-secrets.log) |

## Open issues

| Issue | Impact | Follow-up / responsible task |
| --- | --- | --- |
| `M2.2` frozen human-judged queries not yet published | Current `15` queries are keyword/metadata weak labels (`queries.jsonl`), favoring lexical `BM25` over semantic similarity | Re-run `dense_hybrid_pilot` once `M2.2` freezes the `40`-query human-judged set (`20` dev / `20` test) |
| Optional neural E5 (`fastembed`) not installed in base `.venv` | Baseline measured `tfidf_svd_vn_128d_v1`; pretrained multilingual E5 requires optional `fastembed` install | Optionally install `fastembed` and benchmark `--backend fastembed` side-by-side |
| Multimodal segments & `K` peer review pending | Full `M6.1` closure also waits for `M4.G`/`M5.G` (if multimodal included) and `K` parity/cost review | Hand off text-only spike on `feat/m6.1-dense-hybrid-spike` to `K` |

## Acceptance and handoff

| Task criterion | Result | Evidence |
| --- | --- | --- |
| One CPU-feasible model & populated versioned index over `<= 5,000` records | Met (`tfidf_svd_vn_128d_v1`, `5,000` docs, `14.21 MiB`) | [dense-receipt.json](../../../../artifacts/indexes/dense-svd-v1/dense-receipt.json) |
| Identical corpus/filter/query parity across `bm25`, `dense`, and `hybrid_rrf` | Met (`restrict_to_df=True`) | [service.py](../../../../packages/retrieval/service.py), [dense_hybrid_pilot.py](../../../../pipelines/benchmark_retrieval/dense_hybrid_pilot.py) |
| Paired `nDCG@10`/`MRR@10` deltas + bootstrap CI, build bytes/time, RAM `<= 8 GiB`, warm `p95 <= 1,000 ms` | Met (under `v1` weak labels; `BM25` retained as simplest default) | [m6_1_dense_hybrid_spike.json](../../../../artifacts/benchmarks/m6_1_dense_hybrid_spike.json) |
| Re-run on frozen human-judged `M2.2` test & `K` peer review | Pending (`M2.2` not yet closed) | Ready for frozen `M2.2` test plug-in & `K` review |

Final task status: **IN_PROGRESS** (`M6.1` text-only CPU spike built, benchmarked, and verified on `feat/m6.1-dense-hybrid-spike`; awaiting `M2.2` human-judged test set, optional multimodal phase, and `K` peer review).
