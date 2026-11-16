from __future__ import annotations

from typing import Literal

from pydantic import BaseModel, ConfigDict, Field


class NicheQueryFilter(BaseModel):
    model_config = ConfigDict(extra="forbid")

    video_format: str | None = None
    food_category: str | None = None
    price_tier: str | None = None
    occasion: str | None = None
    duration_bucket: str | None = None
    city_norm: str | None = None
    region: str | None = None


class RetrievalRequest(BaseModel):
    model_config = ConfigDict(extra="forbid")

    query: str = Field(min_length=1, max_length=2000)
    mode: Literal["bm25", "dense", "hybrid_rrf"] = "bm25"
    top_k: int = Field(default=5, ge=1, le=20)
    rerank: bool = True
    filters: NicheQueryFilter = Field(default_factory=NicheQueryFilter)


class ScriptGenerationRequest(BaseModel):
    model_config = ConfigDict(extra="forbid")

    brief: str = Field(min_length=5, max_length=3000)
    target_duration_sec: int | None = Field(default=None, ge=10, le=300)
    top_k_evidence: int = Field(default=5, ge=2, le=10)
    generation_mode: Literal["gemini_free", "offline_grounded"] = "gemini_free"
    filters: NicheQueryFilter = Field(default_factory=NicheQueryFilter)
