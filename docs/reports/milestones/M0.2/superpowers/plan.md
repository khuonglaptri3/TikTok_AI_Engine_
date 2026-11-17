# M0.2 — Execution & Verification Plan

- **Date:** 2026-11-17
- **Task ID:** `M0.2`
- **Primary Owner:** Nguyễn Việt Nguyên (`N`)

## Execution Steps
1. **Skill & Workspace Check:** Verify installed process skills and branch state; record provenance in `evidence/workflow.md`.
2. **TDD RED (Failing Contract Tests First):** Expand `tests/contract/test_data_contracts.py` with tests covering:
   - `NaN` / `+Inf` / `-Inf` rejection on request, response, multimodal, and `timings_ms` contracts.
   - Malformed / whitespace-only / unknown fields (`extra="forbid"`), inverted whisper/voice time ranges (`end_sec < start_sec`), invalid SHA256/filename in corpus manifest, invalid IQR ordering in `NicheBenchmarkSummary`.
   - Timing invariants (`ms` key suffix and non-negative finite durations in `StageTimer` and response `timings_ms`).
   - Explicit error payloads (`PROVIDER_KEY_MISSING`, `QUOTA_BLOCKED`, `CORPUS_NOT_READY`, `INDEX_NOT_READY`, `UNSUPPORTED_DOMAIN`) and secret redaction in `AppSettings.__repr__`, `ViralRagError`, and Python `logging` (`SecretRedactingFilter`).
   - Run `pytest tests/contract/test_data_contracts.py` and capture RED failure log in `evidence/red-contract-tests.log`.
3. **Implement Hardening (`packages/common/` & `packages/data_contracts/`):**
   - Add `redact_secrets`, `SecretRedactingFilter`, `get_safe_logger`, and `StageTimer` finite/non-blank validation in `packages/common/logging/__init__.py`.
   - Harden `AppSettings` (`allow_inf_nan=False`, non-blank string validators, masked `gemini_api_key` and URL password in `repr`/`str`/`safe_summary()`) in `packages/common/settings/__init__.py`.
   - Sanitize `ViralRagError` messages in `packages/common/exceptions/__init__.py`.
   - Add shared finite/timing/string/hex validators in `packages/data_contracts/_validators.py` and apply `allow_inf_nan=False` + boundary validators across `analytics.py`, `corpus.py`, `errors.py`, `multimodal.py`, `query.py`, `retrieval.py`, `script.py`.
4. **TDD GREEN & Full Verification:**
   - Run `pytest tests/contract/test_data_contracts.py` -> save `evidence/green-contract-tests.log`.
   - Run `python3 scripts/check_secrets.py`, `python3 -m mypy packages apps pipelines`, `python3 -m ruff check packages/common packages/data_contracts tests/contract`, and full `python3 -m pytest -v` -> save logs to `evidence/`.
5. **Report & Index:**
   - Author `docs/reports/milestones/M0.2/README.md` and `docs/reports/milestones/M0.2/evidence/workflow.md`, and update `docs/reports/milestones/README.md` with truthful `IN_PROGRESS` (awaiting peer review by `K`) status.
