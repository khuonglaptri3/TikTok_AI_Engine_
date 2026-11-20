from __future__ import annotations

import math
from typing import get_args

import pytest
from pydantic import ValidationError

import packages.data_contracts as contracts_pkg
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
