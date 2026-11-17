from __future__ import annotations

from pydantic import BaseModel, ConfigDict, Field


class CorpusFileChecksum(BaseModel):
    model_config = ConfigDict(frozen=True)

    filename: str
    rows: int = Field(ge=0)
    columns: int = Field(ge=1)
    sha256: str = Field(min_length=64, max_length=64)
    size_bytes: int = Field(ge=1)


class CorpusManifest(BaseModel):
    model_config = ConfigDict(frozen=True)

    snapshot_id: str
    parent_snapshot_id: str | None = None
    parent_manifest_sha256: str | None = Field(default=None, min_length=64, max_length=64)
    created_at: str
    date_window_start: str
    date_window_end: str
    total_creators: int = Field(ge=1)
    total_videos: int = Field(ge=1)
    transcribed_videos: int = Field(ge=0)
    poi_tagged_videos: int = Field(ge=0)
    ec_tagged_videos: int = Field(ge=0)
    files: list[CorpusFileChecksum]
    caveats: list[str]
