# M0.2 — Specification: Contracts, Bounded Settings, Error Hygiene & Finite Timings

- **Date:** 2026-11-17
- **Task ID:** `M0.2`
- **Primary Owner:** Nguyễn Việt Nguyên (`N`)
- **Peer Reviewer:** Trần Đình Khương (`K`)
- **Requirement Source:** [TikTok_AI_Engine_Milestone.md](../../../../planning/TikTok_AI_Engine_Milestone.md) (`M0.2`) & [team-kickoff-and-push-2026-11-17](../../../tasks/team-kickoff-and-push-2026-11-17/README.md)

## Scope & Requirements
1. Revalidate `packages/common/` (`settings`, `logging`, `exceptions`) and `packages/data_contracts/` (`analytics`, `corpus`, `errors`, `multimodal`, `query`, `retrieval`, `script`) while preserving backward compatibility for all existing callers and endpoints.
2. Enforce **no `NaN` / `Inf` escapes** across all Pydantic v2 contract models and `AppSettings` numeric bounds (`allow_inf_nan=False`, finite non-negative numeric invariants).
3. Enforce **timings in `ms`**: `StageTimer` records finite non-negative millisecond stages and `total_ms`; response contracts carrying `timings_ms` reject negative, non-finite, or non-`_ms` keys (while permitting empty `{}` when not measured in isolated unit tests).
4. Enforce **malformed / boundary & missing/unknown field rejection**:
   - Strict `extra="forbid"` on query/error/input contracts where unknown fields must fail fast (`NicheQueryFilter`, `RetrievalRequest`, `ScriptGenerationRequest`, `TrustAuditRequest`, `CanonicalErrorResponse`).
   - Reject blank/whitespace-only required text (`query`, `brief`, `transcript`, `comment_id`, `video_id`, `snapshot_id`, `code`, `message`, `StageTimer` stage names) and empty/whitespace-only filter strings.
   - Enforce temporal/quantile/checksum invariants: `end_sec >= start_sec` (`RawWhisperSegment`, `VoiceSegmentRecord`), `duration_q25_sec <= duration_median_sec <= duration_q75_sec` & `hashtag_q25 <= hashtag_q75` (`NicheBenchmarkSummary`), valid 64-char hex SHA256 and safe local filenames (`CorpusFileChecksum`, `CorpusManifest`), and subset counts `<= total_videos`.
5. Enforce **explicit missing-key / quota / domain error payloads & no credentials in logs**:
   - `AppSettings.__repr__` / `__str__` and safe redaction utilities (`redact_secrets`, `SecretRedactingFilter`, `get_safe_logger`) mask `gemini_api_key`, `AIza*` keys, `Bearer` tokens, `key=` query parameters, and URL passwords so credentials never enter logs or error payloads.
   - `ViralRagError` subclasses sanitize messages before serialization into `CanonicalErrorResponse` and preserve exact HTTP statuses (`503 PROVIDER_KEY_MISSING`, `429 QUOTA_BLOCKED`, `503 CORPUS_NOT_READY`, `503 INDEX_NOT_READY`, `422 UNSUPPORTED_DOMAIN`).

## Acceptance Criteria
- Executable contract tests fail on malformed, whitespace-only, out-of-range, inverted-interval, `NaN`/`Inf`, negative/`non-ms` timing, unknown-field, and credential-leakage scenarios (TDD RED -> GREEN).
- All existing API/demo endpoints and test suites remain compatible (`mypy packages apps pipelines`, `pytest`, `scripts/check_secrets.py`, and `ruff` pass with zero regressions).
- Peer review of API compatibility completed by Trần Đình Khương (`K`) before gate `M0.G`.
