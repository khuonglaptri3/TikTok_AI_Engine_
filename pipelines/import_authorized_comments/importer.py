from __future__ import annotations

import csv
import hashlib
import json
import os
from collections import defaultdict
from datetime import UTC, datetime, timedelta
from pathlib import Path
from typing import Any, Literal

import pandas as pd
from pydantic import BaseModel, ConfigDict, ValidationError

from packages.analytics import load_verified_corpus
from packages.data_contracts.multimodal import RawCommentInput, RawIncrementalVideoRecord
from pipelines.ingest_incremental_to_gold import ingest_incremental_batch_to_gold


class AuthorizedCommentReceipt(BaseModel):
    model_config = ConfigDict(frozen=True)

    status: Literal["READY", "IMPORTED"]
    source_label: str
    source_sha256: str
    base_snapshot_id: str
    output_snapshot_id: str | None = None
    as_of_utc: str
    input_rows: int
    matched_videos: int


def _sha256_file(path: Path) -> str:
    digest = hashlib.sha256()
    with path.open("rb") as fp:
        for chunk in iter(lambda: fp.read(1024 * 1024), b""):
            digest.update(chunk)
    return digest.hexdigest()


def _read_rows(path: Path, *, max_rows: int = 1000) -> list[dict[str, Any]]:
    if not 1 <= max_rows <= 5000:
        raise ValueError("max_rows must be from 1 to 5000")
    if not path.is_file():
        raise ValueError("Comments input file is missing")
    rows: list[dict[str, Any]] = []
    try:
        if path.suffix.lower() == ".csv":
            with path.open("r", encoding="utf-8-sig", newline="") as fp:
                reader = csv.DictReader(fp)
                if reader.fieldnames is None or not {"video_id", "comment_id", "text"}.issubset(reader.fieldnames):
                    raise ValueError("CSV requires video_id, comment_id, and text columns")
                if len(reader.fieldnames) != len(set(reader.fieldnames)):
                    raise ValueError("CSV has duplicate column names")
                for row in reader:
                    if None in row:
                        raise ValueError("CSV row has surplus cells; quote commas inside text")
                    rows.append(dict(row))
                    if len(rows) > max_rows:
                        raise ValueError(f"Comments input exceeds the {max_rows}-row ceiling")
        elif path.suffix.lower() == ".jsonl":
            with path.open("r", encoding="utf-8-sig") as fp:
                for line in fp:
                    if not line.strip():
                        continue
                    try:
                        row = json.loads(line)
                    except json.JSONDecodeError:
                        raise ValueError("Comments JSONL has an invalid row") from None
                    if not isinstance(row, dict):
                        raise ValueError("Comments JSONL rows must be objects")
                    rows.append(row)
                    if len(rows) > max_rows:
                        raise ValueError(f"Comments input exceeds the {max_rows}-row ceiling")
        else:
            raise ValueError("Comments input must be UTF-8 CSV or JSONL")
    except (UnicodeError, csv.Error):
        raise ValueError("Comments input is not valid UTF-8 CSV or JSONL") from None
    if not rows:
        raise ValueError("Comments input contains no rows")
    return rows


def _nonnegative_count(value: Any, field: str, row_number: int) -> int:
    if value is None or value == "":
        return 0
    clean = str(value).strip()
    if not clean.isascii() or not clean.isdecimal():
        raise ValueError(f"Row {row_number}: {field} must be a nonnegative integer")
    return int(clean)


def _atomic_write(path: Path, content: str) -> None:
    temporary = path.with_name(path.name + ".tmp")
    temporary.write_text(content, encoding="utf-8", newline="\n")
    os.replace(temporary, path)


def import_authorized_comments(
    comments_file: Path,
    base_corpus_dir: Path,
    work_dir: Path,
    output_corpus_dir: Path,
    *,
    source_label: str,
    as_of_utc: datetime,
    preflight_only: bool = False,
    max_rows: int = 1000,
) -> AuthorizedCommentReceipt:
    """Validate a supplied comment export and enrich existing fresh Gold videos."""
    if not source_label.strip():
        raise ValueError("A nonblank source_label is required for provenance")
    if work_dir.exists() or output_corpus_dir.exists():
        raise ValueError("Work and output Gold paths must be new and nonexisting")
    if as_of_utc.tzinfo is None:
        as_of_utc = as_of_utc.replace(tzinfo=UTC)
    as_of_utc = as_of_utc.astimezone(UTC)

    rows = _read_rows(comments_file, max_rows=max_rows)
    source_sha256 = _sha256_file(comments_file)
    base_manifest, _, videos = load_verified_corpus(base_corpus_dir)
    by_video = {str(row["video_id"]): row for row in videos.to_dict(orient="records")}
    cutoff = as_of_utc - timedelta(days=120)
    grouped: dict[str, list[RawCommentInput]] = defaultdict(list)
    prior_comment_ids: dict[str, set[str]] = defaultdict(set)
    if "fact_comments.parquet" in {entry.filename for entry in base_manifest.files}:
        prior_comments = pd.read_parquet(
            base_corpus_dir / "fact_comments.parquet", columns=["video_id", "comment_id"],
        )
        for old_video_id, old_comment_id in prior_comments.itertuples(index=False, name=None):
            prior_comment_ids[str(old_video_id)].add(str(old_comment_id))
    seen_comment_ids: set[str] = set()
    for row_number, row in enumerate(rows, start=1):
        video_id = str(row.get("video_id") or "").strip()
        comment_id = str(row.get("comment_id") or "").strip()
        text = row.get("text")
        if not video_id or not comment_id or not isinstance(text, str) or not text.strip():
            raise ValueError(f"Row {row_number}: video_id, comment_id, and nonblank text are required")
        if comment_id in seen_comment_ids:
            raise ValueError(f"Row {row_number}: duplicate comment_id")
        seen_comment_ids.add(comment_id)
        video = by_video.get(video_id)
        if video is None:
            raise ValueError(f"Row {row_number}: video_id is absent from the verified Gold snapshot")
        created = datetime.fromisoformat(str(video["create_time"]).replace("Z", "+00:00"))
        if created.tzinfo is None:
            created = created.replace(tzinfo=UTC)
        if not cutoff <= created.astimezone(UTC) <= as_of_utc:
            raise ValueError(f"Row {row_number}: video is outside the 120-day rolling window")
        comment_data: dict[str, Any] = {"comment_id": comment_id, "text": text}
        if row.get("author_handle") is not None and str(row["author_handle"]).strip():
            comment_data["author_handle"] = str(row["author_handle"])
        for field in ("like_count", "reply_count"):
            if row.get(field) not in (None, ""):
                comment_data[field] = _nonnegative_count(row[field], field, row_number)
        try:
            comment = RawCommentInput.model_validate(comment_data)
        except ValidationError:
            raise ValueError(f"Row {row_number}: invalid comment fields") from None
        grouped[video_id].append(comment)
        if len(grouped[video_id]) > 50:
            raise ValueError(f"Row {row_number}: video exceeds the 50-comment ceiling")
        if len(prior_comment_ids[video_id] | {item.comment_id for item in grouped[video_id]}) > 50:
            raise ValueError(f"Row {row_number}: merged video exceeds the 50-comment ceiling")

    receipt = AuthorizedCommentReceipt(
        status="READY" if preflight_only else "IMPORTED",
        source_label=source_label.strip(),
        source_sha256=source_sha256,
        base_snapshot_id=base_manifest.snapshot_id,
        output_snapshot_id=None if preflight_only else output_corpus_dir.name,
        as_of_utc=as_of_utc.isoformat(),
        input_rows=len(rows),
        matched_videos=len(grouped),
    )
    if preflight_only:
        return receipt

    work_dir.mkdir(parents=True, exist_ok=False)
    batch_lines = []
    for video_id, comments in grouped.items():
        row = by_video[video_id]
        record = RawIncrementalVideoRecord(
            video_id=video_id,
            author_id=str(row["author_id"]),
            author_handle=str(row["author_handle"]),
            create_time=str(row["create_time"]),
            comments=comments,
        )
        batch_lines.append(record.model_dump_json(exclude_unset=True))
    batch_path = work_dir / "authorized_comments.jsonl"
    _atomic_write(batch_path, "\n".join(batch_lines) + "\n")
    ingest_incremental_batch_to_gold(
        base_corpus_dir, batch_path, output_corpus_dir, update_existing=True,
    )
    _atomic_write(work_dir / "import_receipt.json", json.dumps(receipt.model_dump(), indent=2) + "\n")
    return receipt
