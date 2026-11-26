# M5.2 Four-Aspect Sentiment with Source Spans Implementation Plan

> **For agentic workers:** REQUIRED SUB-SKILL: Use superpowers:subagent-driven-development (recommended) or superpowers:executing-plans to implement this plan task-by-task. Steps use checkbox (`- [ ]`) syntax for tracking.

**Goal:** Upgrade the four-aspect (`taste`, `price`, `hygiene`, `service`) ABSA module to preserve `observed` vs `absent_unknown` separately from `observed neutral`, emit 100%-verifiable character-offset `source_spans`, gate creator-vs-viewer `sentiment_discrepancy` on `>= 3` overlapping viewer comments, surface before/after-filter and threshold sensitivity in `/api/v1/trust/audit-video` and `/demo/`, and ship the video-disjoint evaluation & blinded `120`–`200`-unit double-annotation pipeline ready for `M3.3` pilot data.

**Architecture:** Deterministic NFC-indexed clause-window span extraction (`packages/absa/spans.py`) feeds support-gated aggregation (`packages/absa/analyzer.py`) and additive frozen Pydantic contracts (`packages/data_contracts/multimodal.py`), keeping the 14-column `fact_absa_reviews.parquet` Gold sink backward-compatible for `M3.1`. Independent video-disjoint evaluation, span offset auditing, and blinded pilot pool generation live in `packages/absa/evaluation.py` and `pipelines/audit_m5_2_absa/run_baseline_checks.py`.

**Tech Stack:** Python 3.11+, Pydantic v2 (`ConfigDict(frozen=True, allow_inf_nan=False)`), NumPy, Pandas, FastAPI, Gradio Markdown formatter, `pytest`, `mypy` (Linux & `--platform win32`).

**Spec:** [spec.md](spec.md)

## Global Constraints

- Authorized provider/GPU/hosting spend is **`USD 0`**; `M5.2` runs 100% locally on CPU with zero external network calls or LLM calls.
- Preserve Dual-Tier Data discipline: never modify historical `data/corpus/` snapshots or existing benchmark JSON receipts (`Output already exists` fail-closed).
- Preserve 100% backward compatibility with existing `AspectSentimentScores`, `AbsaComparisonRecord` legacy fields, and 14-column `fact_absa_reviews.parquet` in `pipelines/ingest_incremental_to_gold/converter.py`.
- Enforce exact span offset invariant: for every `AspectSpanEvidence`, `unicodedata.normalize("NFC", raw_unit_text)[start_char:end_char] == span_text` and `0 <= start_char < end_char <= len(nfc_text)`.
- Enforce support abstention: viewer aspect summaries require `min_viewer_comments = 3` **distinct comment units** before `comparison_status == "compared_supported_overlap"`; call the resulting delta a **`sentiment discrepancy`**, never proof of deception, hygiene truth, or verified diner consensus.
- Real-pilot acceptance (`aspect_detection_macro_f1 >= 0.65`, `observed_sentiment_macro_f1 >= 0.60`, `audited_span_validity_rate >= 0.95` over `120`–`200` double-annotated units across `>= 10` videos) stays fail-closed (`m5_2_pilot_gate_eligible = False`) on synthetic fixtures, keeping `M5.2` status **`IN_PROGRESS`** until `M3.3` real data arrives.
- All repository reports, docstrings, logs, and guidelines must be in **English** (preserving Vietnamese F&B source quotations/examples for evidence integrity), with `python3 scripts/check_secrets.py` exiting `0` before every commit.

## Review Focus

1. **NFD decomposed Vietnamese diacritics + leading/trailing whitespace (`"  Nước dùng ngon  "` in NFD):** Calling `.strip()` before computing regex match offsets shifts `start_char..end_char`; normalization to NFC must happen once up front and whitespace trimming must adjust `(start_char, end_char)` indices directly on the NFC string (pinned in Task 2).
2. **False-positive `"k "` substring on non-price tokens (`"check in quán"`, `"100k views"`):** Price detection must use Unicode word-bounded patterns (`\b\d+\s*(?:k|ka|cành|nghìn|ngàn)\b` excluding `views/fl/follow/tim`) rather than raw substring `"k "` (pinned in Task 2).
3. **Single viewer comment mentioning the same aspect in 3 clauses (`c_01` has 3 `taste` spans, 0 other comments):** `mention_unit_count` must count **distinct `unit_id`s** (`1 < 3`), not raw `span_count` (`3`), so one verbose commenter never bypasses the 3-comment abstention rule (pinned in Task 2).
4. **Opposing clauses on the same aspect within a single text unit (`"Nước dùng thơm nhưng hơi mặn"`):** Canceling positive and negative clauses (`mean_score == 0.0`) must yield `presence_status = "observed"` and `polarity_label = "neutral"`, never collapsing back to `absent_unknown` (pinned in Task 2).
5. **Cross-table `unit_id` collisions & prediction leakage during `real_pool` export:** Sampling both `fact_voice_segments.parquet` and `fact_comments.parquet` must namespace `unit_id` (`f"{video_id}::utt::{segment_id}"` / `f"{video_id}::cmt::{comment_id}"`) and omit model predictions from the human annotation JSONL when `include_predictions=False` (pinned in Task 4).

---

### Task 1: Typed `M5.2` Multimodal Contracts & Validator Invariants

**Files:**
- Modify: `packages/data_contracts/multimodal.py:146-234`
- Modify: `packages/data_contracts/__init__.py`
- Create: `tests/unit/test_m5_2_aspect_spans.py`

**Interfaces:**
- Consumes: `packages.data_contracts._validators.require_non_blank`, `RawWhisperSegment`, `RawCommentInput`
- Produces:
  - `ASPECT_NAMES: tuple[AspectName, ...] = ("taste", "price", "hygiene", "service")`
  - `AspectName`, `AspectPresenceStatus`, `ObservedAspectPolarity`, `AspectPolaritySummaryLabel`, `TextUnitSourceKind`
  - `AspectSpanEvidence(unit_id, source_kind, aspect, polarity_label, polarity_score, start_char, end_char, span_text)`
  - `AspectAggregateSummary(aspect, presence_status, polarity_label, mean_score, mention_unit_count, span_count, sufficient_support)`
  - `AspectDiscrepancyDetail(aspect, comparison_status, creator_mean_score, viewer_mean_score, viewer_support_count, min_viewer_support_required, sentiment_discrepancy)`
  - Additive fields on `AbsaComparisonRecord` (`koc_aspect_summaries`, `viewer_aspect_summaries`, `aspect_discrepancies`, `supported_overlapping_aspects`, `supported_sentiment_discrepancy`, `discrepancy_abstention_reason`, `discrepancy_interpretation_note`, `source_spans`) and `TrustAuditRequest` (`utterances: list[RawWhisperSegment] = Field(default_factory=list)`)

- [ ] **Step 1: Write the failing contract invariant tests in `tests/unit/test_m5_2_aspect_spans.py`**

```python
from __future__ import annotations

import math
import pytest
from pydantic import ValidationError

from packages.data_contracts.multimodal import (
    ASPECT_NAMES,
    AspectAggregateSummary,
    AspectDiscrepancyDetail,
    AspectSpanEvidence,
    RawWhisperSegment,
    TrustAuditRequest,
)


def test_m5_2_contract_span_and_summary_invariants() -> None:
    assert ASPECT_NAMES == ("taste", "price", "hygiene", "service")

    valid_span = AspectSpanEvidence(
        unit_id="c_01",
        source_kind="viewer_comment",
        aspect="service",
        polarity_label="negative",
        polarity_score=-1.0,
        start_char=10,
        end_char=32,
        span_text="nhân viên phục vụ chậm",
    )
    assert valid_span.end_char - valid_span.start_char == len(valid_span.span_text)

    with pytest.raises(ValidationError):
        AspectSpanEvidence(
            unit_id="c_01",
            source_kind="viewer_comment",
            aspect="service",
            polarity_label="negative",
            polarity_score=-0.5,
            start_char=5,
            end_char=10,
            span_text="mismatch_length",
        )

    with pytest.raises(ValidationError):
        AspectSpanEvidence(
            unit_id="c_01",
            source_kind="viewer_comment",
            aspect="taste",
            polarity_label="positive",
            polarity_score=math.nan,
            start_char=0,
            end_char=4,
            span_text="ngon",
        )

    absent = AspectAggregateSummary(
        aspect="hygiene",
        presence_status="absent_unknown",
        polarity_label="unknown",
        mean_score=None,
        mention_unit_count=0,
        span_count=0,
        sufficient_support=False,
    )
    assert absent.mean_score is None

    with pytest.raises(ValidationError):
        AspectAggregateSummary(
            aspect="hygiene",
            presence_status="absent_unknown",
            polarity_label="neutral",
            mean_score=0.0,
            mention_unit_count=0,
            span_count=0,
            sufficient_support=False,
        )

    with pytest.raises(ValidationError):
        AspectDiscrepancyDetail(
            aspect="price",
            comparison_status="abstained_viewer_low_support",
            creator_mean_score=0.8,
            viewer_mean_score=-0.4,
            viewer_support_count=2,
            min_viewer_support_required=3,
            sentiment_discrepancy=1.2,
        )

    req = TrustAuditRequest(
        video_id="v_utt",
        transcript="Nước dùng đậm đà lắm mọi người ơi",
        utterances=[RawWhisperSegment(start_sec=0.0, end_sec=2.5, text="Nước dùng đậm đà lắm")],
    )
    assert len(req.utterances) == 1
```

- [ ] **Step 2: Run `pytest` to verify RED failure**

Run: `python3 -m pytest tests/unit/test_m5_2_aspect_spans.py -v`
Expected: FAIL (`ImportError: cannot import name 'ASPECT_NAMES' from 'packages.data_contracts.multimodal'`)

- [ ] **Step 3: Implement `M5.2` models and validators in `packages/data_contracts/multimodal.py` & `__init__.py`**

Add `ASPECT_NAMES`, `AspectName`, `AspectPresenceStatus`, `ObservedAspectPolarity`, `AspectPolaritySummaryLabel`, `TextUnitSourceKind`, `AspectSpanEvidence` (validating `end_char > start_char` and `len(span_text) == end_char - start_char`), `AspectAggregateSummary` (validating `absent_unknown` <-> `polarity_label == "unknown"` and `mean_score is None` and `mention_unit_count == 0`, while `observed` requires `polarity_label in {"positive", "neutral", "negative"}`, `mean_score is not None`, and `mention_unit_count >= 1`), `AspectDiscrepancyDetail` (validating `sentiment_discrepancy is not None` iff `comparison_status == "compared_supported_overlap"`), defaulted fields on `AbsaComparisonRecord`, and `utterances: list[RawWhisperSegment] = Field(default_factory=list)` on `TrustAuditRequest`. Re-export new contract types in `packages/data_contracts/__init__.py`.

- [ ] **Step 4: Run `pytest` on new + existing contract tests to verify GREEN**

Run: `python3 -m pytest tests/unit/test_m5_2_aspect_spans.py tests/contract/test_data_contracts.py -v`
Expected: PASS (`11 passed`)

- [ ] **Step 5: Commit Task 1**

```bash
python3 scripts/check_secrets.py
git add packages/data_contracts/multimodal.py packages/data_contracts/__init__.py tests/unit/test_m5_2_aspect_spans.py
git commit -m "feat(m5.2): add typed aspect span, presence, and discrepancy contracts"
```

---

### Task 2: Exact-Offset 4-Aspect Span Engine, Neutral/Unknown Separation & Support-Gated Discrepancy

**Files:**
- Create: `packages/absa/spans.py`
- Modify: `packages/absa/analyzer.py`
- Modify: `packages/absa/__init__.py`
- Modify: `tests/unit/test_m5_2_aspect_spans.py`

**Interfaces:**
- Consumes: Task 1 contracts (`AspectSpanEvidence`, `AspectAggregateSummary`, `AspectDiscrepancyDetail`, `RawWhisperSegment`, `CommentRecord`)
- Produces:
  - `TextUnitInput(unit_id: str, source_kind: TextUnitSourceKind, text: str)` in `packages/absa/spans.py`
  - `extract_unit_aspect_spans(unit: TextUnitInput, *, polarity_tau: float = 0.15) -> list[AspectSpanEvidence]`
  - `summarize_units_aspects(units: list[TextUnitInput], *, min_support_units: int = 1, polarity_tau: float = 0.15) -> tuple[dict[AspectName, AspectAggregateSummary], list[AspectSpanEvidence], list[str]]`
  - `analyze_koc_vs_viewer_absa(..., utterances: list[RawWhisperSegment] | None = None, min_viewer_comments: int = 3, polarity_tau: float = 0.15) -> AbsaComparisonRecord`

- [ ] **Step 1: Add failing tests for NFD exact offsets, `"check in"` vs `"45k"` price neutrality, generic-praise unknown retention, single-comment multi-clause support abstention, and same-aspect canceling clauses**

```python
import unicodedata
from packages.absa import analyze_koc_vs_viewer_absa
from packages.absa.spans import TextUnitInput, extract_unit_aspect_spans
from packages.data_contracts.multimodal import CommentRecord, RawWhisperSegment


def test_m5_2_exact_nfc_offsets_neutral_vs_unknown_and_support_abstention() -> None:
    # 1. NFD input with leading/trailing whitespace + contrastive multi-aspect sentence
    raw_nfd = unicodedata.normalize(
        "NFD",
        "   Nước dùng đậm đà, giá 45k cũng bình thường nhưng bàn ghế hơi bẩn và phục vụ quá chậm!  ",
    )
    nfc_expected = unicodedata.normalize("NFC", raw_nfd)
    spans = extract_unit_aspect_spans(
        TextUnitInput(unit_id="c_nfd", source_kind="viewer_comment", text=raw_nfd)
    )
    by_aspect = {s.aspect: s for s in spans}
    assert set(by_aspect) == {"taste", "price", "hygiene", "service"}
    assert by_aspect["taste"].polarity_label == "positive"
    assert by_aspect["price"].polarity_label == "neutral"
    assert by_aspect["price"].polarity_score == 0.0
    assert by_aspect["hygiene"].polarity_label == "negative"
    assert by_aspect["service"].polarity_label == "negative"
    for sp in spans:
        assert nfc_expected[sp.start_char : sp.end_char] == sp.span_text

    # 2. False-positive guard ("check in quán", "100k views") & generic praise -> 0 spans
    noise_spans = extract_unit_aspect_spans(
        TextUnitInput(
            unit_id="c_generic",
            source_kind="viewer_comment",
            text="Đỉnh của chóp luôn, hôm qua mới check in quán được 100k views!",
        )
    )
    assert noise_spans == []

    # 3. Opposing clauses on the SAME aspect -> observed + neutral (never absent_unknown)
    mixed_unit = TextUnitInput(
        unit_id="c_mixed",
        source_kind="viewer_comment",
        text="Nước dùng rất thơm nhưng vị lại hơi mặn.",
    )
    mixed_spans = extract_unit_aspect_spans(mixed_unit)
    assert len(mixed_spans) == 2
    assert {s.polarity_label for s in mixed_spans} == {"positive", "negative"}

    # 4. Single commenter repeating Taste in 3 clauses must NOT pass >=3 comment support
    one_verbose = [
        CommentRecord(
            comment_id="c_solo",
            video_id="v1",
            author_handle="u1",
            text="Nước dùng ngon. Thịt bò tươi. Nước chấm đậm đà.",
            original_text="Nước dùng ngon. Thịt bò tươi. Nước chấm đậm đà.",
            like_count=0,
            reply_count=0,
            is_seeding=False,
        )
    ]
    comp_low = analyze_koc_vs_viewer_absa(
        video_id="v1",
        caption="Check in quán phở mới",
        transcript="Nước dùng đậm đà ngon xuất sắc",
        comments=one_verbose,
    )
    assert comp_low.viewer_aspect_summaries["taste"].span_count == 3
    assert comp_low.viewer_aspect_summaries["taste"].mention_unit_count == 1
    assert comp_low.viewer_aspect_summaries["taste"].sufficient_support is False
    assert comp_low.aspect_discrepancies["taste"].comparison_status == "abstained_viewer_low_support"
    assert comp_low.aspect_discrepancies["taste"].sentiment_discrepancy is None
    assert comp_low.supported_overlapping_aspects == []
    assert comp_low.supported_sentiment_discrepancy is None
    assert comp_low.koc_aspect_summaries["hygiene"].presence_status == "absent_unknown"
    assert comp_low.koc_aspect_summaries["hygiene"].mean_score is None

    # 5. Three distinct clean viewer comments on Taste + creator utterance -> compared_supported_overlap
    three_comments = [
        CommentRecord(
            comment_id=f"c_{i}",
            video_id="v2",
            author_handle=f"u_{i}",
            text=txt,
            original_text=txt,
            like_count=1,
            reply_count=0,
            is_seeding=False,
        )
        for i, txt in enumerate(
            [
                "Nước dùng hơi mặn và nguội",
                "Thịt bò khô và vị nhạt quá",
                "Nước lèo dở tệ luôn",
            ],
            start=1,
        )
    ]
    comp_ok = analyze_koc_vs_viewer_absa(
        video_id="v2",
        caption="",
        transcript="Nước dùng đậm đà thơm ngon",
        utterances=[RawWhisperSegment(start_sec=0.0, end_sec=3.0, text="Nước dùng đậm đà thơm ngon")],
        comments=three_comments,
    )
    assert comp_ok.supported_overlapping_aspects == ["taste"]
    assert comp_ok.supported_sentiment_discrepancy is not None
    assert comp_ok.supported_sentiment_discrepancy > 1.0
    assert any(s.unit_id == "v2_utt_000" for s in comp_ok.source_spans)
```

- [ ] **Step 2: Run `pytest` to verify RED failure**

Run: `python3 -m pytest tests/unit/test_m5_2_aspect_spans.py -v`
Expected: FAIL (`ModuleNotFoundError: No module named 'packages.absa.spans'`)

- [ ] **Step 3: Implement `packages/absa/spans.py` and integrate into `packages/absa/analyzer.py` & `packages/absa/__init__.py`**

Implement `packages/absa/spans.py`:
- Normalize input text with `unicodedata.normalize("NFC", unit.text)` once; split into clause spans `(c_start, c_end)` via `re.finditer` over `[.!?…\n;]+` and contrastive conjunctions `(?:,\s*|\s+)(?:nhưng\s+mà|nhưng|tuy\s+nhiên|bù\s+lại|ngược\s+lại|chỉ\s+có\s+điều|điểm\s+trừ\s+là|điểm\s+cộng\s+là|còn\s+về)\b`, plus comma boundaries when adjacent segments match distinct aspect targets.
- Use Unicode word boundaries `(?<!\w)...(?!\w)` for aspect target phrases across `taste`, `price` (including `(?<!\w)\d{1,4}\s*(?:k|ka|cành|nghìn|ngàn)(?!\w)` when not followed by `(?:views?|fl|followers?|tim|sub)`), `hygiene`, and `service`.
- Score each aspect match within its local clause (or sub-window around the aspect trigger if multiple aspects co-occur in one comma-less clause): handle negation prefixes (`không`, `chẳng`, `chả`, `chưa`, `kém`, `thiếu`) including softened litotes (`không quá đắt` / `không tệ` -> `0.0` neutral, `không ngon` -> negative) and explicit neutral phrases (`bình thường`, `tạm ổn`, `tạm được`, `ổn áp`, `vừa phải`, `tầm trung`, or bare factual price/aspect mention with `0` pos/neg hits -> `polarity_score = 0.0`, `polarity_label = "neutral"`).
- Trim whitespace around `(start_char, end_char)` by advancing/retreating indices directly on `nfc_text` and assert `nfc_text[start_char:end_char] == span_text`.
- Aggregate per aspect in `summarize_units_aspects`: `mention_unit_count = len({sp.unit_id for sp in aspect_spans})`, `mean_score = round(mean(scores), 4)` when `mention_unit_count >= 1` else `None`, `polarity_label = "positive"` if `mean_score >= polarity_tau` else `"negative"` if `mean_score <= -polarity_tau` else `"neutral"` (when `observed`, else `"unknown"`).
- Wire `analyze_koc_vs_viewer_absa` in `packages/absa/analyzer.py` so legacy `koc_scores`, `viewer_clean_scores`, `pr_hype_gap`, and `undisclosed_pr_risk` stay intact for `M3.1` compatibility while populating all `M5.2` summaries, `aspect_discrepancies`, `supported_overlapping_aspects`, `supported_sentiment_discrepancy`, `discrepancy_abstention_reason`, `discrepancy_interpretation_note`, and `source_spans`.

- [ ] **Step 4: Run `pytest` across `M5.2`, `M4.2`, and `M3.1` ABSA suites to verify GREEN**

Run: `python3 -m pytest tests/unit/test_m5_2_aspect_spans.py tests/unit/test_m4_2_disclosure.py tests/unit/test_incremental_absa_seeding.py -v`
Expected: PASS

- [ ] **Step 5: Commit Task 2**

```bash
python3 scripts/check_secrets.py
git add packages/absa/spans.py packages/absa/analyzer.py packages/absa/__init__.py tests/unit/test_m5_2_aspect_spans.py
git commit -m "feat(m5.2): implement NFC-exact 4-aspect span extractor and support-gated discrepancy"
```

---

### Task 3: Filter & Threshold Sensitivity, `/api/v1/trust/audit-video` & `/demo/` Presentation

**Files:**
- Modify: `packages/seeding/evaluation.py:380-440`
- Modify: `apps/api/app/routers/trust.py:13-39`
- Modify: `apps/demo/presentation.py:158-229`
- Modify: `tests/unit/test_m5_2_aspect_spans.py`

**Interfaces:**
- Consumes: Task 2 `analyze_koc_vs_viewer_absa` (`utterances`, `min_viewer_comments`, `polarity_tau`)
- Produces:
  - Extended `compute_comment_filter_sensitivity(..., utterances: list[RawWhisperSegment] | None = None)` returning existing keys plus `before_filter_supported_discrepancy`, `after_filter_supported_discrepancy`, `supported_discrepancy_shift`, `per_aspect_filter_shift`, and `threshold_sensitivity` (`polarity_tau in (0.05, 0.15, 0.25)` x `min_viewer_comments in (1, 3, 5)`)
  - `/api/v1/trust/audit-video` forwarding `payload.utterances` and returning full `M5.2` fields + `threshold_sensitivity`
  - Updated `format_trust_audit_markdown` rendering `observed` vs `absent_unknown`, `n=<count>` support/abstention status, `Sentiment Discrepancy` wording, threshold sensitivity summary, and `[unit_id @ start:end]` source span citations

- [ ] **Step 1: Add failing API, sensitivity-grid, and `/demo/` Markdown tests to `tests/unit/test_m5_2_aspect_spans.py`**

```python
import asyncio
import httpx
from apps.api.app.main import create_app
from apps.demo.presentation import format_trust_audit_markdown


def test_m5_2_trust_api_filter_and_threshold_sensitivity_and_demo_markdown() -> None:
    app = create_app()

    async def _call() -> dict:
        transport = httpx.ASGITransport(app=app)
        async with httpx.AsyncClient(transport=transport, base_url="http://test") as client:
            resp = await client.post(
                "/api/v1/trust/audit-video",
                json={
                    "video_id": "v_api_52",
                    "caption": "Review phở bò phố cổ giá 45k",
                    "transcript": "Nước dùng đậm đà ngon xuất sắc, nhân viên nhiệt tình lắm",
                    "utterances": [
                        {"start_sec": 0.0, "end_sec": 3.2, "text": "Nước dùng đậm đà ngon xuất sắc"},
                        {"start_sec": 3.2, "end_sec": 6.0, "text": "nhân viên nhiệt tình lắm"},
                    ],
                    "comments": [
                        {"comment_id": "c1", "author_handle": "u1", "text": "Nước dùng hơi mặn, giá 45k bình thường"},
                        {"comment_id": "c2", "author_handle": "u2", "text": "Nước lèo nhạt nhẽo, nhân viên phục vụ chậm"},
                        {"comment_id": "c3", "author_handle": "u3", "text": "Thịt bò khô và vị dở quá"},
                        {"comment_id": "s1", "author_handle": "sp1", "text": "Nước dùng ở quán này đậm đà ngon xuất sắc luôn mọi người"},
                        {"comment_id": "s2", "author_handle": "sp2", "text": "Nước dùng ở quán này đậm đà ngon xuất sắc luôn mọi người nha"},
                    ],
                },
            )
            assert resp.status_code == 200
            return resp.json()

    payload = asyncio.run(_call())
    comp = payload["comparison"]
    assert comp["supported_overlapping_aspects"] == ["taste"]
    assert comp["aspect_discrepancies"]["service"]["comparison_status"] == "abstained_viewer_low_support"
    assert comp["koc_aspect_summaries"]["hygiene"]["presence_status"] == "absent_unknown"
    assert len(comp["source_spans"]) >= 5

    sens = payload["filter_sensitivity"]
    assert "before_filter_supported_discrepancy" in sens
    assert "after_filter_supported_discrepancy" in sens
    assert "threshold_sensitivity" in sens
    assert len(sens["threshold_sensitivity"]) == 9  # 3 tau x 3 min_viewer_comments

    md = format_trust_audit_markdown(payload, hide_seeding=False)
    assert "Sentiment Discrepancy" in md or "Độ lệch cảm xúc quan sát được" in md
    assert "absent_unknown" in md
    assert "v_api_52_utt_000" in md
    assert "@" in md and ":" in md
```

- [ ] **Step 2: Run `pytest` to verify RED failure**

Run: `python3 -m pytest tests/unit/test_m5_2_aspect_spans.py::test_m5_2_trust_api_filter_and_threshold_sensitivity_and_demo_markdown -v`
Expected: FAIL (`AssertionError: 'before_filter_supported_discrepancy' in sens`)

- [ ] **Step 3: Implement sensitivity grid, router wiring, and `/demo/` Markdown table + span citations**

Update `compute_comment_filter_sensitivity` in `packages/seeding/evaluation.py` (computing `analyze_koc_vs_viewer_absa` on all comments as unflagged vs only `not c.is_seeding` comments, plus the `3 x 3` `(polarity_tau, min_viewer_comments)` sweep), pass `utterances=payload.utterances` in `apps/api/app/routers/trust.py`, and update `format_trust_audit_markdown` in `apps/demo/presentation.py` so legacy tests in `test_m4_2_disclosure.py`, `test_m5_1_comment_indicators.py`, and `test_api_and_demo.py` remain satisfied while displaying `M5.2` presence/neutrality, `n=<count>` support & abstention status, observed sentiment discrepancy qualification, threshold sensitivity range, and top grounded `[unit_id @ start:end]` span excerpts.

- [ ] **Step 4: Run `pytest` across `M5.2`, `M5.1`, `M4.2`, and API/demo smoke suites to verify GREEN**

Run: `python3 -m pytest tests/unit/test_m5_2_aspect_spans.py tests/unit/test_m5_1_comment_indicators.py tests/unit/test_m4_2_disclosure.py tests/smoke/test_api_and_demo.py -v`
Expected: PASS

- [ ] **Step 5: Commit Task 3**

```bash
python3 scripts/check_secrets.py
git add packages/seeding/evaluation.py apps/api/app/routers/trust.py apps/demo/presentation.py tests/unit/test_m5_2_aspect_spans.py
git commit -m "feat(m5.2): wire overlapping discrepancy, threshold sensitivity, and span citations into trust API and demo"
```

---

### Task 4: Video-Disjoint `M5.2` Evaluator, Span Auditor, Blinded `120`–`200`-Unit Pool CLI, Guidelines & Report

**Files:**
- Create: `packages/absa/evaluation.py`
- Modify: `packages/absa/__init__.py`
- Create: `pipelines/audit_m5_2_absa/__init__.py`
- Create: `pipelines/audit_m5_2_absa/run_baseline_checks.py`
- Create: `docs/reports/milestones/M5.2/evidence/annotation_guidelines.md`
- Create: `docs/reports/milestones/M5.2/README.md`
- Modify: `docs/reports/milestones/M5.2/evidence/workflow.md`
- Modify: `docs/reports/milestones/README.md`
- Modify: `tests/unit/test_m5_2_aspect_spans.py`

**Interfaces:**
- Consumes: `ASPECT_NAMES`, `TextUnitInput`, `extract_unit_aspect_spans`, `summarize_units_aspects`, `get_peak_rss_mib`
- Produces:
  - `split_units_by_video(rows: list[dict[str, Any]], *, video_id_col: str = "video_id", dev_ratio: float = 0.5, seed: int = 42) -> dict[str, list[dict[str, Any]]]`
  - `audit_source_span_validity(units_by_id: dict[str, str], spans: list[AspectSpanEvidence | dict[str, Any]]) -> dict[str, Any]`
  - `compute_m5_2_annotator_agreement(rows: list[dict[str, Any]]) -> dict[str, Any]`
  - `evaluate_m5_2_aspect_sentiment(rows: list[dict[str, Any]], *, spans: list[AspectSpanEvidence | dict[str, Any]], is_real_pilot_data: bool = False, human_signoff_complete: bool = False, total_annotated_units: int | None = None, total_unique_videos: int | None = None, n_boot: int = 300, seed: int = 42) -> dict[str, Any]`
  - `build_m5_2_annotation_pool(videos_df: pd.DataFrame, voice_df: pd.DataFrame | None, comments_df: pd.DataFrame | None, *, max_units: int = 180, double_overlap: int = 50, seed: int = 42, include_predictions: bool = False) -> list[dict[str, Any]]`
  - CLI `python3 -m pipelines.audit_m5_2_absa.run_baseline_checks --mode fixture_dry_run --output artifacts/benchmarks/m5_2_fixture_dry_run_v1.json`

- [ ] **Step 1: Add failing evaluator, span-auditor, collision-free blinded pool, and CLI dry-run tests to `tests/unit/test_m5_2_aspect_spans.py`**

```python
from pathlib import Path
import pandas as pd
import pytest
from packages.absa.evaluation import (
    audit_source_span_validity,
    build_m5_2_annotation_pool,
    compute_m5_2_annotator_agreement,
    evaluate_m5_2_aspect_sentiment,
    split_units_by_video,
)
from pipelines.audit_m5_2_absa.run_baseline_checks import run_fixture_dry_run


def test_m5_2_evaluator_span_auditor_blinded_pool_and_fixture_cli(tmp_path: Path) -> None:
    # 1. Span validity auditor catches tampered slice and passes exact NFC slice
    units_map = {"u1": "Nước dùng đậm đà, phục vụ quá chậm"}
    audit_res = audit_source_span_validity(
        units_map,
        [
            {
                "unit_id": "u1",
                "aspect": "taste",
                "start_char": 0,
                "end_char": 16,
                "span_text": "Nước dùng đậm đà",
            },
            {
                "unit_id": "u1",
                "aspect": "service",
                "start_char": 0,
                "end_char": 5,
                "span_text": "DRIFT",
            },
        ],
    )
    assert audit_res["total_spans"] == 2
    assert audit_res["valid_spans"] == 1
    assert audit_res["validity_rate"] == 0.5
    assert audit_res["meets_95pct_gate"] is False

    # 2. Collision-free blinded pool across voice segments + comments (same raw ID '1')
    v_df = pd.DataFrame([{"video_id": f"vid_{i:02d}", "caption": f"Quán số {i}"} for i in range(10)])
    voice_df = pd.DataFrame(
        [{"video_id": f"vid_{i:02d}", "segment_id": "1", "text": "Nước dùng đậm đà ngon lắm"} for i in range(10)]
    )
    cmt_df = pd.DataFrame(
        [{"video_id": f"vid_{i:02d}", "comment_id": "1", "text": "Giá 45k bình thường, phục vụ nhanh"} for i in range(10)]
    )
    pool = build_m5_2_annotation_pool(v_df, voice_df, cmt_df, max_units=20, double_overlap=6, include_predictions=False)
    assert len(pool) == 20
    assert len({r["unit_id"] for r in pool}) == 20  # zero cross-table ID collision
    assert all("pred_aspects" not in r for r in pool)

    # 3. Video-disjoint split + agreement + fixture dry-run fail-closed gate
    out_json = tmp_path / "m5_2_dry_run.json"
    receipt = run_fixture_dry_run(output=out_json)
    assert out_json.exists()
    assert receipt["real_pilot_data_available"] is False
    assert receipt["held_out_metrics"]["m5_2_pilot_gate_eligible"] is False
    assert receipt["held_out_metrics"]["span_audit"]["validity_rate"] == 1.0
    assert receipt["held_out_metrics"]["aspect_detection_macro_f1"] >= 0.65
    assert receipt["held_out_metrics"]["observed_sentiment_macro_f1"] >= 0.60

    splits = split_units_by_video(
        [{"video_id": f"v{i}", "unit_id": f"u{i}"} for i in range(10)],
        dev_ratio=0.5,
        seed=42,
    )
    dev_vids = {r["video_id"] for r in splits["dev"]}
    held_vids = {r["video_id"] for r in splits["held_out"]}
    assert dev_vids.isdisjoint(held_vids)

    iaa = compute_m5_2_annotator_agreement(
        [
            {
                "review_assignment": "double_review_N_K",
                "K_human_verified": True,
                "N_human_verified": True,
                "K_aspects": {"taste": "positive", "price": "neutral", "hygiene": "absent_unknown", "service": "negative"},
                "N_aspects": {"taste": "positive", "price": "neutral", "hygiene": "absent_unknown", "service": "negative"},
            }
        ]
    )
    assert iaa["double_verified_unit_count"] == 1
    assert iaa["raw_agreement_4state"] == 1.0
```

- [ ] **Step 2: Run `pytest` to verify RED failure**

Run: `python3 -m pytest tests/unit/test_m5_2_aspect_spans.py::test_m5_2_evaluator_span_auditor_blinded_pool_and_fixture_cli -v`
Expected: FAIL (`ModuleNotFoundError: No module named 'packages.absa.evaluation'`)

- [ ] **Step 3: Implement `packages/absa/evaluation.py`, `pipelines/audit_m5_2_absa/run_baseline_checks.py`, `annotation_guidelines.md`, and `M5.2/README.md`**

1. Implement `packages/absa/evaluation.py` (`split_units_by_video`, `audit_source_span_validity`, `compute_m5_2_annotator_agreement`, `evaluate_m5_2_aspect_sentiment` with video-cluster bootstrap 95% CIs, and `build_m5_2_annotation_pool` enforcing `1 <= max_units <= 200`, collision-free `unit_id`s `f"{vid}::utt::{seg_id}"` / `f"{vid}::cmt::{cmt_id}"` / `f"{vid}::cap"`, and `include_predictions=False` default).
2. Implement `pipelines/audit_m5_2_absa/run_baseline_checks.py` supporting `--mode fixture_dry_run` (`12` synthetic videos, `72` text units covering creator utterances + viewer comments, neutral mentions, contrastive clauses, negation, and seeding contamination; fail-closed if `--output` exists) and `--mode real_pool` (exporting blinded human JSONL + separate `*_locked_predictions.jsonl` from a Gold snapshot once `M3.3` runs).
3. Author `docs/reports/milestones/M5.2/evidence/annotation_guidelines.md` in English, run `python3 -m pipelines.audit_m5_2_absa.run_baseline_checks --mode fixture_dry_run --output artifacts/benchmarks/m5_2_fixture_dry_run_v1.json`, record verification logs, author `docs/reports/milestones/M5.2/README.md` (`Status: IN_PROGRESS`), and add `M5.2` row to `docs/reports/milestones/README.md`.

- [ ] **Step 4: Run full verification suite (`pytest`, Linux & Windows `mypy`, secret hygiene, layout & link check)**

Run:
- `python3 -m pytest -v`
- `python3 -m mypy packages apps pipelines`
- `python3 -m mypy --platform win32 packages apps pipelines`
- `python3 scripts/check_secrets.py`
Expected: All `pytest` pass (`198 passed`), `mypy` clean on both platforms (`103 source files`), `0` secret leaks, `0` broken relative links, exact `M5.2/` directory layout (`README.md`, `evidence/`, `superpowers/{spec.md, plan.md}`).

- [ ] **Step 5: Commit Task 4**

```bash
python3 scripts/check_secrets.py
git add packages/absa/evaluation.py packages/absa/__init__.py pipelines/audit_m5_2_absa/ artifacts/benchmarks/m5_2_fixture_dry_run_v1.json docs/reports/milestones/M5.2/ docs/reports/milestones/README.md tests/unit/test_m5_2_aspect_spans.py
git commit -m "feat(m5.2): add video-disjoint ABSA evaluator, span auditor, fixture dry-run, and milestone report"
```

---

### Task 5: Blinded `K` `115`-Unit Co-Annotation, TDD `real_eval` Harness & Final `M5.2` Evaluation (`2026-11-26`)

**Files:**
- Modify: `packages/absa/evaluation.py`, `packages/absa/__init__.py`
- Modify: `pipelines/audit_m5_2_absa/run_baseline_checks.py`
- Modify: `tests/unit/test_m5_2_aspect_spans.py`
- Modify (after `K` confirmation): `data/annotations/m5_2_pilot_pool.jsonl`
- Create (after `K` confirmation): `artifacts/benchmarks/m5_2_real_pilot_eval_v1.json`, `docs/reports/milestones/M5.2/evidence/m5_2_joint_annotation_receipt.json`
- Modify (after `K` confirmation): `docs/reports/milestones/M5.2/README.md`, `docs/reports/milestones/M5.2/evidence/workflow.md`, `docs/reports/milestones/README.md`, `docs/planning/TikTok_AI_Engine_Milestone.md`

- [ ] **Step 1:** Extract `K`'s `115` assigned units (`50` `double_review_N_K` + `65` `K_only`) from `data/annotations/m5_2_pilot_pool.jsonl` strictly blinded to `N_aspects`, `N_spans`, AI drafts, and `m5_2_pilot_locked_predictions.jsonl`; verify 100% exact `NFC` offsets on `K_spans` and present all `115` units in a review artifact for `K`'s explicit confirmation.
- [ ] **Step 2:** TDD (`RED -> GREEN`) `validate_and_summarize_m5_2_pool` and `run_real_pilot_eval` (`--mode real_eval`) in `tests/unit/test_m5_2_aspect_spans.py`, `packages/absa/evaluation.py`, and `pipelines/audit_m5_2_absa/run_baseline_checks.py`.
- [ ] **Step 3:** Upon `K`'s explicit confirmation, write `K_human_verified=True` + adjudicated labels/spans to `data/annotations/m5_2_pilot_pool.jsonl`, run `--mode real_eval`, run full `pytest`, Linux/Windows `mypy`, `check_secrets.py`, and docs hygiene, update `M5.2 -> COMPLETE`, commit, and push to `origin/main`.
