# M1.2 — Superpowers Workflow Provenance

- **Date:** 2026-11-18 (Asia/Saigon)
- **Task ID:** `M1.2`
- **Primary Owner:** Trần Đình Khương (`K`)
- **Peer Reviewer:** Nguyễn Việt Nguyên (`N`, pending independent receipt/build verification)
- **Skills read and applied:** `using-superpowers`, `brainstorming`, `writing-plans`, `executing-plans`, `test-driven-development`, `verification-before-completion`
- **Authorization provenance:** Explicit user approval (`"Yes do all this task"` / `"Tiep tuc di"`) to build the new immutable Gold snapshot incorporating `M1.1`'s taxonomy fixes while preserving `data/corpus/20261117_recovered_v1` untouched.

## Process & Key Decisions
1. **Strict TDD (`RED -> GREEN`) for Parent Lineage:** Added `test_historical_builder_records_verified_parent_provenance` and `test_historical_builder_fails_closed_on_corrupted_parent_snapshot` to `tests/unit/test_snapshot_continuity.py`, observed RED failure ([red-m1_2-tests.log](red-m1_2-tests.log)), implemented `parent_corpus_dir` / `--parent-corpus` in `pipelines/build_gold_corpus/`, corrected synthetic raw column names (`statsV2.playCount`, `user.id`) in the test fixture, and verified `20/20` GREEN ([green-m1_2-tests.log](green-m1_2-tests.log)).
2. **Preserve Default Runtime Compatibility (`20261117_recovered_v1` Retained):** Published the new snapshot at a fresh ID `data/corpus/20261118_taxonomy_fix_v1` (`manifest.json` SHA256 `49f23739f9e2ea8f1f66fe1b299fe636c19965c99fcadf2bdd6eef7dc18c27de`) without mutating `data/corpus/20261117_recovered_v1` or `AppSettings.corpus_dir` defaults, keeping `retrieval_v2.json` and existing regression suites 100% reproducible until `M2.2` builds the next paired BM25 index.

## Verification Receipts
- TDD RED: `pytest tests/unit/test_snapshot_continuity.py -v` -> `2 failed, 18 passed` ([red-m1_2-tests.log](red-m1_2-tests.log))
- TDD GREEN: `pytest tests/unit/test_snapshot_continuity.py -v` -> `20 passed in 13.25s` ([green-m1_2-tests.log](green-m1_2-tests.log))
- Snapshot build (`python -m pipelines.build_gold_corpus --output data/corpus/20261118_taxonomy_fix_v1 --parent-corpus data/corpus/20261117_recovered_v1`): `EXIT=0` in `637.32s` ([gold-build.log](gold-build.log), [m1.2-build-receipt.json](m1.2-build-receipt.json))
- Workspace secret scan (`python scripts/check_secrets.py`): `EXIT=0` (`Zero secret leaks detected`).
