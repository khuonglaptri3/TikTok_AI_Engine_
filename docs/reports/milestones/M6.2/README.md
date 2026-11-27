# M6.2 — Source-Resolving Q&A and Demo Integration

- Status: COMPLETE (`30`-question evaluation dataset, 2 `K` TDD fixes for `#quan10` backfill & non-F&B retrieval abstention, `30`-question offline ASGI latency benchmark `p50 = 40.32 ms` / `p95 = 69.00 ms <= 5,000 ms`, `180/180 = 100%` valid answerable citations, `10/10 = 100%` strict refusals, live `M3`–`M6` multimodal corpus wiring into `apps/api` & `/demo/`, and **both `N` (`30/30`) and `K` (`30/30`) human answer/provenance inspections (`18/20 = 90.0%` supported each, `28/30 = 93.33%` agreement)** complete; upstream `M3.G`, `M4.G`, `M5.G`, and `M6.1` closed `PASS` / `COMPLETE` on `2026-11-27`)
- Execution date: 2026-11-25 to 2026-11-27 (Asia/Ho_Chi_Minh)
- Requirement source: [TikTok_AI_Engine_Milestone.md](../../../planning/TikTok_AI_Engine_Milestone.md) (`M6.2`)
- Primary owner: Trần Đình Khương (`K`, `7` pts) · Peer reviewer: Nguyễn Việt Nguyên (`N`, `3` pts)
- Specification: [spec.md](superpowers/spec.md)
- Execution plan: [plan.md](superpowers/plan.md)

## Conclusion

Completed the **`30`-question held-out Q&A/demo evaluation**, two-contributor (`N` `30/30` + `K` `30/30`) full beat-vs-source provenance inspection ([m6_2_joint_inspection_receipt.json](evidence/m6_2_joint_inspection_receipt.json)), live `M3`–`M6` multimodal Gold corpus integration into `apps/api` and `/demo/`, and `K`'s TDD hardening across retrieval and caption hashtag location backfill (`p95 = 69.00 ms <= 5,000 ms`, `180/180 = 100%` valid answerable citations, `0` citations on all `10/10` no-answer cases). With upstream gates `M3.G`, `M4.G`, and `M5.G` confirmed `PASS` and `M6.1` `COMPLETE`, **`M6.2` is `COMPLETE`**:

- **100% Source Identity, Temporal Provenance & Fresh `M3.3` Parity (`180/180` citations):** Every retrieved item and script beat across all `20` answerable prompts resolves 1-to-1 to `m3_3_pilot_snapshot_v2` (`100%` citation coverage), qualifying historical rows as `wps_estimated` and fresh ASR rows as `audio_derived` (never exact speech timing). After adding concatenated district hashtag aliases (`#quan10`, `#tanphu`, `#binhthanh`) in [location_poi.py](../../../../packages/taxonomy/location_poi.py), **`8/8` (`100%`)** fresh `M3.3` queries hit their target `audio_derived` video at Rank #1 in retrieval AND cite it directly in `/api/v1/script/generate` (including `m6_2_16` -> `7711004930638630152`).
- **Two-Person Claim Entailment & `10/10` Bounded Refusals ([m6_2_answers_sheet.jsonl](evidence/m6_2_answers_sheet.jsonl)):**
  - `N` (`18/20 = 90.0%`) and `K` (`18/20 = 90.0%`, mean **`90.0% >= 90.0%`**; unadjudicated intersection `17/20 = 85.0%` with `m6_2_06` Cần Thơ dish-splitting and `m6_2_07` Vũng Tàu intro-beat selection preserved transparently) independently audited all `20` answerable drafts (`28/30 = 93.33%` exact agreement across all `30` prompts).
  - After wiring `is_blatant_out_of_domain_query` into `HybridRetrievalService.search` ([service.py](../../../../packages/retrieval/service.py)), all **`10/10` (`100%`)** no-answer prompts (`m6_2_21`–`m6_2_30`: `4` epistemic refusals, `1` non-F&B Bitcoin/stocks domain refusal, `2` OOV dishes, `2` unindexed provinces, `1` negation-only query) abstain cleanly in retrieval (`insufficient_evidence = true`, `0` hits) and either fail closed with HTTP `422 UNSUPPORTED_DOMAIN` (`5/10`) or emit `0` citations with explicit insufficient-evidence warnings (`5/10`).
- **Offline CPU Latency & Error Boundaries ([m6_2_offline_dry_run_receipt.json](evidence/m6_2_offline_dry_run_receipt.json)):** Single-concurrency ASGI combined latency (`concurrency = 1`, `4` CPU cores, `1,096.88 MiB` peak RSS, `9.66 s` startup artifact load excluded) achieved **`p50 = 40.32 ms`**, **`p95 = 69.00 ms <= 5,000 ms`**, and `max = 70.96 ms` (`0` LLM calls; `503 PROVIDER_KEY_MISSING`, `422 UNSUPPORTED_DOMAIN`, and `diagnostic_only_unvalidated` trust policy verified).

## Work performed

- **Held-out `30`-question pool & epistemic/location guardrails (`N` & `K`):** Authored [held_out_questions_30.jsonl](../../../../data/evaluation/m6_2/held_out_questions_30.jsonl) (`0` overlap with `v1`/`v2_pilot`), implemented `detect_unsupported_epistemic_claim`, `is_blatant_out_of_domain_query` ([templates.py](../../../../packages/llm/prompts/templates.py)), and concatenated `#quan1`–`#quan12` district hashtag resolution ([location_poi.py](../../../../packages/taxonomy/location_poi.py)), verified by `3/3` TDD tests in [test_m6_2_eval_dataset.py](../../../../tests/unit/test_m6_2_eval_dataset.py).
- **Two-contributor `30/30` inspection & Studio `/demo/` integration (`N` & `K`):** Executed [run_m6_2_eval.py](evidence/run_m6_2_eval.py), verified Studio `/demo/` UI ([ui.py](../../../../apps/demo/ui.py), [visuals.py](../../../../apps/demo/visuals.py)), and recorded both `N` (`30/30`) and `K` (`30/30`) verified judgments in [m6_2_answers_sheet.jsonl](evidence/m6_2_answers_sheet.jsonl) and [m6_2_joint_inspection_receipt.json](evidence/m6_2_joint_inspection_receipt.json).

## Outputs

| File | Purpose |
| --- | --- |
| [m6_2_joint_inspection_receipt.json](evidence/m6_2_joint_inspection_receipt.json) | Two-contributor (`30/30 N` + `30/30 K`) claim/citation/provenance/refusal receipt (`18/20 = 90.0%` each, `180/180` citations, `p95 = 69.00 ms`) |
| [m6_2_answers_sheet.jsonl](evidence/m6_2_answers_sheet.jsonl) | Per-question ASGI outputs with `N_human_verified = true` (`30/30`) and `K_human_verified = true` (`30/30`) |
| [m6_2_offline_dry_run_receipt.json](evidence/m6_2_offline_dry_run_receipt.json) | Single-concurrency latency (`p50 = 40.32 ms`, `p95 = 69.00 ms`), RSS (`1,096.88 MiB`), and `180/180` resolution receipt |
| [held_out_questions_30.jsonl](../../../../data/evaluation/m6_2/held_out_questions_30.jsonl) | `30` disjoint held-out Q&A/guardrail prompts (`inspector_N` & `inspector_K` verified) |
| [run_m6_2_eval.py](evidence/run_m6_2_eval.py) / [test_m6_2_eval_dataset.py](../../../../tests/unit/test_m6_2_eval_dataset.py) | Reproducible ASGI evaluation runner and `3` schema/epistemic/hashtag TDD regression tests |
| [workflow.md](evidence/workflow.md) | Two-contributor (`N` + `K`) TDD bugfix and inspection provenance ledger |

## Verification

| Check | Result | Scope / evidence |
| --- | --- | --- |
| `python3 docs/reports/milestones/M6.2/evidence/run_m6_2_eval.py` | PASS (`p95 = 69.00 ms`, `180/180` valid IDs, `10/10` strict refusals) | `m3_3_pilot_snapshot_v2` + `bm25-m3_3-pilot`; `8/8` fresh `M3.3` targets cited in both retrieval & script; [m6_2_offline_dry_run_receipt.json](evidence/m6_2_offline_dry_run_receipt.json) |
| `python3 -m pytest tests/unit/test_m6_2_eval_dataset.py -v` | PASS (`3 passed in 0.74s`) | Disjoint `30`Q contract, epistemic `422` refusals, `#quan10` district backfill, and non-F&B retrieval abstention |
| `python3 -m pytest -q` & `python3 -m mypy` (Linux & `--platform win32`) | PASS (`271 passed, 10 skipped`; `117` source files `0` errors) | Full workspace regression and cross-platform static typing |
| `python3 scripts/check_secrets.py` & docs hygiene check | PASS (`0` leaks; `0` broken links) | Repository secret hygiene and `M6.2/` layout compliance |

## Open issues

| Issue | Impact | Follow-up / responsible task |
| --- | --- | --- |
| Preserved `2/20` answerable claim-support disagreements (`m6_2_06` Cần Thơ dish-splitting & `m6_2_07` Vũng Tàu intro-beat selection) | Mean two-inspector support is `90.0% >= 90.0%` (`18/20` each); unadjudicated intersection `17/20 = 85.0%` is reported transparently alongside diagnostic-only `M5.1` comment policy | Recorded transparently in [m6_2_joint_inspection_receipt.json](evidence/m6_2_joint_inspection_receipt.json) and [M6.G](../M6.G/README.md) |

## Acceptance and handoff

| Task criterion | Result | Evidence |
| --- | --- | --- |
| Disjoint `30` held-out questions including `>= 10` no-answer/insufficient-evidence cases | Met (`20` answerable + `10` no-answer; `0` overlap with `v1`/`v2_pilot`) | [held_out_questions_30.jsonl](../../../../data/evaluation/m6_2/held_out_questions_30.jsonl) |
| `100%` source resolution & honest temporal provenance (`wps_estimated` vs `audio_derived`), `>= 95%` citation coverage, `>= 90%` supported claims, `100%` bounded no-answer refusals | Met (`180/180 = 100%` resolved & cited; `N = 18/20 = 90.0%`, `K = 18/20 = 90.0%`; `10/10` strict refusals) | [m6_2_joint_inspection_receipt.json](evidence/m6_2_joint_inspection_receipt.json), [m6_2_answers_sheet.jsonl](evidence/m6_2_answers_sheet.jsonl) |
| Offline request `p95 <= 5 s` excluding startup (`concurrency = 1`) + `N` & `K` error/integration review | Met (`p50 = 40.32 ms`, `p95 = 69.00 ms <= 5,000 ms`; `30/30` `N` + `30/30` `K` verified) | [m6_2_offline_dry_run_receipt.json](evidence/m6_2_offline_dry_run_receipt.json) |
| Upstream gates `M4.G` & `M5.G` closed & `M6.1` backend finalized | Met (`M3.G`, `M4.G`, `M5.G` = `PASS`; `M6.1` = `COMPLETE` with `bm25-v3` retained) | [M3.G](../M3.G/README.md), [M4.G](../M4.G/README.md), [M5.G](../M5.G/README.md), [M6.1](../M6.1/README.md) |

Final task status: **`COMPLETE` (all `M6.2` benchmarks, TDD fixes, `apps/` multimodal wiring, `30/30 N` + `30/30 K` human inspections, and upstream gate prerequisites satisfied)**.
