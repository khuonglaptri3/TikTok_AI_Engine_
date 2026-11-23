# M3.G — Acquisition & Resource Gate Preparation Specification (`G3`)

- **Task ID:** `M3.G` (Gate `G3` decision preparation; official decision remains `NOT_RUN` pending `M3.3` `K` `15/15` inspection and `K`/`N` joint sign-off)
- **Primary Owner (`M3.G` Gate Decision):** Trần Đình Khương (`K`)
- **Peer Reviewer & Preparation Contributor:** Nguyễn Việt Nguyên (`N`)
- **Requirement Source:** [TikTok_AI_Engine_Milestone.md](../../../../planning/TikTok_AI_Engine_Milestone.md) (`M3.G`, line 100)
- **Date:** 2026-11-23 (Asia/Ho_Chi_Minh)
- **Repository Baseline:** `main` @ `186a4b0a`

## 1. Purpose and Scope

Assemble reproducible, non-synthetic verification evidence for Gate `G3` (`M3.G`) using real `M3.3` pilot outputs on `main`, while preserving **`Gate G3 = NOT_RUN`** (`M3.G` Status `IN_PROGRESS`) until prerequisites close:

1. **Repeated Dual-Sink Ingest (`M3.1` Replay) Verification:**
   - Verify byte-for-byte SHA256 immutability of historical Gold `20261118_taxonomy_fix_v1` (`70,996` videos) and live pilot snapshot `m3_3_pilot_snapshot_v1` (`71,026` videos).
   - Execute real `ingest_incremental_batch_to_gold` replays from `data/raw_incremental/m3_3_pilot_run/batch/videos_4m.jsonl` over `m3_3_pilot_snapshot_v1` into disposable `/tmp` targets under both `update_existing=False` (skip-replay idempotency) and `update_existing=True` (enrichment/coalesce idempotency), asserting zero duplicate `video_id`/`segment_id`/`comment_id` keys, exact row-count parity (`71,026` videos, `436` voice segments, `0` comments, `30` ABSA rows), finite wall-time/RAM measurements, and verified manifest checksums.
2. **Real-Pilot Throughput, Coverage & Capacity Accounting:**
   - Measure total audio duration across all `29` captured `.mp3` files (`m3_3_pilot_run/batch/audio_64k/*.mp3`) alongside the `10` transcribed ASR videos (`16.683` min in `197.269 s`, `RTF = 0.1971`) from [m3_3_pilot_receipt.json](../../M3.3/evidence/m3_3_pilot_receipt.json).
   - Report observed `capture_yield_rate = 0.6` (`30/50`), `comment_coverage_rate = 0.0` (including observed headless `EmptyResponseException` / `AntiBotChallengeError` block when re-tested on `2026-11-23` with `TikTokApi`), and current `sample_inspection_sheet.jsonl` sign-off counts (`N = 15/15`, `K = 0/15`).
   - Record conservative capacity projections (wall time, CPU ASR cost, disk, RAM) for a hypothetical bounded future batch **strictly contingent** on a new approved collection budget, explicitly keeping `annotation_time` flagged as `PENDING_MEASUREMENT` rather than extrapolating unrecorded human timings.
3. **Strict Epistemic & Gate Boundaries:**
   - Never overwrite `data/corpus/` or `artifacts/` outputs (`M3.G` replay writes strictly to `/tmp/`).
   - Keep `M3.G` `Status = IN_PROGRESS` and `Gate G3 = NOT_RUN` until `K` completes `15/15` `M3.3` verification, both `K` and `N` supply observed annotation time, and `K` + `N` jointly record the `G3` decision (`PASS` or `BLOCKED` on comment collection / scope boundary).
