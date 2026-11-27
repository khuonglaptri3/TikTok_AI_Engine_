# M6.G — Superpowers Workflow & Verification Ledger

- **Task ID:** `M6.G` (`Gate G6`)
- **Executed at:** `2026-11-27T08:44:00+07:00` – `2026-11-27T09:05:00+07:00` (`Asia/Ho_Chi_Minh`)
- **Contributors:** Nguyễn Việt Nguyên (`N`) & Trần Đình Khương (`K`)

## 1. Skills Applied

1. `using-superpowers` & `writing-plans`: Authored [spec.md](../superpowers/spec.md) and [plan.md](../superpowers/plan.md) prior to implementing the `G6` probe.
2. `test-driven-development`:
   - **RED:** Created `tests/unit/test_m6_g_gate_checks.py` and executed `pytest tests/unit/test_m6_g_gate_checks.py -v` -> `3 failed (FileNotFoundError: Missing M6.G probe script)`.
   - **GREEN:** Implemented `docs/reports/milestones/M6.G/evidence/run_g6_checks.py` (including offline `uv build --offline` fallback when Anaconda `setuptools` lacked `backports.tarfile`), re-ran `run_g6_checks.py` (`PASS in 39.899s`, `0` snapshot byte mutations) and `pytest tests/unit/test_m6_g_gate_checks.py -v` (`3 passed in 13.74s`).
3. `verification-before-completion`: Executed full workspace `pytest -q`, Linux `mypy`, `--platform win32` `mypy`, `python3 scripts/check_secrets.py`, and `24`-task documentation/link parity verification before claiming `COMPLETE`.

## 2. Key Decisions & Provenance

- **Owner-Confirmed `N` Concurrence (`2026-11-27T08:39:15+07:00`):** Repository owner `K` relayed that contributor `N` reviewed all updated results (`M3.G`, `M4.G`, `M5.G`, `M6.1`, `M6.2`, and `apps/` multimodal wiring) and confirmed concurrence across all pending items.
- **Separated `G6` Rulings:** Recorded `local_cpu_release = PASS` (`1,347.97 MiB` peak RSS, `154.87 MiB` active demo disk, `USD 0` spend) separately from `public_hosting = BLOCKED` (`G1` upstream TikTok redistribution & comment PII restrictions, `Render Free` `512 MB` RAM OOM, and `Railway`/`Fly.io` lack of perpetual card-free tier).
