# M3.G — Acquisition & Resource Gate Preparation Plan

**Goal:** Produce a reproducible `M3.1` repeated-ingest replay receipt, full `29`-file `.mp3` audio-minute & throughput capacity projections, honest open-blocker accounting (`K 0/15`, `comment_coverage_rate = 0.0`, `annotation_time = PENDING_MEASUREMENT`), and compliant `docs/reports/milestones/M3.G/` documentation without altering immutable corpus data or prematurely marking Gate `G3` as `PASS`.

## Steps

1. **Pre-execution artifact & schema checks:**
   - Confirm [manifest.json](../../../../../data/corpus/20261118_taxonomy_fix_v1/manifest.json) and [manifest.json](../../../../../data/corpus/m3_3_pilot_snapshot_v1/manifest.json) pass `load_verified_corpus` SHA256 verification untouched.
   - Verify exact row/inspection counts in `docs/reports/milestones/M3.3/evidence/sample_inspection_sheet.jsonl` and read exact metrics from `docs/reports/milestones/M3.3/evidence/m3_3_pilot_receipt.json`.
2. **Execute live `M3.1` repeated-ingest & capacity verification script (writing snapshots strictly under `/tmp/`):**
   - Measure total duration and bytes of all `29` `.mp3` files under `data/raw_incremental/m3_3_pilot_run/batch/audio_64k/` (from `videos_4m.jsonl` `duration_sec` / `audio_path` + `crawl_manifest.json` / `ffmpeg` or container metadata if available).
   - Run `ingest_incremental_batch_to_gold(base_corpus_dir=Path("data/corpus/m3_3_pilot_snapshot_v1"), incremental_jsonl=Path("data/raw_incremental/m3_3_pilot_run/batch/videos_4m.jsonl"), ..., update_existing=False)` into `/tmp/m3_g_replay_skip` -> measure wall ms, peak RSS, row counts, and SHA256 verification.
   - Run `ingest_incremental_batch_to_gold(..., update_existing=True)` into `/tmp/m3_g_replay_enrich` -> measure wall ms, peak RSS, row counts, zero duplicate keys, and SHA256 verification.
   - Save JSON receipt to `docs/reports/milestones/M3.G/evidence/g3_capacity_and_replay_receipt.json` (cleaning up `/tmp/m3_g_replay_*`).
3. **Author `M3.G` documentation & ledger (`IN_PROGRESS`, `G3 = NOT_RUN`):**
   - Write `docs/reports/milestones/M3.G/evidence/workflow.md`, `docs/reports/milestones/M3.G/README.md`, and add the `M3.G` row in `docs/reports/milestones/README.md`.
4. **Full pre-handoff verification:**
   - Run `python3 scripts/check_secrets.py` (`0` leaks), relative markdown link validation across `docs/reports/milestones/M3.G/` and `docs/reports/milestones/README.md`, `M3.G/` top-level directory check (`README.md`, `evidence/`, `superpowers/{spec.md, plan.md}`), and relevant `pytest` (`test_snapshot_continuity.py`, `test_incremental_absa_seeding.py`, `test_m3_3_pilot_pipeline.py`).
