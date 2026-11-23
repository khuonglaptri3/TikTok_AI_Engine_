# M6.1 — Independent Parity, Qrels & Cost Peer Review (`K`)

- **Reviewer:** Trần Đình Khương (`K`)
- **Primary Owner:** Nguyễn Việt Nguyên (`N`)
- **Review Date:** 2026-11-20 (Asia/Ho_Chi_Minh)
- **Reviewed Baseline:** `main` @ `1531174e` (`M6.1` commits `eb43b0df` & `f70e6867`; `M2.2` finalized at `ba1dbb9a`)
- **Post-Fix Verification Branch:** `feat/k-m4.2-m5.1-m6.1-peer-reviews`
- **Verdict:** **`K` PARITY & COST PEER REVIEW COMPLETE (`bm25-v3` confirmed as recommended production default; `M6.1` stays `IN_PROGRESS` pending optional `fastembed` `hybrid_rrf` re-run under `restrict_to_df=True` and conditional post-`M4.G`/`M5.G` multimodal scope)**

## 1. Defects Found During `K` Adversarial Audit & Resolved via TDD (`RED -> GREEN`)

All code defects were reproduced in [red-k-review-fixes.log](red-k-review-fixes.log) (`2 failed, 8 passed`) and fixed in [green-k-review-fixes.log](green-k-review-fixes.log) (`18/18` dense + resource tests passed):

1. **`[C1]` Missing `restrict_to_df=True` in `dense_hybrid_v2_pilot.py` (`line 97`):** `benchmark_dense_backend` called `HybridRetrievalService.from_dirs(df_videos=df_parity, ...)` without `restrict_to_df=True` (default `False`). On all `27/40` unfiltered queries, `bm25.search(..., top_k=80, allowed_video_ids=None)` searched all `21,748` documents instead of the `5,000`-doc parity pool, starving `bm25` to `< 10` results on `d_k02` (`7`), `d_n02` (`6`), `d_k04` (`8`), and `t_n05` (`8`) and polluting `hybrid_rrf` rank fusion.
   - **Fix:** Enforced `restrict_to_df=True` in `dense_hybrid_v2_pilot.py`, filtered `fused_raw` strictly to `self.video_lookup` before viral boost and `top_k` slicing in `packages/retrieval/service.py`, and ensured contiguous `1..k` card ranks.
2. **`[C2]` Pre-Signoff Draft Qrels in `m6_1_v2_pilot.json` (`46/408` Labels Updated in `M2.2` Closure `ba1dbb9a`):** `m6_1_v2_pilot.json` used `qrels_sha256 = 46a2263f...` (`human_signoff_complete=false`, `38` positives in `5k`), whereas finalized `M2.2` qrels (`9a478e54...`, `K` & `N` `408/408` verified) has **`47` positives in `5k`** (`+23.7%`, expanding evaluated positive-pool queries from `6 -> 7` on `dev` and `9 -> 11` on `locked_test`).
   - **Fix:** Executed a clean post-fix benchmark receipt (consolidated into [m6_1_v2_final_qrels_minilm_refresh.json](../../../../../artifacts/benchmarks/m6_1_v2_final_qrels_minilm_refresh.json) with `dense-svd-v2` + `dense-minilm-v1`, preserving `m6_1_v2_pilot.json` untouched) and recorded exact `unjudged_rate_at_10` per configuration in `pilot_m2_2.py`.
3. **`[I1]` & `[I3]` OOV Fast-Path Symmetry, Unsafe Implicit `e5-base` Download Removal, & `QdrantDenseAdapter` `> 5,000` Filter Safety:**
   - Removed the implicit `SentenceTransformer("intfloat/multilingual-e5-base")` auto-download fallback in `service.py` when `_dense_encoder is None`.
   - Aligned early OOV anchor short-circuiting across `bm25`, `hybrid_rrf`, and `dense` (after index-readiness verification) so OOV queries do not pay wasted dense query encoding.
   - Fixed `QdrantDenseAdapter.search_vectors` (`qdrant_adapter.py`) so `len(allowed_video_ids) > 5000` post-filters strictly against `allowed_video_ids` rather than leaking cross-city/unallowed hits.

## 2. Post-Fix `5,000`-Doc Parity Results on Finalized `M2.2` Two-Human Qrels (`9a478e54...`)

From [m6_1_v2_final_qrels_minilm_refresh.json](../../../../../artifacts/benchmarks/m6_1_v2_final_qrels_minilm_refresh.json) (`dense-svd-v2`, identical to the earlier partial `m6_1_v2_final_qrels_parity.json` receipt) and [khuong_m6_1_qrels_and_parity_audit.json](khuong_m6_1_qrels_and_parity_audit.json) (`locked_test`, `n=11` pos-pool / `n=16` all answerable; `4/4` `no_answer` abstained with `0` fabricated support):

| Configuration (`5,000`-Doc Exact Parity) | `MRR@10` (pos-11 / all-16) | `nDCG@10` (pos-11 / all-16) | `Recall@10` (pos-11) | `Unjudged@10` Rate | Warm `p50 / p95` (100 req) |
| --- | ---: | ---: | ---: | ---: | ---: |
| `bm25` (`bm25-v3`, `restrict_to_df=True`) | `0.8485` / `0.5833` | `0.8624` / `0.5929` | **`1.0000`** | `51.33%` | `9.75 ms` / `27.36 ms` |
| `bm25_reranked` (`bm25-v3`, `restrict_to_df=True`) | `0.8485` / `0.5833` | `0.8621` / `0.5927` | **`1.0000`** | `51.33%` | `16.24 ms` / `41.48 ms` |
| `dense` (`tfidf_svd_vn_128d_v1`) | `0.5985` / `0.4115` | `0.6539` / `0.4496` | `0.9074` | `64.67%` | `12.64 ms` / `33.27 ms` |
| `dense_reranked` (`tfidf_svd_vn_128d_v1`) | `0.7909` / `0.5437` | `0.7658` / `0.5265` | `0.9234` | `57.33%` | `20.72 ms` / `49.86 ms` |
| `hybrid_rrf` (`tfidf_svd_vn_128d_v1`) | `0.8485` / `0.5833` | `0.8562` / `0.5887` | `0.9870` | `56.00%` | `17.72 ms` / `37.42 ms` |
| `hybrid_rrf_reranked` (`tfidf_svd_vn_128d_v1`) | **`0.9091`** / **`0.6250`** | **`0.8694`** / **`0.5977`** | `0.9545` | `54.00%` | `28.10 ms` / `89.30 ms` |
| `dense` (`MiniLM-L12-v2`, offline rescored on final qrels)* | `0.3039` / `0.2089` | `0.2558` / `0.1758` | `0.4297` | **`84.67%`** | `36.42 ms` / `79.19 ms` (prior) |
| `dense_reranked` (`MiniLM-L12-v2`, offline rescored)* | `0.6212` / `0.4271` | `0.4965` / `0.3413` | `0.5206` | **`82.00%`** | `51.49 ms` / `97.99 ms` (prior) |

*\*Note on `MiniLM` & Pooling Bias:* `qrels_pooled_draft.jsonl` was pooled from `bm25` $\cup$ `bm25_reranked` top-10; **`84.67%`** of `MiniLM` top-10 hits are unjudged (scored conservatively as `0`, making `0.2558` a pooled lower bound rather than exhaustive semantic error), and `dense-minilm-v1` requires `~252 MB` external ONNX weights (`fastembed==0.9.1`) in addition to its `7.79 MB` `embeddings.npy`.

- **Paired Bootstrap Decision (`hybrid_rrf_reranked - bm25_reranked` on `tfidf_svd`):** `delta_MRR@10 = +0.0606` (`[+0.0000, +0.1818]`), **`delta_nDCG@10 = +0.0073` (`[-0.0688, +0.1018]`, spans `0`)**, `delta_Recall@10 = -0.0455` (`[-0.1364, +0.0000]`). Because `nDCG@10` CI spans zero while `bm25_reranked` achieves higher `Recall@10` (`1.0000`), `~2x` lower `p95`, and zero dense build/RAM overhead (and `QdrantDenseAdapter` remains unpopulated in live runtime, `qdrant_populated=false`), **retaining `bm25-v3` + reranking as the production default is empirically justified**.
