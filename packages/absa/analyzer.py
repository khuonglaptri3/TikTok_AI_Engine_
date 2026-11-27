from __future__ import annotations

import re
import unicodedata
from collections.abc import Callable
from typing import Literal

from packages.absa.disclosure import analyze_disclosure_and_promo
from packages.absa.spans import TextUnitInput, summarize_units_aspects
from packages.data_contracts.multimodal import (
    ASPECT_NAMES,
    DEFAULT_DISCREPANCY_INTERPRETATION_NOTE,
    AbsaComparisonRecord,
    AspectComparisonStatus,
    AspectDiscrepancyDetail,
    AspectName,
    AspectSentimentScores,
    AspectSpanEvidence,
    CommentRecord,
    RawWhisperSegment,
)

SENTENCE_SPLIT_RE = re.compile(r"(?<=[.!?…])\s+|\n+|[,;]\s+(?:nhưng|mà|tuy nhiên)\s+")

ASPECT_KEYWORDS: dict[str, tuple[str, ...]] = {
    "taste": (
        "vị",
        "nước dùng",
        "nước lèo",
        "nước chấm",
        "thịt",
        "tươi",
        "đậm đà",
        "ngon",
        "vừa miệng",
        "thơm",
        "giòn",
        "mặn",
        "nhạt",
        "tanh",
        "nguội",
        "ngấy",
        "dở",
        "khô",
        "bở",
    ),
    "price": (
        "giá",
        "tiền",
        "cành",
        "k ",
        "rẻ",
        "hạt dẻ",
        "bình dân",
        "hợp lý",
        "đắt",
        "mắc",
        "chát",
        "chặt chém",
        "ít đồ",
        "đầy đặn",
    ),
    "hygiene": (
        "vệ sinh",
        "sạch",
        "sạch sẽ",
        "thoáng",
        "mát",
        "không gian",
        "bàn ghế",
        "dơ",
        "bẩn",
        "mùi hôi",
        "ruồi",
        "ngột ngạt",
        "nóng",
        "khói",
        "tóc",
    ),
    "service": (
        "phục vụ",
        "nhân viên",
        "chủ quán",
        "thái độ",
        "nhiệt tình",
        "dễ thương",
        "nhanh",
        "lâu",
        "chậm",
        "cọc",
        "lồi lõm",
        "khinh khách",
        "quên món",
        "chờ",
    ),
}

POS_WORDS: tuple[str, ...] = (
    "ngon",
    "đậm đà",
    "tươi",
    "giòn",
    "thơm",
    "vừa miệng",
    "rẻ",
    "hạt dẻ",
    "hợp lý",
    "đầy đặn",
    "sạch",
    "sạch sẽ",
    "thoáng",
    "mát",
    "nhiệt tình",
    "dễ thương",
    "nhanh",
    "ưng",
    "xuất sắc",
    "chất lượng",
)

NEG_WORDS: tuple[str, ...] = (
    "dở",
    "mặn",
    "nhạt",
    "tanh",
    "nguội",
    "khô",
    "bở",
    "ngấy",
    "đắt",
    "mắc",
    "chát",
    "chặt chém",
    "ít",
    "dơ",
    "bẩn",
    "hôi",
    "ruồi",
    "khói",
    "nóng",
    "ngột ngạt",
    "lâu",
    "chậm",
    "thái độ",
    "cọc",
    "lồi lõm",
    "tệ",
    "thất vọng",
    "né",
    "quảng cáo lố",
    "pr lố",
)

NEGATION_TOKENS: tuple[str, ...] = ("không ", "chẳng ", "chả ", "chưa ")

PR_PROMO_SIGNALS: tuple[str, ...] = (
    "giảm giá",
    "khuyến mãi",
    "voucher",
    "mã giảm",
    "khai trương",
    "tặng ngay",
    "chi nhánh",
    "địa chỉ nằm tại",
    "nhớ ghé trải nghiệm",
)


def _clause_polarity(clause: str) -> float:
    pos = 0.0
    neg = 0.0
    for pw in POS_WORDS:
        if pw in clause:
            if any(f"{neg_tok}{pw}" in clause for neg_tok in NEGATION_TOKENS):
                neg += 1.0
            else:
                pos += 1.0
    for nw in NEG_WORDS:
        if nw in clause:
            if any(f"{neg_tok}{nw}" in clause for neg_tok in NEGATION_TOKENS):
                pos += 0.5
            else:
                neg += 1.2
    total = pos + neg
    if total == 0.0:
        return 0.0
    return max(-1.0, min(1.0, (pos - neg) / total))


def score_text_aspects(texts: list[str]) -> tuple[AspectSentimentScores, list[str]]:
    """Compute [-1.0, +1.0] polarity across Taste, Price, Hygiene, and Service plus negative pain points."""
    buckets: dict[str, list[float]] = {"taste": [], "price": [], "hygiene": [], "service": []}
    pain_points: list[str] = []

    for raw in texts:
        norm = unicodedata.normalize("NFC", raw).lower()
        for clause in SENTENCE_SPLIT_RE.split(norm):
            c = clause.strip()
            if not c:
                continue
            pol = _clause_polarity(c)
            if pol == 0.0:
                continue
            matched_any = False
            for aspect, kws in ASPECT_KEYWORDS.items():
                if any(kw in c for kw in kws):
                    buckets[aspect].append(pol)
                    matched_any = True
                    if pol <= -0.35 and len(pain_points) < 6:
                        label = f"[{aspect}] {c[:110]}"
                        if label not in pain_points:
                            pain_points.append(label)
            if not matched_any:
                buckets["taste"].append(pol * 0.6)

    def _avg(vals: list[float]) -> float:
        return round(sum(vals) / len(vals), 4) if vals else 0.0

    return (
        AspectSentimentScores(
            taste=_avg(buckets["taste"]),
            price=_avg(buckets["price"]),
            hygiene=_avg(buckets["hygiene"]),
            service=_avg(buckets["service"]),
        ),
        pain_points,
    )


def analyze_koc_vs_viewer_absa(
    video_id: str,
    caption: str,
    transcript: str,
    comments: list[CommentRecord],
    is_ad: bool = False,
    is_ec_video: bool = False,
    hashtags: list[str] | tuple[str, ...] | None = None,
    utterances: list[RawWhisperSegment] | None = None,
    min_viewer_comments: int = 3,
    polarity_tau: float = 0.15,
    absa_engine: Literal["lexicon_v1", "phobert_ner_t4_finetuned", "phobert_hybrid"] = "lexicon_v1",
) -> AbsaComparisonRecord:
    if min_viewer_comments < 1:
        raise ValueError("min_viewer_comments must be >= 1")

    koc_scores, _ = score_text_aspects([f"{caption}. {transcript}"])
    clean_comments = [c for c in comments if not c.is_seeding]
    seeding_count = len(comments) - len(clean_comments)

    if clean_comments:
        viewer_scores, viewer_pains = score_text_aspects([c.text for c in clean_comments])
    else:
        viewer_scores = AspectSentimentScores(taste=0.0, price=0.0, hygiene=0.0, service=0.0)
        viewer_pains = []

    koc_mean = (koc_scores.taste + koc_scores.price + koc_scores.hygiene + koc_scores.service) / 4.0
    viewer_mean = (
        (viewer_scores.taste + viewer_scores.price + viewer_scores.hygiene + viewer_scores.service) / 4.0
        if clean_comments
        else koc_mean
    )
    hype_gap = round(koc_mean - viewer_mean, 4)

    # M4.2 separated disclosure/commerce flags and lexical promotional cues
    disclosure_info = analyze_disclosure_and_promo(
        caption=caption,
        transcript=transcript,
        is_ad=is_ad,
        is_ec_video=is_ec_video,
        hashtags=hashtags,
    )

    # Deprecated compatibility heuristic score (never an undisclosed sponsorship probability)
    combined_lower = unicodedata.normalize("NFC", f"{caption} {transcript}").lower()
    promo_hits = sum(1 for kw in PR_PROMO_SIGNALS if kw in combined_lower)
    seeding_ratio = (seeding_count / len(comments)) if comments else 0.0

    if is_ad or is_ec_video:
        pr_risk = 1.0
    else:
        raw_risk = (
            0.18 * min(promo_hits, 3)
            + 0.25 * max(0.0, koc_mean)
            + 0.30 * max(0.0, hype_gap)
            + 0.25 * seeding_ratio
        )
        pr_risk = round(max(0.0, min(0.98, raw_risk)), 4)

    # M5.2 NFC-exact 4-aspect span evidence and support-gated discrepancy
    clean_vid = video_id.strip() or video_id
    creator_units: list[TextUnitInput] = []
    if caption.strip():
        creator_units.append(
            TextUnitInput(
                unit_id=f"{clean_vid}_caption",
                source_kind="creator_caption",
                text=caption,
            )
        )
    utt_units = (
        [
            TextUnitInput(
                unit_id=f"{clean_vid}_utt_{idx:03d}",
                source_kind="creator_utterance",
                text=seg.text,
            )
            for idx, seg in enumerate(utterances)
            if seg.text.strip()
        ]
        if utterances
        else []
    )
    if utt_units:
        creator_units.extend(utt_units)
    elif transcript.strip():
        creator_units.append(
            TextUnitInput(
                unit_id=f"{clean_vid}_transcript",
                source_kind="creator_transcript",
                text=transcript,
            )
        )

    custom_extractor: Callable[[TextUnitInput], list[AspectSpanEvidence]] | None = None
    if absa_engine in {"phobert_ner_t4_finetuned", "phobert_hybrid"}:
        from packages.absa.neural_absa import get_phobert_absa_model

        nn_bundle = get_phobert_absa_model()
        use_hybrid = absa_engine == "phobert_hybrid"
        custom_extractor = lambda u: nn_bundle.extract_unit_spans(  # noqa: E731
            u,
            hybrid_lexicon=use_hybrid,
            polarity_tau=polarity_tau,
        )

    koc_aspect_summaries, koc_spans, _ = summarize_units_aspects(
        creator_units,
        min_support_units=1,
        polarity_tau=polarity_tau,
        span_extractor=custom_extractor,
    )

    viewer_units: list[TextUnitInput] = []
    for c in clean_comments:
        raw_text = c.original_text if c.original_text.strip() else c.text
        if raw_text.strip():
            viewer_units.append(
                TextUnitInput(
                    unit_id=c.comment_id,
                    source_kind="viewer_comment",
                    text=raw_text,
                )
            )
    viewer_aspect_summaries, viewer_spans, span_viewer_pains = summarize_units_aspects(
        viewer_units,
        min_support_units=min_viewer_comments,
        polarity_tau=polarity_tau,
        span_extractor=custom_extractor,
    )

    merged_viewer_pains = list(viewer_pains)
    for pain in span_viewer_pains:
        if pain not in merged_viewer_pains and len(merged_viewer_pains) < 6:
            merged_viewer_pains.append(pain)

    aspect_discrepancies: dict[AspectName, AspectDiscrepancyDetail] = {}
    for aspect in ASPECT_NAMES:
        koc_sum = koc_aspect_summaries[aspect]
        viewer_sum = viewer_aspect_summaries[aspect]
        comparison_status: AspectComparisonStatus
        sentiment_discrepancy: float | None
        if koc_sum.presence_status != "observed":
            comparison_status = "abstained_creator_absent"
            sentiment_discrepancy = None
        elif viewer_sum.presence_status != "observed":
            comparison_status = "abstained_viewer_absent"
            sentiment_discrepancy = None
        elif viewer_sum.mention_unit_count < min_viewer_comments:
            comparison_status = "abstained_viewer_low_support"
            sentiment_discrepancy = None
        else:
            assert koc_sum.mean_score is not None
            assert viewer_sum.mean_score is not None
            comparison_status = "compared_supported_overlap"
            sentiment_discrepancy = round(
                float(koc_sum.mean_score) - float(viewer_sum.mean_score),
                4,
            )
        aspect_discrepancies[aspect] = AspectDiscrepancyDetail(
            aspect=aspect,
            comparison_status=comparison_status,
            creator_mean_score=koc_sum.mean_score,
            viewer_mean_score=viewer_sum.mean_score,
            viewer_support_count=viewer_sum.mention_unit_count,
            min_viewer_support_required=min_viewer_comments,
            sentiment_discrepancy=sentiment_discrepancy,
        )

    supported_overlapping_aspects: list[AspectName] = [
        aspect
        for aspect in ASPECT_NAMES
        if aspect_discrepancies[aspect].comparison_status == "compared_supported_overlap"
    ]
    if supported_overlapping_aspects:
        supported_sentiment_discrepancy: float | None = round(
            sum(
                float(aspect_discrepancies[aspect].sentiment_discrepancy or 0.0)
                for aspect in supported_overlapping_aspects
            )
            / len(supported_overlapping_aspects),
            4,
        )
        discrepancy_abstention_reason: str | None = None
    else:
        supported_sentiment_discrepancy = None
        discrepancy_abstention_reason = (
            f"insufficient_overlapping_aspect_support_min_{min_viewer_comments}_comments"
        )

    return AbsaComparisonRecord(
        video_id=video_id,
        koc_scores=koc_scores,
        viewer_clean_scores=viewer_scores,
        pr_hype_gap=hype_gap,
        undisclosed_pr_risk=pr_risk,
        disclosure_flag_status=disclosure_info.disclosure_flag_status,
        promotional_language_indicators=disclosure_info.matched_indicators,
        lexical_promo_score=disclosure_info.lexical_promo_score,
        sponsorship_ground_truth_status=disclosure_info.sponsorship_ground_truth_status,
        disclosure_target_note=disclosure_info.disclosure_target_note,
        viewer_pain_points=merged_viewer_pains,
        clean_comment_count=len(clean_comments),
        seeding_comment_count=seeding_count,
        koc_aspect_summaries=koc_aspect_summaries,
        viewer_aspect_summaries=viewer_aspect_summaries,
        aspect_discrepancies=aspect_discrepancies,
        supported_overlapping_aspects=supported_overlapping_aspects,
        supported_sentiment_discrepancy=supported_sentiment_discrepancy,
        discrepancy_abstention_reason=discrepancy_abstention_reason,
        discrepancy_interpretation_note=DEFAULT_DISCREPANCY_INTERPRETATION_NOTE,
        source_spans=[*koc_spans, *viewer_spans],
    )
