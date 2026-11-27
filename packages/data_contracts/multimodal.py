from __future__ import annotations

from datetime import datetime
from typing import Any, Literal

from pydantic import BaseModel, ConfigDict, Field, field_validator, model_validator

from packages.data_contracts._validators import (
    normalize_optional_non_blank,
    require_non_blank,
    validate_timings_ms,
)

AspectName = Literal["taste", "price", "hygiene", "service"]
ASPECT_NAMES: tuple[AspectName, ...] = ("taste", "price", "hygiene", "service")
AspectPresenceStatus = Literal["observed", "absent_unknown"]
ObservedAspectPolarity = Literal["positive", "neutral", "negative"]
AspectPolaritySummaryLabel = Literal["positive", "neutral", "negative", "unknown"]
TextUnitSourceKind = Literal[
    "creator_caption",
    "creator_transcript",
    "creator_utterance",
    "viewer_comment",
]
AspectComparisonStatus = Literal[
    "compared_supported_overlap",
    "abstained_creator_absent",
    "abstained_viewer_absent",
    "abstained_viewer_low_support",
]
DEFAULT_DISCREPANCY_INTERPRETATION_NOTE = (
    "Observed creator-speech vs viewer-comment sentiment discrepancy on supported overlapping "
    "aspects (>=3 viewer comments); not proof of deception, hygiene truth, or verified diner consensus."
)


class RawWhisperSegment(BaseModel):
    model_config = ConfigDict(frozen=True, allow_inf_nan=False)

    start_sec: float = Field(ge=0.0)
    end_sec: float = Field(ge=0.0)
    text: str

    @model_validator(mode="after")
    def _validate_interval(self) -> RawWhisperSegment:
        if self.end_sec < self.start_sec:
            raise ValueError("RawWhisperSegment end_sec must be >= start_sec")
        return self


class RawCommentInput(BaseModel):
    model_config = ConfigDict(frozen=True, allow_inf_nan=False)

    comment_id: str
    author_handle: str = ""
    text: str
    like_count: int = Field(default=0, ge=0)
    reply_count: int = Field(default=0, ge=0)

    @field_validator("comment_id")
    @classmethod
    def _validate_comment_id(cls, val: str) -> str:
        return require_non_blank(val)


class RawIncrementalVideoRecord(BaseModel):
    """Canonical schema for freshly crawled 4-month videos before Dual-Sink conversion."""

    model_config = ConfigDict(extra="ignore", allow_inf_nan=False)

    video_id: str
    author_id: str
    author_handle: str
    author_nickname: str = ""
    follower_count: int = Field(default=0, ge=0)
    create_time: str
    caption: str = ""
    hashtags: list[str] = Field(default_factory=list)
    duration_sec: int = Field(default=0, ge=0)
    play_count: int = Field(default=0, ge=0)
    digg_count: int = Field(default=0, ge=0)
    comment_count: int = Field(default=0, ge=0)
    share_count: int = Field(default=0, ge=0)
    collect_count: int = Field(default=0, ge=0)
    is_ad: bool = False
    is_ec_video: bool = False
    playlist_id: str | None = None
    poi_id: str | None = None
    poi_name: str | None = None
    poi_address: str | None = None
    poi_city: str | None = None
    poi_category_tiny: str | None = None
    audio_path: str | None = None
    pitch_std: float | None = None
    energy_cv: float | None = None
    transcript: str = ""
    whisper_segments: list[RawWhisperSegment] = Field(default_factory=list)
    comments: list[RawCommentInput] = Field(default_factory=list)

    @field_validator("video_id", "author_id", "author_handle", "create_time")
    @classmethod
    def _validate_ids(cls, val: str) -> str:
        return require_non_blank(val)

    @field_validator("create_time")
    @classmethod
    def _validate_create_time(cls, val: str) -> str:
        clean = require_non_blank(val)
        try:
            datetime.fromisoformat(clean.replace("Z", "+00:00"))
        except ValueError as exc:
            raise ValueError(f"Invalid ISO-8601 create_time: {val!r}") from exc
        return clean


class VoiceSegmentRecord(BaseModel):
    model_config = ConfigDict(frozen=True, allow_inf_nan=False)

    segment_id: str
    video_id: str
    seq_no: int = Field(ge=0)
    start_sec: float = Field(ge=0.0)
    end_sec: float = Field(ge=0.0)
    timestamp_source: Literal["audio_derived", "whisper_exact", "wps_estimated"]
    text: str
    words_per_sec: float = Field(ge=0.0)
    pitch_std: float | None = None
    energy_cv: float | None = None

    @field_validator("segment_id", "video_id")
    @classmethod
    def _validate_ids(cls, val: str) -> str:
        return require_non_blank(val)

    @model_validator(mode="after")
    def _validate_interval(self) -> VoiceSegmentRecord:
        if self.end_sec < self.start_sec:
            raise ValueError("VoiceSegmentRecord end_sec must be >= start_sec")
        return self


class CommentRecord(BaseModel):
    model_config = ConfigDict(frozen=True, allow_inf_nan=False)

    comment_id: str
    video_id: str
    author_handle: str
    text: str
    original_text: str = ""
    like_count: int = Field(ge=0)
    reply_count: int = Field(ge=0)
    is_seeding: bool
    seeding_reason: str | None = None
    observable_label: Literal[
        "observable_duplicate",
        "contact_or_link",
        "noise_or_empty",
        "template_phrase_match",
        "no_indicator_observed",
        "unknown_ambiguous",
    ] = "no_indicator_observed"
    observable_reason_codes: list[str] = Field(default_factory=list)
    diagnostic_only: bool = True
    similarity_score: float = Field(default=0.0, ge=0.0, le=1.0)
    cluster_id: int | None = None

    @field_validator("comment_id", "video_id")
    @classmethod
    def _validate_ids(cls, val: str) -> str:
        return require_non_blank(val)


class AspectSentimentScores(BaseModel):
    model_config = ConfigDict(frozen=True, allow_inf_nan=False)

    taste: float = Field(ge=-1.0, le=1.0)
    price: float = Field(ge=-1.0, le=1.0)
    hygiene: float = Field(ge=-1.0, le=1.0)
    service: float = Field(ge=-1.0, le=1.0)


class AspectSpanEvidence(BaseModel):
    model_config = ConfigDict(frozen=True, allow_inf_nan=False)

    unit_id: str
    source_kind: TextUnitSourceKind
    aspect: AspectName
    polarity_label: ObservedAspectPolarity
    polarity_score: float = Field(ge=-1.0, le=1.0)
    start_char: int = Field(ge=0)
    end_char: int = Field(gt=0)
    span_text: str

    @field_validator("unit_id")
    @classmethod
    def _validate_unit_id(cls, val: str) -> str:
        return require_non_blank(val)

    @field_validator("span_text")
    @classmethod
    def _validate_span_text(cls, val: str) -> str:
        if not val.strip():
            raise ValueError("AspectSpanEvidence span_text must contain non-whitespace characters")
        return val

    @model_validator(mode="after")
    def _validate_span_offsets(self) -> AspectSpanEvidence:
        if self.end_char <= self.start_char:
            raise ValueError("AspectSpanEvidence end_char must be > start_char")
        if len(self.span_text) != self.end_char - self.start_char:
            raise ValueError(
                "AspectSpanEvidence span_text length must equal end_char - start_char"
            )
        return self


class AspectAggregateSummary(BaseModel):
    model_config = ConfigDict(frozen=True, allow_inf_nan=False)

    aspect: AspectName
    presence_status: AspectPresenceStatus
    polarity_label: AspectPolaritySummaryLabel
    mean_score: float | None = Field(default=None, ge=-1.0, le=1.0)
    mention_unit_count: int = Field(ge=0)
    span_count: int = Field(ge=0)
    sufficient_support: bool

    @model_validator(mode="after")
    def _validate_presence_invariants(self) -> AspectAggregateSummary:
        if self.presence_status == "absent_unknown":
            if self.polarity_label != "unknown":
                raise ValueError(
                    "absent_unknown summary requires polarity_label == 'unknown'"
                )
            if self.mean_score is not None:
                raise ValueError("absent_unknown summary requires mean_score is None")
            if self.mention_unit_count != 0:
                raise ValueError("absent_unknown summary requires mention_unit_count == 0")
            if self.span_count != 0:
                raise ValueError("absent_unknown summary requires span_count == 0")
            if self.sufficient_support is not False:
                raise ValueError("absent_unknown summary requires sufficient_support is False")
        else:
            if self.polarity_label not in {"positive", "neutral", "negative"}:
                raise ValueError(
                    "observed summary requires polarity_label in {'positive', 'neutral', 'negative'}"
                )
            if self.mean_score is None or not (-1.0 <= self.mean_score <= 1.0):
                raise ValueError("observed summary requires finite mean_score in [-1.0, 1.0]")
            if self.mention_unit_count < 1:
                raise ValueError("observed summary requires mention_unit_count >= 1")
            if self.span_count < self.mention_unit_count:
                raise ValueError("observed summary requires span_count >= mention_unit_count")
        return self


class AspectDiscrepancyDetail(BaseModel):
    model_config = ConfigDict(frozen=True, allow_inf_nan=False)

    aspect: AspectName
    comparison_status: AspectComparisonStatus
    creator_mean_score: float | None = Field(default=None, ge=-1.0, le=1.0)
    viewer_mean_score: float | None = Field(default=None, ge=-1.0, le=1.0)
    viewer_support_count: int = Field(ge=0)
    min_viewer_support_required: int = Field(default=3, ge=1)
    sentiment_discrepancy: float | None = Field(default=None, ge=-2.0, le=2.0)

    @model_validator(mode="after")
    def _validate_discrepancy_invariants(self) -> AspectDiscrepancyDetail:
        if self.comparison_status == "compared_supported_overlap":
            if self.creator_mean_score is None:
                raise ValueError(
                    "compared_supported_overlap requires creator_mean_score is not None"
                )
            if self.viewer_mean_score is None:
                raise ValueError(
                    "compared_supported_overlap requires viewer_mean_score is not None"
                )
            if self.viewer_support_count < self.min_viewer_support_required:
                raise ValueError(
                    "compared_supported_overlap requires viewer_support_count >= min_viewer_support_required"
                )
            if self.sentiment_discrepancy is None or not (
                -2.0 <= self.sentiment_discrepancy <= 2.0
            ):
                raise ValueError(
                    "compared_supported_overlap requires finite sentiment_discrepancy in [-2.0, 2.0]"
                )
        else:
            if self.sentiment_discrepancy is not None:
                raise ValueError(
                    f"{self.comparison_status} requires sentiment_discrepancy is None"
                )
        return self


class AbsaComparisonRecord(BaseModel):
    model_config = ConfigDict(frozen=True, allow_inf_nan=False)

    video_id: str
    koc_scores: AspectSentimentScores
    viewer_clean_scores: AspectSentimentScores
    pr_hype_gap: float = Field(ge=-2.0, le=2.0)
    undisclosed_pr_risk: float = Field(ge=0.0, le=1.0)
    disclosure_flag_status: Literal[
        "observed_ad",
        "observed_ecommerce",
        "observed_ad_and_ecommerce",
        "unlabeled_unknown",
    ] = "unlabeled_unknown"
    promotional_language_indicators: list[str] = Field(default_factory=list)
    lexical_promo_score: float = Field(default=0.0, ge=0.0, le=1.0)
    sponsorship_ground_truth_status: Literal["undisclosed_sponsorship_deferred"] = (
        "undisclosed_sponsorship_deferred"
    )
    disclosure_target_note: str = (
        "Platform flags (is_ad / is_ec_video) indicate observed platform metadata only; "
        "unlabeled items remain unlabeled_unknown (not verified negative), "
        "and undisclosed sponsorship prediction remains deferred."
    )
    viewer_pain_points: list[str]
    clean_comment_count: int = Field(ge=0)
    seeding_comment_count: int = Field(ge=0)
    koc_aspect_summaries: dict[AspectName, AspectAggregateSummary] = Field(default_factory=dict)
    viewer_aspect_summaries: dict[AspectName, AspectAggregateSummary] = Field(default_factory=dict)
    aspect_discrepancies: dict[AspectName, AspectDiscrepancyDetail] = Field(default_factory=dict)
    supported_overlapping_aspects: list[AspectName] = Field(default_factory=list)
    supported_sentiment_discrepancy: float | None = Field(default=None, ge=-2.0, le=2.0)
    discrepancy_abstention_reason: str | None = None
    discrepancy_interpretation_note: str = DEFAULT_DISCREPANCY_INTERPRETATION_NOTE
    source_spans: list[AspectSpanEvidence] = Field(default_factory=list)

    @field_validator("video_id", "discrepancy_interpretation_note")
    @classmethod
    def _validate_video_id(cls, val: str) -> str:
        return require_non_blank(val)

    @field_validator("discrepancy_abstention_reason")
    @classmethod
    def _validate_abstention_reason(cls, val: str | None) -> str | None:
        return normalize_optional_non_blank(val)

    @model_validator(mode="after")
    def _validate_aspect_map_keys(self) -> AbsaComparisonRecord:
        for aspect, summary in self.koc_aspect_summaries.items():
            if summary.aspect != aspect:
                raise ValueError(
                    f"koc_aspect_summaries key {aspect!r} does not match summary.aspect {summary.aspect!r}"
                )
        for aspect, summary in self.viewer_aspect_summaries.items():
            if summary.aspect != aspect:
                raise ValueError(
                    f"viewer_aspect_summaries key {aspect!r} does not match summary.aspect {summary.aspect!r}"
                )
        for aspect, detail in self.aspect_discrepancies.items():
            if detail.aspect != aspect:
                raise ValueError(
                    f"aspect_discrepancies key {aspect!r} does not match detail.aspect {detail.aspect!r}"
                )
        return self


class TrustAuditRequest(BaseModel):
    model_config = ConfigDict(extra="forbid", allow_inf_nan=False)

    video_id: str = "live_audit"
    caption: str = ""
    transcript: str = Field(min_length=5, max_length=10000)
    utterances: list[RawWhisperSegment] = Field(default_factory=list)
    hashtags: list[str] = Field(default_factory=list)
    is_ad: bool = False
    is_ec_video: bool = False
    comments: list[RawCommentInput] = Field(default_factory=list)
    absa_engine: Literal["lexicon_v1", "phobert_ner_t4_finetuned", "phobert_hybrid"] = "lexicon_v1"

    @field_validator("video_id")
    @classmethod
    def _validate_video_id(cls, val: str) -> str:
        return require_non_blank(val)

    @field_validator("transcript")
    @classmethod
    def _validate_transcript(cls, val: str) -> str:
        clean = require_non_blank(val)
        if len(clean) < 5:
            raise ValueError("transcript must contain at least 5 non-whitespace characters")
        return clean


class TrustAuditResponse(BaseModel):
    model_config = ConfigDict(frozen=True, allow_inf_nan=False)

    comparison: AbsaComparisonRecord
    comments: list[CommentRecord]
    absa_model_used: str = "lexicon_v1"
    comment_filter_policy: Literal[
        "diagnostic_only_unvalidated",
        "validated_filter_applied",
    ] = "diagnostic_only_unvalidated"
    comment_filter_note: str = (
        "M5.1 auto-filtering requires >=150 human-annotated pilot comments "
        "(macro precision >=0.85, recall >=0.60); showing observable diagnostic indicators without filtering."
    )
    filter_sensitivity: dict[str, Any] = Field(default_factory=dict)
    timings_ms: dict[str, float]

    @field_validator("timings_ms")
    @classmethod
    def _validate_timings(cls, val: dict[str, float]) -> dict[str, float]:
        return validate_timings_ms(val)
