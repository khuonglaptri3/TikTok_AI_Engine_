from __future__ import annotations

from pydantic import BaseModel, ConfigDict, Field, field_validator, model_validator

from packages.data_contracts._validators import validate_timings_ms


class PostingHourStat(BaseModel):
    model_config = ConfigDict(frozen=True, allow_inf_nan=False)

    hour: int = Field(ge=0, le=23)
    video_count: int = Field(ge=0)
    median_plays: float = Field(ge=0.0)
    median_engagement_rate: float = Field(ge=0.0)


class NicheBenchmarkSummary(BaseModel):
    model_config = ConfigDict(frozen=True, allow_inf_nan=False)

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

    @field_validator("timings_ms")
    @classmethod
    def _validate_timings(cls, val: dict[str, float]) -> dict[str, float]:
        return validate_timings_ms(val)

    @model_validator(mode="after")
    def _validate_quantiles_and_counts(self) -> NicheBenchmarkSummary:
        if not (self.duration_q25_sec <= self.duration_median_sec <= self.duration_q75_sec):
            raise ValueError("Duration quantiles must satisfy q25 <= median <= q75")
        if self.hashtag_q25 > self.hashtag_q75:
            raise ValueError("Hashtag quantiles must satisfy hashtag_q25 <= hashtag_q75")
        if self.transcribed_videos > self.matched_videos or self.poi_tagged_videos > self.matched_videos:
            raise ValueError("Subset counts cannot exceed matched_videos")
        return self
