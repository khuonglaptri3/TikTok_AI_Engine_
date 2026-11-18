# Incoming M0.2 delivery review

- Review date: 2026-11-18 (Asia/Saigon).
- Reviewed revision: `c3348e93d66ad4eeba133c1d05752d26da18d774`, merge of PR #1.
- Incoming implementation: `dcf534f7b7bf2ca2bbcb44b88481905ce3105b4e`, authored and committed by `NguyenVietNguyen2612` on 2026-11-17 at 16:37:01 +07:00.
- Comparison: `b12af51..origin/main`; 24 changed files, 1,076 insertions and 222 deletions.
- Authorization and limits: delegated read-only code/progress review under the owner's synchronization request and this task's [specification](../superpowers/spec.md) and [plan](../superpowers/plan.md). Only this review and synthetic probe evidence were written. No fixes, milestone status edits, commits, pushes, crawls or provider calls were performed.

## Conclusion

Nguyen has delivered and merged a substantial M0.2 implementation: typed contract validation, finite response timings, masked settings representations, domain-error sanitization helpers and expanded executable tests. This is code and verification evidence, rather than a plan-only contribution. The incoming diff changes no corpus, index, acquisition worker, new data batch or taxonomy sample.

**Keep M0.2 IN_PROGRESS.** Independent controlled probes reproduce two credential-redaction gaps in the new logging/error code. The M0.2 report already leaves peer review pending, but its assertion that no credentials can enter logs/error payloads is broader than the observed behavior. An existing merge does not settle that acceptance criterion. **G0 remains NOT_RUN**, separately from M0.2: M0.G also requires reviewed M0.1/M0.3 evidence and the recorded foundation decision.

## Delivered behavior

| Area | Observed implementation | Qualification |
| --- | --- | --- |
| Contracts | `allow_inf_nan=False` across the contract models; blank request/identifier rejection; unknown request/error fields forbidden; checksum hex/local-filename checks; duration/hashtag quantile ordering; subset-count checks | Reviewed in the incoming diff. Existing persisted model shapes and request defaults are retained. |
| Timing | `StageTimer` clamps non-finite or negative clock differences to finite, non-negative millisecond values; response timing dictionaries require `_ms` names and finite non-negative values | A synthetic non-finite-clock probe returned `step_ms=0.0`, `total_ms=0.0`. This clamping behavior does not expose a clock-failure flag. |
| Settings | `.gemini_api_key` remains a string for existing `.strip()` callers; `repr`, `str` and `safe_summary()` mask its value and URL passwords | Controlled probes verified masking in `repr` and `safe_summary`. Ordinary `model_dump()` retains actual settings values; the new log-safe surface is specifically `safe_summary`/`repr`/`str`. |
| Errors | Existing 503/429/422 domain status mappings remain; error messages pass through shared redaction | JSON-formatted credentials are not fully covered; see findings below. |
| Tests | Contract module grows from 3 to 9 collected cases, with additional validation assertions and parameterized NaN/Inf cases | Contributor logs report 63 total tests, compared with the prior 57-test baseline. Full-suite success cannot prove untested redaction boundaries. |
| Reporting | M0.2 has its own README, evidence and exactly two planning files; index row is IN_PROGRESS | The current report still describes an uncommitted pre-branch state, although the changes are now merged. |

## Findings requiring follow-up before M0.2 closure

### 1. High: exception and stack text bypass the new logging filter

Source: [logging helpers](../../../../../packages/common/logging/__init__.py), lines 47-59.

`SecretRedactingFilter.filter()` sanitizes `record.getMessage()` and only sanitizes `record.exc_text` when that attribute is already populated. On the ordinary first `logger.exception(...)` emission, `exc_text` is still unset: `logging.Formatter` renders `record.exc_info` after handler filtering. The exception text therefore reaches the output without redaction. `record.stack_info` is also not sanitized.

Controlled results in [nguyen-probes.json](nguyen-probes.json): `logger_message=REDACTED`, `logger_traceback=LEAK`, `logger_stack_info=LEAK`. Only synthetic marker strings were used. This is a reproduced helper defect, not evidence that an actual owner credential leaked.

Minimal reproduction, with a `StreamHandler` carrying `SecretRedactingFilter`:

```python
marker = "synthetic_probe_" + "credential_value"
try:
    raise ValueError("password=" + marker)
except ValueError:
    logger.exception("operation failed")
# The formatted handler output still contains marker.
```

Required follow-up: sanitize the fully formatted exception/stack content or otherwise ensure those channels are safely rendered; add a regression that checks the actual handler output for a first exception emission. Nguyen owns the M0.2 implementation follow-up; K independently reviews and reproduces it.

### 2. Medium: quoted JSON secret fields bypass redaction in logs and API errors

Source: [logging helpers](../../../../../packages/common/logging/__init__.py), lines 15-16 and 21-29; [domain exceptions](../../../../../packages/common/exceptions/__init__.py), line 15; [canonical error model](../../../../../packages/data_contracts/errors.py), lines 21-24.

The key/value regex expects `password`, `token`, `api_key`, etc. to be followed directly by whitespace and `=` or `:`. The closing quote in a normal JSON key prevents matching. For example, `redact_secrets(json.dumps({"password": marker}))` retains the synthetic marker. The same input remains visible in `QuotaBlockedError(...).message` and `CanonicalErrorResponse(...).model_dump_json()`, both of which use the shared helper. The separate Google-key regex does cover matching `AIza...` values; it does not solve arbitrary passwords or access tokens in quoted mappings.

Controlled results: `redaction_kv=REDACTED`, `redaction_json=LEAK`, `domain_error_json_secret=LEAK`, `canonical_error_json_secret=LEAK` in [the probe evidence](nguyen-probes.json).

Required follow-up: include structured/quoted credential cases in the shared redaction boundary and test both log output and serialized error payloads. Avoid claiming complete credential coverage from the current simple `key=value` test alone.

### 3. Low: refresh publication provenance in the current M0.2 report

Source: [M0.2 report](../../../milestones/M0.2/README.md), lines 6, 48-49 and 61.

The current narrative still says the changes are uncommitted on `main`, branch creation is blocked, and publication is a next step. Git now establishes the contributor commit and merged PR above. Preserve historical command receipts while updating the current narrative to the actual integrated revision and the remaining review/fix work. The stronger redaction acceptance assertion at lines 12 and 58 also needs qualification until findings 1-2 are resolved.

## Compatibility and remaining contract boundaries

The inspected production timer call sites in analytics, retrieval, script generation and the trust route already use `_ms` suffixes, so the new response-key validation aligns with those paths. The retained `StageTimer.measure("parse")` compatibility intentionally returns `parse`, while a response constructed with that dictionary rejects it. A synthetic probe confirmed this difference; it is a documented internal/public boundary, rather than a demonstrated failure of a current endpoint. Callers adding stages must retain `_ms` naming when passing the dictionary into a response.

No breaking field removal or type change was found in the incoming contract diff. The tightened whitespace/unknown-field rules deliberately reject some formerly accepted malformed requests. The reviewer did not independently run the full API/demo suite; the coordinating agent owns the fresh suite and type/secret checks for this synchronized revision. Do not read this source inspection as an unconditional API compatibility approval.

The following older or wider-scope gaps remain distinguishable from the new redaction defects:

| Boundary | Observed fact | Implication / receiving work |
| --- | --- | --- |
| Manifest completeness and dates | `CorpusManifest` accepts an empty file list and an invalid `created_at`/inverted date window. The synthetic constructor probe reproduced this. `load_verified_corpus()` separately rejects missing required files and duplicates and verifies declared SHA256 values before loading. | Model-level validation is narrower than full snapshot acceptance. Do not describe the constructor as verifying actual table rows, columns, byte sizes or calendar provenance. M1.1/M1.2 own lineage and full integrity review. No hash bypass of the actual current loader was demonstrated. |
| Segment bounds | New validators enforce `end >= start`, matching the M0.2 specification. A 5-second raw record still accepts a zero-duration segment or a segment from 10 to 20 seconds. | Existing input models lack media-duration cross-checks. The active M4.1 requirement is stricter: `0 <= start < end <= media_duration`. This is future/unaccepted temporal quality, not a newly introduced M0.2 regression. |
| Timestamp wording | `VoiceSegmentRecord.timestamp_source` still permits `whisper_exact`; `_build_voice_segments()` still emits that value. | The active plan calls ASR boundaries `audio_derived` estimates. Reconcile terminology and strict media bounds in M3/M4 before claiming precise audio evidence. Current contract hardening does not complete that work. |
| Raw creation date | `RawIncrementalVideoRecord.create_time` is checked only for a non-blank string. Ingestion catches parse failure and substitutes the current UTC time (`converter.py:208-211`). | Freshness provenance is not established by this string validator. M3.1/M3.2 need fail-closed/date-provenance review before a live acquisition pilot. This behavior predates the incoming commit. |
| Configured call cap | `AppSettings(max_llm_calls_per_turn=5)` remains accepted (`settings/__init__.py:35`); the same upper bound existed before this change. | The setting does not encode AGENTS.md's two-call ceiling. No live call was made and no current execution exceeding the ceiling was demonstrated; retain this as an inherited configuration-boundary follow-up for M0.2/M2.3. |

## Claimed versus independently observed verification

| Evidence | Contributor's committed record | This delegated review |
| --- | --- | --- |
| Contract tests | 9 passed in 0.18 seconds on Linux/Python 3.12.3 | Test source and complete committed GREEN log read; no duplicate test run here. |
| Full suite | 63 passed in 19.84 seconds | Complete committed full-suite log read; fresh local suite is assigned to the coordinating agent. No independent full-suite PASS is claimed in this file. |
| mypy | Success over 76 source files | Committed receipt read; fresh command assigned to the coordinating agent. |
| Ruff | Scoped common/contracts/tests PASS | Committed receipt read; not independently rerun here. |
| Secret scanner | Zero leaks | Committed receipt read; fresh scan assigned to the coordinating agent. A static secret scan does not validate runtime redaction. |
| RED provenance | Recorded collection-time ImportError for missing `SecretRedactingFilter`; 0 collected items, exit 2 | This demonstrates an expected missing API before implementation. It is not separate observed RED assertion failures for every added invariant. No additional unrecorded RED tests are inferred. |
| Synthetic boundary probes | Not part of the incoming evidence | Fresh Python 3.12.14 execution, exit 0, output in [nguyen-probes.json](nguyen-probes.json). Finite timer/settings behavior held; logging/error gaps reproduced. |
| Diff whitespace | Not supplied as an incoming receipt | `git diff --check b12af51..origin/main` exited 1 on the added milestone index row's CRLF/trailing-whitespace treatment. This is a formatting observation, not a runtime failure; no rewrite of checksum-bound evidence was attempted. |

Probe invocation used an inline Python program piped to `uv run --no-project --python 3.12 --with '.[demo,dev]' python -`. The first attempt used an invalid logging `extra={"stack_info": ...}` override and exited before producing a result; the corrected probe constructs a `LogRecord` with `sinfo` and completed. The saved JSON contains only that completed run's results plus the completed domain/canonical error follow-up. It contains no real credentials. The timer probe mocks only `time.perf_counter`; no provider, network, collector, snapshot publication or data mutation is involved.

## Next assignments and gate interpretation

The [kickoff](../../team-kickoff-and-push-2026-11-17/README.md) and [active allocation](../../../../planning/TikTok_AI_Engine_Milestone.md) remain authoritative:

1. Nguyen completes the M0.2 redaction follow-up, refreshes its current report and submits the actual validation evidence; K performs and records API compatibility review. M0.2 stays IN_PROGRESS until its criteria are met.
2. K reconciles M0.1 preservation/provenance/rights gaps and M0.3 install/package/API/demo reproduction. Nguyen independently verifies input/artifact receipts and installation/demo behavior on his own machine.
3. After the contract baseline, Nguyen leads M1.1 taxonomy/lineage review: 120 stratified records, with both contributors annotating 30 overlapping records and reporting agreement and field-level errors. K leads M1.2 after its listed prerequisites and reviews Nguyen's M1.1 outputs.
4. Nguyen owns M0.G evidence assembly/decision with K's peer review after M0.1-M0.3 are reviewed. No G0 PASS follows merely from PR #1 or a 63-test log.

Equal allocation is unchanged: 94 estimated effort points each across the active roadmap. This review verifies submitted work, not actual hours or unreported availability.

## Actual process provenance

- Read `C:/Users/lanph/.codex/plugins/cache/openai-curated-remote/superpowers/7.0.1/skills/using-superpowers/SKILL.md`; its explicit subagent instruction exempts a dispatched specific-task subagent from the conversation-start workflow.
- Read this task's canonical specification/plan and repository `AGENTS.md` before source review.
- Read the installed 7.0.1 `systematic-debugging/SKILL.md`; applied root-cause investigation and minimal controlled hypotheses to the redaction boundary. No implementation/fix phase was authorized or performed.
- Read the installed 7.0.1 `verification-before-completion/SKILL.md`; completion assertions in this file are limited to inspected Git/source records and the completed probes. Broader suite results are explicitly contributor claims or coordinating-agent responsibilities.
- Incoming M0.2 `evidence/workflow.md` states that process skill files were unavailable on the contributor machine and that an equivalent document/TDD process was used. That is a reported limitation, not proof of installed Superpowers execution; this review does not retroactively relabel the contributor's work.

Review output is complete for the delegated read-only scope. Findings remain open; no product or milestone acceptance is approved by this evidence file.
