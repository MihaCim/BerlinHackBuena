from __future__ import annotations

from fastapi import APIRouter

from app.api.v1 import agents, buildings, health

api_router = APIRouter()
api_router.include_router(health.router, tags=["health"])
api_router.include_router(buildings.router, prefix="/buildings", tags=["buildings"])
api_router.include_router(agents.router, prefix="/agents", tags=["agents"])
