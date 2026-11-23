# M5.2 — Four-Aspect Sentiment with Source Spans

- Status: IN_PROGRESS (`K` completed all 4 offline `M5.2` implementation tasks in [plan.md](superpowers/plan.md): typed `M5.2` multimodal contracts, NFC-exact 4-aspect `source_spans` & support-gated `sentiment_discrepancy`, `/api/v1/trust/audit-video` + `/demo/` `3x3` threshold sensitivity & citation wiring, video-disjoint evaluator/span auditor/blinded pool CLI, `K`+`N` annotation guidelines, and `12`-video / `72`-unit synthetic fixture dry-run (`206 passed`, `104`-file Linux/Windows `mypy`); awaiting `M3.3` real pilot capture for `120`–`200`-unit `K`+`N` double-annotation and `N` peer review)
- Execution date: 2026-11-20 to 2026-11-23 (Asia/Ho_Chi_Minh)
- Requirement source: [TikTok_AI_Engine_Milestone.md](../../../planning/TikTok_AI_Engine_Milestone.md) (`M5.2`)
- Repository version: `feat/k-m5.2-aspect-spans-baseline` (branched from `main` @ `60b80147`)
- Primary owner: Trần Đình Khương (`K`) · Peer reviewer: Nguyễn Việt Nguyên (`N`, pending peer review & real-pilot double-annotation)
- Specification: [spec.md](superpowers/spec.md)
- Execution plan: [plan.md](superpowers/plan.md)

## Conclusion

**All 4 engineering, API/`/demo/`, evaluation, and guideline tasks of `M5.2` are complete and verified (`206 passed`, `104`-file strict Linux & `win32` `mypy`, `0` secret leaks); task status remains `IN_PROGRESS` (`m5_2_pilot_gate_eligible = false`) strictly because real pilot double-annotation (`120`–`200` units across `>= 10` videos) awaits live `M3.3` pilot capture and `N`'s peer review.**

- **Typed multimodal contracts ([multimodal.py](../../../../packages/data_contracts/multimodal.py)):** Added frozen `allow_inf_nan=False` models `AspectSpanEvidence` (`0 <= start_char < end_char` and unstripped `len(span_text) == end_char - start_char`), `AspectAggregateSummary` (separating `absent_unknown` / `mean_score=None` from `observed` + `neutral` / `mean_score=0.0`), and `AspectDiscrepancyDetail` (`sentiment_discrepancy is None` on all `"abstained_*"` statuses, framed strictly as an observed `sentiment discrepancy`), preserving 100% backward compatibility with `AbsaComparisonRecord` and 14-column `fact_absa_reviews.parquet`.
- **NFC-exact 4-aspect span extractor & support-gated discrepancy ([spans.py](../../../../packages/absa/spans.py), [analyzer.py](../../../../packages/absa/analyzer.py)):** Preserves 1-to-1 `NFC` codepoint offsets across NFD inputs and unstripped `CommentRecord.original_text`, partitions contrastive/coordinated Vietnamese multi-aspect clauses, guards F&B false-positive traps (`"quán lâu đời"`, `"ăn sạch cả tô"` vs `"Quán ăn sạch sẽ"`, `"giá đỗ"` / `"giá như..."` vs `"Giá như vậy là bình thường"`, `"check in 100k views"`, negated neutral `"không chấp nhận được"` / `"không ổn"`), and gates creator-vs-viewer `sentiment_discrepancy` on `min_viewer_comments = 3` distinct non-seeding viewer comment units (`mention_unit_count`).
- **API/`/demo/` sensitivity & citation surfaces ([trust.py](../../../../apps/api/app/routers/trust.py), [evaluation.py](../../../../packages/seeding/evaluation.py), [presentation.py](../../../../apps/demo/presentation.py)):** Forwards `TrustAuditRequest.utterances` into `analyze_koc_vs_viewer_absa`, publishes before/after `M5.1` filter shifts plus a `3x3` `(polarity_tau in {0.05, 0.15, 0.25} x min_viewer_comments in {1, 3, 5})` sensitivity grid, and renders `absent_unknown` vs `observed neutral`, `n=<mention_unit_count>`, and `[unit_id @ start_char:end_char]` span citations in `/demo/`.
- **Video-disjoint `M5.2` evaluator, span auditor, blinded pool CLI & synthetic dry-run ([evaluation.py](../../../../packages/absa/evaluation.py), [run_baseline_checks.py](../../../../pipelines/audit_m5_2_absa/run_baseline_checks.py), [m5_2_fixture_dry_run_v1.json](../../../../artifacts/benchmarks/m5_2_fixture_dry_run_v1.json)):** Implemented `split_units_by_video` (`0` video overlap), `audit_source_span_validity` (`>= 95%` exact `NFC` slice gate), `compute_m5_2_annotator_agreement`, `evaluate_m5_2_aspect_sentiment` (per-aspect binary presence F1, 3-class gold-observed sentiment F1 penalizing `pred == "absent_unknown"` on gold-observed aspects, 300-resample video-cluster bootstrap 95% CIs, and fail-closed `m5_2_pilot_gate_eligible`), and `build_m5_2_annotation_pool` (`1 <= max_units <= 200`, collision-free `f"{vid}::utt::{seg_id}"` / `f"{vid}::cmt::{cmt_id}"` / `f"{vid}::cap"`, blinded `include_predictions=False`). On the `12`-video / `72`-unit synthetic edge-regression fixture (`is_real_pilot_data=False`), held-out (`36` units across `6` disjoint videos) achieved `aspect_detection_macro_f1 = 1.0000` (`[1.0000, 1.0000]`), `observed_sentiment_macro_f1 = 0.9267` (`[0.8618, 0.9781]`), `span_audit.validity_rate = 1.0000` (`54/54` held-out spans, `112/112` total spans), and `max_abs_supported_discrepancy_shift = 0.8000` across `M5.1` duplicate-contaminated threads while failing closed (`m5_2_pilot_gate_eligible = false`).

## Work performed

- **Task 1 — Typed `M5.2` contracts & validator invariants ([multimodal.py](../../../../packages/data_contracts/multimodal.py), [__init__.py](../../../../packages/data_contracts/__init__.py)):** Implemented and re-exported `ASPECT_NAMES`, `AspectSpanEvidence`, `AspectAggregateSummary`, `AspectDiscrepancyDetail`, additive `AbsaComparisonRecord` fields, and `TrustAuditRequest.utterances` (`4103e100`).
- **Task 2 — Exact-offset 4-aspect span engine & support-gated discrepancy ([spans.py](../../../../packages/absa/spans.py), [analyzer.py](../../../../packages/absa/analyzer.py)):** Implemented `TextUnitInput`, `extract_unit_aspect_spans`, `summarize_units_aspects`, and support-gated `analyze_koc_vs_viewer_absa` (`248e1898`, refined in `5b7d6d49` and `d52bcbfa`).
- **Task 3 — `/api/v1/trust/audit-video` utterances, `3x3` threshold sensitivity & `/demo/` span citations ([trust.py](../../../../apps/api/app/routers/trust.py), [evaluation.py](../../../../packages/seeding/evaluation.py), [presentation.py](../../../../apps/demo/presentation.py)):** Wired `utterances` into `/api/v1/trust/audit-video` and `compute_comment_filter_sensitivity`, added before/after-filter per-aspect shifts + `3x3` `(polarity_tau, min_viewer_comments)` sensitivity cells, and updated `format_trust_audit_markdown` (`7cf7bc0e`).
- **Task 4 — Video-disjoint evaluator, `NFC` span auditor, blinded `120`–`200`-unit pool CLI, `K`+`N` guidelines & dry-run receipt ([evaluation.py](../../../../packages/absa/evaluation.py), [run_baseline_checks.py](../../../../pipelines/audit_m5_2_absa/run_baseline_checks.py), [annotation_guidelines.md](evidence/annotation_guidelines.md), [m5_2_fixture_dry_run_v1.json](../../../../artifacts/benchmarks/m5_2_fixture_dry_run_v1.json)):** Implemented full offline evaluation/IAA/pool-export pipeline (including multimodal `M3.3` `video_id` scoping on Dual-Sink `fact_videos.parquet`, fail-closed empty/untrimmed/invalid-aspect `NFC` span auditing, and verified span backing on predicted observed `(unit_id, aspect)` pairs in Fix Round 1), authored English `K`/`N` double-annotation guidelines, generated SHA256-pinned synthetic regression receipt (`m5_2_pilot_gate_eligible = false`), and expanded `tests/unit/test_m5_2_aspect_spans.py` to `12` comprehensive unit/API/CLI tests.

## Outputs

| File | Purpose |
| --- | --- |
| [annotation_guidelines.md](evidence/annotation_guidelines.md) | Formal English `K` & `N` double-annotation protocol for 4 aspects, `absent_unknown` vs `observed neutral`, exact `NFC` character spans, and `120`–`200`-unit `M3.3` evaluation gate |
| [workflow.md](evidence/workflow.md) | Superpowers `brainstorming`, `writing-plans`, and `subagent-driven-development` provenance, review loops, and verification ledger across Tasks 1–4 |
| [pytest-full-m5_2.log](evidence/pytest-full-m5_2.log) | Full `206`-test repository `pytest` verification log after Task 4 Fix Round 1 completion |
| [pytest-tasks1-2.log](evidence/pytest-tasks1-2.log) | Historical `202`-test milestone checkpoint log after Task 2 |
| [m5_2_fixture_dry_run_v1.json](../../../../artifacts/benchmarks/m5_2_fixture_dry_run_v1.json) | `12`-video / `72`-unit synthetic regression dry-run receipt (`is_real_pilot_data=false`, `m5_2_pilot_gate_eligible=false`) with `code_files_sha256` provenance |
| [spans.py](../../../../packages/absa/spans.py), [analyzer.py](../../../../packages/absa/analyzer.py), [evaluation.py](../../../../packages/absa/evaluation.py) | NFC-exact 4-aspect span extractor, `>= 3`-comment discrepancy engine, video-disjoint evaluator, `NFC` span auditor, IAA, and blinded pool builder |
| [trust.py](../../../../apps/api/app/routers/trust.py), [evaluation.py](../../../../packages/seeding/evaluation.py), [presentation.py](../../../../apps/demo/presentation.py) | Typed `/api/v1/trust/audit-video` `utterances` forwarding, before/after-filter + `3x3` threshold sensitivity grid, and `/demo/` span-citation rendering |
| [run_baseline_checks.py](../../../../pipelines/audit_m5_2_absa/run_baseline_checks.py) | Fail-closed `fixture_dry_run` and `real_pool` (`<= 200` blinded units + separate `*_locked_predictions.jsonl`) CLI |
| [test_m5_2_aspect_spans.py](../../../../tests/unit/test_m5_2_aspect_spans.py) | `12` TDD unit/contract/API/CLI tests covering invariants, Vietnamese F&B linguistic traps, sensitivity grid, multimodal Dual-Sink pool scoping, fail-closed span backing, and CLI checks |

## Verification

| Check | Result | Scope / evidence |
| --- | --- | --- |
| `python3 -m pipelines.audit_m5_2_absa.run_baseline_checks --mode fixture_dry_run --output artifacts/benchmarks/m5_2_fixture_dry_run_v1.json` | PASS | Held-out (`36` units / `6` videos): aspect F1 `1.0000`, observed sentiment F1 `0.9267`, span validity `1.0000` (`54/54`), `m5_2_pilot_gate_eligible = false`; [m5_2_fixture_dry_run_v1.json](../../../../artifacts/benchmarks/m5_2_fixture_dry_run_v1.json) |
| `python3 -m pytest tests/unit/test_m5_2_aspect_spans.py -v` | PASS (`12 passed in 6.29s`) | All contract, NFC span, discrepancy, API/`/demo/` `3x3` sensitivity, evaluator, span auditor, Dual-Sink pool scoping, and blinded CLI tests |
| `python3 -m pytest -v` | PASS (`206 passed in 29.80s`) | Full repository suite; [pytest-full-m5_2.log](evidence/pytest-full-m5_2.log) |
| `python3 -m mypy packages apps pipelines tests/unit/test_m5_2_aspect_spans.py` | PASS (`105 source files`) | Strict Linux static type check |
| `python3 -m mypy --platform win32 packages apps pipelines` | PASS (`104 source files`) | Strict Windows cross-platform static type check |
| `python3 scripts/check_secrets.py` | PASS (`0` leaks) | Full workspace secret hygiene |

## Open issues

| Issue | Impact | Follow-up / responsible task |
| --- | --- | --- |
| Real pilot text units (`120`–`200` across `>= 10` videos) awaiting `M3.3` live capture (`MS_TOKEN` prerequisite) | `m5_2_pilot_gate_eligible` intentionally remains `false` on synthetic fixtures; real held-out aspect F1 (`>= 0.65`), observed sentiment F1 (`>= 0.60`), audited span validity (`>= 95%`), and `K`+`N` IAA cannot be signed off until `M3.3` runs | Complete `M3.3` capture, run `pipelines.audit_m5_2_absa.run_baseline_checks --mode real_pool`, complete `K` & `N` double-annotation + adjudication, and obtain `N` peer review before `M5.G` |
| Implicit idiomatic complaints without lexical wait/negative cues (e.g., `"Ngồi từ trưa tới chiều mới thấy mặt nhân viên mang đĩa ra"`) score as `service = neutral` (`0.0`) rather than `negative` | Observed held-out neutral precision `0.7500` / negative recall `0.8571` (`observed_sentiment_macro_f1 = 0.9267`) on synthetic edge fixture; bounded CPU lexicon behavior documented transparently | Re-assess idiom error distribution on real `M3.3` `dev` videos before locking held-out `M5.G` evaluation (`K` & `N`) |

## Acceptance and handoff

| Task criterion | Result | Evidence |
| --- | --- | --- |
| Preserve aspect presence/unknown separately from observed neutral, unit IDs, character offsets, and support counts for Taste, Price, Hygiene, Service | Met | [multimodal.py](../../../../packages/data_contracts/multimodal.py), [spans.py](../../../../packages/absa/spans.py), [test_m5_2_aspect_spans.py](../../../../tests/unit/test_m5_2_aspect_spans.py) |
| Compare creator speech and comments only on supported overlapping aspects (`>= 3` comments); qualify as `sentiment discrepancy` | Met | [analyzer.py](../../../../packages/absa/analyzer.py), [trust.py](../../../../apps/api/app/routers/trust.py), [presentation.py](../../../../apps/demo/presentation.py) |
| Publish before/after-filter gaps and threshold sensitivity; video-disjoint evaluator (`F1 >= 0.65` / `0.60`, span validity `>= 95%`) | Met on offline engine & synthetic fixture dry-run (`1.0000` / `0.9267` / `100%`); real pilot pending `M3.3` | [evaluation.py](../../../../packages/absa/evaluation.py), [run_baseline_checks.py](../../../../pipelines/audit_m5_2_absa/run_baseline_checks.py), [m5_2_fixture_dry_run_v1.json](../../../../artifacts/benchmarks/m5_2_fixture_dry_run_v1.json) |
| Double-annotate `120`–`200` real pilot units across `>= 10` videos & `N` peer review | Not verified yet (guidelines & blinded pool CLI ready; awaiting `M3.3` real capture & `N` review) | [annotation_guidelines.md](evidence/annotation_guidelines.md) |

Final task status: **IN_PROGRESS** (`M5.G` gate remains **`NOT_RUN`**; all offline `M5.2` code, API/`/demo/`, guidelines, and dry-run verification complete and ready for `M3.3` real-pilot annotation and `N` peer review).
