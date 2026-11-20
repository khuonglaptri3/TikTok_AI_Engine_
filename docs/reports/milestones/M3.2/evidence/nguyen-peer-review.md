# M3.2 — Independent Peer Review Report (`N`)

- **Task ID:** `M3.2` (Actual Bounded Collector Worker)
- **Primary Owner:** Trần Đình Khương (`K`)
- **Peer Reviewer:** Nguyễn Việt Nguyên (`N`)
- **Review Date:** `2026-11-20T09:03:25+07:00` (Asia/Ho_Chi_Minh)
- **Evaluated Revision:** `main` @ `1531174eb234554c7edae20f0e5ba86cd51bbf02`
- **Verdict:** **`APPROVED` (Zero Critical / Important blocking issues)**

## 1. Independent Code Inspection Summary (`pipelines/crawl_incremental/`)

1. **120-Day Rolling Cutoff & `70,996` Historical ID Protection ([worker.py](../../../../../pipelines/crawl_incremental/worker.py), [crawler_service.py](../../../../../pipelines/crawl_incremental/crawler_service.py)):**
   - Pre-detail checks skip protected historical IDs and out-of-window timestamps (`compute_cutoff_utc`, `is_within_rolling_window`) before calling `fetch_video_detail`.
   - Post-detail gates re-check canonical redirected video IDs and post-detail `create_time` (closing `--flat-playlist` null discovery timestamps).
   - Malformed timestamps (`bool`, non-finite floats, invalid strings) fail isolated per item as `invalid_create_time` without crashing the batch.
2. **Failure Isolation, Capped Retries & Credential Redaction ([worker.py](../../../../../pipelines/crawl_incremental/worker.py), [providers.py](../../../../../pipelines/crawl_incremental/providers.py)):**
   - Transient failures (`TransientCollectorError`) retry up to `1 + max_retries` times (`default = 3` total attempts); permanent/validation failures break immediately and record per-item `failed` status.
   - `_sanitize_reason` redacts quoted JSON and unquoted `ms_token`, `msToken`, `cookie`, `sessionid`, and `csrf_token` values prior to `redact_secrets` before writing `collector_checkpoint.json` or `crawl_manifest.json`.
   - Live collection fails closed with `LiveNetworkDisabledError` unless `--allow-live-network`, a non-empty `MS_TOKEN`, and a populated `--base-corpus` historical ID set are all present.
3. **Crash-Safe Atomic Persistence & Resume ([worker.py](../../../../../pipelines/crawl_incremental/worker.py)):**
   - `videos_4m.jsonl` is written atomically via `.tmp` + `os.replace` before updating `collector_checkpoint.json` after every succeeded item.
   - `resume=True` reloads prior records intersecting `checkpoint.succeeded_ids`, re-filters against current `protected_ids` and `cutoff_utc`, strips missing `.mp3` `audio_path` pointers, and preserves `collected_comments_total` / `accumulated_audio_min` counters before continuing so `max_comments_total` (`1,000`) and `max_audio_minutes` (`60.0`) ceilings cannot be exceeded across resume boundaries.
4. **Synthetic Fixture Separation & 64 kbps Audio Receipts ([models.py](../../../../../pipelines/crawl_incremental/models.py), [__main__.py](../../../../../pipelines/crawl_incremental/__main__.py)):**
   - `OfflineFixtureCollectorProvider` sets `is_synthetic_fixture=True` and `source_mode="offline_fixture"`, visibly separated from `live_provider`.
   - Audio receipts track `converted_64k_mp3` (`audio_sha256`, `audio_bytes`, `target_bitrate_kbps=64`), `unavailable`, `failed`, and `skipped_audio_ceiling`, leaving missing modalities as `None` / `[]`.

## 2. Independent Verification Reproduced on `main` (`1531174e`)

- `.venv/bin/python -m pytest tests/unit/test_bounded_collector_worker.py -v` -> **`12 passed in 12.62s`**
- `.venv/bin/python docs/reports/milestones/M3.2/evidence/run_m3_2_fixture_verification.py` -> **PASS** (`70,996` protected IDs, `base_snapshot_byte_identical = true`, `Run 1`: `12` requested / `3` succeeded / `2` failed / `7` skipped / `2` audio converted; `Run 2 resume`: `1` succeeded / `1` failed / `10` skipped / `4` persisted rows; `M3.1` Gold round-trip = `71,000` videos across `5` tables)
- `.venv/bin/python -m ruff check pipelines/crawl_incremental tests/unit/test_bounded_collector_worker.py docs/reports/milestones/M3.2/evidence/run_m3_2_fixture_verification.py` -> **`All checks passed!`**
- `.venv/bin/python -m mypy pipelines/crawl_incremental tests/unit/test_bounded_collector_worker.py --follow-imports=silent` -> **`Success: no issues found in 7 source files`**
- `python3 scripts/check_secrets.py` -> **`PASS: Zero secret leaks detected across workspace.`**

## 3. Non-Blocking Notes Carried to `M3.3`

1. `LiveTikTokCollectorProvider` host-network behavior (`yt-dlp` extractor yield and TikTok rate limits) is verified only via unit mocks and fail-closed guards in `M3.2`; live acquisition limits will be measured directly in bounded pilot `M3.3`.
2. During live discovery, `discover_candidates` passes `--playlist-end max_candidate_videos` (`50`) per creator before `worker.py` caps `unique_candidates` at `max_candidate_videos` (`50`), which ensures enough recent videos even if an early creator has older content while keeping detail/audio/comment fetches bounded at `50`.
