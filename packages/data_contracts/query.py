from __future__ import annotations

from typing import Literal

from pydantic import BaseModel, ConfigDict, Field, field_validator

from packages.data_contracts._validators import normalize_optional_non_blank, require_non_blank


class NicheQueryFilter(BaseModel):
    model_config = ConfigDict(extra="forbid", allow_inf_nan=False)

    video_format: str | None = None
    food_category: str | None = None
    price_tier: str | None = None
    occasion: str | None = None
    duration_bucket: str | None = None
    city_norm: str | None = None
    region: str | None = None

    @field_validator(
        "video_format",
        "food_category",
        "price_tier",
        "occasion",
        "duration_bucket",
        "city_norm",
        "region",
    )
    @classmethod
    def _validate_optional_filter(cls, val: str | None) -> str | None:
        return normalize_optional_non_blank(val)


class RetrievalRequest(BaseModel):
    model_config = ConfigDict(extra="forbid", allow_inf_nan=False)

    query: str = Field(min_length=1, max_length=2000)
    mode: Literal["bm25", "dense", "hybrid_rrf"] = "bm25"
    top_k: int = Field(default=5, ge=1, le=20)
    rerank: bool = True
    filters: NicheQueryFilter = Field(default_factory=NicheQueryFilter)

    @field_validator("query")
    @classmethod
    def _validate_query(cls, val: str) -> str:
        return require_non_blank(val)


class ScriptGenerationRequest(BaseModel):
    model_config = ConfigDict(extra="forbid", allow_inf_nan=False)

    brief: str = Field(min_length=5, max_length=3000)
    target_duration_sec: int | None = Field(default=None, ge=10, le=300)
    top_k_evidence: int = Field(default=5, ge=2, le=10)
    generation_mode: Literal["gemini_free", "offline_grounded"] = "gemini_free"
    filters: NicheQueryFilter = Field(default_factory=NicheQueryFilter)

    @field_validator("brief")
    @classmethod
    def _validate_brief(cls, val: str) -> str:
        clean = require_non_blank(val)
        if len(clean) < 5:
            raise ValueError("brief must contain at least 5 non-whitespace characters")
        return clean
