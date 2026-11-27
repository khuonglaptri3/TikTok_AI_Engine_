# M6.G — Gate G6 Execution & Verification Plan

- **Task ID:** `M6.G` (`Gate G6`)
- **Authored at:** `2026-11-27T08:44:00+07:00` (`Asia/Ho_Chi_Minh`)
- **Specification:** [spec.md](spec.md)

## Execution Steps

1. **Upstream Reciprocal Closure (`M3.G`, `M4.G`, `M5.G`, `M6.1`, `M6.2`):**
   - Record owner-confirmed `N` sign-off (`2026-11-27T08:39:15+07:00`) across `g3-gate-decision-receipt.json`, `g4-gate-decision-receipt.json`, and `g5-gate-decision-receipt.json`, transitioning `M3.G`, `M4.G`, and `M5.G` to `COMPLETE` (`G3 = PASS`, `G4 = PASS`, `G5 = PASS`).
   - Transition `M6.1` (`bm25-v3` default confirmed across `N` & `K`, fresh `M3.3` segments searchable via `bm25-m3_3-pilot`) and `M6.2` (`30/30 N` + `30/30 K` verified, `p95 = 69.00 ms`) to `COMPLETE`, and sync `apps/api/app/dependencies.py` milestone status metadata.
2. **TDD `RED -> GREEN` for Gate `G6` Probe (`tests/unit/test_m6_g_gate_checks.py` & `evidence/run_g6_checks.py`):**
   - Write `tests/unit/test_m6_g_gate_checks.py` first (`RED`) testing fail-closed upstream gate/task checks, hosting candidate evaluation (`local_cpu_release = PASS` vs `public_hosting = BLOCKED`), and live ASGI `/demo/` + multimodal endpoint readiness.
   - Implement `docs/reports/milestones/M6.G/evidence/run_g6_checks.py` (`GREEN`) to verify all `5` Gold snapshots, `G0`–`G5` receipts, `sdist + wheel` package build, disk/RAM footprints, end-to-end ASGI `/demo/` stage timings, and hosting eligibility matrix, emitting `g6_verification_receipt.json` and `g6-gate-decision-receipt.json`.
3. **Full Workspace Verification & Final Sync (`verification-before-completion`):**
   - Run `run_g6_checks.py`, full `pytest -q`, Linux `mypy`, `--platform win32` `mypy`, `python3 scripts/check_secrets.py`, and markdown link/structure hygiene across all `24` indexed milestone tasks.
   - Write `docs/reports/milestones/M6.G/README.md` and `evidence/workflow.md`, and update `docs/reports/milestones/README.md` and `docs/planning/TikTok_AI_Engine_Milestone.md`.
