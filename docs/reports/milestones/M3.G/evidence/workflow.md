# M3.G — Superpowers Workflow & Verification Ledger

- **Task:** `M3.G` (`Gate G3` — Bounded Real Capture-to-Transcript-to-Search & Measured Capacity Decision)
- **Dates:** `2026-11-23` to `2026-11-26` (`Asia/Ho_Chi_Minh`)
- **Primary Owner (`G3` Gate Decision):** Trần Đình Khương (`K`) · **Peer Reviewer & Replay Contributor:** Nguyễn Việt Nguyên (`N`)
- **Spec & Plan:** [spec.md](../superpowers/spec.md), [plan.md](../superpowers/plan.md)

## 1. Two-Contributor Execution Provenance

1. **Stage A — `M3.1` Repeated-Ingest Replays & Initial Capacity Prep (`2026-11-23`, Contributor `N`):**
   - Verified pre/post SHA-256 immutability of `20261118_taxonomy_fix_v1` and `m3_3_pilot_snapshot_v1`.
   - Executed `/tmp` `ingest_incremental_batch_to_gold` replays over `videos_4m.jsonl` with `update_existing=False` (`5,635.45 ms`) and `update_existing=True` (`6,140.35 ms`, `zero_duplicate_keys=true`, `1,322.89 MiB` RSS), audited all `29` `.mp3` durations (`2,801 s` = `46.683` min, `0.4601 MiB/min`), and recorded `N_minutes = 15.0` in [g3_capacity_and_replay_receipt.json](g3_capacity_and_replay_receipt.json).
2. **Stage B — MLOps Readiness Gate Probe & Whole-Branch Review Hardening (`2026-11-23`, Contributor `K`):**
   - Grounded `M3.G` in `DVC`/`LakeFS` SHA-256 verification and `Dagster` `@asset_check(blocking=True)` per-downstream readiness checks via `using-superpowers` -> `brainstorming` -> `writing-plans` -> `executing-plans` + `test-driven-development`.
   - Implemented `docs/reports/milestones/M3.G/evidence/run_g3_checks.py` and `tests/unit/test_m3_g_gate_checks.py` (`RED -> GREEN`), dispatched an independent whole-branch code reviewer, and fixed all 6 findings (`M5.1` `>= 10` videos threshold, `expected_total = 30` & `video_id` parity, fail-closed `G0`/`M3.x` receipt checks, dynamic telemetry, `3 -> 2` duplicate-comment `update_existing=True` probe, and strict non-converted `.mp3` status/orphan checks).
3. **Stage C — Cross-Branch Unification Across `v1`, `v2`, and `v5` (`2026-11-26`, Contributor `K`):**
   - Unified `origin/main` (`m3_3_pilot_snapshot_v2`: `452` native-ID comments across `28/30` pilot videos), `feat/k-m3.3-hybrid-crawler-upgrade` (`m3_3_playwright_comments_20261125_v5`: `2,823` DOM comments across `118/130` fresh F&B videos), `feat/m4.1-audio-prosody-and-timestamp-eval` (PR #10), `feat/demo-ux-ui-redesign`, and `feat/k-m3.g-gate-decision`.
   - Guarded optional `playwright.sync_api` imports in `pipelines/capture_playwright_comments/{capture.py, __main__.py}` (`TYPE_CHECKING` + lazy runtime import) and `tests/unit/test_playwright_comment_capture.py` (`pytest.importorskip`) so offline CLI/HTML/Gold unit tests (`14 passed, 10 skipped`) execute cleanly on base CPU hosts without Chromium installed, and verified the full unified suite (`265 passed, 10 skipped`; `117` source files clean on Linux & `--platform win32` `mypy`).
   - Recorded `K`'s inspection timing (`K_minutes = 18.0`, combined `33.0` person-minutes across `30/30` pilot videos) and re-executed `python3 docs/reports/milestones/M3.G/evidence/run_g3_checks.py` -> **`PASS in 29.639s`** (`M4.1 = READY_UNBLOCKED`, `M5.1 = READY_UNBLOCKED`, `M5.2 = READY_UNBLOCKED`, `10/10` searchable, `0` byte mutations across `base`, `v1`, `v2`, and `v5`).

## 2. Key Verification Receipts

- `g3_verification_receipt.json` SHA-256: `82bc9c6f9efc26d134ee1e189008d477f59ec263ebc5792ce0b71953ac81f12f`
- `g3_capacity_and_replay_receipt.json` SHA-256: `f308a52614436c5f4198eb35ead441abe858d8632c589a765e3a8998eb69ed3c`
- `m3_3_original_pass_receipt.json` SHA-256: `3a67062ed46c73052397f42f7a247f6b6594c24186d925a1b2508a2dae591d8a`
- `m3_3_pilot_receipt.json` SHA-256: `487d0c5897ca537d71b0529ef8b84cc2f2f285ed970f881ccbc89e54d175ce05`
- `playwright_comment_capture_20261125.json` SHA-256: `ba111596cefe14cae228ac1cabca7398507a1e7f51d03d0cf2ff1385c349022e`
