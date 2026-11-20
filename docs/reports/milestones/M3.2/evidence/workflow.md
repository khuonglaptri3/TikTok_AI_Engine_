# M3.2 — Workflow Provenance & Execution Ledger

- **Date:** 2026-11-19 (Asia/Ho_Chi_Minh)
- **Task ID:** `M3.2`
- **Primary Owner:** Trần Đình Khương (`K`)
- **Peer Reviewer:** Nguyễn Việt Nguyên (`N`, completed & approved `2026-11-20`)
- **Spec:** [../superpowers/spec.md](../superpowers/spec.md)
- **Plan:** [../superpowers/plan.md](../superpowers/plan.md)

## Pre-Flight & Rulings
- Skills loaded: `using-superpowers`, `brainstorming` (*Architectural* path approved by `K`), `writing-plans`, `executing-plans`, `test-driven-development`, `verification-before-completion`.
- Ruling: `plan.md` Task 3 referred to `ingest_incremental_batch`; actual `M3.1` export in `pipelines.ingest_incremental_to_gold` is `ingest_incremental_batch_to_gold` — use `ingest_incremental_batch_to_gold` — cost if wrong: one import rename in test.

## Execution Log
- **Task 1:** complete ([red-task1-bounds-cutoff.log](red-task1-bounds-cutoff.log) -> [green-task1-bounds-cutoff.log](green-task1-bounds-cutoff.log), tests: `python3 -m pytest tests/unit/test_bounded_collector_worker.py -v` -> `2/2 passed`).
- **Task 2:** complete ([red-task2-retry-resume.log](red-task2-retry-resume.log) -> [green-task2-retry-resume.log](green-task2-retry-resume.log), tests: `python3 -m pytest tests/unit/test_bounded_collector_worker.py -v` -> `3/3 passed`).
- **Task 3:** complete ([red-task3-audio-cli.log](red-task3-audio-cli.log) -> [green-task3-audio-cli.log](green-task3-audio-cli.log), tests: `python3 -m pytest tests/unit/test_bounded_collector_worker.py -v` -> `6/6 passed`).
- **Task 4:** complete ([fixture-verification.log](fixture-verification.log), [m3_2_fixture_verification_receipt.json](m3_2_fixture_verification_receipt.json), [mypy-m3_2.log](mypy-m3_2.log) -> `0` mypy issues across 7 source files; `70,996`-ID historical protection + `M3.1` Gold round-trip `71,000` rows verified with `100%` base byte identity).

## Fresh-Context Code Review & Fix Pass (`9e4ee657-b174-4728-b339-8f3f0479c58a`)
- `Final: fixed C1 quoted/JSON/Cookie secret redaction & unchained TimeoutExpired` — `test_c1_quoted_json_and_cookie_header_secrets_redacted_and_timeout_not_chained` RED->GREEN ([red-final-review-fixes.log](red-final-review-fixes.log) -> [green-final-review-fixes.log](green-final-review-fixes.log)), suite `165/165`.
- `Final: fixed C2 atomic per-item videos_4m.jsonl persistence across mid-batch crash` — `test_c2_mid_batch_interruption_persists_atomic_jsonl_and_resumes_without_data_loss` RED->GREEN, suite `165/165`.
- `Final: fixed C3 bool/overflow timestamp isolation in _parse_iso_create_time` — `test_c3_malformed_bool_and_overflow_timestamps_isolated_per_item` RED->GREEN, suite `165/165`.
- `Final: fixed C4 flat-playlist null discovery timestamp & post-detail historical/cutoff skip gates` — `test_c4_flat_discovery_null_timestamp_and_post_detail_historical_or_window_gates` RED->GREEN, suite `165/165`.
- `Final: fixed I1/I2 resume window/protection filtering, stale mp3 cleanup & persisted_records_count` — `test_i1_i2_resume_filters_expired_prior_rows_cleans_stale_audio_and_tracks_persisted_counts` RED->GREEN, suite `165/165`.
- `Final: fixed I3 CLI live_provider fail-closed when base-corpus protected IDs are empty` — `test_i3_cli_live_provider_fails_closed_when_base_corpus_missing_protected_ids` RED->GREEN, suite `165/165`.
- `Final: minor (deferred): Preserve discovery candidate ordering rather than checkpoint-first ordering in videos_4m.jsonl when a middle item fails on Run 1 and succeeds on resume=True (unique video_id set and M3.1 ingestion output are unaffected).`

## Final Verification Receipts
- `python3 -m pytest tests/unit/test_bounded_collector_worker.py -v` -> `EXIT=0`, `12 passed in 1.36s` ([green-final-review-fixes.log](green-final-review-fixes.log))
- `python3 -m mypy pipelines/crawl_incremental tests/unit/test_bounded_collector_worker.py --follow-imports=silent` -> `EXIT=0`, `Success: no issues found in 7 source files` ([mypy-m3_2.log](mypy-m3_2.log))
- `python3 docs/reports/milestones/M3.2/evidence/run_m3_2_fixture_verification.py` -> `EXIT=0`, `70,996` historical IDs protected, `base_snapshot_byte_identical=true`, `M3.1` round-trip `71,000` rows ([m3_2_fixture_verification_receipt.json](m3_2_fixture_verification_receipt.json))
- `python3 -m pytest -v` -> `EXIT=0`, `177 passed in 31.53s` ([pytest-full-m3_2-linux.log](pytest-full-m3_2-linux.log))
- `python3 scripts/check_secrets.py` -> `EXIT=0`, `PASS: Zero secret leaks detected across workspace.` ([check-secrets-m3_2.log](check-secrets-m3_2.log))

## Independent Peer Review Sign-Off (`N`, `2026-11-20`)
- Contributor `N` audited `worker.py`, `providers.py`, `crawler_service.py`, `models.py`, `__main__.py`, and `test_bounded_collector_worker.py`, and reproduced `pytest` (`12 passed in 12.62s`), `run_m3_2_fixture_verification.py` (`70,996` protected IDs, `base_snapshot_byte_identical=true`, `71,000`-row round-trip), `ruff check`, `mypy` (`7` files), and `scripts/check_secrets.py` (`0` leaks).
- Zero blocking findings; recorded [nguyen-peer-review.md](nguyen-peer-review.md) and [nguyen_signoff_receipt.json](nguyen_signoff_receipt.json), transitioning `M3.2` to `COMPLETE`.
