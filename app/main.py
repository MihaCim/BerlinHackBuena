from __future__ import annotations

from pathlib import Path

from fastapi import FastAPI

from app.api.v1.router import api_router
from app.core.config import get_settings
from app.core.logging import configure_logging
from context_engine.cli import load_local_env


def create_app() -> FastAPI:
    configure_logging()
    load_local_env(Path.cwd() / ".env")
    settings = get_settings()
    app = FastAPI(title=settings.app_name, version=settings.version)
    app.include_router(api_router, prefix="/api/v1")
    return app


app = create_app()
