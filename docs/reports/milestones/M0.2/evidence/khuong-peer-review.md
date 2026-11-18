# M0.2 — Peer Review by Trần Đình Khương (`K`)

- **Review date:** 2026-11-18 (Asia/Saigon)
- **Task ID:** `M0.2`
- **Primary Owner:** Nguyễn Việt Nguyên (`N`)
- **Peer Reviewer:** Trần Đình Khương (`K`)
- **Reviewed commits:** `dcf534f7b7bf2ca2bbcb44b88481905ce3105b4e` (authored by `NguyenVietNguyen2612`), merged via PR #1 into `main` at `c3348e93d66ad4eeba133c1d05752d26da18d774`

## 1. Review Summary & Verdict

- **API & Contract Compatibility:** **PASS.** All 76 source files pass `mypy packages apps pipelines` (`0` issues) and all 63 project tests pass (`pytest -v`, `50.47s`), including the live `/demo/` and FastAPI endpoints (`apps/api`, `apps/demo`, `packages/analytics`, `packages/retrieval`, `packages/script_engine`, `packages/seeding`, `packages/absa`). Preserving `AppSettings.gemini_api_key: str` with `repr=False` and custom `__repr__` / `__str__` / `safe_summary()` masking kept existing `.gemini_api_key.strip()` callers 100% compatible.
- **Contract & Numeric Hardening:** **PASS.** `allow_inf_nan=False`, `extra="forbid"` on request and error schemas, non-blank string validators, temporal interval ordering (`end_sec >= start_sec`), quantile ordering (`duration_q25_sec <= duration_median_sec <= duration_q75_sec`, `hashtag_q25 <= hashtag_q75`), 64-character lowercase hex SHA256 and safe basename checks on `CorpusFileChecksum`, and finite non-negative `*_ms` validation on `timings_ms` all behave as specified.
- **Overall Task Status:** **Keep `IN_PROGRESS` pending 2 runtime redaction fixes before `M0.G` (`G0`).** Controlled synthetic boundary probes ([nguyen-probes.json](../../../tasks/team-progress-sync-2026-11-18/evidence/nguyen-probes.json)) reproduced two credential-redaction gaps in `packages/common/logging/__init__.py` and `packages/data_contracts/errors.py` that are not yet covered by `tests/contract/test_data_contracts.py`.

## 2. Open Findings Requiring Follow-Up Before `M0.2` Closure

| ID | Severity | Location | Finding & Minimal Reproduction | Required Fix for `M0.2` Completion |
| --- | --- | --- | --- | --- |
| `M0.2-REV-1` | High | `packages/common/logging/__init__.py:47-59` (`SecretRedactingFilter.filter`) | `SecretRedactingFilter` sanitizes `record.getMessage()` and `record.exc_text` only if `exc_text` is already populated. During a standard `logger.exception(...)` call, `logging.Formatter` formats `record.exc_info` *after* `Handler.filter()` runs, and `record.stack_info` is never sanitized. Consequently, secrets embedded in exception messages or stack traces bypass the filter on first emission (`logger_traceback=LEAK`, `logger_stack_info=LEAK` in [nguyen-probes.json](../../../tasks/team-progress-sync-2026-11-18/evidence/nguyen-probes.json)). | Format/sanitize `exc_info` (or attach a redacting `Formatter` / pre-populate redacted `exc_text` and `stack_info` inside `SecretRedactingFilter.filter`) and add a regression test asserting that `logger.exception(...)` and `stack_info=True` handler outputs contain zero raw secret markers. |
| `M0.2-REV-2` | Medium | `packages/common/logging/__init__.py:15-29` (`redact_secrets`), `packages/common/exceptions/__init__.py:15`, `packages/data_contracts/errors.py:21-24` | `_KV_SECRET_RE` matches `(?:api[_-]?key|token|secret|password)\s*[=:]\s*([^\s,;'"\])}]+)` where the key name is immediately followed by `=` or `:`. In JSON-serialized payloads (`{"password": "..."}`, `{"api_key": "..."}`), the closing quote after the key name prevents matching (`redaction_json=LEAK`, `domain_error_json_secret=LEAK`, `canonical_error_json_secret=LEAK`). | Extend `_KV_SECRET_RE` (or add a quoted-key pattern) in `redact_secrets` so quoted JSON/dict keys (`"password": "..."`, `'token': '...'`) are redacted across logs, `ViralRagError`, and `CanonicalErrorResponse`, and add unit tests in `tests/contract/test_data_contracts.py`. |
| `M0.2-REV-3` | Low | `docs/reports/milestones/M0.2/README.md` | The initial `M0.2` report described changes as uncommitted on `main` (`b12af51f`) due to a sandbox branch lock, whereas `dcf534f` is now merged on `main` (`c3348e9`). | Refreshed in `M0.2/README.md` during this peer review while preserving all original verification logs untouched. |

## 3. Verification Evidence Checked by Reviewer

- [nguyen-progress.md](../../../tasks/team-progress-sync-2026-11-18/evidence/nguyen-progress.md) and [nguyen-probes.json](../../../tasks/team-progress-sync-2026-11-18/evidence/nguyen-probes.json)
- [pytest-current.log](../../../tasks/team-progress-sync-2026-11-18/evidence/pytest-current.log) (`63 passed in 50.47s` at `c3348e9`)
- [mypy-current.log](../../../tasks/team-progress-sync-2026-11-18/evidence/mypy-current.log) (`Success: no issues found in 76 source files` at `c3348e9`)
- [secrets-current.log](../../../tasks/team-progress-sync-2026-11-18/evidence/secrets-current.log) (`PASS: Zero secret leaks detected across workspace.`)
