from __future__ import annotations

from pydantic import BaseModel, ConfigDict, Field, field_validator

from packages.data_contracts._validators import require_non_blank, validate_timings_ms


class VideoCitation(BaseModel):
    model_config = ConfigDict(frozen=True, allow_inf_nan=False)

    video_id: str
    author_handle: str
    tiktok_url: str
    play_count: int = Field(ge=0)
    viral_multiplier: float = Field(ge=0.0)
    engagement_rate: float = Field(ge=0.0)

    @field_validator("video_id")
    @classmethod
    def _validate_video_id(cls, val: str) -> str:
        return require_non_blank(val)


class EvidenceCard(BaseModel):
    model_config = ConfigDict(frozen=True, allow_inf_nan=False)

    rank: int = Field(ge=1)
    score: float
    lexical_score: float = 0.0
    rerank_score: float | None = None
    citation: VideoCitation
    video_format: str
    food_category: str
    dishes: list[str]
    city_norm: str | None = None
    district_norm: str | None = None
    poi_name: str | None = None
    price_tier: str
    occasions: list[str]
    duration_sec: int = Field(ge=0)
    duration_bucket: str
    hook_text: str
    body_beats: list[str]
    cta_text: str
    transcript_excerpt: str


class RetrievalResponse(BaseModel):
    model_config = ConfigDict(frozen=True, allow_inf_nan=False)

    query: str
    mode: str
    reranked: bool
    total_candidates: int = Field(ge=0)
    relaxed_filters: list[str]
    items: list[EvidenceCard]
    timings_ms: dict[str, float]

    @field_validator("timings_ms")
    @classmethod
    def _validate_timings(cls, val: dict[str, float]) -> dict[str, float]:
        return validate_timings_ms(val)
