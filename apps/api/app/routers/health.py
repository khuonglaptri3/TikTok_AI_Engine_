from __future__ import annotations

from typing import Any

from fastapi import APIRouter, Request

from apps.api.app.dependencies import ServiceContainer
from packages.taxonomy import DURATION_BUCKETS, FOOD_CATEGORIES, OCCASION_LABELS, PRICE_TIERS, VIDEO_FORMATS

router = APIRouter(tags=["health & metadata"])


def _container(request: Request) -> ServiceContainer:
    return request.app.state.container  # type: ignore[no-any-return]


@router.get("/health/live")
async def health_live() -> dict[str, str]:
    return {"status": "alive", "service": "tiktok-viral-rag-engine"}


@router.get("/health/ready")
async def health_ready(request: Request) -> dict[str, Any]:
    c = _container(request)
    qdrant_ready, qdrant_points = (
        c.retrieval.qdrant.check_collection_ready() if c.retrieval.qdrant else (False, 0)
    )
    return {
        "status": "ready",
        "corpus_snapshot_id": c.analytics.manifest.snapshot_id,
        "total_creators": c.analytics.manifest.total_creators,
        "total_videos": c.analytics.manifest.total_videos,
        "indexed_bm25_videos": len(c.retrieval.bm25.video_ids),
        "poi_tagged_videos": c.analytics.manifest.poi_tagged_videos,
        "qdrant_dense_ready": qdrant_ready,
        "qdrant_points": qdrant_points,
        "gemini_key_configured": c.gemini.is_configured,
    }


@router.get("/api/v1/demo/modules")
async def demo_modules(request: Request) -> dict[str, Any]:
    c = _container(request)
    return {
        "project": "ViralFoodRAG — Evidence-Based TikTok Content Intelligence & Script Engine",
        "corpus_snapshot_id": c.analytics.manifest.snapshot_id,
        "total_videos": c.analytics.manifest.total_videos,
        "transcribed_videos": c.analytics.manifest.transcribed_videos,
        "poi_tagged_videos": c.analytics.manifest.poi_tagged_videos,
        "gemini_key_configured": c.gemini.is_configured,
        "taxonomy": {
            "video_formats": list(VIDEO_FORMATS),
            "food_categories": list(FOOD_CATEGORIES),
            "price_tiers": list(PRICE_TIERS),
            "occasions": list(OCCASION_LABELS),
            "duration_buckets": list(DURATION_BUCKETS),
        },
        "caveats": c.analytics.manifest.caveats,
    }


@router.get("/api/v1/evaluation/summary")
async def evaluation_summary(request: Request) -> dict[str, Any]:
    c = _container(request)
    return c.load_benchmark_summary()
