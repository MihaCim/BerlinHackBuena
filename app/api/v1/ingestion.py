from __future__ import annotations

from typing import Annotated

from fastapi import APIRouter, Depends, HTTPException, Query

from app.core.config import Settings, get_settings
from app.ingestion import IngestionService

router = APIRouter()


def get_ingestion_service(
    settings: Annotated[Settings, Depends(get_settings)],
) -> IngestionService:
    return IngestionService(data_dir=settings.data_dir, db_path=settings.ingestion_db_path)


@router.post("/base")
async def ingest_base(
    service: Annotated[IngestionService, Depends(get_ingestion_service)],
    reprocess: Annotated[bool, Query()] = False,
) -> dict[str, object]:
    if not service.data_dir.exists():
        raise HTTPException(status_code=404, detail=f"Data directory not found: {service.data_dir}")
    return await service.ingest_base(reprocess=reprocess)


@router.post("/incremental/{day}")
async def ingest_incremental_day(
    day: str,
    service: Annotated[IngestionService, Depends(get_ingestion_service)],
    reprocess: Annotated[bool, Query()] = False,
) -> dict[str, object]:
    try:
        return await service.ingest_incremental_day(day=day, reprocess=reprocess)
    except FileNotFoundError as exc:
        raise HTTPException(status_code=404, detail=str(exc)) from exc


@router.post("/incremental")
async def ingest_all_incremental(
    service: Annotated[IngestionService, Depends(get_ingestion_service)],
    reprocess: Annotated[bool, Query()] = False,
) -> dict[str, object]:
    return await service.ingest_all_incremental(reprocess=reprocess)


@router.get("/status")
async def ingest_status(
    service: Annotated[IngestionService, Depends(get_ingestion_service)],
) -> dict[str, object]:
    return await service.status()
