# M2.3 — Workflow Provenance & Verification Ledger

- **Date:** 2026-11-18 (Asia/Ho_Chi_Minh)
- **Task ID:** `M2.3`
- **Primary Owner:** Nguyễn Việt Nguyên (`N`)
- **Peer Reviewer:** Trần Đình Khương (`K`, pending)

## Process & Decisions
1. Branched `feat/m2.3-script-guardrails` from `main` (`c3348e93`) and authored `superpowers/spec.md` and `superpowers/plan.md` prior to code edits.
2. Wrote TDD RED regressions first (`tests/unit/test_script_guardrails.py` & `tests/unit/test_offline_draft.py`) covering:
   - Empty `valid_evidence_ids` (`no-evidence`) failing closed with warning;
   - `BoundedGeminiClient` enforcing per-turn call budget (`<= max_llm_calls_per_turn`) and `llm_deadline_seconds` (`HttpOptions(timeout=timeout_ms)`), mapping timeouts to bounded `QuotaBlockedError`;
   - `_build_offline_grounded_draft` differentiating `hook_text` (Beat 1), `body_beats` (Beat 2/3), and `cta_text` (Beat 4).
3. Refused to pad offline templates with invented facts when `target_duration_sec` exceeds safe reference wording (`3/15` briefs — `n03`, `n04`, `n09` — fell slightly short of the strict `max(2s, 5%)` timeline tolerance by `2.4s–4.6s` and were accurately flagged `timing_valid=False` by the guardrail).
4. Authored `N`'s `15` held-out briefs (`nguyen_15_queries.jsonl`) and ran `offline_grounded` (`0` provider calls), leaving human claim entailment columns and `K`'s `15` briefs blank for two-person review.

## Commands & Verification Receipts
- `.venv/bin/python -m pytest tests/unit/test_script_guardrails.py tests/unit/test_offline_draft.py -v` (RED) -> `EXIT=1`, `2 failed, 17 passed` ([red-m2_3-tests.log](red-m2_3-tests.log))
- `.venv/bin/python -m pytest tests/unit/test_script_guardrails.py tests/unit/test_offline_draft.py -v` (GREEN) -> `EXIT=0`, `19 passed in 0.79s` ([green-m2_3-tests.log](green-m2_3-tests.log))
- `.venv/bin/python docs/reports/milestones/M2.3/evidence/run_m2_3_audit.py` -> `15/15` valid membership & citation coverage, `0` fabricated IDs, `12/15` `timing_valid`, `0` provider calls ([audit_15.log](audit_15.log), [nguyen_15_summary.json](nguyen_15_summary.json))
- `.venv/bin/python -m ruff check packages/llm packages/script_engine tests/unit/test_script_guardrails.py tests/unit/test_offline_draft.py` -> `EXIT=0`, `All checks passed!` ([ruff.log](ruff.log))
- `.venv/bin/python -m mypy packages apps pipelines` -> `EXIT=0`, `Success: no issues found in 76 source files` ([mypy.log](mypy.log))
- `.venv/bin/python -m pytest -v` -> `EXIT=0`, `66 passed in 15.89s` ([pytest-full.log](pytest-full.log))
- `.venv/bin/python scripts/check_secrets.py` -> `EXIT=0`, `PASS: Zero secret leaks detected across workspace.` ([check-secrets.log](check-secrets.log))

## Follow-up Gemini Claim-Entailment Audit (`2026-11-19`, `feat/m2.2-m2.3-llm-audit`)
- Per contributor override (`<= 15 RPM`), ran `audit_claims_with_gemini.py --batch-size 3 --max-rpm 14` (`gemini-3.1-flash-lite`, `5` requests) over `nguyen_15_drafts_audit.csv`.
- Observed `47/55` (`85.45%`) supported factual claims and `15/15` (`100%`) `citation_coverage_ok`; results persisted in `nguyen_15_llm_claim_audit.json` and `nguyen_15_drafts_audit.csv` while keeping `human_claim_audit_completed=False`.
