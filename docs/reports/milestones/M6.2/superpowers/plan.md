# M6.2 — Execution Plan

1. **Task 1 — Held-Out 30-Question Dataset & Guardrails (Complete on this branch):**
   - Author `30` held-out questions (`20` answerable across historical core + fresh `M3.3` ASR videos; `10` no-answer/insufficient-evidence/epistemic refusal cases) in `data/evaluation/m6_2/held_out_questions_30.jsonl`.
   - Verify zero overlap with `v1` and `v2_pilot`, validate `NicheQueryFilter` & `RetrievalRequest` contracts, and probe retrieval/domain guardrails against `data/corpus/m3_3_pilot_snapshot_v2` + `artifacts/indexes/bm25-m3_3-pilot`.
   - Add deterministic unit regression coverage in `tests/unit/test_m6_2_eval_dataset.py`.
2. **Task 2 — Accepted Module Wiring & Offline 30-Repetition Latency Benchmark (Pending `M3.G`/`M4.G`/`M5.G`):**
   - Wire only gate-accepted modules (or explicit provisional flags/abstentions where a gate is incomplete) into `/api/v1/*` and `/demo/`.
   - Run `30` sequential requests (`concurrency = 1`) measuring cold vs warm `p50`/`p95` (`<= 5.0 s`), peak RSS, and separate LLM timings if live free-tier synthesis is toggled.
3. **Task 3 — Two-Human (`N` + `K`) Inspection & `M6.2` Sign-Off:**
   - **Step 3.1 (`K` TDD Hardening, `2026-11-26`):** Add failing tests in `tests/unit/test_m6_2_eval_dataset.py` for (a) blatant non-F&B retrieval abstention (`m6_2_24` Bitcoin/stocks -> `insufficient_evidence=True`, `items=[]`) and (b) concatenated district hashtag `#quan10` location backfill (`m6_2_16` -> `7711004930638630152` cited in `GroundedScriptEngine`); implement fixes in `packages/llm/prompts/templates.py`, `packages/retrieval/service.py`, and `packages/taxonomy/location_poi.py`; verify `RED -> GREEN`.
   - **Step 3.2 (`K` Independent `30/30` Inspection):** Re-run `run_m6_2_eval.py` preserving `N`'s verified fields, inspect generated script beats and cited Gold captions/transcripts across all `30` questions (`wps_estimated` vs `audio_derived`, citation coverage, claim entailment, `10/10` refusals), present the workbook to `K` for explicit confirmation, and record `K_human_verified=True` alongside `N_human_verified=True` (`M6.2` stays `IN_PROGRESS` only until upstream gates `M3.G`/`M4.G`/`M5.G` close).
