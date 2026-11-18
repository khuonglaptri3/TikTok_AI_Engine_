# M0.2 — Workflow Provenance & Verification Ledger

- **Date:** 2026-11-17 (Asia/Ho_Chi_Minh)
- **Task ID:** `M0.2`
- **Primary Owner:** Nguyễn Việt Nguyên (`N`)
- **Peer Reviewer:** Trần Đình Khương (`K`, pending)

## Process & Skill Check
- Checked local skill directories (`~/.gemini/antigravity-cli/builtin/skills`, `~/.agents/skills`, `~/.codex/skills`); standalone `superpowers` skill files (`using-superpowers`, `brainstorming`, `writing-plans`, `test-driven-development`, `verification-before-completion`) were not installed on this machine.
- Followed the equivalent `AGENTS.md` Section 7 process directly:
  1. Authored `superpowers/spec.md` and `superpowers/plan.md` prior to code modifications.
  2. Expanded `tests/contract/test_data_contracts.py` first (`RED` observed in `red-contract-tests.log`).
  3. Implemented boundary, finite-float, ms-timing, error-sanitization, and secret-redaction hardening across `packages/common/` and `packages/data_contracts/`.
  4. Caught and fixed a `%s` format-string interaction bug in `SecretRedactingFilter` during TDD (`green-contract-tests.log` later passed 9/9).
  5. Executed full verification suite (`check-secrets`, `ruff`, `mypy`, `pytest`).

## Key Decisions
1. **API Compatibility for `AppSettings.gemini_api_key`:** Kept `gemini_api_key: str` with `repr=False` plus custom `__repr__` / `__str__` / `safe_summary()` masking rather than switching to `pydantic.SecretStr`, so existing callers (`.gemini_api_key.strip()`) remain 100% compatible without breaking downstream packages.
2. **Millisecond Timing Enforcement:** Preserved `StageTimer.measure("parse")` compatibility for internal stage names while enforcing finite non-negative `*_ms` keys in all public API response `timings_ms` schemas (`validate_timings_ms`). Empty `{}` remains valid for isolated unit fixtures.
3. **Sandbox Git Branch Boundary:** Creating `.git/refs/heads/feat/m0.2-contracts-validation` inside the sandbox failed with a lock/directory permission error; changes were completed in the workspace on `main` (`b12af51f`) so the contributor can create the branch and commit outside the sandbox.

## Commands & Verification Receipts
- `.venv/bin/python -m pytest tests/contract/test_data_contracts.py -v` (RED) -> `EXIT_CODE=2` ([red-contract-tests.log](red-contract-tests.log))
- `.venv/bin/python -m pytest tests/contract/test_data_contracts.py -v` (GREEN) -> `EXIT=0`, `9 passed in 0.18s` ([green-contract-tests.log](green-contract-tests.log))
- `.venv/bin/python -m ruff check packages/common packages/data_contracts tests/contract` -> `EXIT=0`, `All checks passed!` ([ruff.log](ruff.log))
- `.venv/bin/python scripts/check_secrets.py` -> `EXIT=0`, `PASS: Zero secret leaks detected across workspace.` ([check-secrets.log](check-secrets.log))
- `.venv/bin/python -m mypy packages apps pipelines` -> `EXIT=0`, `Success: no issues found in 76 source files` ([mypy.log](mypy.log))
- `.venv/bin/python -m pytest -v` -> `EXIT=0`, `63 passed in 19.84s` ([pytest-full.log](pytest-full.log))

## Follow-up Fix Ledger (`2026-11-18`, `fix/m0.2-redaction-followups`)
- Addressed peer-review findings `M0.2-REV-1` (first-emission `exc_info` traceback and `stack_info` sanitization in `SecretRedactingFilter.filter`) and `M0.2-REV-2` (quoted JSON/dict keys/values in `redact_secrets`).
- TDD RED confirmed on `tests/contract/test_data_contracts.py::test_redaction_covers_json_payloads_exceptions_and_stack_info` before patching `packages/common/logging/__init__.py`.
- Follow-up verification commands:
  - `.venv/bin/python -m pytest tests/contract/test_data_contracts.py -v` -> `EXIT=0`, `10 passed in 0.30s` ([green-followup-tests.log](green-followup-tests.log))
  - `.venv/bin/python -m ruff check packages/common packages/data_contracts tests/contract` -> `EXIT=0`, `All checks passed!` ([ruff-followup.log](ruff-followup.log))
  - `.venv/bin/python -m mypy packages apps pipelines` -> `EXIT=0`, `Success: no issues found in 76 source files` ([mypy-followup.log](mypy-followup.log))
  - `.venv/bin/python -m pytest -v` -> `EXIT=0`, `75 passed in 20.37s` ([pytest-full-followup.log](pytest-full-followup.log))
  - `.venv/bin/python scripts/check_secrets.py` -> `EXIT=0`, `PASS: Zero secret leaks detected across workspace.` ([check-secrets-followup.log](check-secrets-followup.log))
- Merged `fix/m0.2-redaction-followups` (`03de1a65`) directly into `main` (`5d778a2b`) and marked `M0.2` as `COMPLETE` per explicit contributor instruction without a separate re-review round.
