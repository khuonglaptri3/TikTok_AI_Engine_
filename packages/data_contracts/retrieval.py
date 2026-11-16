from __future__ import annotations

from pydantic import BaseModel, ConfigDict, Field


class VideoCitation(BaseModel):
    model_config = ConfigDict(frozen=True)

    video_id: str
    author_handle: str
    tiktok_url: str
    play_count: int = Field(ge=0)
    viral_multiplier: float = Field(ge=0.0)
    engagement_rate: float = Field(ge=0.0)


class EvidenceCard(BaseModel):
    model_config = ConfigDict(frozen=True)

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
    model_config = ConfigDict(frozen=True)

    query: str
    mode: str
    reranked: bool
    total_candidates: int = Field(ge=0)
    relaxed_filters: list[str]
    items: list[EvidenceCard]
    timings_ms: dict[str, float]
