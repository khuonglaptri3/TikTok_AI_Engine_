# M2.3 — Workflow Provenance & Verification Ledger

- **Date:** 2026-11-18 (Asia/Ho_Chi_Minh)
- **Task ID:** `M2.3`
- **Primary Owner:** Nguyễn Việt Nguyên (`N`)
- **Peer Reviewer:** Trần Đình Khương (`K`, completed code review, TDD regression fixes, 15 briefs, and `K`-side 30-draft full-transcript claim audit on `2026-11-19`)

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

## Peer Review & 30-Draft Human Claim Audit (`K`, 2026-11-19)
1. Loaded `using-superpowers`, `brainstorming` (*Bounded* path approved by `K`), `test-driven-development`, and `verification-before-completion`.
2. Executed three TDD cycles (`RED -> GREEN`) in `tests/unit/test_offline_draft.py` -> `packages/script_engine/service.py` to fix cross-city fabrication, dish-origin location parsing, `c0.dishes` hijacking, soft-facet retrieval starvation on `20261118_taxonomy_fix_v1`, mid-sentence word slicing / `wps` timing drift, music/placeholder excerpt selection, and `< 3`-word trivial sign-off `cta_text` selection:
   - Round 1: [red-khuong-review-fixes.log](red-khuong-review-fixes.log) (`3 failed, 6 passed`) -> [green-khuong-review-fixes.log](green-khuong-review-fixes.log) (`22 passed`).
   - Round 2: [red-khuong-review-fixes-round2.log](red-khuong-review-fixes-round2.log) (`5 failed, 14 passed`) -> [green-khuong-review-fixes-round2.log](green-khuong-review-fixes-round2.log) (`32 passed`).
   - Round 3: [red-khuong-review-fixes-round3.log](red-khuong-review-fixes-round3.log) (`1 failed, 19 passed`) -> [green-khuong-review-fixes-round3.log](green-khuong-review-fixes-round3.log) (`33 passed`).
3. Authored `15` held-out briefs (`k01..k15` in [khuong_15_queries.jsonl](khuong_15_queries.jsonl)), preserved `nguyen_15_drafts_audit.csv` untouched, generated `30` offline drafts (`0` provider calls) over `20261118_taxonomy_fix_v1` + `bm25-v3`, read 100% of cited full source transcripts across all `30` drafts (`120` beats), adjudicated hard-case clusters `C1–C5` with `K` ([khuong_c1_c5_adjudication.json](khuong_c1_c5_adjudication.json)), and populated `K_*` columns while leaving `N_*` columns untouched ([combined_30_drafts_audit.csv](combined_30_drafts_audit.csv), [khuong_30_drafts_claim_audit.jsonl](khuong_30_drafts_claim_audit.jsonl), [khuong-peer-review.md](khuong-peer-review.md)).
4. Verification on Linux (`Python 3.11.14`):
   - `python3 docs/reports/milestones/M2.3/evidence/run_m2_3_30_drafts_audit.py` -> `30/30` structural/timing/membership/coverage pass, `0` fabricated IDs, `K_supported_factual_claims = 108/120 = 90.00%` ([audit_30.log](audit_30.log), [combined_30_summary.json](combined_30_summary.json))
   - `python3 -m mypy packages/llm tests/unit/test_offline_draft.py tests/unit/test_script_guardrails.py --follow-imports=silent && python3 -m mypy packages/script_engine --follow-imports=silent` -> `EXIT=0` ([mypy-k-review-scoped.log](mypy-k-review-scoped.log))
   - `python3 scripts/check_secrets.py` -> `EXIT=0`, `PASS: Zero secret leaks detected across workspace.` ([check-secrets-k-review.log](check-secrets-k-review.log))

## Final `N` 30-Draft Claim-Audit Sign-Off (`2026-11-19`)
- Contributor `N` reviewed all `30` offline drafts (`120` beats + untruncated cited transcripts from `combined_30_drafts_detailed.jsonl`) and explicitly concurred with `K`'s beat-level entailment judgments on `2026-11-19T16:34+07:00` ([nguyen_signoff_receipt.json](nguyen_signoff_receipt.json)).
- Re-ran [run_m2_3_30_drafts_audit.py](run_m2_3_30_drafts_audit.py) to populate `N_total_factual_claims`, `N_supported_factual_claims`, and `N_citation_coverage_ok` in [combined_30_drafts_audit.csv](combined_30_drafts_audit.csv) (`108/120 = 90.00% >= 90%` supported claims, `30/30 = 100%` citation coverage, `0` fabricated IDs) and update [combined_30_summary.json](combined_30_summary.json). `M2.3` transitioned to `COMPLETE`.
