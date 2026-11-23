# M3.G — Workflow Provenance & Gate Preparation Ledger

- **Date:** 2026-11-23 (Asia/Ho_Chi_Minh)
- **Task ID:** `M3.G` (Gate `G3` — Acquisition & Resource Decision Preparation)
- **Gate Status:** `NOT_RUN` (`Task Status: IN_PROGRESS` — preparation & `M3.1` repeated-ingest evidence assembled by `N`; official `G3` decision awaits `K`'s `15/15` `M3.3` inspection, recorded annotation times, and `K`/`N` joint sign-off)
- **Primary Owner (`M3.G` Gate Decision):** Trần Đình Khương (`K`) · **Peer Reviewer & Preparation Contributor:** Nguyễn Việt Nguyên (`N`)
- **Spec & Plan:** [spec.md](../superpowers/spec.md), [plan.md](../superpowers/plan.md)

## 1. Execution & Verification Steps (`2026-11-23`)

1. **Pre-execution planning (`AGENTS.md` §7):** Authored [spec.md](../superpowers/spec.md) and [plan.md](../superpowers/plan.md) prior to executing `M3.1` repeated-ingest checks and capacity calculations (fixing a relative path typo in `plan.md` prior to execution).
2. **Corpus & Batch Inspection:**
   - Verified pre-replay byte-for-byte SHA256 checksums across [data/corpus/20261118_taxonomy_fix_v1](../../../../../data/corpus/20261118_taxonomy_fix_v1/manifest.json) (`70,996` historical videos) and [data/corpus/m3_3_pilot_snapshot_v1](../../../../../data/corpus/m3_3_pilot_snapshot_v1/manifest.json) (`71,026` total videos, `436` voice segments, `0` comments) via `load_verified_corpus`.
   - Counted all `29` extracted `64 kbps` `.mp3` files under `data/raw_incremental/m3_3_pilot_run/batch/audio_64k/` (`2,801 s` = `46.683` audio minutes, `22,524,055` bytes -> `0.4601 MiB/audio-min`) and confirmed `30` `sample_inspection_sheet.jsonl` rows (`N: 15 assigned / 15 verified`, `K: 15 assigned / 0 verified`).
3. **Executed Live `M3.1` Repeated-Ingest Replays (`/tmp/m3_g_replay_*`, zero corpus mutation):**
   - `update_existing=False` (`skip_replay_update_existing_false`): completed in `5,635.45 ms` with `71,026` videos (`71,026` unique `video_id`), `436` voice segments (`436` unique `segment_id`), `0` comments, `30` ABSA rows, `zero_duplicate_keys=True`, `manifest_checksums_verified=True`.
   - `update_existing=True` (`enrichment_coalesce_update_existing_true`): completed in `6,140.35 ms` with identical deduplicated counts (`71,026` / `436` / `0` / `30`), `zero_duplicate_keys=True`, `manifest_checksums_verified=True`.
   - Post-replay SHA256 hashes of `20261118_taxonomy_fix_v1` and `m3_3_pilot_snapshot_v1` remained `100%` identical (`base_corpus_bytes_preserved_sha256=true`, `pilot_snapshot_bytes_preserved_sha256=true`); process peak RSS = `1,322.89 MiB`.
   - Saved structured receipt to [g3_capacity_and_replay_receipt.json](g3_capacity_and_replay_receipt.json).
4. **Live Comment Collection Diagnostic (`2026-11-23`):**
   - Re-tested `TikTokApi` with updated `MS_TOKEN` (`len=156`) in this headless Linux session (no GUI `DISPLAY`) against video `7710799156024986887`: `TikTokApi.make_request` raised `EmptyResponseException` (`AntiBotChallengeError` under fail-closed collector rules). Stopped cleanly with zero retry/bypass and recorded `comment_coverage_rate=0.0` as an open blocker requiring desktop GUI (`--no-tiktok-headless`) or explicit `M5` deferral decision in `G3`.
5. **Annotation Timing Update (`2026-11-23`):** Recorded contributor `N`'s self-reported inspection duration (`~15.0` min across `15` videos = `~1.0` min/video) and projected `~50.0` human review min for a `50`-video batch in [g3_capacity_and_replay_receipt.json](g3_capacity_and_replay_receipt.json), keeping `K`'s inspection timing explicitly `PENDING_MEASUREMENT`.
6. **Pre-Handoff Verification (`2026-11-23`):**
   - Executed `tests/unit/test_snapshot_continuity.py tests/unit/test_incremental_absa_seeding.py tests/unit/test_m3_3_pilot_pipeline.py`, `python3 scripts/check_secrets.py`, and relative markdown link / layout checks (results recorded in [../README.md](../README.md)).
