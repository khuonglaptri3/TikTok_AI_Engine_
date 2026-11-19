"""Observable Duplicate, Contact/Link, and Noise Comment Indicators (M5.1)."""

from packages.seeding.detector import detect_comment_indicators, detect_seeding_comments
from packages.seeding.evaluation import (
    compute_comment_filter_sensitivity,
    compute_inter_annotator_agreement,
    evaluate_comment_indicator_metrics,
    split_comments_by_video,
)

__all__ = [
    "compute_comment_filter_sensitivity",
    "compute_inter_annotator_agreement",
    "detect_comment_indicators",
    "detect_seeding_comments",
    "evaluate_comment_indicator_metrics",
    "split_comments_by_video",
]
