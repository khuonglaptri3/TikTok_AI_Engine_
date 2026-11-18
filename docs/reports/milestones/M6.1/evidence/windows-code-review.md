# Read-only review of the Windows resource repair

- Date: 2026-11-18 (Asia/Saigon).
- Reviewer: AI subagent `/root/windows_resource_review`, requested under Superpowers `requesting-code-review` 7.0.1. This is not a human K/N milestone approval.
- Scope: new shared peak-memory helper/test, both M6.1 consumer changes, and equivalent UTC aliases in the two crawl helpers.
- Assessment: **No Critical, Important or Minor code findings. Ready from the code-review perspective once final checks pass on the committed source.**

The review verified Windows `PROCESS_MEMORY_COUNTERS` field order and pointer-sized fields, the process handle/signatures/structure size/error behavior, and byte conversion against the [Microsoft structure documentation](https://learn.microsoft.com/en-us/windows/win32/api/psapi/ns-psapi-process_memory_counters) and [GetProcessMemoryInfo documentation](https://learn.microsoft.com/en-us/windows/win32/api/psapi/nf-psapi-getprocessmemoryinfo). Pipeline integrations retain `peak_rss_mb` while declaring MiB and process-lifetime scope. The 8192 MiB resource threshold remains consistent with8 GiB.

Independent read-only verification ran `PYTHONDONTWRITEBYTECODE=1; python -B -m pytest -q -p no:cacheprovider tests/unit/test_resource_measurements.py`: all8 cases passed, including a native Windows measurement. No files, index, HEAD or branch state were modified by the reviewer.

Reviewed source SHA256:

| File | SHA256 |
| --- | --- |
| `packages/common/resources.py` | `13fcf66e3128dc37c1df8ed74bac2113667b3f211cbfccb6cfc6e6e8d7052cbe` |
| `tests/unit/test_resource_measurements.py` | `644e73406cab472b948910e2bcf87fbaafedc93bdee848cd8c5220e766bffa86` |
| `pipelines/build_dense_sparse_index/dense.py` | `3c4abf35526533f812e8b9f4c5dae4df3283034e53de52a918485988d7d22319` |
| `pipelines/benchmark_retrieval/dense_hybrid_pilot.py` | `ead11bbb23750b6ec3a60bbb72431c7baa7bdb0415a493e45b974469789d99ed` |

Considered boundaries: native Linux/macOS execution was unavailable on the Windows review host; Linux conversion uses an OS-boundary test double. Full-suite/packaging/runtime/publication checks belong to the executor. Sampling placement is unchanged, so this is not a new complete build-stage profiling methodology. Scientific M6.1 acceptance and formal G0 approval remain separate.
