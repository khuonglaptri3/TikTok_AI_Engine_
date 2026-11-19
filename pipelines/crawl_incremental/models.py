from __future__ import annotations

from typing import Literal

from pydantic import BaseModel, ConfigDict, Field, field_validator

from packages.data_contracts._validators import require_non_blank, validate_timings_ms

SourceMode = Literal["offline_fixture", "live_provider"]
ItemStatus = Literal["succeeded", "failed", "skipped"]
AudioReceiptStatus = Literal[
    "converted_64k_mp3",
    "unavailable",
    "failed",
    "skipped_audio_ceiling",
]


class CollectorBounds(BaseModel):
    """Hard bounded ceilings for incremental discovery and multimodal collection."""

    model_config = ConfigDict(frozen=True, allow_inf_nan=False)

    window_days: int = Field(default=120, ge=1, le=365)
    max_creators: int = Field(default=5, ge=1, le=100)
    max_candidate_videos: int = Field(default=50, ge=1, le=1000)
    max_succeeded_videos: int = Field(default=30, ge=1, le=500)
    max_audio_minutes: float = Field(default=60.0, ge=0.0, le=600.0)
    max_comments_total: int = Field(default=1000, ge=0, le=50000)
    max_comments_per_video: int = Field(default=50, ge=0, le=1000)
    max_retries: int = Field(default=2, ge=0, le=10)
    session_deadline_seconds: float = Field(default=7200.0, gt=0.0, le=86400.0)


class AudioConversionReceipt(BaseModel):
    """Per-video 64 kbps .mp3 conversion provenance."""

    model_config = ConfigDict(frozen=True, allow_inf_nan=False)

    status: AudioReceiptStatus
    target_bitrate_kbps: int = 64
    audio_path: str | None = None
    audio_bytes: int = Field(default=0, ge=0)
    audio_sha256: str | None = None
    reason: str | None = None


class CollectorItemReceipt(BaseModel):
    """Per-candidate execution outcome recorded in crawl_manifest.json."""

    model_config = ConfigDict(frozen=True, allow_inf_nan=False)

    video_id: str
    author_handle: str = ""
    create_time: str | None = None
    status: ItemStatus
    attempts: int = Field(default=0, ge=0)
    reason: str = ""
    comment_count: int = Field(default=0, ge=0)
    audio_receipt: AudioConversionReceipt | None = None

    @field_validator("video_id")
    @classmethod
    def _validate_vid(cls, val: str) -> str:
        return require_non_blank(val)


class CollectorCheckpoint(BaseModel):
    """Resumable state stored atomically in collector_checkpoint.json."""

    model_config = ConfigDict(allow_inf_nan=False)

    source_mode: SourceMode
    as_of_utc: str
    cutoff_utc: str
    succeeded_ids: list[str] = Field(default_factory=list)
    skipped_reasons: dict[str, str] = Field(default_factory=dict)
    failed_reasons: dict[str, str] = Field(default_factory=dict)
    audio_receipts: dict[str, AudioConversionReceipt] = Field(default_factory=dict)


class CrawlManifest(BaseModel):
    """Idempotent manifest distinguishing requested, succeeded, failed, and skipped items."""

    model_config = ConfigDict(frozen=True, allow_inf_nan=False)

    source_mode: SourceMode
    is_synthetic_fixture: bool
    as_of_utc: str
    cutoff_utc: str
    base_corpus_snapshot_id: str
    historical_protected_count: int = Field(ge=0)
    creators_queried: list[str] = Field(default_factory=list)
    bounds: CollectorBounds
    requested_count: int = Field(ge=0)
    succeeded_count: int = Field(ge=0)
    failed_count: int = Field(ge=0)
    skipped_count: int = Field(ge=0)
    persisted_records_count: int = Field(default=0, ge=0)
    duplicate_candidates_ignored: int = Field(default=0, ge=0)
    converted_audio_count: int = Field(default=0, ge=0)
    collected_comments_count: int = Field(default=0, ge=0)
    accumulated_audio_minutes: float = Field(default=0.0, ge=0.0)
    stopped_reason: str | None = None
    output_jsonl: str
    items: list[CollectorItemReceipt] = Field(default_factory=list)
    timings_ms: dict[str, float] = Field(default_factory=dict)

    @field_validator("timings_ms")
    @classmethod
    def _validate_timings(cls, val: dict[str, float]) -> dict[str, float]:
        return validate_timings_ms(val)
