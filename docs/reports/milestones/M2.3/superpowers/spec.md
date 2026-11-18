# M2.3 — Specification: Qualified Scripts, Structural Guardrails & Bounded Provider Bounds

- **Date:** 2026-11-18
- **Task ID:** `M2.3`
- **Primary Owner:** Nguyễn Việt Nguyên (`N`)
- **Peer Reviewer:** Trần Đình Khương (`K`)
- **Requirement Source:** [TikTok_AI_Engine_Milestone.md](../../../../planning/TikTok_AI_Engine_Milestone.md) (`M2.3`)

## Scope & Requirements
1. Enforce bounded provider execution in `packages/llm/clients/gemini.py` and `packages/script_engine/service.py`:
   - Enforce per-turn LLM call budget (`<= max_llm_calls_per_turn`, default `2`) and request deadline (`llm_deadline_seconds` via client timeout), mapping timeouts/quota/missing-key errors to explicit bounded exceptions (`ProviderKeyMissingError`, `QuotaBlockedError`) with zero paid fallback.
   - Ensure `offline_grounded` runs with zero provider calls (`$0`).
2. Improve `offline_grounded` beat-level source differentiation in `packages/script_engine/service.py` (`Beat 1` prefers `hook_text`, `Beat 2/3` prefer `body_beats` / `transcript_excerpt`, `Beat 4` prefers `cta_text`) while preserving strict source-excerpt attribution and creative-draft / non-firsthand framing.
3. Verify and strengthen `recalculate_timeline_and_verify` (`packages/llm/guardrails/verifier.py`) for empty, foreign-ID, no-evidence (`valid_evidence_ids == set()`), and timing-mismatch (`abs(delta) <= max(2.0s, 5% target)`) regressions, reporting valid source membership (`valid_citations_ratio`) and required-content coverage (`citation_coverage_ratio`) separately.
4. Author Nguyễn's `15` diverse F&B queries (`evidence/nguyen_15_queries.jsonl`) and run `offline_grounded` over them to emit `evidence/nguyen_15_drafts_audit.csv` with automated structural/membership receipts and blank human claim-audit columns (`N` & `K` review).

## Acceptance Criteria
- Regression tests cover empty, foreign-ID, no-evidence, timing tolerance (`max(2s, 5%)`), timeout/`<=2` call bounds, and beat-level `hook`/`body_beats`/`cta` selection (TDD RED -> GREEN).
- All `15` generated drafts in `nguyen_15_drafts_audit.csv` have `0` fabricated `video_id`s, explicit `creative_draft` / `grounding_verified=False` status, and recorded structural metrics.
- `scripts/check_secrets.py`, `ruff`, `mypy`, and full `pytest` pass cleanly; task remains `IN_PROGRESS` until `K` supplies his `15` queries and both complete the `30`-draft claim audit & review.
