from __future__ import annotations

from typing import Annotated

from fastapi import APIRouter, Depends, HTTPException, Query

from app.core.config import Settings, get_settings
from app.services.context_agent import ContextAgentService

router = APIRouter()


def get_context_agent_service(
    settings: Annotated[Settings, Depends(get_settings)],
) -> ContextAgentService:
    return ContextAgentService(
        workspace_root=settings.repo_root,
        model=settings.context_agent_model,
        sub_model=settings.context_agent_sub_model,
        openrouter_api_key=settings.openrouter_api_key.get_secret_value()
        if settings.openrouter_api_key
        else None,
        openrouter_api_base=settings.openrouter_api_base,
    )


@router.get("/status")
async def context_agent_status(
    service: Annotated[ContextAgentService, Depends(get_context_agent_service)],
) -> dict[str, object]:
    return await service.status()


@router.post("/base")
async def build_base_context(
    service: Annotated[ContextAgentService, Depends(get_context_agent_service)],
) -> dict[str, object]:
    try:
        return await service.build_base_context()
    except ValueError as exc:
        raise HTTPException(status_code=400, detail=str(exc)) from exc
    except Exception as exc:
        raise HTTPException(status_code=503, detail=f"Context agent failed: {exc}") from exc


@router.post("/base/enrich")
async def enrich_base_context(
    service: Annotated[ContextAgentService, Depends(get_context_agent_service)],
    max_batches: Annotated[int | None, Query(ge=1)] = None,
) -> dict[str, object]:
    try:
        return await service.enrich_base_context(max_batches=max_batches)
    except ValueError as exc:
        raise HTTPException(status_code=400, detail=str(exc)) from exc
    except Exception as exc:
        raise HTTPException(status_code=503, detail=f"Context agent failed: {exc}") from exc


@router.post("/base/enrich/{batch_id}")
async def enrich_base_batch(
    batch_id: str,
    service: Annotated[ContextAgentService, Depends(get_context_agent_service)],
) -> dict[str, object]:
    try:
        return await service.enrich_base_batch(batch_id=batch_id)
    except ValueError as exc:
        raise HTTPException(status_code=404, detail=str(exc)) from exc
    except Exception as exc:
        raise HTTPException(status_code=503, detail=f"Context agent failed: {exc}") from exc
