from __future__ import annotations

from pydantic import BaseModel, ConfigDict, Field


class PostingHourStat(BaseModel):
    model_config = ConfigDict(frozen=True)

    hour: int = Field(ge=0, le=23)
    video_count: int = Field(ge=0)
    median_plays: float = Field(ge=0.0)
    median_engagement_rate: float = Field(ge=0.0)


class NicheBenchmarkSummary(BaseModel):
    model_config = ConfigDict(frozen=True)

    matched_videos: int = Field(ge=0)
    transcribed_videos: int = Field(ge=0)
    poi_tagged_videos: int = Field(ge=0)
    median_plays: float = Field(ge=0.0)
    p75_plays: float = Field(ge=0.0)
    median_engagement_rate: float = Field(ge=0.0)
    duration_q25_sec: float = Field(ge=0.0)
    duration_median_sec: float = Field(ge=0.0)
    duration_q75_sec: float = Field(ge=0.0)
    median_word_per_second: float = Field(ge=0.0)
    hashtag_q25: int = Field(ge=0)
    hashtag_q75: int = Field(ge=0)
    top_hashtags: list[str]
    top_posting_hours: list[PostingHourStat]
    top_poi_venues: list[str]
    applied_filters: dict[str, str]
    timings_ms: dict[str, float]
