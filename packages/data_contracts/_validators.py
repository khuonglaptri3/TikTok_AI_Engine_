"""Shared Pydantic v2 boundary, finite-number, and ms-timing validators."""

from __future__ import annotations

import math
import re
from pathlib import Path

_HEX_SHA256_RE = re.compile(r"^[0-9a-fA-F]{64}$")


def require_non_blank(val: str) -> str:
    """Strip whitespace and reject blank strings."""
    clean = val.strip()
    if not clean:
        raise ValueError("Value must be non-blank")
    return clean


def normalize_optional_non_blank(val: str | None) -> str | None:
    """Strip optional string values and reject blank non-None strings."""
    if val is None:
        return None
    clean = val.strip()
    if not clean:
        raise ValueError("Optional string field cannot be empty or whitespace-only")
    return clean


def validate_timings_ms(timings: dict[str, float]) -> dict[str, float]:
    """Ensure all timing entries use *_ms keys and finite non-negative float values."""
    cleaned: dict[str, float] = {}
    for key, val in timings.items():
        clean_key = key.strip()
        if not clean_key or not clean_key.endswith("_ms"):
            raise ValueError(f"Timing key {key!r} must be non-empty and end with '_ms'")
        fval = float(val)
        if not math.isfinite(fval) or fval < 0.0:
            raise ValueError(f"Timing value for {clean_key!r} must be finite and >= 0.0")
        cleaned[clean_key] = fval
    return cleaned


def validate_hex_sha256(val: str) -> str:
    """Ensure SHA256 digest is an exact 64-character hexadecimal string."""
    clean = val.strip().lower()
    if not _HEX_SHA256_RE.match(clean):
        raise ValueError("SHA256 must be a 64-character hexadecimal string")
    return clean


def validate_local_filename(val: str) -> str:
    """Ensure manifest filenames stay strictly local without path traversal."""
    clean = val.strip()
    if not clean or Path(clean).name != clean or "/" in clean or "\\" in clean or ".." in clean:
        raise ValueError(f"Filename must be a local basename without path separators: {val!r}")
    return clean
