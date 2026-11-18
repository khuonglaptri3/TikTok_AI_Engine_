"""Centralized typed environment settings loader (.env + os.environ)."""

from __future__ import annotations

import os
from functools import lru_cache
from pathlib import Path
from typing import Any

from pydantic import BaseModel, ConfigDict, Field, field_validator

from packages.common.logging import redact_secrets

MAX_LLM_CALLS_PER_TURN = 2


def _parse_dotenv(dotenv_path: Path) -> dict[str, str]:
    values: dict[str, str] = {}
    if not dotenv_path.is_file():
        return values
    for raw_line in dotenv_path.read_text(encoding="utf-8").splitlines():
        line = raw_line.strip()
        if not line or line.startswith("#") or "=" not in line:
            continue
        key, val = line.split("=", 1)
        clean_val = val.strip().strip('"').strip("'")
        values[key.strip()] = clean_val
    return values


class AppSettings(BaseModel):
    model_config = ConfigDict(frozen=True, extra="ignore", allow_inf_nan=False)

    env: str = Field(default="local")
    gemini_api_key: str = Field(default="", repr=False)
    gemini_fast_model: str = Field(default="gemini-2.5-flash")
    max_llm_calls_per_turn: int = Field(
        default=MAX_LLM_CALLS_PER_TURN, ge=1, le=MAX_LLM_CALLS_PER_TURN
    )
    llm_deadline_seconds: float = Field(default=30.0, gt=0.0, le=120.0)
    rate_limit_rpm: int = Field(default=15, ge=1, le=300)

    corpus_dir: Path = Field(default=Path("data/corpus/20261117_recovered_v1"))
    bm25_index_dir: Path = Field(default=Path("artifacts/indexes/bm25-v2"))
    dense_index_dir: Path | None = Field(default=None)
    benchmark_report_path: Path = Field(default=Path("artifacts/benchmarks/retrieval_v2.json"))

    qdrant_url: str = Field(default="http://127.0.0.1:6333")
    qdrant_collection: str = Field(default="tiktok_fnb_videos_v1")
    redis_url: str = Field(default="redis://127.0.0.1:6379/0")

    embedding_model: str = Field(default="intfloat/multilingual-e5-base")
    embedding_device: str = Field(default="cpu")
    reranker_model: str = Field(default="cross-encoder/mmarco-mMiniLMv2-L12-H384-v1")
    reranker_enabled: bool = Field(default=True)

    @field_validator(
        "env",
        "gemini_fast_model",
        "qdrant_url",
        "qdrant_collection",
        "redis_url",
        "embedding_model",
        "embedding_device",
        "reranker_model",
    )
    @classmethod
    def _reject_blank_setting(cls, val: str) -> str:
        clean = val.strip()
        if not clean:
            raise ValueError("Setting string must be non-empty")
        return clean

    def safe_summary(self) -> dict[str, Any]:
        """Return a log-safe dictionary with API keys and URL passwords redacted."""
        return {
            "env": self.env,
            "gemini_api_key": "***" if self.gemini_api_key.strip() else "",
            "gemini_fast_model": self.gemini_fast_model,
            "max_llm_calls_per_turn": self.max_llm_calls_per_turn,
            "llm_deadline_seconds": self.llm_deadline_seconds,
            "rate_limit_rpm": self.rate_limit_rpm,
            "corpus_dir": str(self.corpus_dir),
            "bm25_index_dir": str(self.bm25_index_dir),
            "dense_index_dir": str(self.dense_index_dir) if self.dense_index_dir else None,
            "benchmark_report_path": str(self.benchmark_report_path),
            "qdrant_url": redact_secrets(self.qdrant_url),
            "qdrant_collection": self.qdrant_collection,
            "redis_url": redact_secrets(self.redis_url),
            "embedding_model": self.embedding_model,
            "embedding_device": self.embedding_device,
            "reranker_model": self.reranker_model,
            "reranker_enabled": self.reranker_enabled,
        }

    def __repr__(self) -> str:
        parts = ", ".join(f"{k}={v!r}" for k, v in self.safe_summary().items())
        return f"AppSettings({parts})"

    def __str__(self) -> str:
        return self.__repr__()

    @classmethod
    def from_env(cls, dotenv_path: Path | None = None) -> AppSettings:
        root = Path(__file__).resolve().parents[3]
        file_vals = _parse_dotenv(dotenv_path or (root / ".env"))

        def _get(name: str, default: str) -> str:
            if name in os.environ:
                return os.environ[name]
            return file_vals.get(name, default)

        raw_dense = _get("TIKTOK_RAG_DENSE_INDEX_DIR", "").strip()
        return cls(
            env=_get("TIKTOK_RAG_ENV", "local"),
            gemini_api_key=_get("GEMINI_API_KEY", ""),
            gemini_fast_model=_get("TIKTOK_RAG_GEMINI_FAST_MODEL", "gemini-2.5-flash"),
            max_llm_calls_per_turn=int(_get("TIKTOK_RAG_MAX_LLM_CALLS_PER_TURN", "2")),
            llm_deadline_seconds=float(_get("TIKTOK_RAG_LLM_DEADLINE_SECONDS", "30.0")),
            rate_limit_rpm=int(_get("TIKTOK_RAG_RATE_LIMIT_RPM", "15")),
            corpus_dir=Path(_get("TIKTOK_RAG_CORPUS_DIR", "data/corpus/20261117_recovered_v1")),
            bm25_index_dir=Path(_get("TIKTOK_RAG_BM25_INDEX_DIR", "artifacts/indexes/bm25-v2")),
            dense_index_dir=Path(raw_dense) if raw_dense else None,
            benchmark_report_path=Path(
                _get("TIKTOK_RAG_BENCHMARK_REPORT_PATH", "artifacts/benchmarks/retrieval_v2.json")
            ),
            qdrant_url=_get("TIKTOK_RAG_QDRANT_URL", "http://127.0.0.1:6333"),
            qdrant_collection=_get("TIKTOK_RAG_QDRANT_COLLECTION", "tiktok_fnb_videos_v1"),
            redis_url=_get("TIKTOK_RAG_REDIS_URL", "redis://127.0.0.1:6379/0"),
            embedding_model=_get("TIKTOK_RAG_EMBEDDING_MODEL", "intfloat/multilingual-e5-base"),
            embedding_device=_get("TIKTOK_RAG_EMBEDDING_DEVICE", "cpu"),
            reranker_model=_get(
                "TIKTOK_RAG_RERANKER_MODEL", "cross-encoder/mmarco-mMiniLMv2-L12-H384-v1"
            ),
            reranker_enabled=_get("TIKTOK_RAG_RERANKER_ENABLED", "true").lower() in ("1", "true", "yes"),
        )


@lru_cache(maxsize=1)
def get_settings() -> AppSettings:
    return AppSettings.from_env()
