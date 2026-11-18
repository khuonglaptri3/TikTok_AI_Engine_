# M0.G (G0) — Foundation Decision Specification

- **Task ID:** `M0.G` (Gate `G0`)
- **Primary Owner:** Nguyễn Việt Nguyên (`N`)
- **Peer Reviewer:** Trần Đình Khương (`K`)
- **Requirement Source:** [TikTok_AI_Engine_Milestone.md](../../../../planning/TikTok_AI_Engine_Milestone.md) (`M0.G`)
- **Date:** 2026-11-18 (Asia/Ho_Chi_Minh)

## Scope

Assemble, verify, and record the **G0 foundation gate decision** across `M0.1`, `M0.2`, and `M0.3` on the synchronized `main` revision (`1ff574fe`).

## Gate Acceptance Criteria (`M0.G`)

1. **Upstream task completion:** Verify `M0.1`, `M0.2`, and `M0.3` reports and evidence bundles are marked `COMPLETE` and match the milestone index (`docs/reports/milestones/README.md`) and plan (`TikTok_AI_Engine_Milestone.md`).
2. **Automated checks on recorded revision & environment:**
   - `scripts/check_secrets.py` exits `0` (`Zero secret leaks detected`).
   - `mypy packages apps pipelines` passes with `0` issues.
   - `ruff check` passes cleanly on core foundation packages (`packages/`, `apps/`, `tests/contract/`, `tests/smoke/`).
   - Executable contract and smoke tests (`tests/contract/test_data_contracts.py`, `tests/smoke/test_api_and_demo.py`) plus the full `pytest` suite pass with `0` provider calls (`USD 0`).
   - Dependency integrity (`pip check`), editable/package import verification, and `Docker` engine availability status are explicitly recorded (distinguishing source-package verification from an actual Docker container run when unavailable).
3. **Explicit limitations & bounded claims:** Record all unresolved dataset licensing, semantic/ASR/POI ground-truth limits, UI `422` formatting rough edges (`M0.3-UI-1..3`), and Docker daemon boundaries; infer no live provider quota or public hosting eligibility.
4. **Two-person gate review:** Publish `M0.G/README.md`, `evidence/workflow.md`, and machine-readable receipt for independent review by Trần Đình Khương (`K`) before setting `G0` to `PASS`.
