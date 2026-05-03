from __future__ import annotations

from fastapi import APIRouter

from app.core.config import get_settings
from app.schemas.health import HealthResponse

router = APIRouter()


@router.get("/health")
def health() -> HealthResponse:
    settings = get_settings()
    return HealthResponse(status="ok", env=settings.env, version=settings.version)
