# M5.2 — Four-Aspect Sentiment with Source Spans Specification

- **Task ID:** `M5.2` (Four-aspect sentiment with source spans; existing lexicon baseline upgrade)
- **Primary Owner:** Trần Đình Khương (`K`)
- **Peer Reviewer:** Nguyễn Việt Nguyên (`N`)
- **Requirement Source:** [TikTok_AI_Engine_Milestone.md](../../../../planning/TikTok_AI_Engine_Milestone.md) (`M5.2`, line 116)
- **Date:** 2026-11-20 (Asia/Ho_Chi_Minh)
- **Branch:** `feat/k-m5.2-aspect-spans-baseline` (branched from `main` @ `60b80147`)
- **Upstream Boundary:** Independent real text-unit double-annotation (`120`–`200` units across `>= 10` pilot videos) waits for `M3.3` / `M3.G` real pilot capture (`data/raw_incremental/` awaits `MS_TOKEN` live run).

## 1. Problem Statement

The legacy ABSA implementation in [analyzer.py](../../../../../packages/absa/analyzer.py), [multimodal.py](../../../../../packages/data_contracts/multimodal.py), and [presentation.py](../../../../../apps/demo/presentation.py) violates five explicit `M5.2` requirements:

1. **Conflation of Missing Aspects and Observed Neutrality:** `score_text_aspects` returns `0.0` both when an aspect is never mentioned (`absent_unknown`) and when an aspect is explicitly mentioned with neutral sentiment (`observed` + `neutral`), skips neutral clauses completely (`if pol == 0.0: continue`), and dumps generic non-aspect clauses into `taste` (`buckets["taste"].append(pol * 0.6)`).
2. **Missing Verifiable Source Spans:** No `comment_id` / `utterance_id` unit provenance or character offsets (`start_char`, `end_char`, `span_text`) are preserved or audited against the source text.
3. **Unqualified Unweighted Four-Aspect Gap & Missing Support Abstention:** `koc_mean` and `viewer_mean` average across all four aspects (`/ 4.0`) regardless of whether creator speech or viewer comments mention them, without enforcing the mandatory **minimum `3` viewer comments** support threshold per aspect, and legacy `/demo/` phrasing risks over-interpreting heuristic gaps instead of calling them an observed **sentiment discrepancy**.
4. **Incomplete Filter & Threshold Sensitivity:** `compute_comment_filter_sensitivity` reports only legacy 4-way averages before/after `M5.1` indicator filtering, omitting supported overlapping-aspect discrepancy shifts and polarity/support threshold sensitivity.
5. **Missing Video-Disjoint Evaluation & Blinded Double-Annotation Tooling:** No module exists to partition pilot units by `video_id` (`dev` vs `held_out`) prior to tuning, evaluate aspect detection macro-F1 (`>= 0.65`), observed-aspect sentiment macro-F1 (`>= 0.60`), exact source-span validity (`>= 95%`), two-annotator agreement, and export a blinded `120`–`200`-unit workbook across `>= 10` videos.

## 2. Architecture & Component Boundaries

We adopt **Deterministic Clause-Window Span Extraction + Support-Gated Overlapping Discrepancy** on local CPU (`USD 0` provider spend, zero external runtime dependencies):

1. **Typed Contracts ([multimodal.py](../../../../../packages/data_contracts/multimodal.py)):**
   - Retain 100% of existing fields on `AspectSentimentScores`, `AbsaComparisonRecord`, `TrustAuditRequest`, `TrustAuditResponse`, and the 14-column Gold Parquet `fact_absa_reviews.parquet` schema in [converter.py](../../../../../pipelines/ingest_incremental_to_gold/converter.py) so `M3.1`, `M4.2`, and `M5.1` callers remain unbroken.
   - Add strict frozen Pydantic models (`allow_inf_nan=False`):
     - `AspectName = Literal["taste", "price", "hygiene", "service"]`
     - `AspectPresenceStatus = Literal["observed", "absent_unknown"]`
     - `ObservedAspectPolarity = Literal["positive", "neutral", "negative"]`
     - `AspectPolaritySummaryLabel = Literal["positive", "neutral", "negative", "unknown"]`
     - `TextUnitSourceKind = Literal["creator_caption", "creator_transcript", "creator_utterance", "viewer_comment"]`
     - `AspectSpanEvidence`:
       - `unit_id: str` (non-blank: `comment_id`, `segment_id`, `"{video_id}_caption"`, or `"{video_id}_transcript"`)
       - `source_kind: TextUnitSourceKind`
       - `aspect: AspectName`
       - `polarity_label: ObservedAspectPolarity`
       - `polarity_score: float` (`[-1.0, 1.0]`)
       - `start_char: int` (`>= 0`) and `end_char: int` (`> start_char`), indexing into the NFC-normalized `unit_text`
       - `span_text: str` (non-blank exact slice `unit_text[start_char:end_char]`, with `len(span_text) == end_char - start_char` enforced by validator)
     - `AspectAggregateSummary`:
       - `aspect: AspectName`
       - `presence_status: AspectPresenceStatus`
       - `polarity_label: AspectPolaritySummaryLabel` (`"unknown"` iff `presence_status == "absent_unknown"`)
       - `mean_score: float | None` (`None` iff `presence_status == "absent_unknown"`; finite `[-1.0, 1.0]` including `0.0` when `observed` + `neutral`)
       - `mention_unit_count: int` (`>= 0`, distinct `unit_id` count mentioning this aspect)
       - `span_count: int` (`>= 0`)
       - `sufficient_support: bool` (`True` for creator speech when `mention_unit_count >= 1`; `True` for viewer comments iff `mention_unit_count >= min_viewer_comments`, default `3`)
     - `AspectDiscrepancyDetail`:
       - `aspect: AspectName`
       - `comparison_status: Literal["compared_supported_overlap", "abstained_creator_absent", "abstained_viewer_absent", "abstained_viewer_low_support"]`
       - `creator_mean_score: float | None`
       - `viewer_mean_score: float | None`
       - `viewer_support_count: int`
       - `min_viewer_support_required: int` (default `3`)
       - `sentiment_discrepancy: float | None` (`round(creator_mean_score - viewer_mean_score, 4)` iff `comparison_status == "compared_supported_overlap"`, else `None`)
   - Extend `AbsaComparisonRecord` with additive defaulted fields:
     - `koc_aspect_summaries: dict[AspectName, AspectAggregateSummary]`
     - `viewer_aspect_summaries: dict[AspectName, AspectAggregateSummary]`
     - `aspect_discrepancies: dict[AspectName, AspectDiscrepancyDetail]`
     - `supported_overlapping_aspects: list[AspectName]`
     - `supported_sentiment_discrepancy: float | None = None` (mean of `sentiment_discrepancy` strictly over `supported_overlapping_aspects`; `None` when `supported_overlapping_aspects` is empty)
     - `discrepancy_abstention_reason: str | None = None`
     - `discrepancy_interpretation_note: str` (explicitly qualifying the figure as an observed creator-vs-comment text sentiment discrepancy, never proof of deception, food safety/hygiene ground truth, or verified diner consensus)
     - `source_spans: list[AspectSpanEvidence] = Field(default_factory=list)`
   - Extend `TrustAuditRequest` with optional `utterances: list[RawWhisperSegment] = Field(default_factory=list)` so segment-level creator utterances (`{video_id}_utt_{idx:03d}`) resolve exact per-utterance character spans when provided, falling back cleanly to `caption` + `transcript` units otherwise.

2. **Exact-Offset Clause Extraction & Polarity Engine (`packages/absa/spans.py` & [analyzer.py](../../../../../packages/absa/analyzer.py)):**
   - Normalize each input unit with `unicodedata.normalize("NFC", raw_text)` once before any regex pass; never call `.strip()` before computing `start_char` / `end_char` — instead trim leading/trailing whitespace by advancing `start_char` and retreating `end_char` on the NFC string so `nfc_text[start_char:end_char] == span_text` holds 100% identically.
   - Split units into clause intervals `(clause_start, clause_end)` using `re.finditer` over sentence punctuation, newlines, and Vietnamese contrastive markers (`nhưng`, `tuy nhiên`, `mà`, `bù lại`, `ngược lại`, `chỉ có điều`, `điểm trừ là`, `điểm cộng là`).
   - Separate **Unicode word-bounded aspect target lexicons** (`taste`, `price`, `hygiene`, `service` — fixing `"k "` substring bugs with explicit Vietnamese price patterns like `\b\d+\s*(?:k|ka|cành|nghìn|ngàn)\b` and contextual cues) from **polarity & neutrality cues**:
     - Explicit neutral cues (`bình thường`, `tạm ổn`, `tạm được`, `ổn áp`, `tầm trung`, `không quá đắt`, `không quá tệ`, `vừa phải`, or factual price/menu mention without positive/negative cue) yield `presence_status="observed"`, `polarity_label="neutral"`, `polarity_score=0.0`.
     - Clauses with zero aspect target matches produce **zero** `AspectSpanEvidence` records in `M5.2` (eliminating the legacy `taste` catch-all contamination in `koc_aspect_summaries` / `viewer_aspect_summaries` while keeping legacy `score_text_aspects` compatible where needed or updating it consistently without breaking `M3.1` invariants).
     - Polarity label mapping for observed spans/aggregates uses symmetric threshold `polarity_tau = 0.15` (`score >= +polarity_tau` -> `"positive"`, `score <= -polarity_tau` -> `"negative"`, otherwise `"neutral"`).

3. **Support-Gated Discrepancy, Filter Sensitivity & `/demo/` Presentation ([evaluation.py](../../../../../packages/seeding/evaluation.py), [trust.py](../../../../../apps/api/app/routers/trust.py), [presentation.py](../../../../../apps/demo/presentation.py)):**
   - Enforce `min_viewer_comments: int = 3` per aspect: if `viewer_aspect_summaries[a].mention_unit_count < 3` or `koc_aspect_summaries[a].presence_status != "observed"`, `aspect_discrepancies[a]` abstains (`sentiment_discrepancy = None`).
   - Enhance `compute_comment_filter_sensitivity` (passing `utterances` if present) to include:
     - `before_filter_supported_discrepancy` vs `after_filter_supported_discrepancy` and per-aspect before/after viewer support counts, scores, and abstention states when `M5.1`-flagged comments are excluded vs retained.
     - `threshold_sensitivity`: grid sweep across `polarity_tau in (0.05, 0.15, 0.25)` and `min_viewer_comments in (1, 3, 5)` reporting active overlapping aspect count and mean supported sentiment discrepancy at each setting.
   - Update `format_trust_audit_markdown` in [presentation.py](../../../../../apps/demo/presentation.py) to display per-aspect presence (`observed` vs `absent_unknown`), viewer support count (`n=...`, marking `< 3` as `tạm dừng / thiếu hỗ trợ <3 bình luận`), observed sentiment discrepancy (never deception/hygiene truth), before/after filter & threshold sensitivity summary, and grounded `source_spans` excerpts (`[unit_id @ start:end]`).

4. **Video-Disjoint Evaluator, Span Auditor & Blinded `120`–`200`-Unit Pool Builder (`packages/absa/evaluation.py`, `pipelines/audit_m5_2_absa/run_baseline_checks.py`):**
   - `split_units_by_video(units, seed=42, dev_ratio=0.5)`: deterministic video-disjoint partition (`dev` vs `held_out`) asserting `len(unique_videos) >= 2` (and enforcing `>= 10` videos, `120 <= len(units) <= 200` on real pilot acceptance checks) with zero `video_id` overlap across splits.
   - `audit_source_span_validity(units_by_id, spans)`: verifies `unit_id` existence, `0 <= start_char < end_char <= len(nfc_text)`, `nfc_text[start_char:end_char] == span_text`, and non-whitespace content, reporting `valid_span_count / total_span_count` against the `>= 0.95` (`95%`) acceptance criterion.
   - `evaluate_m5_2_aspect_sentiment(rows, ...)`:
     - Per-aspect binary presence precision/recall/F1 + **`aspect_detection_macro_f1`** across the 4 aspects (provisional pilot gate `>= 0.65`).
     - 3-class (`positive`, `neutral`, `negative`) precision/recall/F1 + **`observed_sentiment_macro_f1`** evaluated strictly on gold-observed `(unit_id, aspect)` pairs (provisional pilot gate `>= 0.60`), plus per-aspect coverage and class counts.
     - Video-cluster bootstrap 95% confidence intervals (`n_boot=500`) and two-human inter-annotator Cohen's kappa (both binary presence kappa and 4-state `absent_unknown | negative | neutral | positive` kappa).
     - Fail-closed gate flag `m5_2_pilot_gate_eligible`: requires `is_real_pilot_data=True`, `human_signoff_complete=True`, `unique_video_count >= 10`, `120 <= total_annotated_units <= 200`, `aspect_detection_macro_f1 >= 0.65`, `observed_sentiment_macro_f1 >= 0.60`, and `audited_span_validity_rate >= 0.95`.
   - `build_m5_2_annotation_pool(...)`: samples `<= 200` (`>= 120` target) creator utterances/captions + viewer comments across `>= 10` pilot videos from Gold `fact_videos.parquet` / `fact_voice_segments.parquet` / `fact_comments.parquet`, **blinded to model predictions** (`include_predictions=False`, saving locked baseline predictions separately), with `double_review_N_K`, `K_only`, and `N_only` assignments.
   - Author formal English double-annotation guidelines at `docs/reports/milestones/M5.2/evidence/annotation_guidelines.md` (preserving Vietnamese F&B examples for evidence integrity).

## 3. Error Handling & Edge Cases

- **Zero comments or `< 3` comments on all aspects:** `supported_overlapping_aspects == []`, `supported_sentiment_discrepancy is None`, `discrepancy_abstention_reason = "insufficient_overlapping_aspect_support_min_3_comments"`; no division by zero or fabricated `0.0` discrepancy.
- **Creator speech mentions no aspects (`koc` all `absent_unknown`):** All 4 `aspect_discrepancies` report `"abstained_creator_absent"` even if viewer comments have `>= 3` mentions; viewer pain points and viewer aspect summaries still surface descriptively.
- **Unicode NFC vs NFD Vietnamese diacritics:** Normalizing to `NFC` at unit entry guarantees deterministic offsets across macOS/Windows/Linux inputs; `validate_unit_span_offsets` raises `ValueError` if any constructed span drifts from `nfc_text[start_char:end_char]`.
- **Contrastive multi-aspect single sentence:** `"Nước dùng đậm đà giá 35k bình thường nhưng bàn ghế hơi bẩn và phục vụ quá lâu"` splits on contrastive/clause boundaries or local aspect windows inside a clause so `taste=positive`, `price=neutral`, `hygiene=negative`, and `service=negative` do not overwrite each other's polarity.

## 4. Verification & Acceptance Plan

1. **TDD Suite (`tests/unit/test_m5_2_aspect_spans.py`):**
   - `absent_unknown` (`mean_score=None`) vs `observed` + `neutral` (`mean_score=0.0`) separation; generic praise (`"Đỉnh của chóp luôn!"`) does not fabricate `taste="observed"`.
   - Contrastive multi-aspect Vietnamese sentence localizes distinct polarities and `100%` exact `nfc_text[start_char:end_char] == span_text` offsets across `caption`, `utterances`, and `comments`.
   - Support abstention boundary (`n=0, 1, 2` viewer comments abstain -> `None`; `n=3` overlapping with creator observed computes exact `sentiment_discrepancy`).
   - Before/after `M5.1` filter sensitivity + `(polarity_tau, min_viewer_comments)` threshold sensitivity grid.
   - Video-disjoint `dev`/`held_out` splitter (`0` video overlap), hand-checkable `aspect_detection_macro_f1`, `observed_sentiment_macro_f1`, `audit_source_span_validity`, two-annotator kappa, blinded pool builder (`include_predictions=False`), and fail-closed `m5_2_pilot_gate_eligible=False` on synthetic fixtures.
   - `/api/v1/trust/audit-video` and `/demo/` Markdown integration check (non-deception wording, `n=...` support badges, span citations, `M3.1` 14-column Gold Parquet backward compatibility).
2. **Offline Fixture Dry-Run (`artifacts/benchmarks/m5_2_fixture_dry_run_v1.json`):**
   - Execute `python3 -m pipelines.audit_m5_2_absa.run_baseline_checks --mode fixture_dry_run` over an explicitly labeled non-pilot multi-video fixture (`>= 12` synthetic videos, `>= 60` units covering all 4 aspects, neutral price/taste mentions, negation, contrastive clauses, and seeding-contaminated threads).
3. **Repository Gates:**
   - Full `pytest -v` (`194 + new M5.2 tests`), strict `mypy packages apps pipelines` on Linux and `--platform win32`, `python3 scripts/check_secrets.py` (`0` leaks), and `AGENTS.md` layout/relative-link checks.
   - Keep `M5.2` status **`IN_PROGRESS`** until `M3.3` supplies real pilot videos/comments and `K` + `N` complete `120`–`200`-unit double-annotation + `N` peer review.
