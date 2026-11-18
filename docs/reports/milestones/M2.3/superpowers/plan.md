# M2.3 — Execution & Verification Plan

- **Date:** 2026-11-18
- **Task ID:** `M2.3`
- **Primary Owner:** Nguyễn Việt Nguyên (`N`)

## Execution Steps
1. **TDD RED:** Expand `tests/unit/test_script_guardrails.py` and `tests/unit/test_offline_draft.py` with tests covering:
   - `valid_evidence_ids == set()` (no-evidence) failing cleanly with `passed=False` and empty citations;
   - `BoundedGeminiClient` enforcing `llm_deadline_seconds` timeout bound (mapped to `QuotaBlockedError`) and `GroundedScriptEngine` enforcing `<= max_llm_calls_per_turn` (`2` calls/turn);
   - `offline_grounded` differentiating `hook_text` (Beat 1), `body_beats` (Beat 2/3), and `cta_text` (Beat 4) when all fields are present on evidence cards.
   - Capture RED failure output in `evidence/red-m2_3-tests.log`.
2. **Implement Hardening (`packages/llm/` & `packages/script_engine/`):**
   - Update `BoundedGeminiClient.generate_structured_json` in `packages/llm/clients/gemini.py` to enforce `llm_deadline_seconds` timeout (`http_options`), map timeout/network errors cleanly into bounded `QuotaBlockedError`, and track per-turn call budget (`<= max_llm_calls_per_turn`).
   - Update `recalculate_timeline_and_verify` in `packages/llm/guardrails/verifier.py` to add an explicit no-evidence warning when `valid_evidence_ids` is empty.
   - Update `_build_offline_grounded_draft` and `generate` in `packages/script_engine/service.py` to pick role-appropriate source excerpts (`hook_text` / `body_beats` / `cta_text`) per beat and enforce per-turn LLM call budget `<= max_llm_calls_per_turn`.
3. **15-Query Draft Generation & Audit Sheet (`evidence/run_m2_3_audit.py`):**
   - Author `15` diverse Vietnamese F&B briefs (`evidence/nguyen_15_queries.jsonl`), run `GroundedScriptEngine` (`offline_grounded`, `$0`, `0` provider calls), and export `evidence/nguyen_15_drafts_audit.csv` + `evidence/nguyen_15_summary.json`.
4. **TDD GREEN & Full Verification:**
   - Run `pytest tests/unit/test_script_guardrails.py tests/unit/test_offline_draft.py -v` -> `evidence/green-m2_3-tests.log`.
   - Run `ruff`, `scripts/check_secrets.py`, `mypy`, and full `pytest -v`.
   - Author `docs/reports/milestones/M2.3/README.md`, `evidence/workflow.md`, and update `docs/reports/milestones/README.md`.
