# M6.1 — Workflow Provenance & Verification Ledger

## Owner-authorized Windows compatibility repair — 2026-11-18

- Authorization: the owner requested fixing the current blocker, updating PR3 and bringing today's completed implementation into main. Merge authorization is explicit; gate/scientific approval is separate.
- Existing source: PR3 head40c457e2 over mainad7eb92f. The prior publication logs reproduce Windows pytest collection failure on unconditional `import resource` and4 configured-mypy errors at getrusage/RUSAGE_SELF in the two M6.1 pipelines.
- Root cause: Unix-only resource imports execute during module import, before tests can collect. The process-memory measurement has a platform-specific API and unit convention; suppressing type errors or returning zero would not verify the memory requirement.
- Skills actually read/reused: installed Superpowers7.0.1 using-superpowers (+ Codex reference), systematic-debugging, test-driven-development (+ writing-good-tests), writing-plans, executing-plans, verification-before-completion, requesting-code-review and finishing-a-development-branch. Paths are under `C:/Users/lanph/.codex/plugins/cache/openai-curated-remote/superpowers/7.0.1/skills/`; the first three and verification were read again for this task, the other already-read instructions are reused.
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

- Initial integrated verification passed120 tests and both Windows/Linux-target mypy (81 files), runtime38/38 and clean package install. Full-pipeline Ruff found five pre-existing UP017 aliases in crawl helpers. Preserve those initial receipts under windows-initial-verification/; apply only equivalent UTC aliases and rerun the complete declared scope. Normalize the two new M6.1 pipeline edits to their existing Git LF representation before final source-hash-bound checks; keep historical evidence byte-identical.

- Byte-preservation attributes cover the new resource helper/test and the two M6.1 pipeline files. The crawl service helper also receives -text because its equivalent UTC alias fix is included in the final measured-source map; all measured source bytes must match the committed hash receipt across platforms. Its __main__ was already covered.

- Fresh-context read-only review found no Critical/Important/Minor code defects and independently ran the8 resource tests successfully, including the native Windows API. [Review](windows-code-review.md). It checked API structure/signatures against Microsoft primary documentation, retained scientific/native-platform limitations and supplied no human K/N sign-off.

- Final integrated source:120 full tests (31.20s),11 contract/smoke (10.48s), Windows/Linux static mypy81, full required Ruff, scanner and dependency checks all pass. Current G0 runtime38/38 and clean installed ASGI share the11-file source map. [Current results](windows-check-results.json). Review is clean; user-authorized commit/push/ready/merge and actual main verification follow. All scientific/gate decisions remain explicitly pending.

- First final handoff found one inherited broken relative link in the original workflow benchmark receipt; corrected its path from the evidence directory. Source/benchmark data and test results are unchanged.
