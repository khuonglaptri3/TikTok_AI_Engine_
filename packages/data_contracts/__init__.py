"""Canonical Pydantic v2 schemas shared across pipelines, packages, and FastAPI."""

from packages.data_contracts.analytics import NicheBenchmarkSummary, PostingHourStat
from packages.data_contracts.corpus import CorpusFileChecksum, CorpusManifest
from packages.data_contracts.errors import CanonicalErrorResponse
from packages.data_contracts.query import NicheQueryFilter, RetrievalRequest, ScriptGenerationRequest
from packages.data_contracts.retrieval import EvidenceCard, RetrievalResponse, VideoCitation
from packages.data_contracts.script import (
    GroundedScriptResponse,
    GuardrailReport,
    ScriptBeat,
    ShootingAdvice,
)

__all__ = [
    "CanonicalErrorResponse",
    "CorpusFileChecksum",
    "CorpusManifest",
    "EvidenceCard",
    "GroundedScriptResponse",
    "GuardrailReport",
    "NicheBenchmarkSummary",
    "NicheQueryFilter",
    "PostingHourStat",
    "RetrievalRequest",
    "RetrievalResponse",
    "ScriptBeat",
    "ScriptGenerationRequest",
    "ShootingAdvice",
    "VideoCitation",
]
