"""Vietnamese F&B 4-Aspect Sentiment (ABSA) & Undisclosed PR Hype Gap Analyzer."""

from packages.absa.analyzer import analyze_koc_vs_viewer_absa, score_text_aspects
from packages.absa.disclosure import (
    analyze_disclosure_and_promo,
    classify_observed_disclosure_flags,
)
from packages.absa.spans import (
    TextUnitInput,
    extract_unit_aspect_spans,
    summarize_units_aspects,
)

__all__ = [
    "TextUnitInput",
    "analyze_disclosure_and_promo",
    "analyze_koc_vs_viewer_absa",
    "classify_observed_disclosure_flags",
    "extract_unit_aspect_spans",
    "score_text_aspects",
    "summarize_units_aspects",
]
