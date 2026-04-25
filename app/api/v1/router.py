from __future__ import annotations

from fastapi import APIRouter

from app.api.v1 import health, properties, webhook

api_router = APIRouter()
api_router.include_router(health.router, tags=["health"])
api_router.include_router(properties.router, prefix="/properties", tags=["properties"])
api_router.include_router(webhook.router, prefix="/webhook", tags=["webhook"])
