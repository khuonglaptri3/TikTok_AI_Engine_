# M3.2 Specification — Actual Bounded Collector Worker (`pipelines/crawl_incremental/`)

- **Task ID:** `M3.2`
- **Primary Owner:** Trần Đình Khương (`K`)
- **Peer Reviewer:** Nguyễn Việt Nguyên (`N`)
- **Date:** `2026-11-19` (`Asia/Ho_Chi_Minh`)
- **Requirement Source:** [TikTok_AI_Engine_Milestone.md](../../../../planning/TikTok_AI_Engine_Milestone.md) (`M3.2`)
- **Dependencies:** `M0.G` (`COMPLETE`), `M3.1` (`COMPLETE`)

---

## 1. Objective & Scope

Implement an invoked, bounded incremental discovery, metadata, 64 kbps `.mp3` audio, and comment collector worker in `pipelines/crawl_incremental/` that feeds `M3.1`'s verified `RawIncrementalVideoRecord` (`videos_4m.jsonl`) Dual-Sink ingestion contract while keeping authored offline fixture execution visibly separate from live provider acquisition.

### In Scope (`M3.2`)
1. **Protocol-driven `BoundedIncrementalCollector` worker (`pipelines/crawl_incremental/worker.py`):**
   - Pluggable `CollectorProvider` interface (`discover_candidates`, `fetch_video_detail`, `fetch_comments`) plus `AudioConverter` interface (`extract_mp3_64k`).
   - Two explicitly separated implementations:
     - `OfflineFixtureCollectorProvider`: reads deterministic local JSON/JSONL candidate fixtures (`is_synthetic_fixture = True`) for offline verification with `0` network calls.
     - `LiveTikTokCollectorProvider`: bounded host-network adapter (`yt-dlp` discovery/metadata/64 kbps `.mp3` + bounded comment fetch) that fails closed unless both `allow_live_network=True` and a non-empty `MS_TOKEN` (where required) are explicitly supplied.
2. **Strict `120`-day rolling window & `70,996`-ID historical protection:**
   - Explicit `as_of_utc` parameter persisted in manifest and checkpoint (`cutoff_utc = compute_cutoff_utc(as_of_utc, window_days=120)`).
   - Every candidate whose `video_id` appears in the protected historical Gold snapshot (`data/corpus/20261118_taxonomy_fix_v1/fact_videos.parquet`, `70,996` unique IDs) is skipped *before* detail, audio, or comment fetching (`skip_reason="historical_protected_id"`).
   - Every candidate with `create_time < cutoff_utc` is skipped (`skip_reason="outside_120d_rolling_window"`). Duplicate candidate IDs within the same discovery stream are deduplicated (`skip_reason="duplicate_candidate_id"`).
3. **Bounded ceilings (zero unlimited discovery):**
   - Hard configurable ceilings in `CollectorBounds` (defaults aligned with `M3.3` ceilings: `max_creators=5`, `max_candidate_videos=50`, `max_succeeded_videos=30`, `max_audio_minutes=60.0`, `max_comments_total=1000`, `max_comments_per_video=50`, `max_retries=2`, `session_deadline_seconds=7200.0`).
   - Discovery halts at `max_creators` and `max_candidate_videos`; processing halts or marks remaining candidates `skipped` (`skip_reason="max_succeeded_ceiling"` or `"session_deadline_exceeded"`) without unbounded loops.
4. **Capped retries, secret-redacted per-item failures, and checkpoint resume:**
   - Retries transient provider/audio/comment errors up to `max_retries` (`total_attempts <= 1 + max_retries`) using an injectable `sleep_fn` (`0s` in tests, bounded backoff in live mode).
   - Isolates per-item failures (`status="failed"`, secret-redacted error summary) so one broken item does not corrupt succeeded records.
   - Persists `collector_checkpoint.json` atomically after each item; resuming on the same `--output-dir` reuses prior `videos_4m.jsonl` succeeded records (`skip_reason="already_succeeded_in_checkpoint"`), retries previously `failed` items when requested, and produces an idempotent `videos_4m.jsonl` without duplicate `video_id` rows.
5. **Idempotent `crawl_manifest.json` & 64 kbps `.mp3` conversion receipts:**
   - Distinguishes `requested`, `succeeded`, `failed`, and `skipped` counts and per-item entries (`requested_count == succeeded_count + failed_count + skipped_count`).
   - Records `source_mode` (`"offline_fixture"` vs `"live_provider"`), `is_synthetic_fixture`, `as_of_utc`, `cutoff_utc`, `base_corpus_snapshot_id`, `historical_protected_count`, `bounds`, `timings_ms`, and per-item `audio_receipt` (`status` in `{"converted_64k_mp3", "unavailable", "failed", "skipped_audio_ceiling"}`, `audio_path`, `audio_bytes`, `audio_sha256`, `target_bitrate_kbps=64`).
   - Preserves missing modalities honestly (`audio_path=None`, `comments=[]` when unavailable) rather than inventing placeholder audio or comments.
6. **CLI integration (`pipelines/crawl_incremental/__main__.py`):**
   - Invokes `BoundedIncrementalCollector` on `--source offline_fixture --fixture-path <path>` or `--source live_provider --allow-live-network --creator <handle>...`, while preserving backward-compatible `--seed-demo-batch` (clearly tagged `is_synthetic_fixture=True`) and existing `crawler_service.py` helper functions.

### Explicitly Out of Scope (`M3.2`)
- Running any live TikTok network pilot capture (`M3.3` is gated on `M2.G` / `G2` plus `N`'s peer review of `M3.2`).
- Whisper CPU ASR transcription and prosody evaluation (`M3.3` / `M4.1`).

---

## 2. Architecture & Data Flow

```text
Creators / Fixture Stream
        │
        ▼
[1. Bounded Discovery] ──(enforces max_creators, max_candidate_videos)──► Requested IDs
        │
        ▼
[2. Pre-Fetch Gate]
   ├─ video_id in historical_ids (70,996)? ──► SKIPPED (historical_protected_id)
   ├─ video_id in checkpoint.succeeded?   ──► SKIPPED (already_succeeded_in_checkpoint)
   ├─ create_time invalid?                ──► FAILED  (invalid_create_time)
   ├─ create_time < cutoff_utc (120d)?    ──► SKIPPED (outside_120d_rolling_window)
   └─ succeeded >= max_succeeded_videos?  ──► SKIPPED (max_succeeded_ceiling)
        │
        ▼
[3. Per-Item Fetch + Capped Retries (<= 1 + max_retries)]
   ├─ Metadata -> RawIncrementalVideoRecord validation
   ├─ Optional 64 kbps .mp3 conversion (if within max_audio_minutes) -> AudioConversionReceipt
   └─ Optional comments fetch (capped by max_comments_per_video & max_comments_total)
        │
        ▼
[4. Atomic Persistence]
   ├─ videos_4m.jsonl            (deduplicated canonical RawIncrementalVideoRecord rows)
   ├─ collector_checkpoint.json  (resumable state)
   └─ crawl_manifest.json        (requested / succeeded / failed / skipped + audio receipts + timings_ms)
```

---

## 3. Acceptance Criteria Mapping

| `M3.2` Requirement | Verification Method |
| --- | --- |
| Invoked discovery/metadata/audio/comment worker with resume, capped retries, per-item failures, idempotent manifests | Unit & CLI integration tests (`tests/unit/test_bounded_collector_worker.py`) + offline fixture run over real `70,996`-ID `20261118_taxonomy_fix_v1` protection set |
| Authored fixture mode stays visibly separate; zero live TikTok recrawl / network calls in `M3.2` | `source_mode="offline_fixture"` & `is_synthetic_fixture=True` enforced in manifest; `live_provider` fails closed without `--allow-live-network` |
| `as_of` / cutoff tests enforce `120`-day window and skip every historical ID | Boundary tests (`cutoff - 1s` skipped, `cutoff` accepted) + real historical ID collision test against `20261118_taxonomy_fix_v1` |
| Manifests distinguish `requested / succeeded / failed / skipped` | Exact count & per-item ledger assertions (`requested == succeeded + failed + skipped`) across initial, retry, and resumed runs |
| `64 kbps` `.mp3` conversion recorded where available; missing modalities stay missing | Receipt tests verifying `converted_64k_mp3` (`bytes`, `sha256`, `64` kbps), `unavailable`, `failed`, and `skipped_audio_ceiling`, plus downstream `M3.1` compatibility check |
