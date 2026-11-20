# M3.3 — Specification: Capped Capture-to-Transcript-to-Search Pilot

- **Task ID:** `M3.3`
- **Primary Owners:** Nguyễn Việt Nguyên (`N`) & Trần Đình Khương (`K`) (shared integration & 50/50 sample inspection)
- **Prerequisite Gates / Tasks:** `G2 = PASS` (`M2.G`), `M3.1 = COMPLETE`, `M3.2 = COMPLETE`
- **Requirement Source:** [TikTok_AI_Engine_Milestone.md](../../../planning/TikTok_AI_Engine_Milestone.md) (`M3.3`, lines 56, 99)

## Scope & Hard Ceilings
Prepare and execute (when live network tools and `MS_TOKEN` are available) the bounded end-to-end fresh-data pilot:
1. **Collection Bounds (`M3.2` worker):** Maximum `5` creators, `50` candidate fresh videos (`<= 120` days, excluding all `70,996` historical IDs), `30` successful videos, `60.0` audio minutes, `1,000` comments, and `1` bounded session (`<= 7,200` seconds / `2` hours).
2. **Measured CPU ASR Pilot Cap:** Transcribe **at most `10` videos** and **at most `20.0` audio minutes** before searchability verification. Enforce `0.0 <= start_sec < end_sec` on `RawWhisperSegment` outputs and leave un-transcribed or audio-missing records untouched (`transcript=""`, `whisper_segments=[]`).
3. **Dual-Sink Gold Ingest (`M3.1`) & Searchability Probe:** Ingest the pilot batch atop `data/corpus/20261118_taxonomy_fix_v1` into a new versioned output snapshot (never mutating historical bytes), build a versioned BM25 index (`BM25Index.build`), and verify that freshly transcribed videos are retrievable via `HybridRetrievalService` with exact source `video_id` matching (`>= 5` real non-synthetic transcribed fresh videos required for pilot `PASS`).
4. **Honest Mode Separation & Fail-Closed Status:**
   - `--mode dry_run_fixture`: verifies wiring, caps, metrics, disk/RAM/RTF measurement, and 50/50 `K`/`N` inspection sheet generation using synthetic fixtures (`is_synthetic_fixture=True`, `pilot_status="FIXTURE_DRY_RUN_ONLY"`). Never counts as live `M3.3` acceptance.
   - `--mode live_pilot`: requires `--allow-live-network`, `MS_TOKEN`, `yt-dlp`, `ffmpeg`, and `faster-whisper`. If host tools, credentials, or TikTok network yield fail (`< 5` real fresh searchable transcribed videos), emit `pilot_status="BLOCKED"` honestly without fake replacement data.
5. **Equal Sample Inspection (`50% K / 50% N`):** Export `sample_inspection_sheet.jsonl` assigning half of succeeded videos to `K` and half to `N` with `human_verified=false` placeholders.
