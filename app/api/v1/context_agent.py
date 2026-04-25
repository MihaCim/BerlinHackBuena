from __future__ import annotations

from typing import Annotated

from fastapi import APIRouter, Depends, HTTPException

from app.core.config import Settings, get_settings
from app.services.context_agent import ContextAgentService

router = APIRouter()


def get_context_agent_service(
    settings: Annotated[Settings, Depends(get_settings)],
) -> ContextAgentService:
    return ContextAgentService(
        workspace_root=settings.repo_root,
        model=settings.context_agent_model,
        tub_api_key=settings.tub_api_key.get_secret_value() if settings.tub_api_key else None,
        tub_api_base=settings.tub_api_base,
        tub_chat_endpoint=settings.tub_chat_endpoint,
        tub_custom_instructions=settings.tub_custom_instructions,
        tub_hide_custom_instructions=settings.tub_hide_custom_instructions,
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
