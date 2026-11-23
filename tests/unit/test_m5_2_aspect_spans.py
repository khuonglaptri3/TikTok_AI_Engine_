from __future__ import annotations

import asyncio
import json
import math
import unicodedata
from pathlib import Path
from typing import Any, get_args

import httpx
import pandas as pd
import pytest
from pydantic import ValidationError

import packages.absa as absa_pkg
import packages.data_contracts as contracts_pkg
from apps.api.app.main import create_app
from apps.demo.presentation import format_trust_audit_markdown
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
    RawCommentInput,
    RawWhisperSegment,
    TextUnitSourceKind,
    TrustAuditRequest,
)
from packages.seeding import detect_seeding_comments


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


def test_m5_2_task2_review_regressions() -> None:
    # Critical 1: Leading-whitespace NFD RawCommentInput through detect_seeding_comments -> analyze_koc_vs_viewer_absa
    raw_input = RawCommentInput(
        comment_id="c_ws_nfd",
        author_handle="diner_ws",
        text=unicodedata.normalize(
            "NFD",
            "   \t Nước dùng đậm đà nhưng phục vụ quá chậm!  ",
        ),
    )
    seeded_records = detect_seeding_comments("v_ws", [raw_input])
    assert len(seeded_records) == 1
    assert seeded_records[0].text != seeded_records[0].original_text  # stripped vs raw preserved
    comp_ws = analyze_koc_vs_viewer_absa(
        video_id="v_ws",
        caption="",
        transcript="Nước dùng thơm ngon",
        comments=seeded_records,
    )
    ws_spans = [sp for sp in comp_ws.source_spans if sp.unit_id == "c_ws_nfd"]
    assert {sp.aspect for sp in ws_spans} == {"taste", "service"}
    nfc_raw = unicodedata.normalize("NFC", raw_input.text)
    for sp in ws_spans:
        assert sp.start_char >= 5
        assert nfc_raw[sp.start_char : sp.end_char] == sp.span_text

    # Important 1: Preposition "với" & leading evaluative aspect-free chunks preserved
    s_voi_neg = extract_unit_aspect_spans(
        TextUnitInput(
            unit_id="c_voi_1",
            source_kind="viewer_comment",
            text="Thất vọng với thái độ nhân viên",
        )
    )
    assert len(s_voi_neg) == 1
    assert s_voi_neg[0].aspect == "service"
    assert s_voi_neg[0].polarity_label == "negative"
    assert s_voi_neg[0].polarity_score < 0.0

    s_voi_pos = extract_unit_aspect_spans(
        TextUnitInput(
            unit_id="c_voi_2",
            source_kind="viewer_comment",
            text="Xứng đáng với giá tiền",
        )
    )
    assert len(s_voi_pos) == 1
    assert s_voi_pos[0].aspect == "price"
    assert s_voi_pos[0].polarity_label == "positive"
    assert s_voi_pos[0].polarity_score > 0.0

    s_voi_space = extract_unit_aspect_spans(
        TextUnitInput(
            unit_id="c_voi_3",
            source_kind="viewer_comment",
            text="Rất ưng với không gian quán",
        )
    )
    assert len(s_voi_space) == 1
    assert s_voi_space[0].aspect == "hygiene"
    assert s_voi_space[0].polarity_label == "positive"

    s_so_voi = extract_unit_aspect_spans(
        TextUnitInput(
            unit_id="c_voi_4",
            source_kind="viewer_comment",
            text="Khẩu phần quá ít so với mức giá 80k",
        )
    )
    assert len(s_so_voi) == 1
    assert s_so_voi[0].aspect == "price"
    assert s_so_voi[0].polarity_label == "negative"

    s_lead_eval = extract_unit_aspect_spans(
        TextUnitInput(
            unit_id="c_lead_1",
            source_kind="viewer_comment",
            text="Rất tệ, bàn ghế dơ",
        )
    )
    assert len(s_lead_eval) == 1
    assert s_lead_eval[0].aspect == "hygiene"
    assert s_lead_eval[0].polarity_label == "negative"
    assert s_lead_eval[0].start_char == 0
    assert s_lead_eval[0].span_text == "Rất tệ, bàn ghế dơ"

    s_lead_only_eval = extract_unit_aspect_spans(
        TextUnitInput(
            unit_id="c_lead_2",
            source_kind="viewer_comment",
            text="Rất thất vọng, nhân viên phục vụ kiểu gì vậy",
        )
    )
    assert len(s_lead_only_eval) == 1
    assert s_lead_only_eval[0].aspect == "service"
    assert s_lead_only_eval[0].polarity_label == "negative"

    # Important 2: Bare "\s+mà" restricted out of unconditional contrastive splits
    s_sao_ma = extract_unit_aspect_spans(
        TextUnitInput(
            unit_id="c_ma_1",
            source_kind="viewer_comment",
            text="Phục vụ sao mà chậm thế!",
        )
    )
    assert len(s_sao_ma) == 1
    assert s_sao_ma[0].aspect == "service"
    assert s_sao_ma[0].polarity_label == "negative"

    s_gia_ma_dat = extract_unit_aspect_spans(
        TextUnitInput(
            unit_id="c_ma_2",
            source_kind="viewer_comment",
            text="Giá tiền sao mà đắt quá",
        )
    )
    assert len(s_gia_ma_dat) == 1
    assert s_gia_ma_dat[0].aspect == "price"
    assert s_gia_ma_dat[0].polarity_label == "negative"

    s_lau_ma = extract_unit_aspect_spans(
        TextUnitInput(
            unit_id="c_ma_3",
            source_kind="viewer_comment",
            text="Bàn ghế lau rồi mà không sạch",
        )
    )
    assert len(s_lau_ma) == 1
    assert s_lau_ma[0].aspect == "hygiene"
    assert s_lau_ma[0].polarity_label == "negative"

    # Contrastive "nhưng mà", ", mà", and distinct-aspect "\s+mà\s+" still split properly
    s_comma_ma = extract_unit_aspect_spans(
        TextUnitInput(
            unit_id="c_ma_4",
            source_kind="viewer_comment",
            text="Nước dùng đậm đà, mà giá hơi đắt",
        )
    )
    assert {(sp.aspect, sp.polarity_label) for sp in s_comma_ma} == {
        ("taste", "positive"),
        ("price", "negative"),
    }

    s_coord_ma = extract_unit_aspect_spans(
        TextUnitInput(
            unit_id="c_ma_5",
            source_kind="viewer_comment",
            text="Nước dùng ngon mà phục vụ chậm",
        )
    )
    assert {(sp.aspect, sp.polarity_label) for sp in s_coord_ma} == {
        ("taste", "positive"),
        ("service", "negative"),
    }

    # Important 3: Vietnamese F&B false-positive compounds ("lâu đời", "ăn sạch", "giá đỗ"/"giá mà") & negated neutrals
    for non_aspect_text in (
        "Quán phở lâu đời ở Quận 3",
        "Quán bán lâu năm",
        "Lâu lắm rồi mới ăn lại",
        "Ăn sạch cả tô luôn, húp sạch tới giọt cuối",
        "Quán đông khách bán sạch và hết sạch từ sớm",
        "Giá như quán mở gần nhà, giá mà biết sớm hơn",
        "Cho thêm dĩa giá trụng, giá đỗ và rau giá sống nhé",
    ):
        assert (
            extract_unit_aspect_spans(
                TextUnitInput(unit_id="c_fp", source_kind="viewer_comment", text=non_aspect_text)
            )
            == []
        ), f"Expected 0 spans for {non_aspect_text!r}"

    s_lau_doi_pos = extract_unit_aspect_spans(
        TextUnitInput(
            unit_id="c_lau_pos",
            source_kind="viewer_comment",
            text="Nước dùng quán lâu đời ngon",
        )
    )
    assert len(s_lau_doi_pos) == 1
    assert s_lau_doi_pos[0].aspect == "taste"
    assert s_lau_doi_pos[0].polarity_label == "positive"
    assert s_lau_doi_pos[0].polarity_score == 1.0

    s_ban_sach_neg = extract_unit_aspect_spans(
        TextUnitInput(
            unit_id="c_sach_mask",
            source_kind="viewer_comment",
            text="Bàn ghế hơi bẩn, quán bán sạch từ tối",
        )
    )
    assert len(s_ban_sach_neg) == 1
    assert s_ban_sach_neg[0].aspect == "hygiene"
    assert s_ban_sach_neg[0].polarity_label == "negative"

    for neg_neutral_text, expected_aspect in (
        ("Thái độ nhân viên không chấp nhận được", "service"),
        ("Phục vụ không ổn", "service"),
        ("Phục vụ chưa ổn", "service"),
        ("Giá tiền thế này không ổn áp", "price"),
    ):
        spans_nn = extract_unit_aspect_spans(
            TextUnitInput(unit_id="c_nn", source_kind="viewer_comment", text=neg_neutral_text)
        )
        assert len(spans_nn) == 1, f"Expected 1 span for {neg_neutral_text!r}"
        assert spans_nn[0].aspect == expected_aspect
        assert spans_nn[0].polarity_label == "negative"
        assert spans_nn[0].polarity_score < 0.0


def test_m5_2_task2_fix_round2_regressions() -> None:
    # 1. Noun-head + "sạch"/"sạch sẽ" must NOT be swallowed by consumption "ăn sạch"/"uống sạch"
    for hygiene_only_text in (
        "Quán ăn sạch sẽ",
        "Bàn ăn sạch sẽ",
    ):
        spans_h = extract_unit_aspect_spans(
            TextUnitInput(unit_id="c_r2_h1", source_kind="viewer_comment", text=hygiene_only_text)
        )
        assert len(spans_h) == 1, f"Expected 1 hygiene span for {hygiene_only_text!r}"
        assert spans_h[0].aspect == "hygiene"
        assert spans_h[0].polarity_label == "positive"
        assert spans_h[0].polarity_score == 1.0

    for food_hygiene_text in (
        "Đồ ăn sạch sẽ",
        "Món ăn sạch sẽ",
        "Thức ăn sạch sẽ",
        "Đồ ăn sạch",
        "Đồ uống sạch sẽ",
        "Nước uống sạch",
    ):
        spans_fh = extract_unit_aspect_spans(
            TextUnitInput(unit_id="c_r2_h2", source_kind="viewer_comment", text=food_hygiene_text)
        )
        by_aspect = {sp.aspect: sp for sp in spans_fh}
        assert "hygiene" in by_aspect, f"Missing hygiene span for {food_hygiene_text!r}"
        assert by_aspect["hygiene"].polarity_label == "positive"
        assert by_aspect["hygiene"].polarity_score == 1.0

    # Consumption "ăn sạch"/"uống sạch" without noun head still produces 0 hygiene spans
    assert (
        extract_unit_aspect_spans(
            TextUnitInput(
                unit_id="c_r2_cons",
                source_kind="viewer_comment",
                text="Đói quá nên ăn sạch cả tô, uống sạch ly trà đá luôn",
            )
        )
        == []
    )

    # 2. Service-wait complaints with "lâu lắm" / "lâu rồi" must return service = negative
    for wait_text in (
        "Phục vụ lâu lắm",
        "Lên món lâu lắm",
        "Chờ lâu lắm",
        "Đợi lâu rồi",
        "Chờ món lâu lắm",
    ):
        spans_w = extract_unit_aspect_spans(
            TextUnitInput(unit_id="c_r2_w", source_kind="viewer_comment", text=wait_text)
        )
        assert len(spans_w) == 1, f"Expected 1 service span for {wait_text!r}"
        assert spans_w[0].aspect == "service"
        assert spans_w[0].polarity_label == "negative"
        assert spans_w[0].polarity_score < 0.0

    # While standalone temporal nostalgia / "lâu đời" still behave accurately
    assert (
        extract_unit_aspect_spans(
            TextUnitInput(
                unit_id="c_r2_nost",
                source_kind="viewer_comment",
                text="Lâu lắm rồi mới ăn lại",
            )
        )
        == []
    )
    s_nost_taste = extract_unit_aspect_spans(
        TextUnitInput(
            unit_id="c_r2_nost2",
            source_kind="viewer_comment",
            text="Lâu lắm rồi mới ăn lại, nước dùng quán lâu đời ngon",
        )
    )
    assert len(s_nost_taste) == 1
    assert s_nost_taste[0].aspect == "taste"
    assert s_nost_taste[0].polarity_label == "positive"
    assert s_nost_taste[0].polarity_score == 1.0

    # 3. Demonstrative/comparative "giá như vậy" / "mức giá như..." must NOT be swallowed by counterfactual "giá như"
    s_gia_bt = extract_unit_aspect_spans(
        TextUnitInput(
            unit_id="c_r2_p1",
            source_kind="viewer_comment",
            text="Giá như vậy là bình thường",
        )
    )
    assert len(s_gia_bt) == 1
    assert s_gia_bt[0].aspect == "price"
    assert s_gia_bt[0].polarity_label == "neutral"
    assert s_gia_bt[0].polarity_score == 0.0

    s_gia_hl = extract_unit_aspect_spans(
        TextUnitInput(
            unit_id="c_r2_p2",
            source_kind="viewer_comment",
            text="Giá như thế này là hợp lý",
        )
    )
    assert len(s_gia_hl) == 1
    assert s_gia_hl[0].aspect == "price"
    assert s_gia_hl[0].polarity_label == "positive"
    assert s_gia_hl[0].polarity_score == 1.0

    s_muc_gia = extract_unit_aspect_spans(
        TextUnitInput(
            unit_id="c_r2_p3",
            source_kind="viewer_comment",
            text="Mức giá như vậy khá ổn",
        )
    )
    assert len(s_muc_gia) == 1
    assert s_muc_gia[0].aspect == "price"


def test_m5_2_trust_api_filter_and_threshold_sensitivity_and_demo_markdown() -> None:
    from packages.seeding.evaluation import compute_comment_filter_sensitivity

    app = create_app()

    async def _call() -> dict[str, Any]:
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
            return dict(resp.json())

    payload = asyncio.run(_call())
    comp = payload["comparison"]
    assert comp["supported_overlapping_aspects"] == ["taste"]
    assert comp["aspect_discrepancies"]["service"]["comparison_status"] == "abstained_viewer_low_support"
    assert comp["koc_aspect_summaries"]["hygiene"]["presence_status"] == "absent_unknown"
    assert comp["koc_aspect_summaries"]["price"]["presence_status"] == "observed"
    assert comp["koc_aspect_summaries"]["price"]["polarity_label"] == "neutral"
    assert comp["koc_aspect_summaries"]["price"]["mean_score"] == 0.0
    assert len(comp["source_spans"]) >= 5
    assert any(sp["unit_id"] == "v_api_52_utt_000" for sp in comp["source_spans"])
    assert not any(sp["unit_id"] == "v_api_52_transcript" for sp in comp["source_spans"])

    sens = payload["filter_sensitivity"]
    assert "before_filter_supported_aspects" in sens
    assert "after_filter_supported_aspects" in sens
    assert "before_filter_supported_discrepancy" in sens
    assert "after_filter_supported_discrepancy" in sens
    assert "supported_discrepancy_shift" in sens
    assert "per_aspect_filter_shift" in sens
    assert set(sens["per_aspect_filter_shift"].keys()) == set(ASPECT_NAMES)
    taste_shift = sens["per_aspect_filter_shift"]["taste"]
    assert taste_shift["before_viewer_support"] == 5
    assert taste_shift["after_viewer_support"] == 3
    assert taste_shift["before_comparison_status"] == "compared_supported_overlap"
    assert taste_shift["after_comparison_status"] == "compared_supported_overlap"
    assert sens["after_filter_supported_discrepancy"] > sens["before_filter_supported_discrepancy"]
    assert sens["supported_discrepancy_shift"] > 0.0

    assert "threshold_sensitivity" in sens
    assert len(sens["threshold_sensitivity"]) == 9  # 3 tau x 3 min_viewer_comments
    grid_pairs = [
        (cell["polarity_tau"], cell["min_viewer_comments"])
        for cell in sens["threshold_sensitivity"]
    ]
    assert grid_pairs == [
        (tau, min_c) for tau in (0.05, 0.15, 0.25) for min_c in (1, 3, 5)
    ]
    by_pair = {
        (cell["polarity_tau"], cell["min_viewer_comments"]): cell
        for cell in sens["threshold_sensitivity"]
    }
    # At min_viewer_comments=1: taste (3), price (1), service (1) all overlap -> 3 supported aspects
    assert by_pair[(0.15, 1)]["supported_aspect_count"] == 3
    # At min_viewer_comments=3: only taste (3) meets support -> 1 supported aspect
    assert by_pair[(0.15, 3)]["supported_overlapping_aspects"] == ["taste"]
    assert by_pair[(0.15, 3)]["supported_sentiment_discrepancy"] == comp["supported_sentiment_discrepancy"]
    # At min_viewer_comments=5: clean viewer support max is 3 -> abstains cleanly (None)
    assert by_pair[(0.15, 5)]["supported_overlapping_aspects"] == []
    assert by_pair[(0.15, 5)]["supported_aspect_count"] == 0
    assert by_pair[(0.15, 5)]["supported_sentiment_discrepancy"] is None

    md = format_trust_audit_markdown(payload, hide_seeding=False)
    assert "Sentiment Discrepancy" in md or "Độ lệch cảm xúc quan sát được" in md
    assert "absent_unknown" in md
    assert "neutral" in md
    assert "n=3" in md
    assert "Bằng Chứng Trích Dẫn Gốc (Source Spans)" in md
    assert "[v_api_52_utt_000 @ 0:30]" in md
    assert "@" in md and ":" in md

    # Edge case 1: Abstained threshold grid (0 clean overlapping aspects across all 9 cells)
    flagged_only = detect_seeding_comments(
        "v_abst",
        [RawCommentInput(comment_id="only_spam", author_handle="sp", text="Inbox zalo 0909123456")],
    )
    abst_comp = analyze_koc_vs_viewer_absa(
        video_id="v_abst",
        caption="Nước dùng đậm đà",
        transcript="Thịt bò mềm ngon",
        comments=flagged_only,
    )
    abst_sens = compute_comment_filter_sensitivity(
        caption="Nước dùng đậm đà",
        transcript="Thịt bò mềm ngon",
        comments=flagged_only,
    )
    assert abst_sens["before_filter_supported_discrepancy"] is None
    assert abst_sens["after_filter_supported_discrepancy"] is None
    assert abst_sens["supported_discrepancy_shift"] is None
    assert all(
        cell["supported_sentiment_discrepancy"] is None
        for cell in abst_sens["threshold_sensitivity"]
    )
    md_abst = format_trust_audit_markdown(
        {
            "comparison": abst_comp.model_dump(),
            "comments": [c.model_dump() for c in flagged_only],
            "filter_sensitivity": abst_sens,
        }
    )
    assert "insufficient_overlapping_aspect_support_min_3_comments" in md_abst
    assert "0/9" in md_abst

    # Edge case 2: Minimal legacy dict fallback (empty koc_aspect_summaries / aspect_discrepancies)
    md_legacy = format_trust_audit_markdown(
        {
            "comparison": {
                "koc_scores": {"taste": 0.5, "price": 0.0, "hygiene": 0.0, "service": 0.0},
                "viewer_clean_scores": {"taste": -0.2, "price": 0.0, "hygiene": 0.0, "service": 0.0},
                "pr_hype_gap": 0.175,
                "undisclosed_pr_risk": 0.25,
                "clean_comment_count": 1,
                "seeding_comment_count": 0,
            },
            "comments": [],
        }
    )
    assert "Hương vị (Taste)" in md_legacy
    assert "+0.50" in md_legacy
    assert "-0.20" in md_legacy
    assert "Bằng Chứng Trích Dẫn Gốc (Source Spans)" not in md_legacy


def test_m5_2_evaluator_span_auditor_blinded_pool_and_fixture_cli(tmp_path: Path) -> None:
    from packages.absa.evaluation import (
        VALID_ASPECT_STATES,
        audit_source_span_validity,
        build_m5_2_annotation_pool,
        compute_m5_2_annotator_agreement,
        evaluate_m5_2_aspect_sentiment,
        split_units_by_video,
    )
    from pipelines.audit_m5_2_absa.run_baseline_checks import run_fixture_dry_run

    for sym in (
        "VALID_ASPECT_STATES",
        "audit_source_span_validity",
        "build_m5_2_annotation_pool",
        "compute_m5_2_annotator_agreement",
        "evaluate_m5_2_aspect_sentiment",
        "predict_unit_aspects",
        "split_units_by_video",
    ):
        assert hasattr(absa_pkg, sym), f"Missing re-export {sym} on packages.absa"
    assert VALID_ASPECT_STATES == ("absent_unknown", "negative", "neutral", "positive")

    # 1. Span validity auditor catches tampered slice and passes exact NFC slice
    units_map = {"u1": unicodedata.normalize("NFD", "Nước dùng đậm đà, phục vụ quá chậm")}
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
    assert audit_res["invalid_spans"] == 1
    assert audit_res["validity_rate"] == 0.5
    assert audit_res["meets_95pct_gate"] is False

    # 2. Collision-free blinded pool across voice segments + comments (same raw ID '1')
    v_df = pd.DataFrame([{"video_id": f"vid_{i:02d}", "caption": f"Quán số {i}"} for i in range(10)])
    voice_df = pd.DataFrame(
        [{"video_id": f"vid_{i:02d}", "segment_id": "1", "text": "Nước dùng đậm đà ngon lắm"} for i in range(10)]
    )
    cmt_df = pd.DataFrame(
        [
            {
                "video_id": f"vid_{i:02d}",
                "comment_id": "1",
                "text": "Giá 45k bình thường, phục vụ nhanh",
                "original_text": "  Giá 45k bình thường, phục vụ nhanh  ",
            }
            for i in range(10)
        ]
    )
    pool = build_m5_2_annotation_pool(
        v_df,
        voice_df,
        cmt_df,
        max_units=20,
        double_overlap=6,
        include_predictions=False,
    )
    assert len(pool) == 20
    assert len({r["unit_id"] for r in pool}) == 20  # zero cross-table ID collision
    assert len({r["video_id"] for r in pool}) == 10  # balanced across all 10 videos
    assert all("pred_aspects" not in r and "pred_spans" not in r for r in pool)
    cmt_units = [r for r in pool if r["source_kind"] == "viewer_comment"]
    assert cmt_units and all(r["text"].startswith("  ") for r in cmt_units)

    # 3. Video-disjoint split + agreement + fixture dry-run fail-closed gate
    out_json = tmp_path / "m5_2_dry_run.json"
    receipt = run_fixture_dry_run(output=out_json)
    assert out_json.exists()
    assert receipt["real_pilot_data_available"] is False
    assert receipt["fixture_type"] == "authored_edge_regression_fixture_NOT_real_pilot"
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
    assert iaa["cohens_kappa_4state"] == 1.0
    assert evaluate_m5_2_aspect_sentiment is not None


def test_m5_2_evaluator_edge_cases_and_real_pool_cli(tmp_path: Path) -> None:
    from packages.absa.evaluation import (
        audit_source_span_validity,
        build_m5_2_annotation_pool,
        compute_m5_2_annotator_agreement,
        evaluate_m5_2_aspect_sentiment,
        split_units_by_video,
    )
    from pipelines.audit_m5_2_absa.run_baseline_checks import (
        run_fixture_dry_run,
        run_real_pool_export,
    )

    # 1. Enforce 1 <= max_units <= 200 on build_m5_2_annotation_pool
    v_df = pd.DataFrame([{"video_id": f"v{i}", "caption": "Nước dùng ngon"} for i in range(3)])
    for invalid_max in (0, -5, 201, 500):
        with pytest.raises(ValueError, match="max_units"):
            build_m5_2_annotation_pool(v_df, None, None, max_units=invalid_max)

    # 2. Enforce split_units_by_video invariants
    with pytest.raises(ValueError):
        split_units_by_video([{"video_id": "only_one", "unit_id": "u1"}], dev_ratio=0.5)
    with pytest.raises(ValueError):
        split_units_by_video(
            [{"video_id": "v1", "unit_id": "u1"}, {"video_id": "v2", "unit_id": "u2"}],
            dev_ratio=1.0,
        )

    # 3. Span auditor rejects bool start_char/end_char, missing unit_id, and blank span_text
    bad_audit = audit_source_span_validity(
        {"u1": "  Nước dùng ngon"},
        [
            {"unit_id": "u1", "aspect": "taste", "start_char": True, "end_char": 5, "span_text": " Nước"},
            {"unit_id": "u1", "aspect": "taste", "start_char": 0, "end_char": 2, "span_text": "  "},
            {"unit_id": "missing", "aspect": "taste", "start_char": 0, "end_char": 4, "span_text": "Nước"},
        ],
    )
    assert bad_audit["valid_spans"] == 0
    assert bad_audit["invalid_spans"] == 3

    # 4. 3-class sentiment recall penalizes pred == "absent_unknown" on gold-observed aspects
    eval_rows = [
        {
            "video_id": f"vid_{i % 10}",
            "unit_id": f"u_{i}",
            "text": "Nước dùng đậm đà",
            "pred_aspects": {
                "taste": "positive" if i % 2 == 0 else "absent_unknown",
                "price": "absent_unknown",
                "hygiene": "absent_unknown",
                "service": "absent_unknown",
            },
            "adjudicated_aspects": {
                "taste": "positive",
                "price": "absent_unknown",
                "hygiene": "absent_unknown",
                "service": "absent_unknown",
            },
        }
        for i in range(40)
    ]
    spans_ok = [
        {
            "unit_id": f"u_{i}",
            "aspect": "taste",
            "start_char": 0,
            "end_char": 16,
            "span_text": "Nước dùng đậm đà",
        }
        for i in range(0, 40, 2)
    ]
    res_missed = evaluate_m5_2_aspect_sentiment(
        eval_rows,
        spans=spans_ok,
        is_real_pilot_data=True,
        human_signoff_complete=True,
        total_annotated_units=150,
        total_unique_videos=10,
        n_boot=50,
        seed=42,
    )
    # Gold taste is positive on all 40 units; pred is positive on 20 and absent_unknown on 20:
    # observed sentiment positive precision = 1.0, recall = 20/40 = 0.5, F1 = 2/3 = 0.6667
    assert res_missed["observed_sentiment_macro_precision"] == 1.0
    assert res_missed["observed_sentiment_macro_recall"] == 0.5
    assert res_missed["observed_sentiment_macro_f1"] == round(2.0 / 3.0, 4)
    assert res_missed["aspect_detection_macro_f1"] == round(2.0 / 3.0, 4)
    assert res_missed["m5_2_pilot_gate_eligible"] is True

    # Gate fails closed if real pilot flag is False or total_annotated_units > 200
    res_not_real = evaluate_m5_2_aspect_sentiment(
        eval_rows,
        spans=spans_ok,
        is_real_pilot_data=False,
        human_signoff_complete=True,
        total_annotated_units=150,
        total_unique_videos=10,
        n_boot=20,
    )
    assert res_not_real["m5_2_pilot_gate_eligible"] is False

    # Empty IAA returns 0.0 cleanly; invalid aspect state raises ValueError
    empty_iaa = compute_m5_2_annotator_agreement([])
    assert empty_iaa["double_verified_unit_count"] == 0
    assert empty_iaa["cohens_kappa_4state"] == 0.0
    with pytest.raises(ValueError):
        compute_m5_2_annotator_agreement(
            [
                {
                    "review_assignment": "double_review_N_K",
                    "K_human_verified": True,
                    "N_human_verified": True,
                    "K_aspects": {"taste": "invalid_label", "price": "neutral", "hygiene": "absent_unknown", "service": "negative"},
                    "N_aspects": {"taste": "positive", "price": "neutral", "hygiene": "absent_unknown", "service": "negative"},
                }
            ]
        )

    # 5. Fail-closed FileExistsError on both fixture_dry_run and real_pool export
    dry_path = tmp_path / "exists_dry.json"
    dry_path.write_text("{}", encoding="utf-8")
    with pytest.raises(FileExistsError):
        run_fixture_dry_run(output=dry_path)

    corpus_dir = tmp_path / "corpus"
    corpus_dir.mkdir()
    pd.DataFrame([{"video_id": f"v{i:02d}", "caption": "Giá 40k bình thường"} for i in range(10)]).to_parquet(
        corpus_dir / "fact_videos.parquet", index=False
    )
    pd.DataFrame(
        [{"video_id": f"v{i:02d}", "segment_id": "s1", "text": "Nước dùng đậm đà"} for i in range(10)]
    ).to_parquet(corpus_dir / "fact_voice_segments.parquet", index=False)
    pd.DataFrame(
        [
            {
                "video_id": f"v{i:02d}",
                "comment_id": "c1",
                "text": "Phục vụ quá chậm",
                "original_text": "  Phục vụ quá chậm ",
            }
            for i in range(10)
        ]
    ).to_parquet(corpus_dir / "fact_comments.parquet", index=False)

    out_pool = tmp_path / "m5_2_pool.jsonl"
    out_preds = tmp_path / "m5_2_locked_preds.jsonl"
    exported = run_real_pool_export(
        corpus_dir=corpus_dir,
        output_pool=out_pool,
        output_locked_predictions=out_preds,
        max_units=25,
        double_overlap=10,
        seed=42,
    )
    assert len(exported) == 25
    assert out_pool.is_file() and out_preds.is_file()
    pool_lines = [json.loads(line) for line in out_pool.read_text(encoding="utf-8").splitlines()]
    pred_lines = [json.loads(line) for line in out_preds.read_text(encoding="utf-8").splitlines()]
    assert all("pred_aspects" not in r and "pred_spans" not in r for r in pool_lines)
    assert len(pred_lines) == 25
    pred_spans_flat = [sp for r in pred_lines for sp in r["pred_spans"]]
    span_check = audit_source_span_validity({r["unit_id"]: r["text"] for r in pool_lines}, pred_spans_flat)
    assert span_check["validity_rate"] == 1.0

    with pytest.raises(FileExistsError):
        run_real_pool_export(
            corpus_dir=corpus_dir,
            output_pool=out_pool,
            output_locked_predictions=tmp_path / "other.jsonl",
        )


def test_m5_2_task4_fix_round1_multimodal_scoping_and_span_backing(tmp_path: Path) -> None:
    from packages.absa.evaluation import (
        audit_source_span_validity,
        build_m5_2_annotation_pool,
        evaluate_m5_2_aspect_sentiment,
    )
    from pipelines.audit_m5_2_absa.run_baseline_checks import run_real_pool_export

    # 1. Critical: 1,200 historical caption-only videos + 10 multimodal M3.3 pilot videos
    pilot_vids = {f"pilot_{i:02d}" for i in range(10)}
    videos_rows = [
        {"video_id": f"hist_{i:04d}", "caption": f"Quán phở lịch sử {i} ngon đậm đà"}
        for i in range(1200)
    ] + [
        {"video_id": f"pilot_{i:02d}", "caption": f"Review quán bún bò số {i} giá 45k bình thường"}
        for i in range(10)
    ]
    voice_rows = [
        {
            "video_id": f"pilot_{i:02d}",
            "segment_id": f"s_{s}",
            "text": "Nước dùng đậm đà ngon xuất sắc",
        }
        for i in range(10)
        for s in range(2)
    ]
    comment_rows = [
        {
            "video_id": f"pilot_{i:02d}",
            "comment_id": f"c_{c}",
            "text": "Bàn ghế hơi bẩn, phục vụ quá chậm",
            "original_text": "  Bàn ghế hơi bẩn, phục vụ quá chậm ",
        }
        for i in range(10)
        for c in range(2)
    ]

    dual_sink_dir = tmp_path / "dual_sink_gold"
    dual_sink_dir.mkdir()
    pd.DataFrame(videos_rows).to_parquet(dual_sink_dir / "fact_videos.parquet", index=False)
    pd.DataFrame(voice_rows).to_parquet(dual_sink_dir / "fact_voice_segments.parquet", index=False)
    pd.DataFrame(comment_rows).to_parquet(dual_sink_dir / "fact_comments.parquet", index=False)

    out_pool = tmp_path / "r1_pool.jsonl"
    out_preds = tmp_path / "r1_preds.jsonl"
    sampled = run_real_pool_export(
        corpus_dir=dual_sink_dir,
        output_pool=out_pool,
        output_locked_predictions=out_preds,
        max_units=180,
        double_overlap=20,
        seed=42,
    )
    # Only the 10 multimodal videos (20 utterances + 20 comments + 10 pilot captions = 50 units) are eligible
    assert len(sampled) == 50
    assert {r["video_id"] for r in sampled} == pilot_vids
    assert {r["source_kind"] for r in sampled} == {
        "creator_utterance",
        "viewer_comment",
        "creator_caption",
    }

    # Caption-only fallback still works when voice_df and comments_df have zero multimodal videos
    cap_fallback = build_m5_2_annotation_pool(
        pd.DataFrame(videos_rows[:5]),
        pd.DataFrame(columns=["video_id", "segment_id", "text"]),
        None,
        max_units=5,
    )
    assert len(cap_fallback) == 5

    # 2. Important: empty spans fail closed, dict spans validate aspect & trimmed span_text
    empty_audit = audit_source_span_validity({"u1": "Nước dùng đậm đà"}, [])
    assert empty_audit["total_spans"] == 0
    assert empty_audit["validity_rate"] == 0.0
    assert empty_audit["meets_95pct_gate"] is False

    dict_invariants = audit_source_span_validity(
        {"u1": "  Nước dùng đậm đà  "},
        [
            {
                "unit_id": "u1",
                "aspect": "ambiance",
                "start_char": 2,
                "end_char": 18,
                "span_text": "Nước dùng đậm đà",
            },
            {
                "unit_id": "u1",
                "aspect": "taste",
                "start_char": 0,
                "end_char": 18,
                "span_text": "  Nước dùng đậm đà",
            },
        ],
    )
    assert dict_invariants["valid_spans"] == 0
    assert [ex["reason"] for ex in dict_invariants["invalid_examples"]] == [
        "invalid_aspect",
        "untrimmed_span_text",
    ]

    # 3. Important: evaluate_m5_2_aspect_sentiment requires every predicted observed (unit_id, aspect) to have >=1 valid span
    rows_40 = [
        {
            "video_id": f"vid_{i % 10}",
            "unit_id": f"u_{i}",
            "text": "Nước dùng đậm đà",
            "pred_aspects": {
                "taste": "positive" if i < 30 else "absent_unknown",
                "price": "absent_unknown",
                "hygiene": "absent_unknown",
                "service": "absent_unknown",
            },
            "adjudicated_aspects": {
                "taste": "positive" if i < 30 else "absent_unknown",
                "price": "absent_unknown",
                "hygiene": "absent_unknown",
                "service": "absent_unknown",
            },
        }
        for i in range(40)
    ]

    res_empty_spans = evaluate_m5_2_aspect_sentiment(
        rows_40,
        spans=[],
        is_real_pilot_data=True,
        human_signoff_complete=True,
        total_annotated_units=150,
        total_unique_videos=10,
        n_boot=20,
    )
    assert res_empty_spans["m5_2_pilot_gate_eligible"] is False

    # Passing 1 valid span for 30 predicted observed (unit_id, aspect) pairs gives validity_rate=1.0 but fails span backing!
    res_partial_backing = evaluate_m5_2_aspect_sentiment(
        rows_40,
        spans=[
            {
                "unit_id": "u_0",
                "aspect": "taste",
                "start_char": 0,
                "end_char": 16,
                "span_text": "Nước dùng đậm đà",
            }
        ],
        is_real_pilot_data=True,
        human_signoff_complete=True,
        total_annotated_units=150,
        total_unique_videos=10,
        n_boot=20,
    )
    assert res_partial_backing["span_audit"]["validity_rate"] == 1.0
    assert res_partial_backing["all_predicted_aspects_span_backed"] is False
    assert res_partial_backing["unbacked_predicted_observed_pair_count"] == 29
    assert res_partial_backing["m5_2_pilot_gate_eligible"] is False

    # Backing all 30 predicted observed (unit_id, aspect) pairs satisfies the gate
    full_backing_spans = [
        {
            "unit_id": f"u_{i}",
            "aspect": "taste",
            "start_char": 0,
            "end_char": 16,
            "span_text": "Nước dùng đậm đà",
        }
        for i in range(30)
    ]
    res_full_backing = evaluate_m5_2_aspect_sentiment(
        rows_40,
        spans=full_backing_spans,
        is_real_pilot_data=True,
        human_signoff_complete=True,
        total_annotated_units=150,
        total_unique_videos=10,
        n_boot=20,
    )
    assert res_full_backing["all_predicted_aspects_span_backed"] is True
    assert res_full_backing["unbacked_predicted_observed_pair_count"] == 0
    assert res_full_backing["m5_2_pilot_gate_eligible"] is True

    # Rows missing unit_id that predict observed aspects must fail span-backing fail-closed
    rows_missing_uid = [{k: v for k, v in r.items() if k != "unit_id"} for r in rows_40]
    res_missing_uid = evaluate_m5_2_aspect_sentiment(
        rows_missing_uid,
        spans=full_backing_spans,
        is_real_pilot_data=True,
        human_signoff_complete=True,
        total_annotated_units=150,
        total_unique_videos=10,
        n_boot=20,
    )
    assert res_missing_uid["all_predicted_aspects_span_backed"] is False
    assert res_missing_uid["unbacked_predicted_observed_pair_count"] == 30
    assert res_missing_uid["m5_2_pilot_gate_eligible"] is False


def test_m5_2_nguyen_peer_review_real_pilot_edge_fixes(tmp_path: Path) -> None:
    """Guard thousand-separated VND amounts, depletion/relief idioms, and comment-required real_pool export."""
    import pandas as pd

    from packages.absa.evaluation import audit_source_span_validity, predict_unit_aspects
    from packages.absa.spans import TextUnitInput
    from pipelines.audit_m5_2_absa.run_baseline_checks import run_real_pool_export

    # 1. Thousand separators inside VND numbers must not split sentences mid-price
    price_unit = TextUnitInput(
        unit_id="u_vnd_190",
        source_kind="creator_utterance",
        text="tại sao lại 190.000 vnd trả lời tôi",
    )
    price_pred, price_spans = predict_unit_aspects(price_unit)
    assert price_pred["price"] == "neutral"
    assert len(price_spans) == 1
    assert "190.000 vnd" in price_spans[0].span_text

    multi_dot_unit = TextUnitInput(
        unit_id="u_vnd_million",
        source_kind="creator_utterance",
        text="Hết 1.250.000đ. Quán hơi đắt",
    )
    multi_pred, multi_spans = predict_unit_aspects(multi_dot_unit)
    assert any("1.250.000đ" in sp.span_text for sp in multi_spans)
    assert multi_pred["price"] == "negative"

    # 2. Depletion verb "lấy sạch" is not hygiene praise; genuine hygiene still works
    deplete_unit = TextUnitInput(
        unit_id="u_deplete",
        source_kind="creator_utterance",
        text="cô lấy sạch ra hết luôn",
    )
    deplete_pred, deplete_spans = predict_unit_aspects(deplete_unit)
    assert deplete_pred["hygiene"] == "absent_unknown"
    assert deplete_spans == []

    clean_unit = TextUnitInput(
        unit_id="u_clean",
        source_kind="viewer_comment",
        text="Bàn ghế lấy đồ xong vẫn sạch sẽ",
    )
    clean_pred, _ = predict_unit_aspects(clean_unit)
    assert clean_pred["hygiene"] == "positive"

    # 3. Relief idioms ("đỡ ngán") and lifting verb ("dở lên") must not trigger negative taste
    relief_unit = TextUnitInput(
        unit_id="u_relief",
        source_kind="creator_utterance",
        text="quẩy chiên thì được nhét chạm tơm ăn cho đỡ ngán với vị ngọt nhẹ",
    )
    relief_pred, _ = predict_unit_aspects(relief_unit)
    assert relief_pred["taste"] == "neutral"

    lift_unit = TextUnitInput(
        unit_id="u_lift",
        source_kind="creator_utterance",
        text="Dở lên má ơi, bên dưới có thay 1 món yêu thích của tôi",
    )
    lift_pred, _ = predict_unit_aspects(lift_unit)
    assert lift_pred["taste"] == "absent_unknown"

    bad_taste_unit = TextUnitInput(
        unit_id="u_bad_taste",
        source_kind="viewer_comment",
        text="Món này dở quá luôn",
    )
    bad_pred, _ = predict_unit_aspects(bad_taste_unit)
    assert bad_pred["taste"] == "negative"

    # All extracted spans remain 1-to-1 NFC aligned
    unit_map = {u.unit_id: u.text for u in (price_unit, multi_dot_unit, clean_unit, bad_taste_unit)}
    all_spans = [*price_spans, *multi_spans]
    assert audit_source_span_validity(unit_map, all_spans)["validity_rate"] == 1.0

    # 4. Official run_real_pool_export fails closed when fact_comments.parquet is empty/missing
    no_cmt_dir = tmp_path / "no_comments_gold"
    no_cmt_dir.mkdir()
    pd.DataFrame([{"video_id": "v1", "caption": "Bún bò 35k"}]).to_parquet(
        no_cmt_dir / "fact_videos.parquet", index=False
    )
    pd.DataFrame([{"video_id": "v1", "segment_id": "s0", "text": "Nước dùng ngon"}]).to_parquet(
        no_cmt_dir / "fact_voice_segments.parquet", index=False
    )
    with pytest.raises(ValueError, match="fact_comments.parquet"):
        run_real_pool_export(
            corpus_dir=no_cmt_dir,
            output_pool=tmp_path / "pool_fail.jsonl",
            output_locked_predictions=tmp_path / "preds_fail.jsonl",
        )


