"""Canonical Pydantic v2 schemas shared across pipelines, packages, and FastAPI."""

from packages.data_contracts.analytics import NicheBenchmarkSummary, PostingHourStat
from packages.data_contracts.corpus import CorpusFileChecksum, CorpusManifest
from packages.data_contracts.errors import CanonicalErrorResponse
from packages.data_contracts.multimodal import (
    ASPECT_NAMES,
    DEFAULT_DISCREPANCY_INTERPRETATION_NOTE,
    AbsaComparisonRecord,
    AspectAggregateSummary,
    AspectComparisonStatus,
    AspectDiscrepancyDetail,
    AspectName,
    AspectPolaritySummaryLabel,
    AspectPresenceStatus,
    AspectSentimentScores,
    AspectSpanEvidence,
    CommentRecord,
    ObservedAspectPolarity,
    RawCommentInput,
    RawIncrementalVideoRecord,
    RawWhisperSegment,
    TextUnitSourceKind,
    TrustAuditRequest,
    TrustAuditResponse,
    VoiceSegmentRecord,
)
from packages.data_contracts.query import (
    NicheQueryFilter,
    RetrievalRequest,
    ScriptGenerationRequest,
)
from packages.data_contracts.retrieval import EvidenceCard, RetrievalResponse, VideoCitation
from packages.data_contracts.script import (
    GroundedScriptResponse,
    GuardrailReport,
    ScriptBeat,
    ShootingAdvice,
)

__all__ = [
    "ASPECT_NAMES",
    "DEFAULT_DISCREPANCY_INTERPRETATION_NOTE",
    "AbsaComparisonRecord",
    "AspectAggregateSummary",
    "AspectComparisonStatus",
    "AspectDiscrepancyDetail",
    "AspectName",
    "AspectPolaritySummaryLabel",
    "AspectPresenceStatus",
    "AspectSentimentScores",
    "AspectSpanEvidence",
    "CanonicalErrorResponse",
    "CommentRecord",
    "CorpusFileChecksum",
    "CorpusManifest",
    "EvidenceCard",
    "GroundedScriptResponse",
    "GuardrailReport",
    "NicheBenchmarkSummary",
    "NicheQueryFilter",
    "ObservedAspectPolarity",
    "PostingHourStat",
    "RawCommentInput",
    "RawIncrementalVideoRecord",
    "RawWhisperSegment",
    "RetrievalRequest",
    "RetrievalResponse",
    "ScriptBeat",
    "ScriptGenerationRequest",
    "ShootingAdvice",
    "TextUnitSourceKind",
    "TrustAuditRequest",
    "TrustAuditResponse",
    "VideoCitation",
    "VoiceSegmentRecord",
]
