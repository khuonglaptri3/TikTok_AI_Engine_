# M6.1 — CPU Dense & Hybrid Retrieval Pilot (Text-Only Spike)

- Status: IN_PROGRESS (`N`'s text-only CPU dense/hybrid spike re-measured on the frozen `408/408` human-verified `M2.2` qrels and confirmed on `2026-11-20`; awaiting `K` peer review of parity/cost evidence and conditional multimodal evaluation after `M4.G`/`M5.G`)
- Execution date: 2026-11-18 to 2026-11-20 (Asia/Ho_Chi_Minh)
- Requirement source: [TikTok_AI_Engine_Milestone.md](../../../planning/TikTok_AI_Engine_Milestone.md) (`M6.1`)
- Current branch: `main` (original spikes on `feat/m6.1-dense-hybrid-spike` @ `c6c36131`, PR3 @ `eb43b0df3d46007b7550de8f4314dc2dbca9c51f`, `feat/m6.1-v2-pilot-eval` @ `dcdd6233`)
- Primary owner: Nguyễn Việt Nguyên (`N`) · Peer reviewer: Trần Đình Khương (`K`)
- Specification: [spec.md](superpowers/spec.md)
- Execution plan: [plan.md](superpowers/plan.md)

## Final Human-Verified `v2_pilot` Parity Outcome (2026-11-20)

Re-ran `dense_hybrid_v2_pilot` over the frozen **`408/408` two-human-verified `M2.2` qrels** (`K_human_verified_all=True`, `N_human_verified_all=True`, `label_source="two_human_verified_pooled_judgments"`) into immutable receipt [m6_1_v2_pilot_human_verified.json](../../../../artifacts/benchmarks/m6_1_v2_pilot_human_verified.json) (`process_peak_rss_mib = 1,318.64 MiB <= 8,192 MiB`), preserving [m6_1_dense_hybrid_spike.json](../../../../artifacts/benchmarks/m6_1_dense_hybrid_spike.json) and [m6_1_v2_pilot.json](../../../../artifacts/benchmarks/m6_1_v2_pilot.json) byte-untouched. Contributor `N` confirmed the text-only parity findings on `2026-11-20T09:23+07:00` ([nguyen_text_spike_signoff_receipt.json](evidence/nguyen_text_spike_signoff_receipt.json)): **`bm25-v3` (+ rule reranker) remains the recommended simplest default backend**.

- **Locked test (`5,000`-doc parity slice, `11/16` pos-pool queries, `4/4` `no_answer` abstentions / `0` fabricated):**
  - `bm25` / `bm25_reranked`: `MRR@10 = 0.8485` (`all16 = 0.5833`), `nDCG@10 = 0.8624` / `0.8644` (`all16 = 0.5929` / `0.5943`), `Pooled Recall@10 = 1.0000`, `warm p95 = 11.56–13.79 ms` (`bm25`) / `22.17–25.45 ms` (`bm25_reranked`).
  - `tfidf_svd_vn_128d_v1` (`dense-svd-v2`, `14,898,542` B): `dense` trails (`MRR@10 = 0.5985`, `dMRR = -0.2500 [-0.4621, -0.0758]`; `nDCG@10 = 0.6539`, `dnDCG = -0.2085 [-0.3297, -0.0924]`, `warm p95 = 25.21 ms`). `hybrid_rrf_reranked` reaches `MRR@10 = 0.9091` / `nDCG@10 = 0.9049` on the 11 locked-test slice queries (`dev n=7`: `0.8571` / `0.8199` vs `bm25_reranked` `0.8730` / `0.8518`), with paired 95% CIs crossing zero (`dMRR = +0.0606 [+0.0000, +0.1818]`, `dnDCG = +0.0404 [-0.0136, +0.1261]`) at ~`2x` latency (`warm p95 = 49.93 ms`).
  - `paraphrase-multilingual-MiniLM-L12-v2` (`dense-minilm-v1`, `7,795,253` B excluding weights): `dense` (`MRR@10 = 0.3039`, `nDCG@10 = 0.2558`, `p95 = 80.15 ms`) and `hybrid_rrf_reranked` (`MRR@10 = 0.7455`, `nDCG@10 = 0.7698`, `p95 = 74.90 ms`) underperform `bm25_reranked` (`dMRR = -0.1030`, `dnDCG = -0.0947`) at ~`3.4x` latency.
- **Full-corpus `bm25-v3` reference (`21,748` docs):** `dev bm25_reranked` `MRR@10 = 0.8233`, `nDCG@10 = 0.7369`; `locked_test bm25_reranked` `MRR@10 = 0.8571`, `nDCG@10 = 0.7178` (`bm25`: `0.7976` / `0.7819`).
- **Root causes verified in code ([encoder.py](../../../../packages/retrieval/dense/encoder.py), [local_index.py](../../../../packages/retrieval/dense/local_index.py), [bm25.py](../../../../packages/retrieval/sparse/bm25.py), [service.py](../../../../packages/retrieval/service.py)):** Fixed-dim `128d`/`384d` embeddings collapse fine-grained Vietnamese F&B compound terms and do not use `M2.2` synonym expansion/negation guardrails; meanwhile `tfidf_svd` pays per-query subword 3-gram generation, `csr_matrix` construction (`1 x 25,000`), brute-force slicing copy over `5,000` vectors under `_restrict_to_df=True`, and sequential BM25+Dense+RRF execution, resulting in `~2x` higher `p95` than sparse CSR inverted-index lookups in `bm25`.

| Configuration (`5,000`-Doc Human-Verified Parity, `locked_test n=11`) | Test `MRR@10` (`All-16`) | Test `nDCG@10` (`All-16`) | Paired vs BM25 Baseline (`95% CI`) | Warm `p50` / `p95` (`100` req) |
| --- | ---: | ---: | --- | ---: |
| `bm25` (`bm25-v3`) | `0.8485` (`0.5833`) | `0.8624` (`0.5929`) | baseline | `3.17–3.38` / **`11.56–13.79 ms`** |
| `bm25_reranked` (`bm25-v3`) | `0.8485` (`0.5833`) | `0.8644` (`0.5943`) | `dMRR=+0.0000`, `dnDCG=+0.0020` | `6.74–7.28` / **`22.17–25.45 ms`** |
| `dense` (`tfidf_svd_vn_128d_v1`) | `0.5985` (`0.4115`) | `0.6539` (`0.4496`) | `dMRR=-0.2500`, `dnDCG=-0.2085` | `10.73` / `25.21 ms` |
| `hybrid_rrf_reranked` (`tfidf_svd`) | **`0.9091`** (`0.6250`) | **`0.9049`** (`0.6221`) | `dMRR=+0.0606 [+0.0000,+0.1818]`, `dnDCG=+0.0404 [-0.0136,+0.1261]` | `19.49` / `49.93 ms` |
| `dense` (`MiniLM-L12-v2`, `fastembed`) | `0.3039` (`0.2089`) | `0.2558` (`0.1758`) | `dMRR=-0.5446`, `dnDCG=-0.6066` | `37.84` / `80.15 ms` |
| `hybrid_rrf_reranked` (`MiniLM`) | `0.7455` (`0.5125`) | `0.7698` (`0.5292`) | `dMRR=-0.1030 [-0.2909,+0.0303]`, `dnDCG=-0.0947 [-0.2491,+0.0148]` | `35.92` / `74.90 ms` |

## Prior Conclusion (`v2_pilot` Initial Draft Run — 2026-11-19, preserved)

**Scientific & resource outcome:** Both **`tfidf_svd_vn_128d_v1`** (`dense-svd-v2`) and pretrained CPU ONNX **`sentence-transformers/paraphrase-multilingual-MiniLM-L12-v2`** (`dense-minilm-v1` via `fastembed==0.9.1`) stay comfortably inside `M6.1` CPU budgets (`<= 5,000` records, `<= 8,192 MiB` RAM, warm `p95 <= 1,000 ms`), **while `bm25-v3` + rule reranking consistently outperforms dense and `hybrid_rrf` on Vietnamese F&B `v2_pilot` queries** ([m6_1_v2_pilot.json](../../../../artifacts/benchmarks/m6_1_v2_pilot.json)). Therefore, **`bm25-v3` remains the recommended production default**, and `M6.1` stays **`IN_PROGRESS`** pending `K`/`N` human verification of `qrels_pooled_draft.jsonl`, multimodal scope (`M4.G`/`M5.G`), and `K` review.

- **Exact `5,000`-doc parity (`20261118_taxonomy_fix_v1`, `dev` & `locked_test`):** Using query-blind deterministic slicing (`(-play_count, video_id)`), `38/153` draft positive pairs land inside the `5k` pool (`dev`: `6` pos-pool queries + `4` `no_answer` + `10` `zero_relevant_pool`; `locked_test`: `9` pos-pool queries + `4` `no_answer` + `7` `zero_relevant_pool`). All evaluated parity configurations enforce `restrict_to_df=True` and score **`4/4` `no_answer` abstentions (`0` fabricated support)** on both splits.
- **Pretrained multilingual MiniLM vs domain `tfidf_svd` vs `bm25-v3` (`locked_test` positive-pool `n=9`):**
  - `bm25_reranked`: `MRR@10 = 0.9444`, `nDCG@10 = 0.9534`, `Recall@10 = 1.0000`, `p95 = 22.70–23.94 ms`
  - `bm25`: `MRR@10 = 0.8704`, `nDCG@10 = 0.8865`, `Recall@10 = 1.0000`, `p95 = 11.89–14.19 ms`
  - `hybrid_rrf_reranked (tfidf_svd)`: `MRR@10 = 0.8704`, `nDCG@10 = 0.8983` (`delta_nDCG = -0.0550`, 95% CI `[-0.1678, +0.0034]`), `p95 = 51.96 ms`
  - `hybrid_rrf_reranked (MiniLM)`: `MRR@10 = 0.7111`, `nDCG@10 = 0.7727` (`delta_nDCG = -0.1807`, 95% CI `[-0.3665, +0.0000]`), `p95 = 104.31 ms`
  - `dense (tfidf_svd)`: `MRR@10 = 0.5463`, `nDCG@10 = 0.6048` (`delta_nDCG = -0.2817`, 95% CI `[-0.5253, -0.0959]`), `p95 = 28.27 ms`
  - `dense (MiniLM)`: `MRR@10 = 0.3000`, `nDCG@10 = 0.2001` (`delta_nDCG = -0.6864`, 95% CI `[-0.8717, -0.4832]`), `p95 = 79.19 ms`
- **Why general multilingual MiniLM underperforms on Vietnamese F&B:** General 50-language MiniLM collapses fine-grained Vietnamese culinary compounds and street-food entities compared to exact `bm25-v3` lexical + bigram matching and corpus-fit `tfidf_svd` character+word n-grams, while consuming `~2.1x` peak build RAM (`3,265.02 MiB` vs `1,571.84 MiB`), `~10.3x` build time (`193.55 s` vs `18.76 s`), and `~4–5x` higher inference `p95` (`79–104 ms` vs `12–24 ms`). (Note: `intfloat/multilingual-e5-small` is absent from `fastembed 0.9.1`'s `TextEmbedding.list_supported_models()`, so `paraphrase-multilingual-MiniLM-L12-v2` (`384d`, `~252 MB`) was evaluated.)
- **Full-corpus `bm25-v3` reference (`21,748` docs):** `dev bm25_reranked` `MRR@10 = 0.8833`, `nDCG@10 = 0.7726`; `locked_test bm25_reranked` `MRR@10 = 0.8036`, `nDCG@10 = 0.7475`, `0` false abstentions (`t_n07` abstained only inside the `5k` subset where its matching pool was empty).
- **Historical artifact integrity & full checks:** `artifacts/indexes/dense-svd-v1/` and `artifacts/benchmarks/m6_1_dense_hybrid_spike.json` remain byte-untouched. All `141` pytest tests (`18.33s`), scoped `ruff`, strict `mypy` (`84` files, Linux and `--platform win32`), and `scripts/check_secrets.py` (`0` leaks) pass.

## Measured `v2_pilot` Resource & `locked_test` Parity Summary (`5,000`-Doc Slice)

| Backend / Config | Index Bytes | Build Time | Peak RSS (Build / Eval) | Test `MRR@10` (pos / all-16) | Test `nDCG@10` (pos / all-16) | Warm p50 / p95 (100 req) |
| --- | ---: | ---: | ---: | ---: | ---: | ---: |
| `bm25` (`bm25-v3`, `5k` parity) | — | — | — / `1,091–1,318 MiB` | `0.8704` / `0.4896` | `0.8865` / `0.4986` | `3.22–3.29 ms` / `11.89–14.19 ms` |
| `bm25_reranked` (`bm25-v3`, `5k`) | — | — | — / `1,091–1,318 MiB` | **`0.9444`** / **`0.5312`** | **`0.9534`** / **`0.5363`** | `6.69–7.05 ms` / `22.70–23.94 ms` |
| `dense` (`tfidf_svd_vn_128d_v1`) | `14,898,542` | `18.756 s` | `1,571.84` / `1,091.29 MiB` | `0.5463` / `0.3073` | `0.6048` / `0.3402` | `10.59 ms` / `28.27 ms` |
| `hybrid_rrf_reranked` (`tfidf_svd`) | `14,898,542` | `18.756 s` | `1,571.84` / `1,091.29 MiB` | `0.8704` / `0.4896` | `0.8983` / `0.5053` | `19.47 ms` / `51.96 ms` |
| `dense` (`MiniLM-L12-v2`, `fastembed`) | `7,795,253` | `193.549 s` | `3,265.02` / `1,317.96 MiB` | `0.3000` / `0.1688` | `0.2001` / `0.1125` | `36.42 ms` / `79.19 ms` |
| `hybrid_rrf_reranked` (`MiniLM`) | `7,795,253` | `193.549 s` | `3,265.02` / `1,317.96 MiB` | `0.7111` / `0.4000` | `0.7727` / `0.4346` | `54.05 ms` / `104.31 ms` |

## `v2_pilot` Verification & New Artifacts (`2026-11-19`)

| Artifact / Check | Result | Scope / Evidence |
| --- | --- | --- |
| Build `dense-svd-v2` (`tfidf_svd`, `5,000` docs) | PASS (`18.756 s`, `1,571.84 MiB`) | [dense-receipt.json](../../../../artifacts/indexes/dense-svd-v2/dense-receipt.json) |
| Build `dense-minilm-v1` (`fastembed` MiniLM, `5,000` docs) | PASS (`193.549 s`, `3,265.02 MiB`) | [dense-receipt.json](../../../../artifacts/indexes/dense-minilm-v1/dense-receipt.json) |
| `dense_hybrid_v2_pilot` (`dev` + `locked_test` + 100-req latency) | PASS (`p95 <= 104.31 ms`, `0` fabricated `no_answer`) | [m6_1_v2_pilot.json](../../../../artifacts/benchmarks/m6_1_v2_pilot.json), [dense_hybrid_v2_pilot.py](../../../../pipelines/benchmark_retrieval/dense_hybrid_v2_pilot.py) |
| Full `pytest -v` | PASS (`141 passed in 18.33s`) | Includes 2 new TDD regressions in [test_dense_hybrid_retrieval.py](../../../../tests/unit/test_dense_hybrid_retrieval.py); [v2-pilot-pytest.log](evidence/v2-pilot-pytest.log) |
| `mypy` (`packages apps pipelines`, Linux & `--platform win32`) | PASS (`84 source files` each) | [v2-pilot-mypy.log](evidence/v2-pilot-mypy.log), [v2-pilot-mypy-win32.log](evidence/v2-pilot-mypy-win32.log) |
| `ruff check` (source + scripts + changed tests) & secret scan | PASS (`All checks passed!`, `0` leaks) | [v2-pilot-ruff.log](evidence/v2-pilot-ruff.log), [v2-pilot-secrets.log](evidence/v2-pilot-secrets.log); note: unrelated repo test files had 3 pre-existing style notices untouched |

## Prior Conclusion & Windows Repair / PR3 Record (2026-11-18, preserved)

**Code integration completed:** [PR3](https://github.com/khuonglaptri3/TikTok_AI_Engine_/pull/3) merged at `eb43b0df3d46007b7550de8f4314dc2dbca9c51f`; a new full run on merged main records **120 passed in 58.09s**. [Main verification](evidence/main-verification.json), [full log](evidence/main-pytest.log), [GitHub merge receipt](../M0.G/evidence/merge-github-receipt.json).


The Windows portability blocker is **resolved** and the integrated repair passes **120/120 full tests**, **11/11 contract/smoke tests**, configured mypy for **81 files** on both Windows and Linux static targets, and clean Ruff across packages/apps/pipelines and the changed tests. The independent G0 probe passes 38/38 and clean wheel/installed-ASGI validation passes. These are new Windows repair/integration results, separate from the original Linux spike below.

Both M6.1 pipelines now import without Unix-only resource on Windows. A shared standard-library helper reads a real process-lifetime peak from Windows GetProcessMemoryInfo or Unix getrusage and normalizes to MiB. Existing peak_rss_mb keys remain compatible; newly written receipts declare peak_rss_unit=MiB and peak_rss_scope=process_lifetime. API failures and invalid readings propagate instead of a fabricated zero/current-RSS fallback.

The owner-authorized PR3 update, ready and merge completed successfully and was reverified on main. That integration does not complete M6.1's frozen human-judged relevance evaluation, conditional multimodal work or human peer sign-off. **M6.1 remains IN_PROGRESS** and no original benchmark/index artifact is overwritten.

## Windows repair verification

| Check | Result | Evidence / scope |
| --- | --- | --- |
| Observed regression RED |8 failures before implementation | [RED](evidence/windows-red.log), including unavailable-resource pipeline imports. |
| Focused resource and dense tests |14 passed | [GREEN](evidence/windows-green.log): native Windows measurement, Linux conversion through an OS-boundary double, invalid/nonfinite readings and OS-error propagation. |
| Full project pytest |120 passed in31.20s | [Current full log](evidence/windows-pytest-full.log), [exit/environment/source receipt](evidence/windows-check-results.json). |
| Contract/smoke |11 passed in10.48s | [Current log](evidence/windows-contract-smoke.log). |
| Configured mypy, Windows and Linux static target |PASS:81 files each | [Windows](evidence/windows-mypy.log), [Linux static](evidence/windows-mypy-linux-target.log). Native Linux/macOS execution was not performed by this repair. |
| Ruff, secret scanner and dependencies |PASS | [Ruff](evidence/windows-ruff.log), [secrets](evidence/windows-secrets.log), [pip](evidence/windows-pip-check.log). Five pre-existing crawl UTC-alias issues were fixed equivalently; [prior findings](evidence/windows-broad-lint-before-fix.log) remain dated evidence. |
| Fresh-context read-only review |No Critical/Important/Minor findings | [Review](evidence/windows-code-review.md); reviewer independently ran all8 resource tests. No human K/N approval is fabricated. |
| G0 asserting runtime and clean installed ASGI |PASS:38/38 runtime assertions; clean package install | [Runtime](../M0.G/evidence/merge-runtime-receipt.json), [package](../M0.G/evidence/merge-package-results.json). Source hashes match the full-suite receipt. |
| Final layout/link/hash/source check |See current handoff receipt | [Workflow](evidence/workflow.md), [handoff](evidence/windows-handoff.json), [current hashes](evidence/windows-artifact-hashes.json); current integrity receipt is generated before commit and actual merge verification is recorded in [main-verification.json](evidence/main-verification.json). |

The native Windows test verifies the OS-backed helper on this host; deterministic unit conversion/error cases use OS-boundary doubles. It does not remeasure the dense spike, prove model quality, measure complete per-stage allocations, or establish current trends. Original Linux numbers remain original results.

## Windows repair outputs and process

| File | Purpose |
| --- | --- |
| [Spec](superpowers/spec.md), [plan](superpowers/plan.md), [workflow](evidence/workflow.md) | Prospective repair/merge authorization, actual skills, RED/GREEN and integration provenance. |
| [Baseline](evidence/windows-baseline.json), [check runner](evidence/windows-run-checks.py), [current receipt](evidence/windows-check-results.json) | Exact starting revision, tested code hashes, environment, commands, durations and log hashes. |
| [Review](evidence/windows-code-review.md), [archived report](evidence/report-before-windows-fix.md) | Independent code assessment and byte-preserved original narrative. Archived links retain their original context. |
| [Peak-memory helper](../../../../packages/common/resources.py), [regressions](../../../../tests/unit/test_resource_measurements.py) | Portable OS measurement and meaningful regression coverage. |

Implementation references: [Python resource availability](https://docs.python.org/3/library/resource.html), [Windows peak-working-set bytes](https://learn.microsoft.com/en-us/windows/win32/api/psapi/ns-psapi-process_memory_counters), and [Linux ru_maxrss KiB](https://man7.org/linux/man-pages/man2/getrusage.2.html). The legacy field suffix is retained for compatibility while the explicit unit is MiB.

## Original CPU spike narrative and measurements (dated, unchanged)
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
