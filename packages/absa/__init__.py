"""Vietnamese F&B 4-Aspect Sentiment (ABSA) & Undisclosed PR Hype Gap Analyzer."""

from packages.absa.analyzer import analyze_koc_vs_viewer_absa, score_text_aspects
from packages.absa.disclosure import (
    analyze_disclosure_and_promo,
    classify_observed_disclosure_flags,
)

__all__ = [
    "analyze_disclosure_and_promo",
    "analyze_koc_vs_viewer_absa",
    "classify_observed_disclosure_flags",
    "score_text_aspects",
]
