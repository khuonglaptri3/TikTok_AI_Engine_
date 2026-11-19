# M3.2 Implementation Plan — Bounded Incremental Collector Worker

> **For agentic workers:** REQUIRED SUB-SKILL: Use `test-driven-development` (`RED -> GREEN -> REFACTOR`) and `verification-before-completion` before making any completion claim.

**Goal:** Build and verify the invoked, bounded discovery/metadata/audio/comment collector worker (`pipelines/crawl_incremental/`) with 120-day `as_of` cutoff, `70,996` historical ID protection, capped retries, checkpoint resume, `requested/succeeded/failed/skipped` idempotent manifests, and 64 kbps `.mp3` conversion receipts while keeping offline fixtures visibly separate from live network collection.

**Architecture:** Protocol-driven `BoundedIncrementalCollector` (`pipelines/crawl_incremental/worker.py`) consuming `CollectorProvider` + `AudioConverter` protocols (`pipelines/crawl_incremental/providers.py`), backed by `OfflineFixtureCollectorProvider` (0 network calls, `is_synthetic_fixture=True`) and fail-closed `LiveTikTokCollectorProvider`, wired into `pipelines/crawl_incremental/__main__.py` while preserving all existing helpers in `crawler_service.py` and downstream `M3.1` (`videos_4m.jsonl`) compatibility.

**Tech Stack:** Python 3.11, Pydantic v2 (`packages.data_contracts.multimodal`), Pandas/PyArrow (`fact_videos.parquet` ID set), `pytest`, `mypy`.

---

## Global Constraints & Review Focus

- **Zero Live Network / Zero Historical Recrawl:** Do NOT invoke live TikTok / `yt-dlp` network requests during `M3.2`. `LiveTikTokCollectorProvider` must fail closed unless `allow_live_network=True` is explicitly set (`M3.3` follows only after Gate `G2` and `N`'s peer review).
- **Historical Byte Preservation:** Never mutate `data/corpus/20261117_recovered_v1` or `data/corpus/20261118_taxonomy_fix_v1`. Default `--base-corpus` to `data/corpus/20261118_taxonomy_fix_v1` (`70,996` unique historical IDs).
- **Secret Hygiene:** Redact credentials (`MS_TOKEN`, cookies, API keys) from all per-item failure strings, checkpoints, manifests, and CLI output; verify with `python3 scripts/check_secrets.py`.
- **Missing Modalities Stay Missing:** When audio extraction or comments are unavailable, keep `audio_path=None` / `comments=[]` rather than fabricating synthetic media or comments.
- **Review Focus for `N`:**
  1. `120`-day `as_of_utc` boundary exactness (`cutoff - 1s` skipped vs `cutoff` accepted) and pre-fetch skip of every historical ID (`0` provider detail/audio/comment calls on historical IDs).
  2. Retry cap (`attempts <= 1 + max_retries`), per-item failure isolation, and idempotent resume (`videos_4m.jsonl` and `crawl_manifest.json` never duplicate rows across interrupted/replayed runs).
  3. Visible separation of `source_mode="offline_fixture"` (`is_synthetic_fixture=True`) vs `source_mode="live_provider"` (`is_synthetic_fixture=False`).

---

## File Map

- **Create:** `pipelines/crawl_incremental/models.py` — Typed Pydantic v2 models (`CollectorBounds`, `AudioConversionReceipt`, `CollectorItemReceipt`, `CollectorCheckpoint`, `CrawlManifest`).
- **Create:** `pipelines/crawl_incremental/providers.py` — `CollectorProvider` & `AudioConverter` protocols, `TransientCollectorError`, `LiveNetworkDisabledError`, `OfflineFixtureCollectorProvider`, `OfflineFixtureAudioConverter`, and fail-closed `LiveTikTokCollectorProvider` + `YtDlpAudioConverter64k`.
- **Create:** `pipelines/crawl_incremental/worker.py` — `BoundedIncrementalCollector` implementing bounded discovery, historical & 120-day pre-fetch filtering, capped retries, secret-redacted per-item error capture, atomic checkpoint resume, 64 kbps `.mp3` receipt tracking, and idempotent `videos_4m.jsonl` + `crawl_manifest.json` publication.
- **Modify:** `pipelines/crawl_incremental/__main__.py` — Expose `--source {offline_fixture,live_provider}`, `--fixture-path`, `--as-of`, `--allow-live-network`, `--resume`, and bounded ceiling flags while keeping `--seed-demo-batch` backward-compatible (emitting `crawl_manifest.json` with `is_synthetic_fixture=True`).
- **Modify:** `pipelines/crawl_incremental/__init__.py` — Export worker, models, and provider interfaces cleanly.
- **Create:** `tests/unit/test_bounded_collector_worker.py` — Comprehensive TDD unit & CLI/ingest-compatibility suite.
- **Create:** `docs/reports/milestones/M3.2/evidence/run_m3_2_fixture_verification.py` — End-to-end offline fixture + resume + real `70,996`-ID `20261118_taxonomy_fix_v1` skip + `M3.1` Dual-Sink compatibility verification probe.

---

## Tasks

### Task 1: TDD Cycle 1 — Cutoff, Historical ID Protection & Discovery Ceilings
- **Files:** `tests/unit/test_bounded_collector_worker.py`, `pipelines/crawl_incremental/models.py`, `pipelines/crawl_incremental/providers.py`, `pipelines/crawl_incremental/worker.py`
- [ ] **Step 1 (RED):** Write failing tests in `tests/unit/test_bounded_collector_worker.py` asserting:
  - `as_of_utc` enforces exact `120`-day cutoff (`cutoff - 1s` -> `skipped` with `outside_120d_rolling_window`; `cutoff` -> `succeeded`).
  - Historical `video_id`s are skipped *before* `fetch_video_detail`, `extract_mp3_64k`, or `fetch_comments` is ever invoked (`0` detail calls on historical IDs).
  - Discovery and collection stop at `max_creators`, `max_candidate_videos`, and `max_succeeded_videos` (no unlimited discovery), with `requested_count == succeeded_count + failed_count + skipped_count`.
- [ ] **Step 2:** Run `python3 -m pytest tests/unit/test_bounded_collector_worker.py -v` and record RED failure log (`docs/reports/milestones/M3.2/evidence/red-task1-bounds-cutoff.log`).
- [ ] **Step 3 (GREEN):** Implement `models.py`, `providers.py`, and core `BoundedIncrementalCollector` in `worker.py`.
- [ ] **Step 4:** Re-run `python3 -m pytest tests/unit/test_bounded_collector_worker.py -v` and confirm PASS (`green-task1-bounds-cutoff.log`).

### Task 2: TDD Cycle 2 — Capped Retries, Per-Item Failures, Secret Redaction & Resume Idempotency
- **Files:** `tests/unit/test_bounded_collector_worker.py`, `pipelines/crawl_incremental/worker.py`
- [ ] **Step 1 (RED):** Add failing tests asserting:
  - Transient errors retry at most `max_retries` times (`attempts == 1 + max_retries` when exhausted -> `status="failed"`), while succeeding on retry `<= max_retries` records exact `attempts` and `status="succeeded"`.
  - Credentials (`AIza...`, `ms_token=...`, `Bearer ...`) inside provider exceptions are redacted in `crawl_manifest.json` and `collector_checkpoint.json`.
  - Resuming on an existing `output_dir` skips already-succeeded items (`already_succeeded_in_checkpoint`), retries previously `failed` items when `resume=True`, preserves deterministic row order/uniqueness in `videos_4m.jsonl`, and produces an idempotent manifest on replay.
- [ ] **Step 2:** Run `pytest` and record RED log (`red-task2-retry-resume.log`).
- [ ] **Step 3 (GREEN):** Implement retry loop, credential redaction, and atomic `collector_checkpoint.json` load/merge/save in `worker.py`.
- [ ] **Step 4:** Re-run `pytest` and confirm PASS (`green-task2-retry-resume.log`).

### Task 3: TDD Cycle 3 — 64 kbps Audio Receipts, Missing Modalities, Live Fail-Closed Gate & CLI Integration
- **Files:** `tests/unit/test_bounded_collector_worker.py`, `pipelines/crawl_incremental/providers.py`, `pipelines/crawl_incremental/worker.py`, `pipelines/crawl_incremental/__main__.py`, `pipelines/crawl_incremental/__init__.py`
- [ ] **Step 1 (RED):** Add failing tests asserting:
  - `64 kbps` `.mp3` conversion records `status="converted_64k_mp3"`, non-zero `audio_bytes`, `64`-hex `audio_sha256`, `target_bitrate_kbps=64`, and relative `audio_path`; missing/unavailable audio or `max_audio_minutes` ceiling leaves `audio_path=None` with explicit receipt status (`unavailable` / `skipped_audio_ceiling`) while still publishing valid metadata + comments.
  - `LiveTikTokCollectorProvider` / `--source live_provider` without `--allow-live-network` (or missing `MS_TOKEN` when required) fails closed with `LiveNetworkDisabledError` and `0` subprocess/network calls.
  - CLI `--source offline_fixture --fixture-path ...` produces `videos_4m.jsonl` + `crawl_manifest.json` (`source_mode="offline_fixture"`, `is_synthetic_fixture=True`) that ingests cleanly through `M3.1`'s `ingest_incremental_batch`!
- [ ] **Step 2:** Run `pytest` and record RED log (`red-task3-audio-cli.log`).
- [ ] **Step 3 (GREEN):** Implement audio receipt handling, `LiveTikTokCollectorProvider` fail-closed guard, CLI flags in `__main__.py`, and exports in `__init__.py`.
- [ ] **Step 4:** Re-run `pytest` and confirm PASS (`green-task3-audio-cli.log`).

### Task 4: Real `70,996`-ID Protection Probe, Full Verification & `M3.2` Report
- **Files:** `docs/reports/milestones/M3.2/evidence/run_m3_2_fixture_verification.py`, `docs/reports/milestones/M3.2/README.md`, `docs/reports/milestones/M3.2/evidence/workflow.md`, `docs/reports/milestones/README.md`
- [ ] **Step 1:** Run `run_m3_2_fixture_verification.py` against the real `70,996`-video `data/corpus/20261118_taxonomy_fix_v1` snapshot (testing real historical ID collisions, 120-day cutoff, transient retry, interrupted resume, 64 kbps `.mp3` receipt, missing-modality preservation, `M3.1` Dual-Sink ingest round-trip, and `100%` SHA256 byte identity of `20261118_taxonomy_fix_v1`).
- [ ] **Step 2:** Run `python3 -m mypy pipelines/crawl_incremental tests/unit/test_bounded_collector_worker.py`, full `python3 -m pytest -v`, and `python3 scripts/check_secrets.py`.
- [ ] **Step 3:** Author `docs/reports/milestones/M3.2/README.md` + `evidence/workflow.md` in English and update `docs/reports/milestones/README.md` (`Status: IN_PROGRESS` pending `N`'s peer review before `M3.3`).
