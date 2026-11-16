from __future__ import annotations

from fastapi import APIRouter, Request

from apps.api.app.dependencies import ServiceContainer
from packages.data_contracts.analytics import NicheBenchmarkSummary
from packages.data_contracts.query import NicheQueryFilter

router = APIRouter(prefix="/api/v1/analytics", tags=["niche analytics"])


@router.post("/niche-benchmark", response_model=NicheBenchmarkSummary)
async def compute_niche_benchmark(
    payload: NicheQueryFilter,
    request: Request,
) -> NicheBenchmarkSummary:
    container: ServiceContainer = request.app.state.container
    return container.analytics.compute_benchmark(payload)
