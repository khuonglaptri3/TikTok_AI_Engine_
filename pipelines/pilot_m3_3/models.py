from __future__ import annotations

from datetime import datetime
from pathlib import Path
from typing import Literal

from pydantic import BaseModel, ConfigDict, Field

PilotMode = Literal["dry_run_fixture", "live_pilot"]
PilotStatus = Literal["PASS", "BLOCKED", "FIXTURE_DRY_RUN_ONLY"]


class M33PilotConfig(BaseModel):
    """Configuration and hard ceilings for the M3.3 vertical slice pilot."""

    model_config = ConfigDict(frozen=True)

    mode: PilotMode = "dry_run_fixture"
    allow_live_network: bool = False
    base_corpus_dir: Path = Path("data/corpus/20261118_taxonomy_fix_v1")
    batch_dir: Path = Path("data/raw_incremental/m3_3_pilot_batch")
    output_gold_dir: Path = Path("data/corpus/m3_3_pilot_snapshot_v1")
    output_bm25_dir: Path = Path("artifacts/indexes/bm25-m3_3-pilot")
    receipt_path: Path = Path("docs/reports/milestones/M3.3/evidence/m3_3_pilot_receipt.json")
    inspection_sheet_path: Path = Path(
        "docs/reports/milestones/M3.3/evidence/sample_inspection_sheet.jsonl"
    )
    fixture_path: Path | None = None
    creators: list[str] = Field(default_factory=list)
    as_of_utc: datetime | None = None

    window_days: int = Field(default=120, ge=1, le=365)
    max_creators: int = Field(default=5, ge=1, le=5)
    max_candidate_videos: int = Field(default=50, ge=1, le=50)
    max_succeeded_videos: int = Field(default=30, ge=1, le=30)
    max_audio_minutes: float = Field(default=60.0, ge=0.0, le=60.0)
    max_comments_total: int = Field(default=1000, ge=0, le=1000)
    session_deadline_seconds: float = Field(default=7200.0, gt=0.0, le=7200.0)

    asr_model_size: str = "small"
    max_asr_videos: int = Field(default=10, ge=1, le=10)
    max_asr_minutes: float = Field(default=20.0, gt=0.0, le=20.0)
    min_searchable_fresh_videos: int = Field(default=5, ge=1, le=30)


class CollectionSummaryReceipt(BaseModel):
    """Summary of M3.2 bounded collection outcomes for M3.3."""

    model_config = ConfigDict(frozen=True, allow_inf_nan=False)

    requested_count: int = 0
    succeeded_count: int = 0
    failed_count: int = 0
    skipped_count: int = 0
    historical_protected_count: int = 0
    converted_audio_count: int = 0
    collected_comments_count: int = 0
    capture_yield_rate: float = 0.0
    failure_rate: float = 0.0
    comment_coverage_rate: float = 0.0


class AsrPilotReceipt(BaseModel):
    """Measured CPU ASR slice timing, RTF, and coverage receipt."""

    model_config = ConfigDict(frozen=True, allow_inf_nan=False)

    engine_model_id: str
    max_videos_cap: int = 10
    max_audio_minutes_cap: float = 20.0
    transcribed_count: int = 0
    skipped_no_audio_count: int = 0
    skipped_asr_ceiling_count: int = 0
    failed_count: int = 0
    accumulated_audio_minutes: float = 0.0
    wall_seconds: float = 0.0
    real_time_factor: float = 0.0
    peak_rss_mib: float = 0.0


class SearchabilityReceipt(BaseModel):
    """Verified searchability of freshly transcribed M3.3 records."""

    model_config = ConfigDict(frozen=True, allow_inf_nan=False)

    indexed_total_documents: int = 0
    probed_fresh_transcribed_count: int = 0
    searchable_fresh_transcribed_count: int = 0
    matched_fresh_video_ids: list[str] = Field(default_factory=list)
    probe_queries: dict[str, str] = Field(default_factory=dict)


class ResourceReceipt(BaseModel):
    """Measured host disk, memory, and total wall-clock duration."""

    model_config = ConfigDict(frozen=True, allow_inf_nan=False)

    wall_seconds: float = 0.0
    peak_rss_mib: float = 0.0
    batch_disk_bytes: int = 0
    gold_snapshot_disk_bytes: int = 0
    bm25_index_disk_bytes: int = 0
    total_disk_bytes: int = 0


class M33PilotReceipt(BaseModel):
    """Top-level receipt for M3.3 pilot run."""

    model_config = ConfigDict(frozen=True, allow_inf_nan=False)

    task_id: str = "M3.3"
    mode: PilotMode
    pilot_status: PilotStatus
    is_synthetic_fixture: bool
    executed_at_utc: str
    blocker_reasons: list[str] = Field(default_factory=list)
    base_corpus_snapshot_id: str
    output_gold_snapshot_id: str | None = None
    collection: CollectionSummaryReceipt = Field(default_factory=CollectionSummaryReceipt)
    asr: AsrPilotReceipt | None = None
    searchability: SearchabilityReceipt = Field(default_factory=SearchabilityReceipt)
    resources: ResourceReceipt = Field(default_factory=ResourceReceipt)
    inspection_k_count: int = 0
    inspection_n_count: int = 0
