from __future__ import annotations

from fastapi import APIRouter

from app.api.v1 import buildings, context_agent, health, ingestion, normalization

api_router = APIRouter()
api_router.include_router(health.router, tags=["health"])
api_router.include_router(buildings.router, prefix="/buildings", tags=["buildings"])
api_router.include_router(ingestion.router, prefix="/ingest", tags=["ingestion"])
api_router.include_router(normalization.router, prefix="/normalize", tags=["normalization"])
api_router.include_router(context_agent.router, prefix="/context-agent", tags=["context-agent"])
