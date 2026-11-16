from __future__ import annotations

import uuid
from collections.abc import Awaitable, Callable

import gradio as gr
from fastapi import FastAPI, Request, Response
from fastapi.responses import JSONResponse, RedirectResponse

from apps.api.app.dependencies import ServiceContainer, build_container
from apps.api.app.routers import analytics, health, retrieval, script
from apps.demo.ui import build_gradio_blocks
from packages.common.exceptions import ViralRagError
from packages.common.settings import AppSettings
from packages.data_contracts.errors import CanonicalErrorResponse


def create_app(
    settings: AppSettings | None = None,
    container: ServiceContainer | None = None,
    mount_demo: bool = True,
) -> FastAPI:
    app = FastAPI(
        title="ViralFoodRAG — Evidence-Based TikTok Intelligence & Script Engine",
        version="1.0.0",
        description="Columnar Niche Micro-Benchmarks, Vietnamese Hybrid RAG, and Bounded Grounded Script Synthesis.",
    )
    app.state.container = container or build_container(settings)

    @app.middleware("http")
    async def attach_request_id(
        request: Request,
        call_next: Callable[[Request], Awaitable[Response]],
    ) -> Response:
        req_id = request.headers.get("X-Request-ID") or uuid.uuid4().hex[:12]
        request.state.request_id = req_id
        response = await call_next(request)
        response.headers["X-Request-ID"] = req_id
        return response

    @app.exception_handler(ViralRagError)
    async def handle_domain_error(request: Request, exc: ViralRagError) -> JSONResponse:
        req_id = getattr(request.state, "request_id", None)
        err = CanonicalErrorResponse(code=exc.code, message=exc.message, request_id=req_id)
        return JSONResponse(status_code=exc.status_code, content=err.model_dump())

    app.include_router(health.router)
    app.include_router(analytics.router)
    app.include_router(retrieval.router)
    app.include_router(script.router)

    @app.get("/", include_in_schema=False)
    async def root_redirect() -> RedirectResponse:
        return RedirectResponse(url="/demo/" if mount_demo else "/docs")

    if mount_demo:
        blocks = build_gradio_blocks(app)
        app = gr.mount_gradio_app(app, blocks, path="/demo")

    return app
