# M5.G — Execution & Verification Plan

**Goal:** Build and execute the deterministic Gate `G5` verification probe (`run_g5_checks.py`) and fail-closed unit test suite (`tests/unit/test_m5_g_gate_checks.py`) auditing `M5.1`, `M5.2`, anti-leakage boundaries, immutable Gold snapshots, and live `/api/v1/trust/audit-video` + `/demo/` diagnostic limits.
**Spec:** [spec.md](spec.md)

## Steps

1. **TDD RED (`tests/unit/test_m5_g_gate_checks.py`):**
   - Test `audit_m5_1_gate_criteria` (rejecting unverified human rows, video overlap, or false `auto_filter_validated` claims when positive support/precision is insufficient; accepting qualified `diagnostic_only_without_filtering`).
   - Test `audit_m5_2_gate_criteria` (rejecting `human_verified=false` silver labels, train/test video overlap, invalid NFC spans, or `< 0.65`/`< 0.60` F1; accepting `180`-unit `N`+`K` verified `held_out` receipt with explicit `service` sparse-support qualification).
   - Test `audit_live_trust_api_and_demo_limits` (verifying `comment_filter_policy == "diagnostic_only_unvalidated"`, `hide_seeding == False` UI default, `< 3`-comment abstention, NFC span citations, and non-accusatory wording).
2. **TDD GREEN (`docs/reports/milestones/M5.G/evidence/run_g5_checks.py`):**
   - Implement `audit_m5_1_gate_criteria`, `audit_m5_2_gate_criteria`, `audit_live_trust_api_and_demo_limits`, and `run_g5_gate_probe` writing `g5_verification_receipt.json` and `g5-gate-decision-receipt.json`.
   - Execute `run_g5_checks.py` against workspace receipts and `4` Gold snapshots (`0` byte mutations).
3. **Full Verification & Handoff:**
   - Run full `pytest -q`, Linux & `win32` `mypy`, `python3 scripts/check_secrets.py`, and docs/link hygiene checks; update `M5.G/README.md`, `milestones/README.md`, and `TikTok_AI_Engine_Milestone.md`.
