from __future__ import annotations

from typing import Annotated

from fastapi import APIRouter, Depends, HTTPException, Query

from app.core.config import Settings, get_settings
from app.services.context_writer import ContextWriterService

router = APIRouter()


def get_context_writer_service(
    settings: Annotated[Settings, Depends(get_settings)],
) -> ContextWriterService:
    return ContextWriterService(
        data_dir=settings.data_dir,
        normalize_dir=settings.normalize_dir,
        output_dir=settings.output_dir,
    )


@router.post("/build/base")
async def build_base_context(
    service: Annotated[ContextWriterService, Depends(get_context_writer_service)],
    overwrite: Annotated[bool, Query()] = True,
) -> dict[str, object]:
    try:
        return await service.build_base_context(overwrite=overwrite)
    except FileNotFoundError as exc:
        raise HTTPException(status_code=404, detail=str(exc)) from exc
    except ValueError as exc:
        raise HTTPException(status_code=400, detail=str(exc)) from exc


@router.get("/status")
async def context_status(
    service: Annotated[ContextWriterService, Depends(get_context_writer_service)],
) -> dict[str, object]:
    return await service.status()
