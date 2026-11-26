# M5.2 — Four-Aspect Sentiment with Source Spans

- Status: COMPLETE
- Execution date: 2026-11-20 to 2026-11-26 (Asia/Ho_Chi_Minh)
- Requirement source: [TikTok_AI_Engine_Milestone.md](../../../planning/TikTok_AI_Engine_Milestone.md) (`M5.2`)
- Repository version: `main` (finalizing `N` + `K` `180`-unit double-annotation, `dev`-only linguistic refinement, & held-out evaluation over `71cf3232`)
- Primary owner: Trần Đình Khương (`K`) · Peer reviewer & co-annotator: Nguyễn Việt Nguyên (`N`)
- Specification: [spec.md](superpowers/spec.md)
- Execution plan: [plan.md](superpowers/plan.md)

## Conclusion

**`M5.2` is `COMPLETE` (`m5_2_pilot_gate_eligible = true`): 4-aspect (`taste`, `price`, `hygiene`, `service`) NFC-exact span extraction, `absent_unknown` vs `observed neutral` separation, `>= 3`-comment support-gated `sentiment_discrepancy`, `3x3` threshold & before/after-filter sensitivity, blinded two-contributor annotation across `180` real multimodal `M3.3` units (`29` videos: `N = 115/115` verified + `K = 115/115` verified, `50` double-annotated), strict `dev` + video-disjoint-train lexical refinement (`0` `held_out` leakage), and frozen `held_out` evaluation (`aspect_detection_macro_f1 = 0.9286 >= 0.65`, `observed_sentiment_macro_f1 = 0.8293 >= 0.60`, `span_validity = 1.0000 >= 0.95`) are complete and verified.**

- **Blinded Two-Person Multimodal Annotation & IAA (`180` units / `29` videos):** Both `N` (`115/115`) and `K` (`115/115`) independently annotated [m5_2_pilot_pool.jsonl](../../../../data/annotations/m5_2_pilot_pool.jsonl) (`116 viewer_comment`, `35 creator_utterance`, `29 creator_caption` from `m3_3_pilot_snapshot_v2`) strictly blinded to [m5_2_pilot_locked_predictions.jsonl](../../../../data/annotations/m5_2_pilot_locked_predictions.jsonl) and each other's overlap labels. Across the `50` `double_review_N_K` units (`200` `(unit, aspect)` pairs), **aspect-presence agreement is `98.50%` (`197/200`, `cohens_kappa_presence = 0.8616`)** and **4-state agreement is `97.50%` (`195/200`, `cohens_kappa_4state = 0.7731`)**, with `44/44 = 100.0%` exact `NFC` slice validity across adjudicated gold spans.
- **Untuned Locked Baseline vs. Strict `dev` + Video-Disjoint-Train Refinement (`0` Video Overlap with `held_out`):**
  - Untuned pre-annotation locked predictions ([m5_2_real_pilot_locked_eval_v1.json](../../../../artifacts/benchmarks/m5_2_real_pilot_locked_eval_v1.json)) achieved `held_out` `aspect_detection_macro_f1 = 0.5380`, `observed_sentiment_macro_f1 = 0.5523`, and `span_validity = 1.0000` (`27/27`).
  - Inspecting **only** `splits["dev"]` (`14` videos / `87` units) and the video-disjoint Playwright expansion set `absa_train_video_disjoint_v1.jsonl` (`90` videos / `2,429` comments, `0` video overlap with all `29` pilot videos) surfaced general Vietnamese F&B bugs: bare dish titles (`"Lẩu mì Hải Sản"`, `"Phở khô hai tô"`) firing `taste=neutral` without evaluative cues, homophones (`"dưa chuột"` -> `"chuột"`, `"mắc cừ"` / `"mắc mệt"` -> `"mắc"`), street-food glove/digestion hygiene (`"không đeo bao tay"`, `"ảy chỉa"`), Southern `"quá rẽ"`, `"khó ăn"`, and abbreviated Vietnamese negations (`ko`, `kh`, `hong`).
  - Evaluated **once** on the unseen `held_out` split (`15` disjoint videos / `93` units) in [m5_2_real_pilot_eval_v1.json](../../../../artifacts/benchmarks/m5_2_real_pilot_eval_v1.json): **`aspect_detection_macro_f1 = 0.9286`** (`95% CI [0.7969, 0.9762]`, exceeding `>= 0.65`; `taste = 0.7857`, `price = 1.0000`, `hygiene = 1.0000`), **`observed_sentiment_macro_f1 = 0.8293`** (`95% CI [0.5331, 1.0000]`, exceeding `>= 0.60`; `positive = 0.8800`, `neutral = 0.9412`, `negative = 0.6667`), and **`audited_span_validity_rate = 1.0000`** (`25/25` held-out spans, `47/47` full-pool spans; `100%` `all_predicted_aspects_span_backed`, exceeding `>= 0.95`).
- **Explicit Qualification on `service` Support & `>= 3`-Comment Abstention:** `service` had `gold_support = 0` across the `180`-unit real pilot sample (`1` predicted FP on `held_out`; even under a conservative 4-aspect denominator penalizing `service = 0.0`, `(0.7857 + 1.0 + 1.0 + 0.0) / 4 = 0.6964 >= 0.65`). On the `29` real pilot videos, enforcing `min_viewer_comments = 3` abstains on `26/29` sparse-comment videos (`videos_with_supported_overlap` drops from `11/29` at `min_c = 1` to `3/29` at `min_c = 3`, `mean_supported_sentiment_discrepancy = -0.2445`), preventing low-support or unverified single-aspect claims.

## Work performed

- **Typed `M5.2` contracts, NFC-exact span engine & `/demo/` sensitivity ([multimodal.py](../../../../packages/data_contracts/multimodal.py), [spans.py](../../../../packages/absa/spans.py), [analyzer.py](../../../../packages/absa/analyzer.py), [trust.py](../../../../apps/api/app/routers/trust.py), [presentation.py](../../../../apps/demo/presentation.py)):** Delivered frozen `AspectSpanEvidence`, `AspectAggregateSummary`, and `AspectDiscrepancyDetail` models, 1-to-1 NFC offset slicing, `>= 3`-comment support abstention, before/after `M5.1` filter shifts, and `3x3` `(polarity_tau, min_viewer_comments)` sensitivity grids.
- **Phase 1 `N` peer review & Phase 2 TDD `real_eval` + `dev`-only refinement ([nguyen_baseline_peer_review.md](evidence/nguyen_baseline_peer_review.md), [evaluation.py](../../../../packages/absa/evaluation.py), [run_baseline_checks.py](../../../../pipelines/audit_m5_2_absa/run_baseline_checks.py), [test_m5_2_aspect_spans.py](../../../../tests/unit/test_m5_2_aspect_spans.py)):** Added `validate_and_summarize_m5_2_pool`, `--mode real_eval`, and `dev`/video-disjoint-train Vietnamese F&B guards (`15/15` unit tests passing).
- **Blinded `180`-unit `N`+`K` annotation, adjudication & side-by-side locked/refined evaluation ([m5_2_pilot_pool.jsonl](../../../../data/annotations/m5_2_pilot_pool.jsonl), [m5_2_real_pilot_locked_eval_v1.json](../../../../artifacts/benchmarks/m5_2_real_pilot_locked_eval_v1.json), [m5_2_real_pilot_eval_v1.json](../../../../artifacts/benchmarks/m5_2_real_pilot_eval_v1.json), [m5_2_joint_annotation_receipt.json](evidence/m5_2_joint_annotation_receipt.json)):** Completed `180/180` human-verified annotations (`44/44` valid gold NFC spans) and published both untuned locked and `dev`-refined evaluation receipts.

## Outputs

| File | Purpose |
| --- | --- |
| [m5_2_real_pilot_eval_v1.json](../../../../artifacts/benchmarks/m5_2_real_pilot_eval_v1.json) / [m5_2_real_pilot_locked_eval_v1.json](../../../../artifacts/benchmarks/m5_2_real_pilot_locked_eval_v1.json) | Official `180`-unit / `29`-video real pilot evaluation receipt (`dev`-refined & preserved untuned locked baseline, `500`-resample cluster CIs, `29`-video filter & `3x3` threshold sensitivity) |
| [m5_2_joint_annotation_receipt.json](evidence/m5_2_joint_annotation_receipt.json) | SHA256 provenance receipt for `N` (`115/115`) + `K` (`115/115`) blinded signoff, IAA (`kappa_presence=0.8616`, `kappa_4state=0.7731`), and `44/44` gold NFC spans |
| [m5_2_pilot_pool.jsonl](../../../../data/annotations/m5_2_pilot_pool.jsonl) / [m5_2_pilot_locked_predictions.jsonl](../../../../data/annotations/m5_2_pilot_locked_predictions.jsonl) | Finalized `180`-unit real pool (`115/115 N` + `115/115 K` verified, `180/180` adjudicated) + untouched locked predictions |
| [annotation_guidelines.md](evidence/annotation_guidelines.md) | Formal English `K` & `N` double-annotation protocol for 4 aspects and exact `NFC` character spans |
| [nguyen_baseline_peer_review.md](evidence/nguyen_baseline_peer_review.md) | Contributor `N` Phase 1 peer-review verification and real-pilot edge regression fixes |
| [workflow.md](evidence/workflow.md) | Complete Phase 1–7 Superpowers engineering, peer-review, blinded annotation, and verification ledger |
| [m5_2_fixture_dry_run_v1.json](../../../../artifacts/benchmarks/m5_2_fixture_dry_run_v1.json) | `12`-video / `72`-unit synthetic regression dry-run receipt (`is_real_pilot_data=false`) |
| [spans.py](../../../../packages/absa/spans.py), [analyzer.py](../../../../packages/absa/analyzer.py), [evaluation.py](../../../../packages/absa/evaluation.py), [run_baseline_checks.py](../../../../pipelines/audit_m5_2_absa/run_baseline_checks.py) | NFC-exact 4-aspect span extractor, `>= 3`-comment discrepancy engine, fail-closed pool validator, and `real_eval` CLI |
| [test_m5_2_aspect_spans.py](../../../../tests/unit/test_m5_2_aspect_spans.py) | `15` TDD unit/contract/API/CLI/real-eval/linguistic-refinement tests |
| [pytest-full-m5_2.log](evidence/pytest-full-m5_2.log) / [pytest-tasks1-2.log](evidence/pytest-tasks1-2.log) | Historical Phase 3–4 milestone checkpoint logs |

## Verification

| Check | Result | Scope / evidence |
| --- | --- | --- |
| `python3 -m pipelines.audit_m5_2_absa.run_baseline_checks --mode real_eval --use-current-engine --output artifacts/benchmarks/m5_2_real_pilot_eval_v1.json --overwrite` | PASS (`units=180`, `kappa_4state=0.7731`, `held_out_aspect_f1=0.9286`, `held_out_sentiment_f1=0.8293`, `span_validity=1.0`, `pilot_gate_eligible=True`) | Real `180`-unit / `29`-video `M3.3` pilot evaluation; [m5_2_real_pilot_eval_v1.json](../../../../artifacts/benchmarks/m5_2_real_pilot_eval_v1.json) |
| `python3 -m pytest tests/unit/test_m5_2_aspect_spans.py -v` | PASS (`15 passed in 14.09s`) | All `15` M5.2 contract, NFC span, API/`/demo/`, `N` review, `real_eval`, and linguistic refinement tests |
| `python3 -m pytest -q` | PASS (`278 passed, 10 skipped`) | Full repository regression suite on `main` |
| `python3 -m mypy packages apps pipelines tests/unit/test_m5_2_aspect_spans.py` (+ `--platform win32`) | PASS (`0` issues) | Strict Linux & Windows static type checks |
| `python3 scripts/check_secrets.py` | PASS (`0` leaks) | Full workspace secret hygiene |

## Open issues

| Issue | Impact | Follow-up / responsible task |
| --- | --- | --- |
| `service` aspect had `gold_support = 0` in the natural `180`-unit `m3_3_pilot_snapshot_v2` sample (`1` predicted FP on `held_out`), and rare implicit complaints without lexical polarity cues (e.g., `held_out` `negative` `recall = 0.50` over `2` gold negatives) remain bounded by lexicon coverage | `service` precision/recall on real pilot data is empirically unmeasured (`0` gold support), though 4-way conservative detection F1 remains `0.6964 >= 0.65` and runtime `min_viewer_comments = 3` abstains on sparse threads | Qualify `service` sparse-sample coverage and retain mandatory `min_viewer_comments = 3` abstention + `sentiment_discrepancy` framing in `M5.G` (`Gate G5`) |

## Acceptance and handoff

| Task criterion | Result | Evidence |
| --- | --- | --- |
| Preserve aspect presence/unknown separately from observed neutral, unit IDs, character offsets, and support counts for Taste, Price, Hygiene, Service | Met (`N` + `K` verified) | [multimodal.py](../../../../packages/data_contracts/multimodal.py), [spans.py](../../../../packages/absa/spans.py) |
| Compare creator speech and comments only on supported overlapping aspects (`>= 3` comments); qualify as `sentiment discrepancy` | Met (`26/29` low-support real videos abstain cleanly) | [analyzer.py](../../../../packages/absa/analyzer.py), [m5_2_real_pilot_eval_v1.json](../../../../artifacts/benchmarks/m5_2_real_pilot_eval_v1.json) |
| Double-annotate `<= 200` units (`>= 120`) across `>= 10` pilot videos; freeze video-disjoint `dev`/`held_out` before tuning | Met (`180` units across `29` videos; `0` video overlap across `14 dev` / `15 held_out` / `90 train` videos; `kappa_presence=0.8616`, `kappa_4state=0.7731`) | [m5_2_pilot_pool.jsonl](../../../../data/annotations/m5_2_pilot_pool.jsonl), [m5_2_joint_annotation_receipt.json](evidence/m5_2_joint_annotation_receipt.json) |
| Held-out `aspect_detection_macro_f1 >= 0.65`, `observed_sentiment_macro_f1 >= 0.60`, and `>= 95%` audited source-span validity; publish before/after-filter & threshold sensitivity | Met (`0.9286 >= 0.65`, `0.8293 >= 0.60`, `1.0000 >= 0.95` across `25/25` held-out & `44/44` gold spans; `3x3` sensitivity published) | [m5_2_real_pilot_eval_v1.json](../../../../artifacts/benchmarks/m5_2_real_pilot_eval_v1.json) |

Final task status: **COMPLETE** (hands off finalized `M5.1` + `M5.2` real-pilot receipts to **`M5.G` (`Gate G5`)**).
