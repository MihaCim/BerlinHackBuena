from __future__ import annotations

from typing import Annotated, Literal

from fastapi import APIRouter, Depends, Header, HTTPException, Query, status
from fastapi.responses import PlainTextResponse
from pydantic import BaseModel, StringConstraints

from app.schemas.human_notes import (
    HumanNotesReadResponse,
    HumanNotesWriteRequest,
    HumanNotesWriteResponse,
)
from app.schemas.properties import PropertyId
from app.services.human_notes import (
    HumanNotesError,
    HumanNotesService,
    get_human_notes_service,
)
from app.services.wiki import TreeNode, WikiService, get_wiki_service

router = APIRouter()

RelPath = Annotated[
    str,
    StringConstraints(pattern=r"^[A-Za-z0-9._/-]+$", min_length=1, max_length=512),
]


class TreeNodeOut(BaseModel):
    name: str
    path: str
    type: Literal["file", "dir"]
    children: list[TreeNodeOut] | None = None


def _to_out(node: TreeNode) -> TreeNodeOut:
    return TreeNodeOut(
        name=node.name,
        path=node.path,
        type=node.type,
        children=[_to_out(c) for c in node.children] if node.children is not None else None,
    )


@router.get("/properties")
async def list_wiki_properties(
    service: Annotated[WikiService, Depends(get_wiki_service)],
) -> list[str]:
    return service.list_properties()


@router.get("/tree")
async def get_tree(
    lie: Annotated[PropertyId, Query(description="Property id, e.g. LIE-001")],
    service: Annotated[WikiService, Depends(get_wiki_service)],
) -> TreeNodeOut:
    node = service.walk_tree(lie)
    if node is None:
        raise HTTPException(status.HTTP_404_NOT_FOUND, f"property {lie!r} not found")
    return _to_out(node)


@router.get(
    "/file",
    response_class=PlainTextResponse,
    responses={200: {"content": {"text/markdown": {}}}},
)
async def get_file(
    path: Annotated[RelPath, Query(description="Path relative to wiki_dir")],
    service: Annotated[WikiService, Depends(get_wiki_service)],
) -> PlainTextResponse:
    try:
        content = await service.read_file(path)
    except ValueError as exc:
        raise HTTPException(status.HTTP_400_BAD_REQUEST, str(exc)) from exc
    if content is None:
        raise HTTPException(status.HTTP_404_NOT_FOUND, f"file {path!r} not found")
    return PlainTextResponse(content=content, media_type="text/markdown; charset=utf-8")


@router.get("/human-notes")
async def get_human_notes(
    path: Annotated[RelPath, Query(description="Path relative to wiki_dir")],
    service: Annotated[HumanNotesService, Depends(get_human_notes_service)],
) -> HumanNotesReadResponse:
    try:
        body = await service.read(path)
    except HumanNotesError as exc:
        raise HTTPException(status.HTTP_400_BAD_REQUEST, str(exc)) from exc
    if body is None:
        raise HTTPException(status.HTTP_404_NOT_FOUND, f"file {path!r} not found")
    return HumanNotesReadResponse(path=path, body=body)


@router.put("/human-notes")
async def put_human_notes(
    payload: HumanNotesWriteRequest,
    path: Annotated[RelPath, Query(description="Path relative to wiki_dir")],
    service: Annotated[HumanNotesService, Depends(get_human_notes_service)],
    pm_user: Annotated[str, Header(alias="x-pm-user", min_length=1, max_length=128)],
) -> HumanNotesWriteResponse:
    try:
        result = await service.write(path, body=payload.body, pm_user=pm_user)
    except HumanNotesError as exc:
        raise HTTPException(status.HTTP_400_BAD_REQUEST, str(exc)) from exc
    return HumanNotesWriteResponse(
        path=result.rel_path,
        bytes_written=result.bytes_written,
        commit_sha=result.commit_sha,
    )
