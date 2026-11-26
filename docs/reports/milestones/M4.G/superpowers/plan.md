# M4.G — Audio Timing/Provenance & Observable Promotion Gate (`G4`) Implementation Plan

## Global Constraints
- `USD 0` spend; 100% offline CPU execution; zero byte mutations to Gold snapshots or historical `M4.1`/`M4.2` workbooks.
- All repository reports, receipts, and code comments in English; preserve Vietnamese test queries/quotations verbatim.
- Two-person reciprocal approval rule: record `K`'s peer-review `PASS` recommendation in `g4-gate-decision-receipt.json`, while keeping `M4.G = IN_PROGRESS` and `G4 = NOT_RUN` until primary owner `N` co-signs `G3` and `G4`.

## Execution Steps

1. **Task 1 — TDD RED (`tests/unit/test_m4_g_gate_checks.py`):**
   - Write unit tests covering `audit_m4_1_gate_criteria`, `audit_m4_2_gate_criteria`, `audit_fresh_pilot_prosody_vs_promo`, and `verify_g4_asgi_epistemic_guardrails` (testing fail-closed boundary/count/invariant abstention, hidden-sponsorship / unlabeled-negative / historical-prosody leakage rejection, and HTTP `422` refusal on undisclosed-PR probability queries).
   - Run `pytest tests/unit/test_m4_g_gate_checks.py -v` and confirm RED (`ModuleNotFoundError`).
2. **Task 2 — TDD GREEN (`docs/reports/milestones/M4.G/evidence/run_g4_checks.py`):**
   - Implement deterministic `run_g4_checks.py` verifying SHA-256 digests across Gold snapshots (`20261118_taxonomy_fix_v1`, `m3_3_pilot_snapshot_v1`, `m3_3_pilot_snapshot_v2`), `M4.1` & `M4.2` artifacts, live `evaluate_m4_1_reference_set` / `compute_m4_1_annotator_agreement` recomputation, `M4.2` anti-leakage & ASGI epistemic probes, and the `29`-video fresh prosody-vs-promo descriptive join.
   - Run `pytest tests/unit/test_m4_g_gate_checks.py -v` and confirm GREEN.
3. **Task 3 — Real Gate Execution, Receipts & Documentation Sync:**
   - Run `python3 docs/reports/milestones/M4.G/evidence/run_g4_checks.py` to generate `g4_verification_receipt.json` and `g4_checks.log` (verifying pre/post Gold snapshot immutability).
   - Write `g4-gate-decision-receipt.json`, `M4.G/evidence/workflow.md`, and `M4.G/README.md`; synchronize `docs/reports/milestones/README.md` and `docs/planning/TikTok_AI_Engine_Milestone.md`.
   - Execute `verification-before-completion`: full `pytest -q`, Linux & `--platform win32` `mypy`, `python3 scripts/check_secrets.py`, and relative-link/structure hygiene checks before committing and pushing to `origin/main`.
