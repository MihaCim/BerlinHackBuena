from __future__ import annotations

from fastapi import APIRouter, HTTPException
from fastapi.responses import PlainTextResponse

from app.core.config import get_settings
from app.services.building_memory import BuildingMemoryService

router = APIRouter()


@router.get("/{building_id}", response_class=PlainTextResponse)
def get_building_md(building_id: str) -> PlainTextResponse:
    service = BuildingMemoryService(get_settings().output_dir)
    markdown = service.load(building_id)
    if markdown is None:
        raise HTTPException(status_code=404, detail=f"building {building_id!r} not found")
    return PlainTextResponse(markdown, media_type="text/markdown; charset=utf-8")
