# M6.2 — Source-Resolving Q&A and Demo Integration

- Status: IN_PROGRESS (Held-out `30`-question evaluation dataset prepared & empirically probed against `m3_3_pilot_snapshot_v2` + `bm25-m3_3-pilot`; full API/`/demo/` latency benchmark over `30` repetitions and two-contributor `N`+`K` response inspection pending `M3.G`/`M4.G`/`M5.G` acceptance)
- Execution date: 2026-11-25 (Asia/Ho_Chi_Minh)
- Requirement source: [TikTok_AI_Engine_Milestone.md](../../../planning/TikTok_AI_Engine_Milestone.md) (`M6.2`)
- Specification: [spec.md](superpowers/spec.md)
- Execution plan: [plan.md](superpowers/plan.md)

## Conclusion

Prepared and empirically validated the **`30` held-out evaluation questions** in [held_out_questions_30.jsonl](../../../../data/evaluation/m6_2/held_out_questions_30.jsonl) (`0` overlap with `M2` `v1`/`v2_pilot` sets; **`20` answerable** + **`10` no-answer / guardrail cases**). Task stays **`IN_PROGRESS`** pending downstream gate alignment (`G3`/`G4`/`G5`), the `30`-repetition offline `p95 <= 5 s` latency benchmark, and joint `N`+`K` answer/provenance inspection.

## Work performed

- **30-question held-out benchmark pool ([held_out_questions_30.jsonl](../../../../data/evaluation/m6_2/held_out_questions_30.jsonl)):**
  - `m6_2_01`–`m6_2_12` (`12` questions): Historical F&B core across `hồ chí minh`, `hà nội`, `đà nẵng`, `huế`, `đà lạt`, `cần thơ`, `vũng tàu`, vegetarian, cooking guides, and rice/dessert categories (`wps_estimated` pacing).
  - `m6_2_13`–`m6_2_20` (`8` questions): Fresh `M3.3` audio/ASR-grounded videos (`8/8` matched their exact `target_video_id` in top-5 BM25 hits on `m3_3_pilot_snapshot_v2`, `audio_derived` provenance).
  - `m6_2_21`–`m6_2_30` (`10` no-answer / insufficient-evidence / guardrail cases): Undisclosed-PR epistemic claim (`m6_2_21`), bot-payment claim (`m6_2_22`), clinical hygiene certification claim (`m6_2_23`), non-F&B domain (`m6_2_24`, triggering `UnsupportedDomainError`), OOV dishes (`m6_2_25`–`26`), unindexed provinces (`m6_2_27`–`28`), negation-only query (`m6_2_29`), and millisecond timestamp lookup on audio-less video (`m6_2_30`).
- **Contract regression tests ([test_m6_2_eval_dataset.py](../../../../tests/unit/test_m6_2_eval_dataset.py)):** Verifies `30`-item count, `>= 10` no-answer count, disjointness from `v1`/`v2_pilot`, valid `NicheQueryFilter` schemas, and provenance metadata.

## Outputs

| File | Purpose |
| --- | --- |
| [held_out_questions_30.jsonl](../../../../data/evaluation/m6_2/held_out_questions_30.jsonl) | `30` held-out Q&A/demo evaluation prompts (`20` answerable + `10` no-answer/guardrail cases) |
| [run_m6_2_eval.py](evidence/run_m6_2_eval.py) | Single-concurrency ASGI `/api/v1/retrieval/search` + `/api/v1/script/generate` (`offline_grounded`) + `/demo/` probe |
| [m6_2_offline_dry_run_receipt.json](evidence/m6_2_offline_dry_run_receipt.json) / [m6_2_answers_sheet.jsonl](evidence/m6_2_answers_sheet.jsonl) | Measured `30`-question dry-run receipt (`p95 = 77.43 ms <= 5,000 ms`, `185/185` resolved citations, `10/10` strict refusals; pending joint `N`+`K` claim audit) |
| [test_m6_2_eval_dataset.py](../../../../tests/unit/test_m6_2_eval_dataset.py) | Schema, no-overlap, epistemic guardrail, and caption location fallback regression tests |
| [workflow.md](evidence/workflow.md) | Empirical probe notes and guardrail fix ledger against `m3_3_pilot_snapshot_v2` |

## Verification

| Check | Result | Scope / evidence |
| --- | --- | --- |
| `python3 docs/reports/milestones/M6.2/evidence/run_m6_2_eval.py` | PASS (`p95 = 77.43 ms`, `185/185` valid IDs, `10/10` strict no-answer) | `m3_3_pilot_snapshot_v2` + `bm25-m3_3-pilot`; startup `9.67 s`, peak RSS `1,158.55 MiB`; [m6_2_offline_dry_run_receipt.json](evidence/m6_2_offline_dry_run_receipt.json) |
| Dataset & guardrail tests (`tests/unit/test_m6_2_eval_dataset.py`) | PASS (`2 passed in 1.27s`) | Disjoint `30`-question contract, epistemic refusals (`422` + retrieval `insufficient_evidence`), and caption `city_norm` fallback |

## Open issues

| Issue | Impact | Follow-up / responsible task |
| --- | --- | --- |
| Full `30`-question API/`/demo/` execution (`p95 <= 5 s`) and two-human `N`+`K` response inspection not yet run | `M6.2` remains `IN_PROGRESS` until `30` outputs and timings are jointly verified | Run `30`-repetition offline benchmark & complete joint `N`+`K` inspection after `M3.G`/`M4.G`/`M5.G` |

## Acceptance and handoff

| Task criterion | Result | Evidence |
| --- | --- | --- |
| Prepare `30` held-out questions including `>= 10` no-answer/insufficient-evidence cases | **Met (draft dataset verified; awaiting `K` co-inspection)** | [held_out_questions_30.jsonl](../../../../data/evaluation/m6_2/held_out_questions_30.jsonl) |
| `>= 95%` citation, `>= 90%` claims, `100%` ID/timestamp/refusal, `p95 <= 5 s`, `N`+`K` audit | Pending full benchmark & `N`+`K` review | Deferred to `M6.2` Task 2–3 |

Final task status: **IN_PROGRESS** (`30` held-out evaluation questions ready; full `M6.2` integration, `30`-repetition latency run, and `N`+`K` inspection pending).
