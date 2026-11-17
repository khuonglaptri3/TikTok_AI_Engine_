from __future__ import annotations

from pydantic import BaseModel, ConfigDict, Field, field_validator, model_validator

from packages.data_contracts._validators import (
    require_non_blank,
    validate_hex_sha256,
    validate_local_filename,
)


class CorpusFileChecksum(BaseModel):
    model_config = ConfigDict(frozen=True, allow_inf_nan=False)

    filename: str
    rows: int = Field(ge=0)
    columns: int = Field(ge=1)
    sha256: str = Field(min_length=64, max_length=64)
    size_bytes: int = Field(ge=1)

    @field_validator("filename")
    @classmethod
    def _validate_filename(cls, val: str) -> str:
        return validate_local_filename(val)

    @field_validator("sha256")
    @classmethod
    def _validate_sha256(cls, val: str) -> str:
        return validate_hex_sha256(val)


class CorpusManifest(BaseModel):
    model_config = ConfigDict(frozen=True, allow_inf_nan=False)

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

    @field_validator("snapshot_id")
    @classmethod
    def _validate_snapshot_id(cls, val: str) -> str:
        return require_non_blank(val)

    @field_validator("parent_manifest_sha256")
    @classmethod
    def _validate_parent_sha(cls, val: str | None) -> str | None:
        return validate_hex_sha256(val) if val is not None else None

    @model_validator(mode="after")
    def _validate_counts(self) -> CorpusManifest:
        if (
            self.transcribed_videos > self.total_videos
            or self.poi_tagged_videos > self.total_videos
            or self.ec_tagged_videos > self.total_videos
        ):
            raise ValueError("Manifest video subset counts cannot exceed total_videos")
        return self
