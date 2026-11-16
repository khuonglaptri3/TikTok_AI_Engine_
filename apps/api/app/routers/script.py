from __future__ import annotations

from fastapi import APIRouter, Request

from apps.api.app.dependencies import ServiceContainer
from packages.data_contracts.query import ScriptGenerationRequest
from packages.data_contracts.script import GroundedScriptResponse

router = APIRouter(prefix="/api/v1/script", tags=["script engine"])


@router.post("/generate", response_model=GroundedScriptResponse)
async def generate_grounded_script(
    payload: ScriptGenerationRequest,
    request: Request,
) -> GroundedScriptResponse:
    container: ServiceContainer = request.app.state.container
    return container.script_engine.generate(payload)
