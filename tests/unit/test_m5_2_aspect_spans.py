from __future__ import annotations

import math
import unicodedata
from typing import get_args

import pytest
from pydantic import ValidationError

import packages.absa as absa_pkg
import packages.data_contracts as contracts_pkg
from packages.absa import analyze_koc_vs_viewer_absa
from packages.absa.spans import (
    TextUnitInput,
    extract_unit_aspect_spans,
    summarize_units_aspects,
)
from packages.data_contracts.multimodal import (
    ASPECT_NAMES,
    AbsaComparisonRecord,
    AspectAggregateSummary,
    AspectDiscrepancyDetail,
    AspectName,
    AspectPolaritySummaryLabel,
    AspectPresenceStatus,
    AspectSentimentScores,
    AspectSpanEvidence,
    CommentRecord,
    ObservedAspectPolarity,
    RawWhisperSegment,
    TextUnitSourceKind,
    TrustAuditRequest,
)


def test_m5_2_contract_span_and_summary_invariants() -> None:
    assert ASPECT_NAMES == ("taste", "price", "hygiene", "service")
    assert get_args(AspectName) == ("taste", "price", "hygiene", "service")
    assert get_args(AspectPresenceStatus) == ("observed", "absent_unknown")
    assert get_args(ObservedAspectPolarity) == ("positive", "neutral", "negative")
    assert get_args(AspectPolaritySummaryLabel) == ("positive", "neutral", "negative", "unknown")
    assert get_args(TextUnitSourceKind) == (
        "creator_caption",
        "creator_transcript",
        "creator_utterance",
        "viewer_comment",
    )

    valid_span = AspectSpanEvidence(
        unit_id=" c_01 ",
        source_kind="viewer_comment",
        aspect="service",
        polarity_label="negative",
        polarity_score=-1.0,
        start_char=10,
        end_char=32,
        span_text="nhân viên phục vụ chậm",
    )
    assert valid_span.unit_id == "c_01"
    assert valid_span.end_char - valid_span.start_char == len(valid_span.span_text)

    # Frozen contract rejects in-place mutation
    with pytest.raises(ValidationError):
        valid_span.polarity_score = 0.5  # type: ignore[misc]

    # Blank unit_id rejected
    with pytest.raises(ValidationError):
        AspectSpanEvidence(
            unit_id="   ",
            source_kind="viewer_comment",
            aspect="service",
            polarity_label="negative",
            polarity_score=-0.5,
            start_char=0,
            end_char=4,
            span_text="chậm",
        )

    # Whitespace-only span_text rejected even when length matches end_char - start_char
    with pytest.raises(ValidationError):
        AspectSpanEvidence(
            unit_id="c_01",
            source_kind="viewer_comment",
            aspect="service",
            polarity_label="negative",
            polarity_score=-0.5,
            start_char=0,
            end_char=4,
            span_text="    ",
        )

    # Mismatched span_text length (including unstripped surrounding spaces vs slice length) rejected
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
            polarity_score=0.8,
            start_char=0,
            end_char=4,
            span_text=" ngon ",
        )

    # Negative start_char or non-positive interval rejected
    with pytest.raises(ValidationError):
        AspectSpanEvidence(
            unit_id="c_01",
            source_kind="viewer_comment",
            aspect="taste",
            polarity_label="positive",
            polarity_score=0.5,
            start_char=-1,
            end_char=3,
            span_text="ngon",
        )
    with pytest.raises(ValidationError):
        AspectSpanEvidence(
            unit_id="c_01",
            source_kind="viewer_comment",
            aspect="taste",
            polarity_label="positive",
            polarity_score=0.5,
            start_char=4,
            end_char=4,
            span_text="",
        )

    # Out-of-range and non-finite polarity_score rejected
    for bad_score in (-1.01, 1.01, math.nan, math.inf, -math.inf):
        with pytest.raises(ValidationError):
            AspectSpanEvidence(
                unit_id="c_01",
                source_kind="viewer_comment",
                aspect="taste",
                polarity_label="positive",
                polarity_score=bad_score,
                start_char=0,
                end_char=4,
                span_text="ngon",
            )


def test_m5_2_aggregate_summary_absent_unknown_vs_observed_neutral_invariants() -> None:
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
    assert absent.polarity_label == "unknown"

    observed_neutral = AspectAggregateSummary(
        aspect="price",
        presence_status="observed",
        polarity_label="neutral",
        mean_score=0.0,
        mention_unit_count=1,
        span_count=2,
        sufficient_support=False,
    )
    assert observed_neutral.mean_score == 0.0
    assert observed_neutral.polarity_label == "neutral"

    # absent_unknown forbids observed labels, numeric scores, non-zero counts, or sufficient_support=True
    for bad_kwargs in (
        {"polarity_label": "neutral", "mean_score": 0.0, "mention_unit_count": 0, "span_count": 0, "sufficient_support": False},
        {"polarity_label": "unknown", "mean_score": 0.0, "mention_unit_count": 0, "span_count": 0, "sufficient_support": False},
        {"polarity_label": "unknown", "mean_score": None, "mention_unit_count": 1, "span_count": 1, "sufficient_support": False},
        {"polarity_label": "unknown", "mean_score": None, "mention_unit_count": 0, "span_count": 1, "sufficient_support": False},
        {"polarity_label": "unknown", "mean_score": None, "mention_unit_count": 0, "span_count": 0, "sufficient_support": True},
    ):
        with pytest.raises(ValidationError):
            AspectAggregateSummary(
                aspect="hygiene",
                presence_status="absent_unknown",
                **bad_kwargs,  # type: ignore[arg-type]
            )

    # observed requires non-unknown polarity, finite mean_score in [-1, 1], mention_unit_count >= 1, and span_count >= mention_unit_count
    for bad_observed in (
        {"polarity_label": "unknown", "mean_score": 0.0, "mention_unit_count": 1, "span_count": 1},
        {"polarity_label": "neutral", "mean_score": None, "mention_unit_count": 1, "span_count": 1},
        {"polarity_label": "positive", "mean_score": 1.2, "mention_unit_count": 1, "span_count": 1},
        {"polarity_label": "positive", "mean_score": math.nan, "mention_unit_count": 1, "span_count": 1},
        {"polarity_label": "positive", "mean_score": 0.5, "mention_unit_count": 0, "span_count": 0},
        {"polarity_label": "positive", "mean_score": 0.5, "mention_unit_count": 2, "span_count": 1},
    ):
        with pytest.raises(ValidationError):
            AspectAggregateSummary(
                aspect="taste",
                presence_status="observed",
                sufficient_support=True,
                **bad_observed,  # type: ignore[arg-type]
            )


def test_m5_2_discrepancy_detail_support_gate_and_abstention_invariants() -> None:
    supported = AspectDiscrepancyDetail(
        aspect="taste",
        comparison_status="compared_supported_overlap",
        creator_mean_score=0.8,
        viewer_mean_score=-0.4,
        viewer_support_count=3,
        min_viewer_support_required=3,
        sentiment_discrepancy=1.2,
    )
    assert supported.sentiment_discrepancy == 1.2

    # All abstained_* statuses require sentiment_discrepancy is None
    for abstained_status in (
        "abstained_creator_absent",
        "abstained_viewer_absent",
        "abstained_viewer_low_support",
    ):
        ok_abstained = AspectDiscrepancyDetail(
            aspect="price",
            comparison_status=abstained_status,  # type: ignore[arg-type]
            creator_mean_score=0.8 if abstained_status != "abstained_creator_absent" else None,
            viewer_mean_score=-0.4 if abstained_status == "abstained_viewer_low_support" else None,
            viewer_support_count=2 if abstained_status == "abstained_viewer_low_support" else 0,
            min_viewer_support_required=3,
            sentiment_discrepancy=None,
        )
        assert ok_abstained.sentiment_discrepancy is None

        with pytest.raises(ValidationError):
            AspectDiscrepancyDetail(
                aspect="price",
                comparison_status=abstained_status,  # type: ignore[arg-type]
                creator_mean_score=0.8,
                viewer_mean_score=-0.4,
                viewer_support_count=2,
                min_viewer_support_required=3,
                sentiment_discrepancy=1.2,
            )

    # compared_supported_overlap rejects missing scores, insufficient support, or missing/out-of-bounds discrepancy
    for bad_overlap in (
        {"creator_mean_score": None, "viewer_mean_score": -0.4, "viewer_support_count": 3, "sentiment_discrepancy": 1.2},
        {"creator_mean_score": 0.8, "viewer_mean_score": None, "viewer_support_count": 3, "sentiment_discrepancy": 1.2},
        {"creator_mean_score": 0.8, "viewer_mean_score": -0.4, "viewer_support_count": 2, "sentiment_discrepancy": 1.2},
        {"creator_mean_score": 0.8, "viewer_mean_score": -0.4, "viewer_support_count": 3, "sentiment_discrepancy": None},
        {"creator_mean_score": 0.8, "viewer_mean_score": -0.4, "viewer_support_count": 3, "sentiment_discrepancy": 2.1},
        {"creator_mean_score": 0.8, "viewer_mean_score": -0.4, "viewer_support_count": 3, "sentiment_discrepancy": math.inf},
    ):
        with pytest.raises(ValidationError):
            AspectDiscrepancyDetail(
                aspect="taste",
                comparison_status="compared_supported_overlap",
                min_viewer_support_required=3,
                **bad_overlap,  # type: ignore[arg-type]
            )


def test_m5_2_absa_comparison_and_trust_request_backward_compatible_defaults() -> None:
    expected_note = (
        "Observed creator-speech vs viewer-comment sentiment discrepancy on supported overlapping "
        "aspects (>=3 viewer comments); not proof of deception, hygiene truth, or verified diner consensus."
    )

    legacy_record = AbsaComparisonRecord(
        video_id="v_legacy_01",
        koc_scores=AspectSentimentScores(taste=0.7, price=0.0, hygiene=0.0, service=0.0),
        viewer_clean_scores=AspectSentimentScores(taste=0.1, price=0.0, hygiene=0.0, service=0.0),
        pr_hype_gap=0.15,
        undisclosed_pr_risk=0.22,
        viewer_pain_points=[],
        clean_comment_count=2,
        seeding_comment_count=0,
    )
    assert legacy_record.koc_aspect_summaries == {}
    assert legacy_record.viewer_aspect_summaries == {}
    assert legacy_record.aspect_discrepancies == {}
    assert legacy_record.supported_overlapping_aspects == []
    assert legacy_record.supported_sentiment_discrepancy is None
    assert legacy_record.discrepancy_abstention_reason is None
    assert legacy_record.discrepancy_interpretation_note == expected_note
    assert legacy_record.source_spans == []

    req_default = TrustAuditRequest(
        video_id="v_default",
        transcript="Nước dùng đậm đà lắm mọi người ơi",
    )
    assert req_default.utterances == []

    req_with_utterances = TrustAuditRequest(
        video_id="v_utt",
        transcript="Nước dùng đậm đà lắm mọi người ơi",
        utterances=[RawWhisperSegment(start_sec=0.0, end_sec=2.5, text="Nước dùng đậm đà lắm")],
    )
    assert len(req_with_utterances.utterances) == 1

    # Top-level package re-exports all M5.2 symbols
    for symbol in (
        "ASPECT_NAMES",
        "AspectName",
        "AspectPresenceStatus",
        "ObservedAspectPolarity",
        "AspectPolaritySummaryLabel",
        "TextUnitSourceKind",
        "AspectSpanEvidence",
        "AspectAggregateSummary",
        "AspectDiscrepancyDetail",
    ):
        assert hasattr(contracts_pkg, symbol), f"Missing re-export {symbol} on packages.data_contracts"


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
    mixed_summaries, _, _ = summarize_units_aspects([mixed_unit], min_support_units=1)
    assert mixed_summaries["taste"].presence_status == "observed"
    assert mixed_summaries["taste"].polarity_label == "neutral"
    assert mixed_summaries["taste"].mean_score is not None

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
    assert (
        comp_low.discrepancy_abstention_reason
        == "insufficient_overlapping_aspect_support_min_3_comments"
    )
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
    assert comp_ok.discrepancy_abstention_reason is None
    assert any(s.unit_id == "v2_utt_000" for s in comp_ok.source_spans)
    assert not any(s.unit_id == "v2_transcript" for s in comp_ok.source_spans)


def test_m5_2_litotes_bare_factual_abstention_branches_and_reexports() -> None:
    for sym in (
        "TextUnitInput",
        "extract_unit_aspect_spans",
        "summarize_units_aspects",
        "analyze_koc_vs_viewer_absa",
    ):
        assert hasattr(absa_pkg, sym), f"Missing re-export {sym} on packages.absa"

    # Softened litotes ("không quá đắt", "không tệ") & bare factual price -> observed neutral 0.0
    litotes_spans = extract_unit_aspect_spans(
        TextUnitInput(
            unit_id="c_lit",
            source_kind="viewer_comment",
            text="Giá 50 cành một tô không quá đắt, phục vụ cũng không tệ nhưng nước dùng không ngon.",
        )
    )
    lit_by_aspect = {s.aspect: s for s in litotes_spans}
    assert lit_by_aspect["price"].polarity_label == "neutral"
    assert lit_by_aspect["price"].polarity_score == 0.0
    assert lit_by_aspect["service"].polarity_label == "neutral"
    assert lit_by_aspect["service"].polarity_score == 0.0
    assert lit_by_aspect["taste"].polarity_label == "negative"
    assert lit_by_aspect["taste"].polarity_score < 0.0

    # Creator absent vs viewer absent vs seeding excluded from viewer support
    comments = [
        CommentRecord(
            comment_id="c_s1",
            video_id="v3",
            author_handle="u1",
            text="Phục vụ quá chậm",
            original_text="Phục vụ quá chậm",
            like_count=0,
            reply_count=0,
            is_seeding=False,
        ),
        CommentRecord(
            comment_id="c_s2",
            video_id="v3",
            author_handle="u2",
            text="Nhân viên phục vụ cọc",
            original_text="Nhân viên phục vụ cọc",
            like_count=0,
            reply_count=0,
            is_seeding=False,
        ),
        CommentRecord(
            comment_id="c_s3",
            video_id="v3",
            author_handle="u3",
            text="Chủ quán thái độ lồi lõm",
            original_text="Chủ quán thái độ lồi lõm",
            like_count=0,
            reply_count=0,
            is_seeding=False,
        ),
        CommentRecord(
            comment_id="c_seed",
            video_id="v3",
            author_handle="bot1",
            text="Không gian sạch sẽ thoáng mát lắm",
            original_text="Không gian sạch sẽ thoáng mát lắm",
            like_count=0,
            reply_count=0,
            is_seeding=True,
        ),
    ]
    comp = analyze_koc_vs_viewer_absa(
        video_id="v3",
        caption="Giá hạt dẻ 35k",
        transcript="Nước dùng đậm đà thơm ngon",
        comments=comments,
    )
    # Price & Taste: creator observed, viewer absent -> abstained_viewer_absent
    assert comp.aspect_discrepancies["price"].comparison_status == "abstained_viewer_absent"
    assert comp.aspect_discrepancies["taste"].comparison_status == "abstained_viewer_absent"
    # Service: creator absent, 3 clean viewer comments observed -> abstained_creator_absent
    assert comp.aspect_discrepancies["service"].comparison_status == "abstained_creator_absent"
    assert comp.aspect_discrepancies["service"].viewer_support_count == 3
    # Hygiene: only seeding comment mentioned hygiene -> clean viewer absent & creator absent
    assert comp.viewer_aspect_summaries["hygiene"].presence_status == "absent_unknown"
    assert comp.aspect_discrepancies["hygiene"].comparison_status == "abstained_creator_absent"
    # Transcript fallback used when utterances is None
    assert any(s.unit_id == "v3_caption" for s in comp.source_spans)
    assert any(s.unit_id == "v3_transcript" for s in comp.source_spans)

