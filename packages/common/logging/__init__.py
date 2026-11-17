"""Per-stage latency timing and secret-safe structured logging helpers."""

from __future__ import annotations

import logging
import math
import re
import time
from collections.abc import Iterator
from contextlib import contextmanager
from typing import Any

_GOOGLE_KEY_RE = re.compile(r"AIza[0-9A-Za-z_-]{12,}")
_BEARER_RE = re.compile(r"(Bearer\s+)[A-Za-z0-9._-]+", flags=re.IGNORECASE)
_KV_SECRET_RE = re.compile(
    r"(?i)\b(GEMINI_API_KEY|api_key|apikey|access_token|token|secret|password|key)\s*([=:])\s*([^\s&\"'`,;]+)"
)
_URL_CRED_RE = re.compile(r"([a-zA-Z][a-zA-Z0-9+.-]*://[^:/@\s]*:)([^@\s]+)(@)")


def redact_secrets(text: str) -> str:
    """Mask API keys, bearer tokens, secret key-value pairs, and URL credentials."""
    if not text:
        return text
    out = _GOOGLE_KEY_RE.sub("[REDACTED]", text)
    out = _BEARER_RE.sub(r"\1[REDACTED]", out)
    out = _URL_CRED_RE.sub(r"\1[REDACTED]\3", out)
    out = _KV_SECRET_RE.sub(r"\1\2[REDACTED]", out)
    return out


def _redact_arg(value: Any) -> Any:
    if isinstance(value, str):
        return redact_secrets(value)
    if isinstance(value, tuple):
        return tuple(_redact_arg(v) for v in value)
    if isinstance(value, list):
        return [_redact_arg(v) for v in value]
    if isinstance(value, dict):
        return {k: _redact_arg(v) for k, v in value.items()}
    return value


class SecretRedactingFilter(logging.Filter):
    """Logging filter that strips credential patterns from formatted log messages."""

    def filter(self, record: logging.LogRecord) -> bool:
        try:
            formatted = record.getMessage()
        except Exception:
            formatted = redact_secrets(str(record.msg))
            if record.args:
                record.args = _redact_arg(record.args)
                record.msg = formatted
        else:
            record.msg = redact_secrets(formatted)
            record.args = None
        if record.exc_text:
            record.exc_text = redact_secrets(record.exc_text)
        return True


def get_safe_logger(name: str) -> logging.Logger:
    """Return a logger with SecretRedactingFilter attached idempotently."""
    logger = logging.getLogger(name)
    if not any(isinstance(flt, SecretRedactingFilter) for flt in logger.filters):
        logger.addFilter(SecretRedactingFilter())
    return logger


class StageTimer:
    """Records measured stage latencies in finite non-negative milliseconds."""

    def __init__(self) -> None:
        self._start_total = time.perf_counter()
        self.stages_ms: dict[str, float] = {}

    @contextmanager
    def measure(self, stage_name: str) -> Iterator[None]:
        clean_name = stage_name.strip()
        if not clean_name:
            raise ValueError("StageTimer stage_name must be non-empty")
        t0 = time.perf_counter()
        try:
            yield
        finally:
            raw_ms = (time.perf_counter() - t0) * 1000.0
            elapsed_ms = max(0.0, round(raw_ms, 2)) if math.isfinite(raw_ms) else 0.0
            self.stages_ms[clean_name] = elapsed_ms

    def finalize(self) -> dict[str, float]:
        out = dict(self.stages_ms)
        raw_total = (time.perf_counter() - self._start_total) * 1000.0
        out["total_ms"] = max(0.0, round(raw_total, 2)) if math.isfinite(raw_total) else 0.0
        return out


__all__ = [
    "SecretRedactingFilter",
    "StageTimer",
    "get_safe_logger",
    "redact_secrets",
]
