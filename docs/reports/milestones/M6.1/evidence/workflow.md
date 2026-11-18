# M6.1 — Workflow Provenance & Verification Ledger

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
- `.venv/bin/python -m pipelines.benchmark_retrieval.dense_hybrid_pilot --corpus data/corpus/20261117_recovered_v1 --bm25 artifacts/indexes/bm25-v2 --dense artifacts/indexes/dense-svd-v1 --queries data/evaluation/v1/queries.jsonl --output artifacts/benchmarks/m6_1_dense_hybrid_spike.json --repetitions 100` -> `EXIT=0` ([m6_1_dense_hybrid_spike.json](../../../../artifacts/benchmarks/m6_1_dense_hybrid_spike.json))
- `.venv/bin/python -m pytest tests/unit/test_dense_hybrid_retrieval.py -v` (GREEN) -> `EXIT=0`, `6 passed in 1.07s` ([green-m6_1-tests.log](green-m6_1-tests.log))
- `.venv/bin/python -m ruff check ...` -> `EXIT=0`, `All checks passed!` ([ruff.log](ruff.log))
- `.venv/bin/python -m mypy packages apps pipelines` -> `EXIT=0`, `Success: no issues found in 80 source files` ([mypy.log](mypy.log))
- `.venv/bin/python -m pytest -v` -> `EXIT=0`, `81 passed in 17.03s` ([pytest-full.log](pytest-full.log))
- `.venv/bin/python scripts/check_secrets.py` -> `EXIT=0`, `PASS: Zero secret leaks detected across workspace.` ([check-secrets.log](check-secrets.log))
