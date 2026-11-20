# M6.1 — Workflow Provenance & Verification Ledger

## Phase 2 — Finalized Human-Verified Qrels Re-Evaluation (`N`) & Adversarial Parity/Cost Peer Review (`K`) — 2026-11-20

- **Contributor `N` (`847ffcb4`):** Re-ran `.venv/bin/python -m pipelines.benchmark_retrieval.dense_hybrid_v2_pilot --dense-dirs artifacts/indexes/dense-svd-v2 artifacts/indexes/dense-minilm-v1 --benchmark-id m6_1_v2_pilot_human_verified --output artifacts/benchmarks/m6_1_v2_pilot_human_verified.json` against frozen two-human-verified `M2.2` qrels (`408/408` verified pairs; `K_human_verified_all=true`, `N_human_verified_all=true`), preserving `m6_1_dense_hybrid_spike.json` and `m6_1_v2_pilot.json` untouched, and confirmed `bm25-v3` (+ rule reranker) retention per `M6.1` simplicity rule ([nguyen_text_spike_signoff_receipt.json](nguyen_text_spike_signoff_receipt.json)).
- **Peer Reviewer `K` (`468eba7c`, merged into `main`):**
  1. Discovered that `pipelines/benchmark_retrieval/dense_hybrid_v2_pilot.py:97` omitted `restrict_to_df=True`, causing unfiltered `bm25` and `hybrid_rrf` queries in `m6_1_v2_pilot.json` (and `m6_1_v2_pilot_human_verified.json`) to search all `21,748` docs on fallback instead of the `5,000`-doc parity slice (`<10` results on `d_k02`, `d_n02`, `d_k04`, `t_n05`), while pure `dense`/`dense_reranked` `MiniLM` & `tfidf_svd` already searched only the `5,000` vectors.
  2. Added `2` TDD regressions in `tests/unit/test_dense_hybrid_retrieval.py` + `dense_hybrid_v2_pilot` import guard in `tests/unit/test_resource_measurements.py` ([red-k-review-fixes.log](red-k-review-fixes.log) `2 failed` -> [green-k-review-fixes.log](green-k-review-fixes.log) `18 passed`): enforced `restrict_to_df=True`, hardened `QdrantDenseAdapter.search_vectors` so `len(allowed_video_ids) > 5000` never leaks unallowed IDs, aligned early OOV short-circuiting across modes in `packages/retrieval/service.py`, removed implicit `SentenceTransformer("intfloat/multilingual-e5-base")` download fallback, and added `unjudged_rate_at_10` in `pilot_m2_2.py`.
  3. Executed [m6_1_v2_final_qrels_parity.json](../../../../../artifacts/benchmarks/m6_1_v2_final_qrels_parity.json) (`dense-svd-v2`, true `restrict_to_df=True` parity on finalized `M2.2` qrels `9a478e54...`) and [khuong_m6_1_qrels_and_parity_audit.json](khuong_m6_1_qrels_and_parity_audit.json) ([khuong_peer_review.md](khuong_peer_review.md)), preserving `m6_1_v2_pilot.json` and `m6_1_v2_pilot_human_verified.json` untouched. Both `N` and `K` concur on retaining `bm25-v3` + reranking; `M6.1` remains `IN_PROGRESS` only for conditional multimodal segment evaluation after `M4.G`/`M5.G`.

## v2_pilot Parity & FastEmbed Comparison — 2026-11-19

- **Date:** 2026-11-19 (Asia/Ho_Chi_Minh)
- **Branch:** `feat/m6.1-v2-pilot-eval` (branched from `main` @ `dcdd6233`)
- **Spec & Plan:** [spec.md](../superpowers/spec.md), [plan.md](../superpowers/plan.md) (updated prospectively before code edits)
- **Process:**
  1. Audited `M2.2` assets on `main`: `data/corpus/20261118_taxonomy_fix_v1` (`70,996` rows, `21,748` transcribed), `artifacts/indexes/bm25-v3`, and `data/evaluation/v2_pilot/{dev_queries.jsonl,test_queries.jsonl,qrels_pooled_draft.jsonl}` (`408` judged pairs; `K_human_verified_all=false`, `N_human_verified_all=false`).
  2. Verified blind `5,000`-record coverage (`(-play_count, video_id)`): `38/153` positive pairs land in the `5k` slice (`dev`: `12/81` across `6` queries; `locked_test`: `26/72` across `9` queries). Kept the query-blind slice rule intact to avoid `locked_test` leakage.
  3. Installed `fastembed==0.9.1` (`onnxruntime==1.32.0`) in `.venv`. Confirmed `intfloat/multilingual-e5-small` is unsupported in `fastembed.TextEmbedding.list_supported_models()`, so benchmarked the supported CPU multilingual neural embedding model `sentence-transformers/paraphrase-multilingual-MiniLM-L12-v2` (`384`-dim, `~252 MB` cached offline after TLS-verified download using combined certifi + `/etc/ssl/certs/tma-ADCA-CA.pem`).
  4. Applied TDD (`RED -> GREEN`): added `test_v2_pilot_split_mode_and_eligible_pool_parity` and `test_v2_pilot_suite_benchmark_structure` (`2 failed, 6 passed` RED), parameterized `evaluate_pilot_split` (`mode`, `eligible_video_ids`) and `measure_warm_latency` (`mode`) in `pipelines/benchmark_retrieval/pilot_m2_2.py`, and implemented `pipelines/benchmark_retrieval/dense_hybrid_v2_pilot.py`. Fixed inverted `cand - base` CI argument order in `_compare_pair` caught during initial inspection (`mean_diff` test assertion added, `8/8 passed` GREEN).
  5. Built versioned `5,000`-doc dense indexes (`dense-svd-v2`: `18.756 s`, `14,898,542` B, `1,571.84 MiB` peak RSS; `dense-minilm-v1`: `193.549 s`, `7,795,253` B excluding ONNX weights, `3,265.02 MiB` peak RSS) and generated `artifacts/benchmarks/m6_1_v2_pilot.json` without modifying `dense-svd-v1` or `m6_1_dense_hybrid_spike.json`.
- **Verification Commands & Logs:**
  - `.venv/bin/python -m pytest -v` -> `141 passed in 18.33s` ([v2-pilot-pytest.log](v2-pilot-pytest.log))
  - `.venv/bin/python -m ruff check packages apps pipelines scripts tests/unit/test_dense_hybrid_retrieval.py` -> `All checks passed!` ([v2-pilot-ruff.log](v2-pilot-ruff.log))
  - `.venv/bin/python -m mypy packages apps pipelines` -> `Success: no issues found in 84 source files` ([v2-pilot-mypy.log](v2-pilot-mypy.log))
  - `.venv/bin/python -m mypy --platform win32 packages apps pipelines` -> `Success: no issues found in 84 source files` ([v2-pilot-mypy-win32.log](v2-pilot-mypy-win32.log))
  - `python3 scripts/check_secrets.py` -> `PASS: Zero secret leaks detected across workspace.` ([v2-pilot-secrets.log](v2-pilot-secrets.log))

## Owner-authorized Windows compatibility repair — 2026-11-18

- Authorization: the owner requested fixing the current blocker, updating PR3 and bringing today's completed implementation into main. Merge authorization is explicit; gate/scientific approval is separate.
- Existing source: PR3 head40c457e2 over mainad7eb92f. The prior publication logs reproduce Windows pytest collection failure on unconditional `import resource` and4 configured-mypy errors at getrusage/RUSAGE_SELF in the two M6.1 pipelines.
- Root cause: Unix-only resource imports execute during module import, before tests can collect. The process-memory measurement has a platform-specific API and unit convention; suppressing type errors or returning zero would not verify the memory requirement.
- Skills actually read/reused: installed Superpowers 7.0.1 using-superpowers (+ Codex reference), systematic-debugging, test-driven-development (+ writing-good-tests), writing-plans, executing-plans, verification-before-completion, requesting-code-review and finishing-a-development-branch (loaded from the local Superpowers plugin skill cache); the first three and verification were read again for this task, the other already-read instructions are reused.
- Prospective spec/plan addenda above precede new tests and source edits. Native ledger/evidence remain under this existing task bundle per repository policy; user requested continuing the current local branch, so no unrelated worktree is created.
- Evidence sources: Python resource documentation states Unix availability; Microsoft documents PeakWorkingSetSize in bytes; Linux getrusage documents ru_maxrss in KiB. New measurements will be process-lifetime peak resident memory normalized to MiB, not per-operation allocation or total host RAM.
- Task1 IN_PROGRESS: baseline/report preservation, RED regressions, then minimal implementation. No original benchmark is rerun or overwritten by planning.

- **Date:** 2026-11-18 (Asia/Ho_Chi_Minh)
- **Task ID:** `M6.1` (Text-Only CPU Spike)
- **Primary Owner:** Nguyễn Việt Nguyên (`N`)
- **Peer Reviewer:** Trần Đình Khương (`K`, pending review)
- **Branch:** `feat/m6.1-dense-hybrid-spike` (branched from `main` @ `c6c36131`)

## Process Check (`AGENTS.md` Section 7)
- Authored [spec.md](../superpowers/spec.md) and [plan.md](../superpowers/plan.md) before modifying code.
- Applied TDD (`RED -> GREEN`): wrote `tests/unit/test_dense_hybrid_retrieval.py` first (`red-m6_1-tests.log`), implemented dense encoders, `LocalDenseIndex`, `QdrantDenseAdapter` population, `HybridRetrievalService` parity integration, and pilot CLI tools.

## Key Engineering Decisions
1. **CPU-Feasible Zero-Dependency Baseline (`tfidf_svd_vn_128d_v1`) + Pluggable Neural Backends:** Installed dependencies in `.venv` omit PyTorch/ONNX runtimes, so `TruncatedSvdDenseEncoder` (`scipy.sparse.linalg.svds` over Vietnamese NFC word + bigram + char-3gram TF-IDF) was chosen for an offline reproducible CPU baseline while keeping `FastEmbedEncoder` (`intfloat/multilingual-e5-small`) and `SentenceTransformerEncoder` ready behind the same `DenseTextEncoder` protocol.
2. **Exact `<= 5,000` Cohort Parity:** `select_eligible_corpus_slice` enforces `1 <= max_records <= 5000`; `HybridRetrievalService(..., restrict_to_df=True)` restricts both `bm25` and `dense` candidate pools (including fallback relaxation) to the exact same `5,000` indexed IDs.
3. **Honest Evaluation Scope:** Because `M2.2`'s frozen 40-query human-judged test set is not published yet, this spike measures parity against the existing `v1` weak-label queries (`15` queries overlapping the `5,000`-doc slice) and reports paired bootstrap uncertainty honestly without promoting weak-label deltas to population accuracy.

## Commands & Verification Receipts
- `.venv/bin/python -m pytest tests/unit/test_dense_hybrid_retrieval.py -v` (RED) -> collection `ImportError` ([red-m6_1-tests.log](red-m6_1-tests.log))
- `.venv/bin/python -m pipelines.build_dense_sparse_index.dense --corpus data/corpus/20261117_recovered_v1 --output artifacts/indexes/dense-svd-v1 --max-records 5000 --dimension 128` -> `5,000` docs, `14,898,224` bytes, `19.418 s`, peak `1,547.24 MiB` RSS
- `.venv/bin/python -m pipelines.benchmark_retrieval.dense_hybrid_pilot --corpus data/corpus/20261117_recovered_v1 --bm25 artifacts/indexes/bm25-v2 --dense artifacts/indexes/dense-svd-v1 --queries data/evaluation/v1/queries.jsonl --output artifacts/benchmarks/m6_1_dense_hybrid_spike.json --repetitions 100` -> `EXIT=0` ([m6_1_dense_hybrid_spike.json](../../../../../artifacts/benchmarks/m6_1_dense_hybrid_spike.json))
- `.venv/bin/python -m pytest tests/unit/test_dense_hybrid_retrieval.py -v` (GREEN) -> `EXIT=0`, `6 passed in 1.07s` ([green-m6_1-tests.log](green-m6_1-tests.log))
- `.venv/bin/python -m ruff check ...` -> `EXIT=0`, `All checks passed!` ([ruff.log](ruff.log))
- `.venv/bin/python -m mypy packages apps pipelines` -> `EXIT=0`, `Success: no issues found in 80 source files` ([mypy.log](mypy.log))
- `.venv/bin/python -m pytest -v` -> `EXIT=0`, `81 passed in 17.03s` ([pytest-full.log](pytest-full.log))
- `.venv/bin/python scripts/check_secrets.py` -> `EXIT=0`, `PASS: Zero secret leaks detected across workspace.` ([check-secrets.log](check-secrets.log))

- TDD RED reproduced8 failures before implementation, including both pipeline imports without resource. Implemented the shared standard-library OS-backed helper and wired both consumers. Focused GREEN:14 tests (8 new resource and6 existing dense tests) passed on Windows; the native Windows peak-reading test used the actual OS API. Prior benchmark artifacts remain unchanged. [RED](windows-red.log), [GREEN](windows-green.log).

- Initial integrated verification passed 120 tests and both Windows/Linux-target mypy (81 files), runtime38/38 and clean package install. Full-pipeline Ruff found five pre-existing UP017 aliases in crawl helpers. Preserve those initial receipts under windows-initial-verification/; apply only equivalent UTC aliases and rerun the complete declared scope. Normalize the two new M6.1 pipeline edits to their existing Git LF representation before final source-hash-bound checks; keep historical evidence byte-identical.

- Byte-preservation attributes cover the new resource helper/test and the two M6.1 pipeline files. The crawl service helper also receives -text because its equivalent UTC alias fix is included in the final measured-source map; all measured source bytes must match the committed hash receipt across platforms. Its __main__ was already covered.

- Fresh-context read-only review found no Critical/Important/Minor code defects and independently ran the8 resource tests successfully, including the native Windows API. [Review](windows-code-review.md). It checked API structure/signatures against Microsoft primary documentation, retained scientific/native-platform limitations and supplied no human K/N sign-off.

- Final integrated source:120 full tests (31.20s),11 contract/smoke (10.48s), Windows/Linux static mypy81, full required Ruff, scanner and dependency checks all pass. Current G0 runtime38/38 and clean installed ASGI share the11-file source map. [Current results](windows-check-results.json). Review is clean; user-authorized commit/push/ready/merge and actual main verification follow. All scientific/gate decisions remain explicitly pending.

- First final handoff found one inherited broken relative link in the original workflow benchmark receipt; corrected its path from the evidence directory. Source/benchmark data and test results are unchanged.

- User-authorized PR3 integration completed: source commit `af5be92bf48433688c47c97b03ecaccc5d8fcb5b`, merge commit `eb43b0df3d46007b7550de8f4314dc2dbca9c51f`, merged_at `2026-11-18T10:45:57Z`. [GitHub PR3](https://github.com/khuonglaptri3/TikTok_AI_Engine_/pull/3). Local main was fast-forwarded by fetch while the topic branch was checked out, then switched to the identical merged tree; no old main checkout removed preserved data. Formal G0 remains NOT_RUN and scientific M6.1 remains IN_PROGRESS.

- Post-merge verification on actual main `eb43b0df3d46007b7550de8f4314dc2dbca9c51f`: 120 passed in 58.09s, exit0; committed source hashes match the full premerge suite/runtime/package map. [Main test receipt](main-verification.json). No production source is changed by the final evidence-only PR.

- Source integration and post-merge full verification are complete. The final evidence-only branch persists the actual PR3 merge receipt and main120-test log through a separate PR, with identical production source. Final remote main ancestry/PR state/source hashes are verified after that metadata merge, avoiding a circular self-commit receipt.
