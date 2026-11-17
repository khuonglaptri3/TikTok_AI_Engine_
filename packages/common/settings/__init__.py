"""Centralized typed environment settings loader (.env + os.environ)."""

from __future__ import annotations

import os
from functools import lru_cache
from pathlib import Path

from pydantic import BaseModel, ConfigDict, Field


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
    model_config = ConfigDict(frozen=True, extra="ignore")

    env: str = Field(default="local")
    gemini_api_key: str = Field(default="")
    gemini_fast_model: str = Field(default="gemini-2.5-flash")
    max_llm_calls_per_turn: int = Field(default=2, ge=1, le=5)
    llm_deadline_seconds: float = Field(default=30.0, gt=0.0, le=120.0)
    rate_limit_rpm: int = Field(default=15, ge=1, le=300)

    corpus_dir: Path = Field(default=Path("data/corpus/20261117_recovered_v1"))
    bm25_index_dir: Path = Field(default=Path("artifacts/indexes/bm25-v2"))
    benchmark_report_path: Path = Field(default=Path("artifacts/benchmarks/retrieval_v2.json"))

    qdrant_url: str = Field(default="http://127.0.0.1:6333")
    qdrant_collection: str = Field(default="tiktok_fnb_videos_v1")
    redis_url: str = Field(default="redis://127.0.0.1:6379/0")

    embedding_model: str = Field(default="intfloat/multilingual-e5-base")
    embedding_device: str = Field(default="cpu")
    reranker_model: str = Field(default="cross-encoder/mmarco-mMiniLMv2-L12-H384-v1")
    reranker_enabled: bool = Field(default=True)

    @classmethod
    def from_env(cls, dotenv_path: Path | None = None) -> AppSettings:
        root = Path(__file__).resolve().parents[3]
        file_vals = _parse_dotenv(dotenv_path or (root / ".env"))

        def _get(name: str, default: str) -> str:
            if name in os.environ:
                return os.environ[name]
            return file_vals.get(name, default)

        return cls(
            env=_get("TIKTOK_RAG_ENV", "local"),
            gemini_api_key=_get("GEMINI_API_KEY", ""),
            gemini_fast_model=_get("TIKTOK_RAG_GEMINI_FAST_MODEL", "gemini-2.5-flash"),
            max_llm_calls_per_turn=int(_get("TIKTOK_RAG_MAX_LLM_CALLS_PER_TURN", "2")),
            llm_deadline_seconds=float(_get("TIKTOK_RAG_LLM_DEADLINE_SECONDS", "30.0")),
            rate_limit_rpm=int(_get("TIKTOK_RAG_RATE_LIMIT_RPM", "15")),
            corpus_dir=Path(_get("TIKTOK_RAG_CORPUS_DIR", "data/corpus/20261117_recovered_v1")),
            bm25_index_dir=Path(_get("TIKTOK_RAG_BM25_INDEX_DIR", "artifacts/indexes/bm25-v2")),
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
