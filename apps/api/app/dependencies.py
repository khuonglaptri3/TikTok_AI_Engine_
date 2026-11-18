from __future__ import annotations

import json
from dataclasses import dataclass
from pathlib import Path
from typing import Any

from packages.analytics import NicheAnalyticsEngine
from packages.common.settings import AppSettings, get_settings
from packages.llm import BoundedGeminiClient
from packages.retrieval import HybridRetrievalService
from packages.script_engine import GroundedScriptEngine

REPO_ROOT = Path(__file__).resolve().parents[3]


def _resolve_path(path: Path) -> Path:
    return path if path.is_absolute() else (REPO_ROOT / path)


@dataclass
class ServiceContainer:
    settings: AppSettings
    analytics: NicheAnalyticsEngine
    retrieval: HybridRetrievalService
    gemini: BoundedGeminiClient
    script_engine: GroundedScriptEngine
    benchmark_report_path: Path

    def load_benchmark_summary(self) -> dict[str, Any]:
        if not self.benchmark_report_path.is_file():
            return {"status": "missing", "path": str(self.benchmark_report_path)}
        loaded = json.loads(self.benchmark_report_path.read_text(encoding="utf-8"))
        return dict(loaded) if isinstance(loaded, dict) else {"raw": loaded}


def build_container(settings: AppSettings | None = None) -> ServiceContainer:
    cfg = settings or get_settings()
    corpus_dir = _resolve_path(cfg.corpus_dir)
    bm25_dir = _resolve_path(cfg.bm25_index_dir)
    dense_dir = _resolve_path(cfg.dense_index_dir) if cfg.dense_index_dir is not None else None
    bench_path = _resolve_path(cfg.benchmark_report_path)

    analytics = NicheAnalyticsEngine.from_corpus_dir(corpus_dir)
    retrieval = HybridRetrievalService.from_dirs(
        df_videos=analytics.df_videos,
        bm25_dir=bm25_dir,
        qdrant_url=cfg.qdrant_url,
        qdrant_collection=cfg.qdrant_collection,
        reranker_enabled=cfg.reranker_enabled,
        dense_dir=dense_dir,
    )
    gemini = BoundedGeminiClient(settings=cfg)
    script_engine = GroundedScriptEngine(
        analytics_engine=analytics,
        retrieval_service=retrieval,
        gemini_client=gemini,
    )
    return ServiceContainer(
        settings=cfg,
        analytics=analytics,
        retrieval=retrieval,
        gemini=gemini,
        script_engine=script_engine,
        benchmark_report_path=bench_path,
    )
