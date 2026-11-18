# M0.2 — Contracts, Bounded Settings & Error/Logging Hygiene

- Status: IN_PROGRESS (API compatibility peer review completed by Trần Đình Khương; 2 runtime redaction follow-ups open for Nguyễn Việt Nguyên before `M0.G`)
- Execution date: 2026-11-17 (implementation by `N`); 2026-11-18 (peer review by `K`, Asia/Ho_Chi_Minh)
- Requirement source: [TikTok_AI_Engine_Milestone.md](../../../planning/TikTok_AI_Engine_Milestone.md) (`M0.2`)
- Repository version: `main` (`c3348e93d66ad4eeba133c1d05752d26da18d774`, merged PR #1 from `dcf534f7b7bf2ca2bbcb44b88481905ce3105b4e`)
- Primary owner: Nguyễn Việt Nguyên (`N`) · Peer reviewer: Trần Đình Khương (`K`)
- Specification: [spec.md](superpowers/spec.md)
- Execution plan: [plan.md](superpowers/plan.md)

## Conclusion

Revalidated and hardened `packages/common/` and `packages/data_contracts/` against `M0.2` engineering invariants without breaking existing callers or endpoints (`63/63` pytest tests and `mypy` over `76` source files pass at merged commit `c3348e9`). All contract models and `AppSettings` reject `NaN` / `Inf` escapes, malformed or whitespace-only inputs, inverted time intervals, invalid SHA256/path entries, out-of-order quantiles, unknown request/error fields, and negative or non-`ms` response timings.

Independent peer review by Trần Đình Khương (`K`, [khuong-peer-review.md](evidence/khuong-peer-review.md)) confirmed 100% API/demo backward compatibility, and identified **two runtime credential-redaction gaps** reproduced via synthetic probes ([nguyen-probes.json](../../tasks/team-progress-sync-2026-11-18/evidence/nguyen-probes.json)): (1) `SecretRedactingFilter` misses unformatted `exc_info` tracebacks and `stack_info` on first emission, and (2) `redact_secrets` misses quoted JSON secret fields (e.g., `{"password": "..."}`). Task `M0.2` remains `IN_PROGRESS` until Nguyễn Việt Nguyên (`N`) resolves these two redaction cases and `K` verifies the regression tests prior to gate `M0.G` (`G0`).

## Work performed

- **`packages/common/logging/__init__.py`:** Added `redact_secrets`, `SecretRedactingFilter`, and `get_safe_logger` to strip Google API keys (`AIza*`), `Bearer` tokens, key-value secret pairs, and URL userinfo passwords from formatted logs; hardened `StageTimer` to reject blank stage names and clamp latencies to finite non-negative `ms`.
- **`packages/common/exceptions/__init__.py`:** Sanitized `ViralRagError` messages with `redact_secrets` and validated non-blank error codes while preserving HTTP status mappings (`503 PROVIDER_KEY_MISSING`, `429 QUOTA_BLOCKED`, `503 CORPUS_NOT_READY`, `503 INDEX_NOT_READY`, `422 UNSUPPORTED_DOMAIN`).
- **`packages/common/settings/__init__.py`:** Enabled `allow_inf_nan=False`, added non-blank string validation for runtime settings, and overrode `__repr__` / `__str__` / `safe_summary()` so `gemini_api_key` and URL passwords are masked while preserving `.gemini_api_key: str` API compatibility.
- **`packages/data_contracts/` (`_validators.py`, `analytics.py`, `corpus.py`, `errors.py`, `multimodal.py`, `query.py`, `retrieval.py`, `script.py`):** Enabled `allow_inf_nan=False` across all models, added `extra="forbid"` to `CanonicalErrorResponse`, enforced `*_ms` finite non-negative `timings_ms`, enforced `end_sec >= start_sec`, quantile ordering (`q25 <= median <= q75`), 64-char hex SHA256 and basename-only manifest paths, and rejected blank/whitespace-only identifiers and text inputs.
- **`tests/contract/test_data_contracts.py`:** Expanded from 3 to 9 executable contract tests covering `NaN`/`Inf`, unknown/malformed inputs, `ms` timings, explicit error codes, and credential redaction in settings, exceptions, and Python `logging`.
- **Reciprocal Peer Review (`2026-11-18`):** Trần Đình Khương (`K`) verified API/demo compatibility at `c3348e9` and recorded two open runtime redaction findings (`M0.2-REV-1`, `M0.2-REV-2`) in [khuong-peer-review.md](evidence/khuong-peer-review.md).

## Outputs

| File | Purpose |
| --- | --- |
| [workflow.md](evidence/workflow.md) | Skill/process provenance, design decisions, and command receipts |
| [khuong-peer-review.md](evidence/khuong-peer-review.md) | Peer review by Trần Đình Khương (`K`): API compatibility sign-off and 2 open redaction findings |
| [red-contract-tests.log](evidence/red-contract-tests.log) | Initial TDD RED test run before implementation |
| [green-contract-tests.log](evidence/green-contract-tests.log) | Post-implementation contract test run (`9 passed`) |
| [check-secrets.log](evidence/check-secrets.log) | Workspace secret scan result (`0` leaks) |
| [ruff.log](evidence/ruff.log) | Scoped Ruff lint output (`All checks passed!`) |
| [mypy.log](evidence/mypy.log) | Strict project-wide static typecheck (`76 source files`) |
| [pytest-full.log](evidence/pytest-full.log) | Full project pytest suite (`63 passed in 19.84s`) |

## Verification

| Check | Result | Scope / evidence |
| --- | --- | --- |
| `.venv/bin/python -m pytest tests/contract/test_data_contracts.py -v` | PASS (`9 passed`) | Contract invariants (`NaN`/`Inf`, bounds, timings, simple `key=val` redaction); [green-contract-tests.log](evidence/green-contract-tests.log) |
| `.venv/bin/python -m ruff check packages/common packages/data_contracts tests/contract` | PASS | Lint & import order on touched packages/tests; [ruff.log](evidence/ruff.log) |
| `.venv/bin/python scripts/check_secrets.py` | PASS (`0` leaks) | Full workspace secret scan; [check-secrets.log](evidence/check-secrets.log) |
| `.venv/bin/python -m mypy packages apps pipelines` | PASS (`76 source files`) | Full package, pipeline, and API/demo type check; [mypy.log](evidence/mypy.log), [mypy-current.log](../../tasks/team-progress-sync-2026-11-18/evidence/mypy-current.log) |
| `.venv/bin/python -m pytest -v` | PASS (`63 passed`) | Full contract, unit, eval, and ASGI smoke suites; [pytest-full.log](evidence/pytest-full.log), [pytest-current.log](../../tasks/team-progress-sync-2026-11-18/evidence/pytest-current.log) |
| Synthetic redaction boundary probes (`K` peer review) | FAIL on 2 boundary cases (`LEAK`) | Traceback/stack redaction (`M0.2-REV-1`) and quoted JSON secret fields (`M0.2-REV-2`); [khuong-peer-review.md](evidence/khuong-peer-review.md), [nguyen-probes.json](../../tasks/team-progress-sync-2026-11-18/evidence/nguyen-probes.json) |

## Open issues

| Issue | Impact | Follow-up / responsible task |
| --- | --- | --- |
| **`M0.2-REV-1` (High):** `SecretRedactingFilter` misses unformatted `exc_info` tracebacks and `stack_info` on first emission | Secrets inside exception messages or stack traces can appear unredacted in formatted log output | Nguyễn Việt Nguyên (`N`) adds traceback/stack redaction and regression tests in `M0.2`; Trần Đình Khương (`K`) re-verifies before `M0.G` |
| **`M0.2-REV-2` (Medium):** `redact_secrets` regex misses quoted JSON secret keys (`{"password": "..."}`) | Structured JSON/dict secret values bypass redaction in logs, `ViralRagError`, and `CanonicalErrorResponse` | Nguyễn Việt Nguyên (`N`) extends `_KV_SECRET_RE` for quoted keys and adds tests in `tests/contract/test_data_contracts.py` before `M0.G` |

## Acceptance and handoff

| Task criterion | Result | Evidence |
| --- | --- | --- |
| Contract tests reject malformed/boundary inputs and unknown fields | Met | [test_data_contracts.py](../../../../tests/contract/test_data_contracts.py), [green-contract-tests.log](evidence/green-contract-tests.log) |
| Timings use `ms` and reject negative / non-finite durations | Met | [logging/__init__.py](../../../../packages/common/logging/__init__.py), [_validators.py](../../../../packages/data_contracts/_validators.py) |
| No `NaN`/`Inf` escapes across `AppSettings` and contracts | Met | `allow_inf_nan=False` + `test_contracts_and_settings_reject_nan_and_inf` |
| Explicit missing-key/quota/error payloads & no credentials in logs | Partially met (2 redaction gaps open) | Simple `key=value`, `AIza*`, `Bearer`, and `AppSettings` repr pass; traceback/stack (`M0.2-REV-1`) and quoted JSON keys (`M0.2-REV-2`) require fix; [khuong-peer-review.md](evidence/khuong-peer-review.md) |
| Peer review of API compatibility by `K` | Met (compatibility `PASS`; redaction follow-up requested) | [khuong-peer-review.md](evidence/khuong-peer-review.md) |

Final task status: **IN_PROGRESS** (API compatibility verified by `K`; awaiting `N`'s fix for `M0.2-REV-1` and `M0.2-REV-2` prior to closing `M0.2` and evaluating `M0.G`).
