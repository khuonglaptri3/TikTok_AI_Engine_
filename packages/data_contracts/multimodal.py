from __future__ import annotations

from typing import Literal

from pydantic import BaseModel, ConfigDict, Field


class RawWhisperSegment(BaseModel):
    model_config = ConfigDict(frozen=True)

    start_sec: float = Field(ge=0.0)
    end_sec: float = Field(ge=0.0)
    text: str


class RawCommentInput(BaseModel):
    model_config = ConfigDict(frozen=True)

    comment_id: str
    author_handle: str = ""
    text: str
    like_count: int = Field(default=0, ge=0)
    reply_count: int = Field(default=0, ge=0)


class RawIncrementalVideoRecord(BaseModel):
    """Canonical schema for freshly crawled 4-month videos before Dual-Sink conversion."""

    model_config = ConfigDict(extra="ignore")

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


class VoiceSegmentRecord(BaseModel):
    model_config = ConfigDict(frozen=True)

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


class CommentRecord(BaseModel):
    model_config = ConfigDict(frozen=True)

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


class AspectSentimentScores(BaseModel):
    model_config = ConfigDict(frozen=True)

    taste: float = Field(ge=-1.0, le=1.0)
    price: float = Field(ge=-1.0, le=1.0)
    hygiene: float = Field(ge=-1.0, le=1.0)
    service: float = Field(ge=-1.0, le=1.0)


class AbsaComparisonRecord(BaseModel):
    model_config = ConfigDict(frozen=True)

    video_id: str
    koc_scores: AspectSentimentScores
    viewer_clean_scores: AspectSentimentScores
    pr_hype_gap: float = Field(ge=-2.0, le=2.0)
    undisclosed_pr_risk: float = Field(ge=0.0, le=1.0)
    viewer_pain_points: list[str]
    clean_comment_count: int = Field(ge=0)
    seeding_comment_count: int = Field(ge=0)


class TrustAuditRequest(BaseModel):
    model_config = ConfigDict(extra="forbid")

    video_id: str = "live_audit"
    caption: str = ""
    transcript: str = Field(min_length=5, max_length=10000)
    is_ad: bool = False
    is_ec_video: bool = False
    comments: list[RawCommentInput] = Field(default_factory=list)


class TrustAuditResponse(BaseModel):
    model_config = ConfigDict(frozen=True)

    comparison: AbsaComparisonRecord
    comments: list[CommentRecord]
    timings_ms: dict[str, float]
