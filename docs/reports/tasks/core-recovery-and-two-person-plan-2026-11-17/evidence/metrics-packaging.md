# Retrieval metrics and package source verification

- Execution date: 2026-11-17, Asia/Saigon.
- Scope: delegated metric/receipt regression and package/container source fixes under the approved [specification](../superpowers/spec.md) and [plan](../superpowers/plan.md), tasks 4 and 5.
- Workspace: isolated worktree `bf1f/TikTok_AI_Engine_`; production changes remain uncommitted. Integration and final data-backed verification belong to the parent task.
- Result: eight focused tests pass; root and Docker COPY-context wheels build; project mypy and scoped Ruff pass. The full-suite observation was **29 passed, 6 failed** before data restoration and while the snapshot fixes were being developed. This is not a claim that the full project passes.

## Implemented outcome

`Recall@10` now divides relevant hits by every relevant video ID. `Precision@10` is exposed separately and divides by 10 even when fewer than 10 results return. The evaluator reports the macro theoretical recall ceiling. Queries with zero relevant IDs are excluded from macro averages and counted explicitly; empty/all-zero-label inputs return zero metrics safely.

The hand-derived regression uses the real BM25 service over four documents: two relevant hits among 20 relevant IDs yield recall `0.1`, precision `0.2`, and maximum possible recall `0.5`. The old capped denominator incorrectly yielded recall `0.2`. Both reranking configurations are tested. A second example with two total relevant IDs demonstrates recall `1.0` versus precision `0.2`.

The versioned CLI defaults to benchmark ID `retrieval_v2` and writes a new receipt path derived from that ID unless `--output` is supplied. Existing output files are never replaced. A receipt/corpus snapshot mismatch is rejected. The report records metric schema version 2, weak-label limitations, per-query relevant counts, SHA256 values for corpus manifest/tables, query file, index receipt/artifacts and relevant implementation files, and BM25 mode/cutoff/index configuration. The integration task must generate the new real-corpus artifact after restoration; this subtask's receipt tests use controlled temporary Parquet/index inputs.

The existing `retrieval_v1.json` remains historical evidence. Its legacy capped recall is not reinterpreted as standard recall. Existing MRR, nDCG and latency assertions are retained under an explicitly historical test name; a new controlled versioned-report regression tests current behavior. Historical artifact SHA256 remains `33c523d528aff22970c40f7bf253e88617a39d901a0ba6e687f0776a9da6b22c`.

Gradio is now a default dependency because default API import requires the one project demo. The empty `demo` extra remains as a backward-compatible installation alias. The Dockerfile copies `pipelines/` before installing the project wheel. Dependency version ranges were otherwise preserved.

## Frozen labels and metric limits

The current query file has 16 keyword/metadata-derived relevance sets. It is a weak-label regression dataset, not independent human relevance judgments. Its SHA256 is `fffeec843da264e398f6c3f3fe8e057cac2b35d2345a9d42eb4a4de50d46ed98`.

| Query | Relevant IDs | Query | Relevant IDs |
| --- | ---: | --- | ---: |
| q01 | 1011 | q09 | 112 |
| q02 | 1 | q10 | 215 |
| q03 | 179 | q11 | 272 |
| q04 | 12 | q12 | 46 |
| q05 | 62 | q13 | 33 |
| q06 | 67 | q14 | 231 |
| q07 | 138 | q15 | 4 |
| q08 | 15 | q16 | 320 |

Even a perfect ranker can reach only macro standard Recall@10 `0.29476803996285084` on these relevance sets: the mean of `min(10, relevant_count) / relevant_count`. A `0.60` standard Recall@10 gate is therefore impossible on this frozen set. This calculation describes label cardinality, not a fresh retrieval measurement.

## Commands and actual verification

All Python-dependent checks used the cached environment resolved by this prefix in the isolated worktree:

```powershell
& 'C:/Users/lanph/.local/bin/uv.exe' run --no-project --python 3.12 --with '.[demo,dev]' python
```

Each command's output was captured with `2>&1 | Tee-Object -FilePath <original task evidence>/<log>` and the native process exit code was propagated. PowerShell sometimes wraps normal uv stderr progress as `NativeCommandError`; actual pytest/build exit codes and results below determine status.

| Command after the prefix | Actual result | Evidence |
| --- | --- | --- |
| `-m pytest tests/unit/test_retrieval_metrics.py -q` before production edits | RED, 4 failed / 1 passed; incorrect recall and missing precision/zero-label counters | [metrics-red.log](metrics-red.log) |
| `-m pytest tests/eval/test_retrieval_benchmark.py -q` before production edits | RED, 2 failed / 1 passed; missing versioned CLI and absent index/corpus mismatch check | [metrics-receipts-red.log](metrics-receipts-red.log) |
| `-m pytest tests/unit/test_retrieval_metrics.py tests/eval/test_retrieval_benchmark.py -q` | GREEN, 8 passed, exit 0; repeated after final implementation cleanup | [metrics-final-green.log](metrics-final-green.log) |
| `-m pytest` | FAIL, 29 passed / 6 failed; names below | [metrics-full-suite.log](metrics-full-suite.log) |
| `-m mypy packages apps pipelines` | PASS, no issues in 75 source files, exit 0 | [metrics-typecheck.log](metrics-typecheck.log) |
| `-m ruff check pipelines/benchmark_retrieval tests/eval/test_retrieval_benchmark.py tests/unit/test_retrieval_metrics.py` | Initial UP017 warning on existing UTC spelling; corrected, then PASS, exit 0 | [initial output](metrics-lint.log), [final output](metrics-lint-green.log) |
| `scripts/check_secrets.py` using standalone `C:/Users/lanph/.local/bin/python3.12.exe` | PASS, zero secret leaks, exit 0 | [metrics-secret-check.log](metrics-secret-check.log) |
| `git diff --check -- pipelines/benchmark_retrieval tests/eval tests/unit/test_retrieval_metrics.py pyproject.toml infra/docker/Dockerfile.api` | PASS, no whitespace errors, exit 0 | Observed directly in the task terminal |

Package checks used the same uv invocation with additional `--with build --with poetry-core`, then `python <original task evidence>/verify_package_context.py`. The script runs `python -m build --wheel --no-isolation --outdir <temporary dist>` for the repository and for a temporary source context populated from the actual Dockerfile COPY instructions; it inspects wheel module membership and `Requires-Dist` metadata.

| Probe | Actual result | Evidence |
| --- | --- | --- |
| `verify_package_context.py --expect-broken` before package edits | Root wheel builds; Gradio absent from default requirements; copied Docker context fails because `pipelines` is missing. Expected RED assertions pass. | [package-red.log](package-red.log) |
| `verify_package_context.py` after package edits | Both wheels build; default metadata requires Gradio; expected API, pipeline and retrieval modules are included. Exit 0. | [package-green.log](package-green.log) |

This verifies the source-packaging failure without a Docker engine or an image pull. It does not claim a built/running Linux container, dependency resolution inside the base image, deployment, or a live provider call.

## Full-suite failures observed

| Test | Observed failure | Follow-up |
| --- | --- | --- |
| `tests/smoke/test_api_and_demo.py::test_api_endpoints_and_gradio_demo_mount_end_to_end` | Old default corpus `dim_creators.parquet` missing | Restore corpus and integrate current defaults; rerun smoke |
| `tests/unit/test_analytics_and_retrieval.py::test_niche_analytics_and_hybrid_retrieval_end_to_end` | Old corpus `dim_creators.parquet` missing | Restore data and update active artifact references |
| `tests/unit/test_incremental_absa_seeding.py::test_dual_sink_incremental_ingestion_and_trust_api` | Old corpus `fact_videos.parquet` missing | Restore data and update active artifact references |
| `tests/unit/test_secret_hygiene.py::test_original_data_directory_preserved_intact` | Historical `data/raw/` absent in the isolated worktree | Data recovery/integration |
| `tests/unit/test_taxonomy_and_corpus.py::test_built_gold_corpus_snapshot_integrity` | Old corpus `dim_creators.parquet` missing | Data recovery/integration |
| `tests/unit/test_snapshot_continuity.py::test_failed_build_releases_publication_lock_for_retry` | Second failed-build attempt encounters leftover publication lock | Parent snapshot implementation task; reported immediately |

The parent task owns those code/data domains and must report its later rerun separately. No failure was skipped or relabeled as a metric pass.

## CLI handoff

After the parent builds the restored snapshot and index, run:

```powershell
python -m pipelines.benchmark_retrieval `
  --corpus data/corpus/20261117_recovered_v1 `
  --index artifacts/indexes/bm25-v2 `
  --queries data/evaluation/v1/queries.jsonl `
  --benchmark-id retrieval_v2 `
  --output artifacts/benchmarks/retrieval_v2.json
```

Use the environment prefix above if `python` is not installed on PATH. Reruns require a new ID/output path. Source hashes describe the exact files at evaluation time; regenerate a new receipt if hashed evaluation/retrieval implementation changes.

## Workflow provenance and boundaries

Read actual installed Superpowers 7.0.1 instructions from `C:/Users/lanph/.codex/plugins/cache/openai-curated-remote/superpowers/7.0.1/skills/`:

- `using-superpowers/SKILL.md`: read at dispatch; its subagent-specific stop clause applies to this delegated worker. Parent task retains overall process ownership.
- `systematic-debugging/SKILL.md`: applied by inspecting the metric source, real service boundary, old artifact/test, default dependency/import profile and Docker COPY context; reproduced each defect before its fix.
- `test-driven-development/SKILL.md` and `test-driven-development/writing-good-tests.md`: applied to real-service, hand-derived metric cases and real temporary corpus/index receipt regressions; observed expected RED before implementation and GREEN afterward. The initial reference lookup under `references/` was absent; the actual sibling `writing-good-tests.md` was subsequently read.
- `verification-before-completion/SKILL.md`: read before final verification/handoff; full suite, focused tests, project mypy, scoped lint, secret scan and package probes were executed and inspected.

Also read the original repository AGENTS.md and the parent's preexisting task spec/plan before implementation. Existing user authorization and assigned scope covered these reversible fixes. No approval was requested, no other production domains were edited, no historical source or benchmark was rewritten, no subagent was spawned, and no commit, push, provider synthesis, crawl, Docker image pull, hosting deployment or spend occurred.

Changed production/test files: `pipelines/benchmark_retrieval/{__init__,__main__}.py`, `tests/unit/test_retrieval_metrics.py`, `tests/eval/test_retrieval_benchmark.py`, `pyproject.toml`, `infra/docker/Dockerfile.api`. [metrics-file-hashes.json](metrics-file-hashes.json) records handoff hashes. Supporting verification script: [verify_package_context.py](verify_package_context.py).
