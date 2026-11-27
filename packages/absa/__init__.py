"""Vietnamese F&B 4-Aspect Sentiment (ABSA) & Undisclosed PR Hype Gap Analyzer."""

from packages.absa.analyzer import analyze_koc_vs_viewer_absa, score_text_aspects
from packages.absa.disclosure import (
    analyze_disclosure_and_promo,
    classify_observed_disclosure_flags,
)
from packages.absa.evaluation import (
    VALID_ASPECT_STATES,
    audit_source_span_validity,
    build_m5_2_annotation_pool,
    compute_m5_2_annotator_agreement,
    evaluate_m5_2_aspect_sentiment,
    predict_unit_aspects,
    split_units_by_video,
    validate_and_summarize_m5_2_pool,
)
from packages.absa.neural_absa import (
    AbsaEngineMode,
    LoadedPhoBertAbsaModel,
    PhoBertNerT4MultiTaskABSA,
    get_phobert_absa_model,
    is_phobert_absa_available,
)
from packages.absa.spans import (
    TextUnitInput,
    extract_unit_aspect_spans,
    summarize_units_aspects,
)

__all__ = [
    "AbsaEngineMode",
    "LoadedPhoBertAbsaModel",
    "PhoBertNerT4MultiTaskABSA",
    "TextUnitInput",
    "VALID_ASPECT_STATES",
    "analyze_disclosure_and_promo",
    "analyze_koc_vs_viewer_absa",
    "audit_source_span_validity",
    "build_m5_2_annotation_pool",
    "classify_observed_disclosure_flags",
    "compute_m5_2_annotator_agreement",
    "evaluate_m5_2_aspect_sentiment",
    "extract_unit_aspect_spans",
    "get_phobert_absa_model",
    "is_phobert_absa_available",
    "predict_unit_aspects",
    "score_text_aspects",
    "split_units_by_video",
    "summarize_units_aspects",
    "validate_and_summarize_m5_2_pool",
]
