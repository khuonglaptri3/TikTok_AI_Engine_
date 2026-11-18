# M0.2 — Contracts, Bounded Settings & Error/Logging Hygiene

- Status: IN_PROGRESS (`M0.2-REV-1` & `M0.2-REV-2` fixed and verified by `N` on `fix/m0.2-redaction-followups`; awaiting `K` re-verification before closing `M0.2`)
- Execution date: 2026-11-17 (initial `N` implementation); 2026-11-18 (`K` peer review & `N` follow-up fixes, Asia/Ho_Chi_Minh)
- Requirement source: [TikTok_AI_Engine_Milestone.md](../../../planning/TikTok_AI_Engine_Milestone.md) (`M0.2`)
- Repository version: `fix/m0.2-redaction-followups` (branched from `origin/feat/m0-m1-m2.1-complete-and-gold-v2` @ `6cf1a6ec`)
- Primary owner: Nguyễn Việt Nguyên (`N`) · Peer reviewer: Trần Đình Khương (`K`)
- Specification: [spec.md](superpowers/spec.md)
- Execution plan: [plan.md](superpowers/plan.md)

## Conclusion

Revalidated and hardened `packages/common/` and `packages/data_contracts/` against `M0.2` engineering invariants without breaking existing callers or endpoints (`63/63` pytest tests and `mypy` over `76` source files pass at merged commit `c3348e9`). All contract models and `AppSettings` reject `NaN` / `Inf` escapes, malformed or whitespace-only inputs, inverted time intervals, invalid SHA256/path entries, out-of-order quantiles, unknown request/error fields, and negative or non-`ms` response timings.

Independent peer review by Trần Đình Khương (`K`, [khuong-peer-review.md](evidence/khuong-peer-review.md)) confirmed 100% API/demo backward compatibility, and identified two runtime credential-redaction gaps (`M0.2-REV-1` traceback/stack emission and `M0.2-REV-2` quoted JSON secret keys). On `fix/m0.2-redaction-followups`, Nguyễn Việt Nguyên (`N`) fixed both gaps in [packages/common/logging/__init__.py](../../../../packages/common/logging/__init__.py) and added executable regression tests in [test_data_contracts.py](../../../../tests/contract/test_data_contracts.py) (`10/10` contract tests, `75/75` full pytest suite in `20.37s`, strict `mypy` across `76` source files, scoped `ruff`, and `check_secrets.py` with `0` leaks). Task `M0.2` awaits `K`'s re-verification of the two regression fixes before closing as `COMPLETE` for `M0.G`.

## Work performed

- **`packages/common/logging/__init__.py`:** Added `redact_secrets`, `SecretRedactingFilter`, and `get_safe_logger` to strip Google API keys (`AIza*`), `Bearer` tokens, key-value secret pairs, and URL userinfo passwords from formatted logs; hardened `StageTimer` to reject blank stage names and clamp latencies to finite non-negative `ms`.
- **`packages/common/exceptions/__init__.py`:** Sanitized `ViralRagError` messages with `redact_secrets` and validated non-blank error codes while preserving HTTP status mappings (`503 PROVIDER_KEY_MISSING`, `429 QUOTA_BLOCKED`, `503 CORPUS_NOT_READY`, `503 INDEX_NOT_READY`, `422 UNSUPPORTED_DOMAIN`).
- **`packages/common/settings/__init__.py`:** Enabled `allow_inf_nan=False`, added non-blank string validation for runtime settings, and overrode `__repr__` / `__str__` / `safe_summary()` so `gemini_api_key` and URL passwords are masked while preserving `.gemini_api_key: str` API compatibility.
- **`packages/data_contracts/` (`_validators.py`, `analytics.py`, `corpus.py`, `errors.py`, `multimodal.py`, `query.py`, `retrieval.py`, `script.py`):** Enabled `allow_inf_nan=False` across all models, added `extra="forbid"` to `CanonicalErrorResponse`, enforced `*_ms` finite non-negative `timings_ms`, enforced `end_sec >= start_sec`, quantile ordering (`q25 <= median <= q75`), 64-char hex SHA256 and basename-only manifest paths, and rejected blank/whitespace-only identifiers and text inputs.
- **`tests/contract/test_data_contracts.py`:** Expanded from 3 to 9 executable contract tests covering `NaN`/`Inf`, unknown/malformed inputs, `ms` timings, explicit error codes, and credential redaction in settings, exceptions, and Python `logging`.
- **Reciprocal Peer Review (`2026-11-18`):** Trần Đình Khương (`K`) verified API/demo compatibility at `c3348e9` and recorded two open runtime redaction findings (`M0.2-REV-1`, `M0.2-REV-2`) in [khuong-peer-review.md](evidence/khuong-peer-review.md).
- **Follow-up Fixes for `M0.2-REV-1` & `M0.2-REV-2` (`2026-11-18`, `fix/m0.2-redaction-followups`):**
  - Updated `redact_secrets` in [packages/common/logging/__init__.py](../../../../packages/common/logging/__init__.py) with `_QUOTED_KV_SECRET_RE` and quoted-key handling in `_KV_SECRET_RE` so JSON/dict quoted keys and values (`{"password": "..."}`, `{'api_key': '...'}`) are masked consistently across logs, `ViralRagError`, and `CanonicalErrorResponse`.
  - Updated `SecretRedactingFilter.filter` to format and redact `exc_info` into `exc_text` (clearing raw `exc_info` afterwards so downstream formatters cannot emit unredacted tracebacks) and sanitize `stack_info` on first emission.
  - Added TDD regression test `test_redaction_covers_json_payloads_exceptions_and_stack_info` in [test_data_contracts.py](../../../../tests/contract/test_data_contracts.py).

## Outputs

| File | Purpose |
| --- | --- |
| [workflow.md](evidence/workflow.md) | Skill/process provenance, design decisions, and command receipts |
| [khuong-peer-review.md](evidence/khuong-peer-review.md) | Peer review by Trần Đình Khương (`K`): API compatibility sign-off and 2 open redaction findings |
| [red-contract-tests.log](evidence/red-contract-tests.log) | Initial TDD RED test run before implementation |
| [green-contract-tests.log](evidence/green-contract-tests.log) | Post-implementation contract test run (`9 passed`) |
| [check-secrets.log](evidence/check-secrets.log) | Workspace secret scan result (`0` leaks) |
| [ruff.log](evidence/ruff.log) | Scoped Ruff lint output (`All checks passed!`) |
| [mypy.log](evidence/mypy.log) | Initial project-wide static typecheck (`76 source files`) |
| [pytest-full.log](evidence/pytest-full.log) | Initial full project pytest suite (`63 passed in 19.84s`) |
| [green-followup-tests.log](evidence/green-followup-tests.log) | Follow-up contract test run (`10 passed` covering `M0.2-REV-1` and `M0.2-REV-2`) |
| [ruff-followup.log](evidence/ruff-followup.log) | Follow-up scoped Ruff lint output (`All checks passed!`) |
| [mypy-followup.log](evidence/mypy-followup.log) | Follow-up project-wide mypy check (`76 source files`, `0` issues) |
| [pytest-full-followup.log](evidence/pytest-full-followup.log) | Follow-up full pytest suite (`75 passed in 20.37s`) |
| [check-secrets-followup.log](evidence/check-secrets-followup.log) | Follow-up secret scan result (`0` leaks) |

## Verification

| Check | Result | Scope / evidence |
| --- | --- | --- |
| `.venv/bin/python -m pytest tests/contract/test_data_contracts.py -v` | PASS (`9 passed`) | Contract invariants (`NaN`/`Inf`, bounds, timings, simple `key=val` redaction); [green-contract-tests.log](evidence/green-contract-tests.log) |
| `.venv/bin/python -m ruff check packages/common packages/data_contracts tests/contract` | PASS | Lint & import order on touched packages/tests; [ruff.log](evidence/ruff.log) |
| `.venv/bin/python scripts/check_secrets.py` | PASS (`0` leaks) | Full workspace secret scan; [check-secrets.log](evidence/check-secrets.log) |
| `.venv/bin/python -m mypy packages apps pipelines` | PASS (`76 source files`) | Full package, pipeline, and API/demo type check; [mypy.log](evidence/mypy.log), [mypy-current.log](../../tasks/team-progress-sync-2026-11-18/evidence/mypy-current.log) |
| `.venv/bin/python -m pytest -v` | PASS (`63 passed`) | Full contract, unit, eval, and ASGI smoke suites; [pytest-full.log](evidence/pytest-full.log), [pytest-current.log](../../tasks/team-progress-sync-2026-11-18/evidence/pytest-current.log) |
| Synthetic redaction boundary probes (`K` peer review) | Initial FAIL (`LEAK` at `c3348e9`); PASS (`REDACTED` after `M0.2-REV-1`/`M0.2-REV-2` fix) | Traceback/stack (`M0.2-REV-1`) and quoted JSON secret fields (`M0.2-REV-2`); [khuong-peer-review.md](evidence/khuong-peer-review.md), [green-followup-tests.log](evidence/green-followup-tests.log) |
| `.venv/bin/python -m pytest tests/contract/test_data_contracts.py -v` (follow-up) | PASS (`10 passed`) | Includes JSON/dict keys, `logger.exception`, `stack_info`, `ViralRagError`, `CanonicalErrorResponse`; [green-followup-tests.log](evidence/green-followup-tests.log) |
| `.venv/bin/python -m ruff check packages/common packages/data_contracts tests/contract` (follow-up) | PASS | Lint & style after follow-up fix; [ruff-followup.log](evidence/ruff-followup.log) |
| `.venv/bin/python -m mypy packages apps pipelines` (follow-up) | PASS (`76 source files`) | Project-wide static types after follow-up fix; [mypy-followup.log](evidence/mypy-followup.log) |
| `.venv/bin/python -m pytest -v` (follow-up) | PASS (`75 passed in 20.37s`) | Full repository suite on `fix/m0.2-redaction-followups`; [pytest-full-followup.log](evidence/pytest-full-followup.log) |
| `.venv/bin/python scripts/check_secrets.py` (follow-up) | PASS (`0` leaks) | Workspace secret scan after follow-up fix; [check-secrets-followup.log](evidence/check-secrets-followup.log) |

## Open issues

| Issue | Impact | Follow-up / responsible task |
| --- | --- | --- |
| **`M0.2-REV-1` & `M0.2-REV-2` fixed by `N`; pending `K` sign-off** | Both runtime redaction gaps are patched and covered by `test_redaction_covers_json_payloads_exceptions_and_stack_info`, awaiting `K`'s verification before closing `M0.2` | Trần Đình Khương (`K`) reviews `fix/m0.2-redaction-followups` and closes `M0.2` ahead of `M0.G` |

## Acceptance and handoff

| Task criterion | Result | Evidence |
| --- | --- | --- |
| Contract tests reject malformed/boundary inputs and unknown fields | Met | [test_data_contracts.py](../../../../tests/contract/test_data_contracts.py), [green-followup-tests.log](evidence/green-followup-tests.log) |
| Timings use `ms` and reject negative / non-finite durations | Met | [logging/__init__.py](../../../../packages/common/logging/__init__.py), [_validators.py](../../../../packages/data_contracts/_validators.py) |
| No `NaN`/`Inf` escapes across `AppSettings` and contracts | Met | `allow_inf_nan=False` + `test_contracts_and_settings_reject_nan_and_inf` |
| Explicit missing-key/quota/error payloads & no credentials in logs | Met (`N` fix verified; awaiting `K` check) | Covers simple `key=val`, `AIza*`, `Bearer`, URL creds, quoted JSON/dict secrets, `logger.exception`, and `stack_info`; [green-followup-tests.log](evidence/green-followup-tests.log) |
| Peer review of API compatibility & follow-up check by `K` | Partial (`PASS` on compatibility; follow-up re-check pending) | [khuong-peer-review.md](evidence/khuong-peer-review.md) |

Final task status: **IN_PROGRESS** (`N` resolved and tested `M0.2-REV-1` and `M0.2-REV-2` on `fix/m0.2-redaction-followups`; awaiting `K` sign-off on the two follow-up fixes before marking `COMPLETE` and evaluating `M0.G`).
