from __future__ import annotations

from typing import Annotated

from fastapi import APIRouter, Depends, HTTPException, Query

from app.core.config import Settings, get_settings
from app.services.normalization import NormalizationService

router = APIRouter()


def get_normalization_service(
    settings: Annotated[Settings, Depends(get_settings)],
) -> NormalizationService:
    return NormalizationService(data_dir=settings.data_dir, normalize_dir=settings.normalize_dir)


@router.post("/base")
async def normalize_base(
    service: Annotated[NormalizationService, Depends(get_normalization_service)],
    overwrite: Annotated[bool, Query()] = True,
) -> dict[str, object]:
    if not service.data_dir.exists():
        raise HTTPException(status_code=404, detail=f"Data directory not found: {service.data_dir}")
    return await service.normalize_base(overwrite=overwrite)


@router.post("/incremental/{day}")
async def normalize_incremental_day(
    day: str,
    service: Annotated[NormalizationService, Depends(get_normalization_service)],
    overwrite: Annotated[bool, Query()] = True,
) -> dict[str, object]:
    try:
        return await service.normalize_incremental_day(day=day, overwrite=overwrite)
    except FileNotFoundError as exc:
        raise HTTPException(status_code=404, detail=str(exc)) from exc


@router.post("/incremental")
async def normalize_all_incremental(
    service: Annotated[NormalizationService, Depends(get_normalization_service)],
    overwrite: Annotated[bool, Query()] = True,
) -> dict[str, object]:
    return await service.normalize_all_incremental(overwrite=overwrite)


@router.get("/status")
async def normalize_status(
    service: Annotated[NormalizationService, Depends(get_normalization_service)],
) -> dict[str, object]:
    return await service.status()
