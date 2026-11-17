from __future__ import annotations

from typing import Literal

from pydantic import BaseModel, ConfigDict, Field

from packages.data_contracts.analytics import NicheBenchmarkSummary
from packages.data_contracts.retrieval import EvidenceCard


class ScriptBeat(BaseModel):
    model_config = ConfigDict(frozen=True)

    section_title: str
    time_range: str
    visual_angle: str
    dialogue: str
    word_count: int = Field(ge=0)
    cited_video_ids: list[str]


class ShootingAdvice(BaseModel):
    model_config = ConfigDict(frozen=True)

    camera_angles: list[str]
    lighting_and_audio: list[str]
    pacing_and_editing: list[str]


class GuardrailReport(BaseModel):
    model_config = ConfigDict(frozen=True)

    passed: bool
    estimated_duration_sec: float = Field(ge=0.0)
    target_duration_sec: float = Field(ge=0.0)
    duration_delta_sec: float
    total_words: int = Field(ge=0)
    valid_citations_ratio: float = Field(ge=0.0, le=1.0)
    cliche_phrases_detected: list[str]
    warnings: list[str]
    citation_coverage_ratio: float = Field(default=0.0, ge=0.0, le=1.0)
    timing_valid: bool = False
    grounding_verified: Literal[False] = False
    validation_scope: Literal["structure_citations_timing"] = "structure_citations_timing"


class GroundedScriptResponse(BaseModel):
    model_config = ConfigDict(frozen=True)

    generation_mode: str
    model_used: str
    hook_options: list[str]
    caption_draft: str
    recommended_hashtags: list[str]
    setting: str
    persona_tone: str
    beats: list[ScriptBeat]
    shooting_advice: ShootingAdvice
    niche_benchmark: NicheBenchmarkSummary
    evidence_cards: list[EvidenceCard]
    guardrail: GuardrailReport
    timings_ms: dict[str, float]
    draft_status: Literal["creative_draft"] = "creative_draft"
    grounding_verified: Literal[False] = False
