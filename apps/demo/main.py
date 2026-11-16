from __future__ import annotations

from fastapi import FastAPI

from apps.api.app.main import create_app as create_api_app


def create_app() -> FastAPI:
    return create_api_app(mount_demo=True)
