# M6.2 — Source-Resolving Q&A and Demo Integration Specification

- **Task ID:** `M6.2`
- **Status:** `IN_PROGRESS` (Held-out 30-question evaluation set prepared; integration gating, 30-repetition offline latency benchmark `p95 <= 5 s`, and joint `N`+`K` answer/provenance inspection pending downstream `M3.G`, `M4.G`, `M5.G` outcomes)
- **Date:** `2026-11-25`
- **Requirement Source:** [TikTok_AI_Engine_Milestone.md](../../../planning/TikTok_AI_Engine_Milestone.md) (`M6.2`)
- **Primary Contributors:** `N` (integration & error-state reviewer) & `K` (joint answer/ID/provenance inspector)

## Scope

1. Prepare a **30-question held-out evaluation dataset** ([held_out_questions_30.jsonl](../../../../data/evaluation/m6_2/held_out_questions_30.jsonl)) disjoint from `M2.1`/`M2.2` (`v1`, `v2_pilot/dev_queries.jsonl`, `v2_pilot/test_queries.jsonl`).
2. Include **`20` answerable F&B questions** (`12` historical core with `wps_estimated` pacing + `8` fresh `M3.3` audio/ASR-grounded videos with `audio_derived` provenance) and **`10` no-answer / insufficient-evidence / guardrail questions** (`>= 10` required).
3. Integrate only capabilities accepted by prior gates into typed FastAPI routes (`/api/v1/*`) and the single Gradio `/demo/` interface, preserving honest limits when any downstream gate remains incomplete.
4. Measure 30-repetition single-concurrency offline request latency (`p95 <= 5.0 s`, excluding startup artifact load, separating optional free-tier LLM call latency) and conduct two-contributor (`N` + `K`) inspection across all `30` outputs.

## Acceptance Criteria

- `100%` valid source IDs/spans and zero fabricated timestamps (never present `wps_estimated` pacing as audio-exact).
- `>= 95%` factual citation coverage and `>= 90%` supported factual claims on answerable questions.
- `100%` bounded insufficient-evidence / domain / epistemic refusal behavior on the `10` no-answer cases.
- Offline request `p95 <= 5.0 s` over `30` repetitions (`concurrency = 1`, hardware recorded).
