# M5.2 — Contributor `N` Phase 1 Peer Review & Real-Pilot Edge Fixes

- **Date:** 2026-11-23 (Asia/Ho_Chi_Minh)
- **Task ID:** `M5.2` ([TikTok_AI_Engine_Milestone.md](../../../../planning/TikTok_AI_Engine_Milestone.md))
- **Reviewer (`N`):** Nguyễn Việt Nguyên
- **Primary Owner (`K`):** Trần Đình Khương
- **Reviewed Baseline:** `main` @ `d89f887f` (merge of PR #6) synced up to `befd1ece`, probed read-only against real `M3.3` pilot Gold snapshot `data/corpus/m3_3_pilot_snapshot_v1/` (`30` fresh videos, `436` Whisper `small` CPU voice segments, `0` comments)
- **Phase 1 Outcome:** **APPROVED WITH FINDINGS (RESOLVED IN PLACE)** — milestone status stays **`IN_PROGRESS`** (`m5_2_pilot_gate_eligible = false`) pending `M3.3` comment capture and Phase 2 `120`–`200`-unit `K`+`N` double-annotation.

---

## 1. Acceptance Criteria Audited (Phase 1 Code, Contracts, Baseline & Real-Data Probe)

1. **Missing-aspect vs observed-neutral separation ([spans.py](../../../../../packages/absa/spans.py), [analyzer.py](../../../../../packages/absa/analyzer.py), [multimodal.py](../../../../../packages/data_contracts/multimodal.py)):**
   - Verified `mention_unit_count == 0` emits `presence_status="absent_unknown"`, `polarity_label="unknown"`, `mean_score=None`, `sufficient_support=False`.
   - Verified `"observed"` + `"neutral"` requires `>= 1` `source_spans` entry (`mean_score == 0.0` preserved, including factual price statements, litotes, and within-unit canceling clauses).
   - Verified Vietnamese F&B false-positive guards (`"giá đỗ"`, `"giá như/giá mà"`, `"hết sạch"`, `"lâu đời/lâu năm"`).
2. **Exact `NFC` character offsets & span-backed prediction gate ([evaluation.py](../../../../../packages/absa/evaluation.py)):**
   - Verified `audit_source_span_validity` normalizes via `unicodedata.normalize("NFC", ...)` without stripping leading/trailing whitespace and requires `target_nfc[start_char:end_char] == span_text`.
   - Verified `evaluate_m5_2_aspect_sentiment` partitions strictly by `video_id` (`split_units_by_video`), enforces fail-closed empty-span checks, and rejects predicted observed `(unit_id, aspect)` pairs lacking valid backing spans (including rows missing `unit_id`, hardened at merge `d89f887f`).
3. **`>= 3` viewer comment abstention & `sentiment discrepancy` framing ([analyzer.py](../../../../../packages/absa/analyzer.py), [presentation.py](../../../../../apps/demo/presentation.py)):**
   - Probed `analyze_koc_vs_viewer_absa` on real `M3.3` video `7710799156024986887`: `0` comments -> `supported_overlapping_aspects=[]`, `supported_sentiment_discrepancy=None` (`insufficient_overlapping_aspect_support_min_3_comments`); `2` viewer comments on `taste` -> `abstained_viewer_low_support` (`None`); `3` distinct viewer comments on `taste` -> `compared_supported_overlap` (`1.6667`) with `discrepancy_interpretation_note` explicitly limiting interpretation to observed text-level sentiment discrepancy.
4. **Offline dry-run receipt & `3x3` sensitivity ([m5_2_fixture_dry_run_v1.json](../../../../../artifacts/benchmarks/m5_2_fixture_dry_run_v1.json)):**
   - Confirmed honest non-pilot metadata (`is_real_pilot_data=false`, `human_signoff_complete=false`, `m5_2_pilot_gate_eligible=false`), held-out (`36` units across `6` disjoint videos) `aspect_detection_macro_f1=1.0`, `observed_sentiment_macro_f1=0.9267`, `span_audit.validity_rate=1.0` (`54/54`), seeding filter shift (`max_abs_supported_discrepancy_shift=0.8`), and full `3x3` `(polarity_tau, min_viewer_comments)` sweep.

---

## 2. Read-Only Probe Findings on Real `M3.3` Data (`466` Creator Units) & In-Place TDD Fixes

Running the `M5.2` span extractor across all `30` captions + `436` Whisper `small` CPU utterances (`466` text units) in `m3_3_pilot_snapshot_v1` produced `115` spans (`taste: 80`, `price: 31`, `hygiene: 1`, `service: 3`) with `115/115` exact `NFC` offset validity (`1.0`), and surfaced four concrete findings:

| # | Real `M3.3` Observation | Root Cause Identified | Resolution Applied in Peer-Review Pass |
| --- | --- | --- | --- |
| 1 | `build_m5_2_annotation_pool` generated a `180`-unit pool (`10` captions + `170` utterances, `0` comments) even though `fact_comments` had `0` rows | `build_m5_2_annotation_pool` supports creator-only fallback, leaving CLI `run_real_pool_export` unprotected when comments are missing | Added fail-closed `require_comments: bool = True` guard in `run_real_pool_export` ([run_baseline_checks.py](../../../../../pipelines/audit_m5_2_absa/run_baseline_checks.py)) raising `ValueError` when `fact_comments.parquet` is missing or empty |
| 2 | `"tại sao lại 190.000 vnd trả lời tôi"` emitted truncated price span `"000 vnd trả lời tôi"` | `_SENTENCE_DELIMITER_RE` (`r"[.!?…\n;]+"`) split inside thousand-separated `"190.000"` | Updated `_SENTENCE_DELIMITER_RE` to avoid breaking between digits (`(?!(?<=\d)\.(?=\d))`) and broadened multi-group VND matching (`\d{1,3}(?:[.,]\d{3})+`) in `_ASPECT_PATTERNS["price"]` ([spans.py](../../../../../packages/absa/spans.py)) |
| 3 | `"cô lấy sạch ra hết luôn"` (only `hygiene` hit across `466` units) was misclassified as `hygiene = positive` | `_GUARDED_BAN_SACH_PATTERN` masked `"bán sạch"` but not `"lấy sạch"` / `"vét sạch"` | Extended `_GUARDED_BAN_SACH_PATTERN` in both `_IGNORED_ASPECT_COMPOUNDS_RE` and `_POLARITY_MASK_RE` to cover `(?:bán|lấy|vét)\s+sạch` while keeping genuine `"sạch sẽ"` / `"sạch tinh"` hygiene mentions untouched |
| 4 | `"quẩy chiên thì được nhét chạm tơm ăn cho đỡ ngán với vị ngọt nhẹ"` scored `taste = negative`; `"Dở lên má ơi..."` scored `taste = negative` | `"ngán"` inside relief idiom `"đỡ ngán"` fired `_NEG_PHRASES`; `"dở lên"` (lifting verb) matched `"dở"` | Added grease/heavy-relief phrases (`"đỡ ngán"`, `"đỡ ngấy"`, `"bớt ngán"`, `"bớt ngấy"`, `"chống ngán"`, `"giải ngán"`, `"giảm ngán"`) to `_POLARITY_MASK_COMPOUNDS`, and added `"dở lên"`, `"dở ra"`, `"dở nắp"` to both `_IGNORED_ASPECT_COMPOUNDS` and `_POLARITY_MASK_COMPOUNDS` |

Pinned all four regressions in `test_m5_2_nguyen_peer_review_real_pilot_edge_fixes` ([test_m5_2_aspect_spans.py](../../../../../tests/unit/test_m5_2_aspect_spans.py)) via `RED -> GREEN` TDD and verified dry-run metric parity (`held_out_aspect_f1=1.0`, `held_out_sentiment_f1=0.9267`, `span_validity=1.0`).

---

## 3. Residual Open Risk Carried to Phase 2 (`M3.3` Comments Required)

- **Whisper `small` ASR phonetic homophones:** Real `M3.3` utterances contained ASR transcription artifacts (`"hơi mắc tiện xíu"`, `"Mắc cấp thêm một số loại rau rừng tố"`, `"sẽ phải giá về định luận đi"`) that trigger lexical `"mắc"` / `"giá"` rules. Retained as transparent lexical baseline behavior and recorded as a primary error-analysis focus for the `dev` split once `120`–`200` real units (including `fact_comments`) are annotated in Phase 2.
- **Official real-pilot gate:** Cannot run `--mode real_pool` until `M3.3` supplies non-empty `fact_comments.parquet` (`K` & `N` double-annotation required before `M5.G`).
