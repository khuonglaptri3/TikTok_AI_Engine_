# M3.2 — Actual Bounded Collector Worker

- Status: COMPLETE (`K`'s bounded collector worker, 12-test TDD suite, fresh-context code review fix pass, offline verification over `70,996` historical IDs + `M3.1` Gold round-trip, AND `N`'s independent peer review of cutoff, failure, and resume behavior complete on `2026-11-20`)
- Execution date: 2026-11-19 to 2026-11-20 (Asia/Ho_Chi_Minh)
- Requirement source: [TikTok_AI_Engine_Milestone.md](../../../planning/TikTok_AI_Engine_Milestone.md) (`M3.2`)
- Repository version: `main` @ `1531174e` + `N` peer review sign-off
- Specification: [spec.md](superpowers/spec.md)
- Execution plan: [plan.md](superpowers/plan.md)

## Conclusion

Implemented and verified the protocol-driven bounded incremental collector worker in [pipelines/crawl_incremental/](../../../../pipelines/crawl_incremental/) (`models.py`, `providers.py`, `worker.py`, `crawler_service.py`, `__main__.py`). All `12/12` dedicated worker/CLI tests, `177/177` workspace pytest tests, `7`-file `mypy` static type checks, `scripts/check_secrets.py`, and an end-to-end offline fixture probe against the real `70,996`-video `data/corpus/20261118_taxonomy_fix_v1` Gold snapshot pass with `100%` byte preservation of historical files and zero live TikTok network requests. Authored fixture runs (`source_mode="offline_fixture"`, `is_synthetic_fixture=True`) remain visibly separate from fail-closed live collection (`source_mode="live_provider"`, `is_synthetic_fixture=False`). On `2026-11-20T09:03+07:00`, contributor Nguyễn Việt Nguyên (`N`) completed independent peer review of cutoff, failure/retry/redaction, and resume behavior ([nguyen-peer-review.md](evidence/nguyen-peer-review.md), [nguyen_signoff_receipt.json](evidence/nguyen_signoff_receipt.json)), reproducing all `12/12` tests, the `70,996`-ID protection probe, `ruff`, `7`-file `mypy`, and `scripts/check_secrets.py` with zero blocking findings. Task `M3.2` is now **`COMPLETE`**, unlocking bounded live pilot `M3.3`.

## Work performed

- **Typed collector bounds, receipts, checkpoint, and manifest contracts ([models.py](../../../../pipelines/crawl_incremental/models.py)):** Defined `CollectorBounds` (`120`-day rolling window, `max_creators=5`, `max_candidate_videos=50`, `max_succeeded_videos=30`, `max_audio_minutes=60.0`, `max_comments_total=1000`, `max_comments_per_video=50`, `max_retries=2`, `session_deadline_seconds=7200.0`), `AudioConversionReceipt` (`64` kbps `.mp3` byte/SHA256 provenance), `CollectorItemReceipt`, `CollectorCheckpoint`, and `CrawlManifest` (`requested`, `succeeded`, `failed`, `skipped`, and `persisted_records_count`).
- **Separated offline fixture vs. fail-closed live provider adapters ([providers.py](../../../../pipelines/crawl_incremental/providers.py), [crawler_service.py](../../../../pipelines/crawl_incremental/crawler_service.py)):** Implemented `OfflineFixtureCollectorProvider` + `OfflineFixtureAudioConverter` (`0` network/subprocess calls, `is_synthetic_fixture=True`) alongside `LiveTikTokCollectorProvider` + `YtDlpAudioConverter64k`, which fail closed with `LiveNetworkDisabledError` unless `--allow-live-network`, a non-empty `MS_TOKEN`, and a populated `--base-corpus` historical ID set are all present. Hardened `write_incremental_batch` with atomic `.tmp` replacement and `download_audio_mp3_64k` with `--force-overwrites`.
- **Crash-safe bounded worker with post-detail gates & secret redaction ([worker.py](../../../../pipelines/crawl_incremental/worker.py), [__main__.py](../../../../pipelines/crawl_incremental/__main__.py)):** Enforced `120`-day `as_of_utc` cutoffs and `70,996`-ID historical skipping both pre-fetch and post-detail (handling `--flat-playlist` null discovery timestamps and canonical redirected IDs), capped transient retries (`<= 1 + max_retries`), redacted quoted/unquoted/Cookie credentials (`ms_token`, `msToken`, `sessionid`, `Bearer`, API keys), persisted `videos_4m.jsonl` and `collector_checkpoint.json` atomically after every item, and preserved missing modalities (`audio_path=None`, `comments=[]`) honestly.
- **Fresh-context code review & real-snapshot `M3.1` round-trip ([run_m3_2_fixture_verification.py](evidence/run_m3_2_fixture_verification.py)):** Dispatched an independent code-review subagent, fixed all 7 Critical/Important findings via `RED -> GREEN` regressions (`C1–C4`, `I1–I3`), and verified an offline fixture + outage-resume batch directly against `20261118_taxonomy_fix_v1` (`70,996` protected IDs -> `71,000`-row temporary 5-table Gold round-trip with `0` base bytes mutated).

## Outputs

| File | Purpose |
| --- | --- |
| [workflow.md](evidence/workflow.md), [nguyen-peer-review.md](evidence/nguyen-peer-review.md), [nguyen_signoff_receipt.json](evidence/nguyen_signoff_receipt.json) | Superpowers execution ledger and `N`'s peer review + `2026-11-20` sign-off receipt |
| [run_m3_2_fixture_verification.py](evidence/run_m3_2_fixture_verification.py) | End-to-end offline fixture + resume + `70,996`-ID protection + `M3.1` Gold round-trip probe |
| [m3_2_fixture_verification_receipt.json](evidence/m3_2_fixture_verification_receipt.json) | Machine-readable receipt proving `70,996` protected IDs, SHA256 preservation, and `71,000`-row round-trip |
| [red-task1-bounds-cutoff.log](evidence/red-task1-bounds-cutoff.log), [green-task1-bounds-cutoff.log](evidence/green-task1-bounds-cutoff.log) | Task 1 TDD RED/GREEN logs (120d boundary, historical skip, ceilings) |
| [red-task2-retry-resume.log](evidence/red-task2-retry-resume.log), [green-task2-retry-resume.log](evidence/green-task2-retry-resume.log) | Task 2 TDD RED/GREEN logs (capped retries, secret redaction, resume) |
| [red-task3-audio-cli.log](evidence/red-task3-audio-cli.log), [green-task3-audio-cli.log](evidence/green-task3-audio-cli.log) | Task 3 TDD RED/GREEN logs (64 kbps receipts, fail-closed live gate, CLI + `M3.1` ingest) |
| [red-final-review-fixes.log](evidence/red-final-review-fixes.log), [green-final-review-fixes.log](evidence/green-final-review-fixes.log) | Code-review fix pass TDD RED (`6 failed`) -> GREEN (`12 passed in 1.36s`) |
| [mypy-m3_2.log](evidence/mypy-m3_2.log) | Static type check over `pipelines/crawl_incremental` and worker unit tests (`0` issues in `7` files) |
| [pytest-full-m3_2-linux.log](evidence/pytest-full-m3_2-linux.log) | Full workspace pytest run on rebased branch (`177 passed in 31.53s`) |
| [check-secrets-m3_2.log](evidence/check-secrets-m3_2.log) | Secret hygiene scan (`0` leaks) |

## Verification

| Check | Result | Scope / evidence |
| --- | --- | --- |
| `python3 -m pytest tests/unit/test_bounded_collector_worker.py -v` | PASS (`12 passed in 1.36s`) | Cutoff boundaries, historical skip, ceilings, retry cap, quoted/Cookie redaction, crash-safe resume, 64k audio receipts, CLI fail-closed gates; [green-final-review-fixes.log](evidence/green-final-review-fixes.log) |
| `python3 docs/reports/milestones/M3.2/evidence/run_m3_2_fixture_verification.py` | PASS (`70,996` protected IDs; `100%` base SHA256 identity) | Offline fixture + resume + `M3.1` Dual-Sink round-trip (`71,000` rows across `5` tables); [m3_2_fixture_verification_receipt.json](evidence/m3_2_fixture_verification_receipt.json) |
| `python3 -m mypy pipelines/crawl_incremental tests/unit/test_bounded_collector_worker.py --follow-imports=silent` | PASS (`0` issues in `7` files) | Strict static typing on collector modules and unit tests; [mypy-m3_2.log](evidence/mypy-m3_2.log) |
| `python3 -m pytest -v` | PASS (`177 passed in 31.53s`) | Full workspace test suite on rebased Linux branch; [pytest-full-m3_2-linux.log](evidence/pytest-full-m3_2-linux.log) |
| `python3 scripts/check_secrets.py` | PASS (`0` leaks) | Workspace secret scan; [check-secrets-m3_2.log](evidence/check-secrets-m3_2.log) |

## Open issues

| Issue | Impact | Follow-up / responsible task |
| --- | --- | --- |
| Live TikTok host-network acquisition is intentionally not exercised in `M3.2` | Offline fixture receipts prove worker logic, not live TikTok rate-limit or `yt-dlp` extractor yield | Capped live pilot (`<= 5` creators, `<= 50` candidates, `<= 30` videos) runs in `M3.3` (`G2 = PASS` and `M3.2 = COMPLETE`) |

## Acceptance and handoff

| Task criterion | Result | Evidence |
| --- | --- | --- |
| Invoked discovery/metadata/audio/comment worker with resume, capped retries, per-item failures, idempotent manifests | Met | [worker.py](../../../../pipelines/crawl_incremental/worker.py), [test_bounded_collector_worker.py](../../../../tests/unit/test_bounded_collector_worker.py) (`12 passed`) |
| Authored fixture mode stays visibly separate (`is_synthetic_fixture=True`) & zero historical recrawl / unlimited discovery | Met | [providers.py](../../../../pipelines/crawl_incremental/providers.py), [__main__.py](../../../../pipelines/crawl_incremental/__main__.py), [m3_2_fixture_verification_receipt.json](evidence/m3_2_fixture_verification_receipt.json) |
| `as_of` / cutoff tests enforce `120`-day window and skip every historical ID (`70,996` IDs) | Met | [test_bounded_collector_worker.py](../../../../tests/unit/test_bounded_collector_worker.py), [m3_2_fixture_verification_receipt.json](evidence/m3_2_fixture_verification_receipt.json) |
| Manifests distinguish `requested / succeeded / failed / skipped` and record `64 kbps` `.mp3` conversion where available | Met | [models.py](../../../../pipelines/crawl_incremental/models.py), [green-final-review-fixes.log](evidence/green-final-review-fixes.log) |
| Reciprocal peer review of cutoff, failure, and resume behavior by `N` before network pilot | Met (`APPROVED`, `0` blocking issues) | [nguyen-peer-review.md](evidence/nguyen-peer-review.md), [nguyen_signoff_receipt.json](evidence/nguyen_signoff_receipt.json) |

Final task status: **`COMPLETE`** (`K`'s bounded collector implementation + `N`'s independent peer review and verification complete on `main`; ready to run capped live pilot `M3.3` with `G2 = PASS`).
