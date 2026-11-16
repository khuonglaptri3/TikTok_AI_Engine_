from __future__ import annotations

from fastapi import APIRouter, Request

from apps.api.app.dependencies import ServiceContainer
from packages.data_contracts.query import RetrievalRequest
from packages.data_contracts.retrieval import RetrievalResponse

router = APIRouter(prefix="/api/v1/retrieval", tags=["hybrid retrieval"])


@router.post("/search", response_model=RetrievalResponse)
async def search_evidence(
    payload: RetrievalRequest,
    request: Request,
) -> RetrievalResponse:
    container: ServiceContainer = request.app.state.container
    return container.retrieval.search(payload)
