# M5.1 — Duplicate, Contact/Link, and Noise Comment Indicators

- Status: IN_PROGRESS (`N`'s observable indicator baseline + `K`'s adversarial code/leakage/sensitivity peer review & `5`-test TDD hardening complete; Phase 2 blinded real pool (`300` comments / `22` videos) exported from `m3_3_pilot_snapshot_v2` and **`N`'s `180/180` half (`60` overlap + `120` `N_only`) complete & confirmed (`N_human_verified=True`)**; awaiting `K`'s `180`-item half + joint adjudication + held-out `1/3` evaluation)
- Execution date: 2026-11-19 to 2026-11-25 (Asia/Ho_Chi_Minh)
- Requirement source: [TikTok_AI_Engine_Milestone.md](../../../planning/TikTok_AI_Engine_Milestone.md) (`M5.1`)
- Repository version: `main` (merging `feat/k-m4.2-m5.1-m6.1-peer-reviews` over `14becda0`)
- Primary owner: Nguyễn Việt Nguyên (`N`) · Peer reviewer: Trần Đình Khương (`K`, baseline code/leakage/sensitivity review complete)
- Specification: [spec.md](superpowers/spec.md)
- Execution plan: [plan.md](superpowers/plan.md)

## Conclusion

**Code, diagnostic-only defaults, `K` adversarial peer-review TDD fixes (`8/8` M5.1 tests, `194/194` repo tests, `100`-file Linux/Windows `mypy`), blinded video-grouped pool sampler, and annotation guidelines are complete and verified; real-comment evaluation remains `BLOCKED` on `M3.3` / `M3.G` pilot collection (`IN_PROGRESS`).**

- `packages/seeding/detector.py` preserves `original_text` verbatim alongside trimmed `text`, emits non-accusatory observable classes (`observable_duplicate`, `contact_or_link`, `noise_or_empty`, `template_phrase_match`, `no_indicator_observed`, `unknown_ambiguous`) with zero bot/payment/verified-diner assertions, exempts both `< 5`-token reactions (`24 -> 0` on the synthetic fixture) and **5–8 syllable ordinary Vietnamese diner inquiries** (`"Cho mình xin địa chỉ"`, `"Quán này ở đâu vậy"`), isolates `contact_or_link` and `noise_or_empty` before pairwise clustering so spam comments never contaminate clean viewers, prioritizes `template_phrase_match`, unifies transitive duplicate clusters via Union-Find, and enforces digit boundaries `(?<!\d)...(?!\d)` so 19-digit TikTok video IDs never false-positive as phone numbers.
- `packages/seeding/evaluation.py` and `pipelines/audit_m5_1_comments/run_baseline_checks.py` now evaluate `auto_filter_eligible` against `total_annotated_pool_count >= 150` (`>= 45` on `held_out_third`, fixing the prior `300/3 = 100 < 150` gate deadlock), sample contiguous whole-video threads **blinded to model predictions** (`include_predictions=False`, saving a separate `*_locked_predictions.jsonl` key reconstructed from 10-column `fact_comments.parquet`), validate strict `OBSERVABLE_COMMENT_CLASSES`, use video-cluster bootstrap CIs, and abstain cleanly (`after_filter_abstained=True`, `after_filter_viewer_mean=None`) instead of fabricating `0.0` neutral sentiment when 100% of comments are flagged.
- `/demo/` (`apps/demo/presentation.py`, `apps/demo/ui.py`) uses `parse_demo_comment_lines` so bare `https://` links and colons (`"19:30"`, `"Giá: 45k"`) are never corrupted, uses neutral `@viewer_01..@viewer_05` example handles, and keeps `hide_seeding=False` unchecked by default.

## Work performed

- **Observable indicator & organic-inquiry hardening ([detector.py](../../../../packages/seeding/detector.py), [multimodal.py](../../../../packages/data_contracts/multimodal.py), [converter.py](../../../../pipelines/ingest_incremental_to_gold/converter.py)):** Preserved `original_text` and 10-column Gold Parquet continuity; added `K`-review fixes for 5–8 syllable Vietnamese diner inquiries, pre-clustering contact/noise isolation, `template_phrase_match` reachability, Union-Find transitive clusters, Telegram/Facebook + repeated-character noise matching, and 19-digit ID phone-regex boundaries.
- **Diagnostic-only UI, URL-safe parser & abstaining filter sensitivity ([trust.py](../../../../apps/api/app/routers/trust.py), [presentation.py](../../../../apps/demo/presentation.py), [ui.py](../../../../apps/demo/ui.py)):** Defaulted `hide_seeding=False`, added `parse_demo_comment_lines`, replaced legacy `@spam_bot`/`@khach_that_*` sample handles, and added `after_filter_abstained` handling when `unflagged_comment_count == 0`.
- **Gate-reachable video-cluster evaluator & blinded pool export ([evaluation.py](../../../../packages/seeding/evaluation.py), [run_baseline_checks.py](../../../../pipelines/audit_m5_1_comments/run_baseline_checks.py), [annotation_guidelines.md](evidence/annotation_guidelines.md)):** Fixed `held_out_third` gate arithmetic (`total_annotated_pool_count >= 150`), blinded human annotation sheets while adding `reconstruct_observable_predictions` for Gold Parquet, enforced strict label validation + `support > 0` macro-recall denominators, and re-verified [m5_1_fixture_dry_run_v2_k_review.json](../../../../artifacts/benchmarks/m5_1_fixture_dry_run_v2_k_review.json) (preserving `m5_1_fixture_dry_run.json` untouched).

## Outputs

| File | Purpose |
| --- | --- |
| [workflow.md](evidence/workflow.md) | `N` baseline + `K` peer-review TDD trace + Phase 2 `N` real-pool annotation receipt |
| [m5_1_pilot_pool.jsonl](../../../../data/annotations/m5_1_pilot_pool.jsonl) / [m5_1_pilot_pool_locked_predictions.jsonl](../../../../data/annotations/m5_1_pilot_pool_locked_predictions.jsonl) | Exported `300`-comment blinded real pool (`22` videos from `m3_3_pilot_snapshot_v2`: `180/180 N_human_verified=True`, `K` `180`-item half pending) + untouched locked predictions |
| [khuong_baseline_peer_review.md](evidence/khuong_baseline_peer_review.md) | `K`'s adversarial audit of label leakage, organic-duplicate FPs, gate math, and filter sensitivity |
| [annotation_guidelines.md](evidence/annotation_guidelines.md) | Written `N`/`K` double-annotation rules (within-thread scope & 5–8 syllable Vietnamese inquiry exclusion) |
| [m5_1_fixture_dry_run_v2_k_review.json](../../../../artifacts/benchmarks/m5_1_fixture_dry_run_v2_k_review.json) / [m5_1_fixture_dry_run.json](../../../../artifacts/benchmarks/m5_1_fixture_dry_run.json) | Post-review synthetic edge-fixture dry-run (`24 -> 0` org-dup FP; `max_abs_mean_score_shift > 0`; v1 preserved) |
| [test_m5_1_comment_indicators.py](../../../../tests/unit/test_m5_1_comment_indicators.py) | `8` TDD unit/API/UI regressions (`3` baseline + `5` `K`-review regressions) |
| [red-k-review-fixes.log](evidence/red-k-review-fixes.log) / [green-k-review-fixes.log](evidence/green-k-review-fixes.log) | `K` peer-review TDD RED (`5 failed`) -> GREEN (`11 passed` across M5.1 + M3.1) logs |

## Verification

| Check | Result | Scope / evidence |
| --- | --- | --- |
| `python3 -m pipelines.audit_m5_1_comments.run_baseline_checks --mode fixture_dry_run --output artifacts/benchmarks/m5_1_fixture_dry_run_v2_k_review.json` | PASS (`24 -> 0` org-dup FP; `diagnostic_only_without_filtering`) | Non-real `12`-video edge fixture; [m5_1_fixture_dry_run_v2_k_review.json](../../../../artifacts/benchmarks/m5_1_fixture_dry_run_v2_k_review.json) |
| `python3 -m pytest tests/unit/test_m5_1_comment_indicators.py tests/unit/test_incremental_absa_seeding.py -v` | PASS (`11 passed in 9.80s`) | M5.1 regressions + M3.1 Dual-Sink continuity; [green-k-review-fixes.log](evidence/green-k-review-fixes.log) |
| `python3 -m pytest -v` | PASS (`194 passed in 29.62s`) | Full post-merge workspace test suite on `main` |
| `python3 -m mypy packages apps pipelines` (+ `--platform win32`) | PASS (`100 source files` each) | Strict Linux & Windows static checks on `main` |
| `python3 scripts/check_secrets.py` | PASS (`0` leaks) | Full workspace secret hygiene |

## Open issues

| Issue | Impact | Follow-up / responsible task |
| --- | --- | --- |
| Real pilot comments (`300` items across `22` videos) exported & `N` half (`180/180`) complete; **`K`'s `180`-item half (`60` overlap + `120` `K_only`) and joint adjudication still pending** | Held-out macro P/R/F1 and human Cohen's kappa cannot be finalized until `K` signs off; automated filtering stays disabled (`diagnostic_only_without_filtering`) | `K` completes `K_label` + `K_human_verified=True` in `data/annotations/m5_1_pilot_pool.jsonl`, then run IAA & held-out evaluation |

## Acceptance and handoff

| Task criterion | Result | Evidence |
| --- | --- | --- |
| Preserve originals and reasons; observable duplicate/contact/noise labels; no bot/payment/seeding/identity assertions | Met (`N` + `K` verified) | [detector.py](../../../../packages/seeding/detector.py), [khuong_baseline_peer_review.md](evidence/khuong_baseline_peer_review.md) |
| Diagnostic flags without automatic filtering until `>= 150` real annotated comments pass `P >= 0.85`, `R >= 0.60` | Met (`held_out_third` gate deadlock fixed & verified) | [evaluation.py](../../../../packages/seeding/evaluation.py), [ui.py](../../../../apps/demo/ui.py) |
| Video/thread-disjoint splitting, agreement, P/R/F1 + bootstrap uncertainty, blinded pool export, written guidelines | Met on fixtures & real-pool export | [evaluation.py](../../../../packages/seeding/evaluation.py), [annotation_guidelines.md](evidence/annotation_guidelines.md) |
| Independently annotate `150`–`300` real pilot comments after `M3.3` | **In progress (`N = 180/180 verified`, `K = 0/180` pending)** | [m5_1_pilot_pool.jsonl](../../../../data/annotations/m5_1_pilot_pool.jsonl) |

Final task status: **IN_PROGRESS** (`N` implementation + `K` baseline review + real `300`-comment pool export + **`N`'s `180/180` half complete & confirmed**; awaiting `K`'s `180`-item half, joint adjudication, and held-out `1/3` evaluation before `M5.G`).
