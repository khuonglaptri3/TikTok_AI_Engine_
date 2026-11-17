from __future__ import annotations

from typing import Literal

from pydantic import BaseModel, ConfigDict, Field, field_validator, model_validator

from packages.data_contracts._validators import require_non_blank, validate_timings_ms


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


class VoiceSegmentRecord(BaseModel):
    model_config = ConfigDict(frozen=True, allow_inf_nan=False)

    segment_id: str
    video_id: str
    seq_no: int = Field(ge=0)
    start_sec: float = Field(ge=0.0)
    end_sec: float = Field(ge=0.0)
    timestamp_source: Literal["whisper_exact", "wps_estimated"]
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
    like_count: int = Field(ge=0)
    reply_count: int = Field(ge=0)
    is_seeding: bool
    seeding_reason: str | None = None
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


class AbsaComparisonRecord(BaseModel):
    model_config = ConfigDict(frozen=True, allow_inf_nan=False)

    video_id: str
    koc_scores: AspectSentimentScores
    viewer_clean_scores: AspectSentimentScores
    pr_hype_gap: float = Field(ge=-2.0, le=2.0)
    undisclosed_pr_risk: float = Field(ge=0.0, le=1.0)
    viewer_pain_points: list[str]
    clean_comment_count: int = Field(ge=0)
    seeding_comment_count: int = Field(ge=0)

    @field_validator("video_id")
    @classmethod
    def _validate_video_id(cls, val: str) -> str:
        return require_non_blank(val)


class TrustAuditRequest(BaseModel):
    model_config = ConfigDict(extra="forbid", allow_inf_nan=False)

    video_id: str = "live_audit"
    caption: str = ""
    transcript: str = Field(min_length=5, max_length=10000)
    is_ad: bool = False
    is_ec_video: bool = False
    comments: list[RawCommentInput] = Field(default_factory=list)

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
    timings_ms: dict[str, float]

    @field_validator("timings_ms")
    @classmethod
    def _validate_timings(cls, val: dict[str, float]) -> dict[str, float]:
        return validate_timings_ms(val)
