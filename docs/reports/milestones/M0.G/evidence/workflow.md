# M0.G (G0) — Workflow Provenance & Verification Ledger

- **Date:** 2026-11-18 (Asia/Ho_Chi_Minh)
- **Task / Gate ID:** `M0.G` (`G0`)
- **Primary Owner:** Nguyễn Việt Nguyên (`N`)
- **Peer Reviewer:** Trần Đình Khương (`K`, pending gate sign-off)
- **Evaluated Revision:** `main` @ `1ff574fefa87b0453116f99e9b802221222593f4`

## Process Check (`AGENTS.md` Section 7)
- Authored [spec.md](../superpowers/spec.md) and [plan.md](../superpowers/plan.md) before executing G0 verification commands.
- Verified prerequisite task reports `M0.1`, `M0.2`, and `M0.3` are marked `COMPLETE` on `main`.
- Ran fresh verification suite directly on `main` (`1ff574fe`) without live Gemini calls (`USD 0`).

## Recorded Verification Commands & Receipts
- `.venv/bin/python scripts/check_secrets.py` -> `EXIT=0`, `PASS: Zero secret leaks detected across workspace.` ([check-secrets.log](check-secrets.log))
- `.venv/bin/python -m ruff check packages apps tests/contract tests/smoke` -> `EXIT=1` with 2 pre-existing style notices (`apps/api/app/routers/health.py:1` `I001`, `packages/retrieval/sparse/bm25.py:188` `UP017`) ([ruff.log](ruff.log))
- `.venv/bin/python -m mypy packages apps pipelines` -> `EXIT=0`, `Success: no issues found in 76 source files` ([mypy.log](mypy.log))
- `.venv/bin/python -m pytest tests/contract tests/smoke -v` -> `EXIT=0`, `11 passed in 6.51s` ([contract-smoke.log](contract-smoke.log))
- `.venv/bin/python -m pytest -v` -> `EXIT=0`, `75 passed in 17.03s` ([pytest-full.log](pytest-full.log))
- `.venv/bin/python -m pip check` -> `EXIT=0`, `No broken requirements found.` ([pip-check.log](pip-check.log))
- `docker --version` -> `Docker version 29.1.3` ([docker-check.log](docker-check.log)); `docker info` -> daemon socket `/var/run/docker.sock` absent in environment ([g0_verification_receipt.json](g0_verification_receipt.json)).
- `.venv/bin/python docs/reports/milestones/M0.G/evidence/run_g0_checks.py` -> `EXIT=0`, snapshots `20261117_recovered_v1` & `20261118_taxonomy_fix_v1` (`264` creators, `70,996` videos) and in-process ASGI endpoints (`/health/live`, `/health/ready`, `/demo/`, benchmark, retrieval, `offline_grounded`, OOD `422`) all pass ([g0_verification_receipt.json](g0_verification_receipt.json)).
