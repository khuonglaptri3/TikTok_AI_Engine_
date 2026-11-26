from __future__ import annotations

import os
from pathlib import Path

from fastapi import FastAPI

from apps.api.app.main import create_app as create_api_app
from packages.common.settings import AppSettings

REPO_ROOT = Path(__file__).resolve().parents[2]
_FRESH_CORPUS_REL = Path("data/corpus/m3_3_pilot_snapshot_v2")
_FRESH_BM25_REL = Path("artifacts/indexes/bm25-m3_3-pilot")


def create_app() -> FastAPI:
    """Create the mounted /demo/ FastAPI app, preferring the M3.3 fresh+historical corpus when unconfigured."""
    settings = AppSettings.from_env()
    if (
        "TIKTOK_RAG_CORPUS_DIR" not in os.environ
        and "TIKTOK_RAG_BM25_INDEX_DIR" not in os.environ
        and settings.corpus_dir == Path("data/corpus/20261117_recovered_v1")
        and (REPO_ROOT / _FRESH_CORPUS_REL / "manifest.json").is_file()
        and (REPO_ROOT / _FRESH_BM25_REL).is_dir()
    ):
        settings = settings.model_copy(
            update={
                "corpus_dir": _FRESH_CORPUS_REL,
                "bm25_index_dir": _FRESH_BM25_REL,
            }
        )
    return create_api_app(settings=settings, mount_demo=True)
