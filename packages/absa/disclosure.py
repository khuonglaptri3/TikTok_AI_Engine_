"""Observed platform disclosure/commerce flag and promotional language separation (M4.2)."""
from __future__ import annotations

import re
import unicodedata
from collections.abc import Iterable
from dataclasses import dataclass
from typing import Literal

DisclosureFlagStatus = Literal[
    "observed_ad",
    "observed_ecommerce",
    "observed_ad_and_ecommerce",
    "unlabeled_unknown",
]

# Strictly separated promotional language categories observed in Gold F&B TikTok texts.
# Note: neutral baseline terms such as "review" occur uniformly (~44-47%) across all flag strata
# and are intentionally excluded from promotional indicator triggers.
PROMO_LEXICON_BY_CATEGORY: dict[str, tuple[str, ...]] = {
    "discount_voucher": (
        "giảm giá",
        "khuyến mãi",
        "voucher",
        "mã giảm",
        "ưu đãi",
        "deal",
        "tri ân",
        "giá chỉ",
        "tặng ngay",
    ),
    "commerce_cart_cta": (
        "giỏ hàng",
        "góc trái",
        "link bio",
        "đặt hàng",
        "mua ngay",
        "combo",
        "freeship",
        "chính hãng",
    ),
    "branch_venue_promo": (
        "khai trương",
        "chi nhánh",
        "địa chỉ nằm tại",
        "buffet",
        "menu",
        "booking",
    ),
    "explicit_text_disclosure": (
        "quảng cáo",
        "tài trợ",
        "paid partnership",
        "nhãn hàng tài trợ",
        "#quangcao",
        "#quảngcáo",
        "#paidpartnership",
        "#ad",
        "#ads",
        "#sponsored",
        "#qc",
        "#taitro",
        "#tàitrợ",
    ),
}

FORBIDDEN_FLAG_LEAKAGE_FEATURES: frozenset[str] = frozenset(
    {
        "is_ad",
        "is_ec_video",
        "disclosure_flag_status",
        "undisclosed_pr_risk",
        "commerce_user",
        "tt_seller",
        "video_format",
        "has_cta",
        "ad",
        "ads",
        "quangcao",
        "quảngcáo",
        "quảng_cáo",
        "qc",
        "paidpartnership",
        "paid_partnership",
        "sponsored",
        "taitro",
        "tàitrợ",
        "tài_trợ",
    }
)

FORBIDDEN_PROSODY_PREFIXES: tuple[str, ...] = (
    "prosody_",
    "audio_",
    "whisper_",
    "voice_",
    "poi_",
)

FORBIDDEN_DISCLOSURE_HASHTAGS: frozenset[str] = frozenset(
    {
        "ad",
        "ads",
        "quangcao",
        "quảngcáo",
        "quảng_cáo",
        "qc",
        "paidpartnership",
        "paid_partnership",
        "sponsored",
        "taitro",
        "tàitrợ",
        "tài_trợ",
    }
)

PLATFORM_CAMPAIGN_META_TAGS: frozenset[str] = frozenset(
    {"vtmgr", "dcgr", "tiktokshop", "muataitiktok"}
)

DEFAULT_DISCLOSURE_TARGET_NOTE = (
    "Platform flags (is_ad / is_ec_video) indicate observed platform metadata only; "
    "unlabeled items remain unlabeled_unknown (not verified negative), "
    "lexical promotional cues are separated from flags, and undisclosed sponsorship "
    "probability prediction remains deferred pending independent ground truth."
)

_NEGATION_PREFIX_RE = re.compile(
    r"(?:không|chẳng|chưa(?:\s+từng)?|cam\s+kết\s+không)\s+(?:nhận\s+|có\s+|hề\s+)?$"
)
_ANTI_AD_SUFFIX_RE = re.compile(r"^\s+lố(?![0-9a-zA-ZÀ-ỹ])")


def _compile_term_pattern(term: str) -> re.Pattern[str]:
    escaped = re.escape(term)
    if term.startswith("#"):
        return re.compile(rf"(?<![0-9a-zA-ZÀ-ỹ_]){escaped}(?![0-9a-zA-ZÀ-ỹ_])")
    return re.compile(rf"(?<![0-9a-zA-ZÀ-ỹ#_]){escaped}(?![0-9a-zA-ZÀ-ỹ_])")


_COMPILED_PROMO_PATTERNS: dict[str, tuple[tuple[str, re.Pattern[str]], ...]] = {
    cat: tuple((term, _compile_term_pattern(term)) for term in terms)
    for cat, terms in PROMO_LEXICON_BY_CATEGORY.items()
}


@dataclass(frozen=True)
class DisclosurePromoAnalysis:
    disclosure_flag_status: DisclosureFlagStatus
    matched_indicators: list[str]
    matched_categories: list[str]
    lexical_promo_score: float
    sponsorship_ground_truth_status: Literal["undisclosed_sponsorship_deferred"]
    disclosure_target_note: str


def _normalize_text(text: str) -> str:
    return unicodedata.normalize("NFC", text or "").lower()


def classify_observed_disclosure_flags(is_ad: bool, is_ec_video: bool) -> DisclosureFlagStatus:
    """Map observable platform flags while keeping unflagged items strictly unknown."""
    if is_ad and is_ec_video:
        return "observed_ad_and_ecommerce"
    if is_ad:
        return "observed_ad"
    if is_ec_video:
        return "observed_ecommerce"
    return "unlabeled_unknown"


def _has_non_negated_match(text: str, term: str, pattern: re.Pattern[str]) -> bool:
    for m in pattern.finditer(text):
        prefix = text[max(0, m.start() - 36) : m.start()]
        if _NEGATION_PREFIX_RE.search(prefix):
            continue
        if term == "quảng cáo":
            suffix = text[m.end() : m.end() + 12]
            if _ANTI_AD_SUFFIX_RE.search(suffix):
                continue
        return True
    return False


def extract_promotional_indicators(
    caption: str,
    transcript: str,
    hashtags: list[str] | tuple[str, ...] | None = None,
) -> tuple[list[str], list[str], float]:
    """Extract categorized lexical promotional indicators independently of platform flags."""
    tag_text = " ".join(f"#{str(t).strip().lstrip('#')}" for t in hashtags if str(t).strip()) if hashtags else ""
    combined = _normalize_text(f"{caption} {transcript} {tag_text}")

    matched_indicators: list[str] = []
    matched_categories: list[str] = []
    for category, compiled_terms in _COMPILED_PROMO_PATTERNS.items():
        cat_hit = False
        for term, pat in compiled_terms:
            if _has_non_negated_match(combined, term, pat):
                matched_indicators.append(f"{category}:{term}")
                cat_hit = True
        if cat_hit:
            matched_categories.append(category)

    # Smooth bounded indicator density across distinct cue matches; strictly lexical, never a PR probability.
    lexical_score = round(min(1.0, len(matched_indicators) / 5.0), 4)
    return matched_indicators, matched_categories, lexical_score


def assert_no_feature_leakage(feature_names: Iterable[str]) -> None:
    """Reject flag-derived leakage columns and unverified historical audio/prosody features."""
    bad: list[str] = []
    for raw in feature_names:
        name = unicodedata.normalize("NFC", raw).strip().lower()
        if name in FORBIDDEN_FLAG_LEAKAGE_FEATURES or any(
            name.startswith(prefix) for prefix in FORBIDDEN_PROSODY_PREFIXES
        ):
            bad.append(raw)
    if bad:
        raise ValueError(
            f"Feature leakage or unverified prosody feature rejected for M4.2: {sorted(bad)}"
        )


def analyze_disclosure_and_promo(
    *,
    caption: str,
    transcript: str,
    is_ad: bool = False,
    is_ec_video: bool = False,
    hashtags: list[str] | tuple[str, ...] | None = None,
) -> DisclosurePromoAnalysis:
    """Return cleanly separated observable flag status and lexical promotional cues."""
    flag_status = classify_observed_disclosure_flags(is_ad=is_ad, is_ec_video=is_ec_video)
    indicators, categories, lexical_score = extract_promotional_indicators(
        caption=caption,
        transcript=transcript,
        hashtags=hashtags,
    )
    return DisclosurePromoAnalysis(
        disclosure_flag_status=flag_status,
        matched_indicators=indicators,
        matched_categories=categories,
        lexical_promo_score=lexical_score,
        sponsorship_ground_truth_status="undisclosed_sponsorship_deferred",
        disclosure_target_note=DEFAULT_DISCLOSURE_TARGET_NOTE,
    )


__all__ = [
    "DEFAULT_DISCLOSURE_TARGET_NOTE",
    "DisclosureFlagStatus",
    "DisclosurePromoAnalysis",
    "FORBIDDEN_DISCLOSURE_HASHTAGS",
    "FORBIDDEN_FLAG_LEAKAGE_FEATURES",
    "PLATFORM_CAMPAIGN_META_TAGS",
    "PROMO_LEXICON_BY_CATEGORY",
    "analyze_disclosure_and_promo",
    "assert_no_feature_leakage",
    "classify_observed_disclosure_flags",
    "extract_promotional_indicators",
]
