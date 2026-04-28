from __future__ import annotations

import difflib
import os
import re
from datetime import datetime, timezone
from pathlib import Path
from typing import Any

from fastapi import FastAPI, HTTPException
from fastapi.responses import PlainTextResponse
from pydantic import BaseModel
from app.api.v1.router import api_router as agent_api_router
from app.core.config import get_settings

from .agent import run_engine
from .ai import gemini_configured
from .chat_agent import answer_with_chat_agent
from .cli import load_local_env
from .intake_agent import process_staged_intake
from .utils import read_json, read_text, write_json, write_text


PROPERTY_ID = "LIE-001"


class RunRequest(BaseModel):
    use_ai: bool = False


class DeltaRequest(BaseModel):
    day: str = "day-01"
    use_ai: bool = False


class AskRequest(BaseModel):
    question: str
    use_ai: bool = False


class ContextEditRequest(BaseModel):
    content: str
    author: str = "frontend-user"


class ResourceRequest(BaseModel):
    name: str = "resource.txt"
    kind: str = "text"
    content: str
    notes: str = ""


class ProcessIntakeRequest(BaseModel):
    use_ai: bool = False


def create_app(source_root: Path | str = Path("data"), output_root: Path | str = Path("outputs")) -> FastAPI:
    load_local_env(Path.cwd() / ".env")
    app = FastAPI(title="Buena Context Engine")
    app.state.source_root = Path(source_root)
    app.state.output_root = Path(output_root)
    os.environ["APP_OUTPUT_DIR"] = str(app.state.output_root)
    get_settings.cache_clear()
    app.include_router(agent_api_router, prefix="/api/v1")

    @app.get("/")
    def index() -> dict[str, str]:
        return {
            "name": "Buena Context Engine API",
            "frontend": "Run the Next.js app from ./frontend on http://127.0.0.1:3000",
        }

    @app.get("/api/status")
    def status() -> dict[str, Any]:
        return read_status(app.state.output_root)

    @app.get("/api/context", response_class=PlainTextResponse)
    def context() -> str:
        context_path = context_file(app.state.output_root)
        if not context_path.exists():
            raise HTTPException(status_code=404, detail="Context has not been generated yet.")
        return read_text(context_path)

    @app.put("/api/context")
    def save_context(payload: ContextEditRequest) -> dict[str, str]:
        context_path = context_file(app.state.output_root)
        if not context_path.exists():
            raise HTTPException(status_code=404, detail="Run bootstrap first.")
        if not payload.content.strip():
            raise HTTPException(status_code=400, detail="Context content is required.")
        current = read_text(context_path)
        updated = mark_user_context_changes(current, payload.content, payload.author)
        write_text(context_path, updated)
        return {
            "status": "saved",
            "context_path": str(context_path),
            "content": updated,
            "message": "Saved direct artifact edits with protected <user> tags.",
        }

    @app.get("/api/patches")
    def patches() -> dict[str, Any]:
        patch_dir = app.state.output_root / "properties" / PROPERTY_ID / "patches"
        if not patch_dir.exists():
            return {"patches": [], "latest": None}
        patch_files = sorted(patch_dir.glob("*.patch.json"))
        latest = read_json(patch_files[-1]) if patch_files else None
        return {"patches": [{"name": p.name, "size": p.stat().st_size} for p in patch_files], "latest": latest}

    @app.post("/api/bootstrap")
    def bootstrap(payload: RunRequest) -> dict[str, Any]:
        state = run_engine(app.state.source_root, app.state.output_root, PROPERTY_ID, "bootstrap", use_ai=payload.use_ai)
        return summarize_state(state)

    @app.post("/api/apply-delta")
    def apply_delta(payload: DeltaRequest) -> dict[str, Any]:
        day = payload.day if payload.day.startswith("day-") else f"day-{payload.day.zfill(2)}"
        delta_path = app.state.source_root / "incremental" / day
        if not delta_path.exists():
            raise HTTPException(status_code=404, detail=f"Delta folder not found: {day}")
        state = run_engine(app.state.source_root, app.state.output_root, PROPERTY_ID, "delta", delta_path=delta_path, use_ai=payload.use_ai)
        return summarize_state(state)

    @app.post("/api/replay")
    def replay(payload: RunRequest) -> dict[str, Any]:
        days = sorted(path for path in (app.state.source_root / "incremental").glob("day-*") if path.is_dir())
        state = run_engine(app.state.source_root, app.state.output_root, PROPERTY_ID, "bootstrap", use_ai=payload.use_ai)
        history = [summarize_state(state)]
        for day in days:
            state = run_engine(app.state.source_root, app.state.output_root, PROPERTY_ID, "delta", delta_path=day, use_ai=payload.use_ai)
            history.append(summarize_state(state))
        result = summarize_state(state)
        result["history"] = history
        return result

    @app.post("/api/ask")
    def ask(payload: AskRequest) -> dict[str, Any]:
        context_path = context_file(app.state.output_root)
        if not context_path.exists():
            raise HTTPException(status_code=404, detail="Run bootstrap first.")
        return answer_with_chat_agent(context_path, payload.question, use_ai=payload.use_ai)

    @app.get("/api/resources")
    def resources() -> dict[str, Any]:
        intake_dir = app.state.output_root / "intake"
        if not intake_dir.exists():
            return {"resources": []}
        records = []
        for path in sorted(intake_dir.glob("*.resource.json"), reverse=True):
            try:
                records.append(read_json(path))
            except ValueError:
                records.append({"name": path.name, "kind": "unknown", "created_at": "", "status": "unreadable"})
        return {"resources": records}

    @app.post("/api/resources")
    def add_resource(payload: ResourceRequest) -> dict[str, Any]:
        if not payload.content.strip():
            raise HTTPException(status_code=400, detail="Resource content is required.")
        created_at = datetime.now(timezone.utc).isoformat()
        slug = slugify(payload.name or payload.kind or "resource")
        stamp = datetime.now(timezone.utc).strftime("%Y%m%d%H%M%S")
        intake_dir = app.state.output_root / "intake"
        raw_path = intake_dir / f"{stamp}_{slug}.txt"
        record_path = intake_dir / f"{stamp}_{slug}.resource.json"
        write_text(raw_path, payload.content)
        record = {
            "id": f"INTAKE-{stamp}",
            "name": payload.name.strip() or raw_path.name,
            "kind": payload.kind.strip() or "text",
            "notes": payload.notes.strip(),
            "created_at": created_at,
            "status": "staged_for_ingestion",
            "raw_path": str(raw_path),
            "record_path": str(record_path),
        }
        write_json(record_path, record)
        return {"status": "staged", "resource": record}

    @app.post("/api/process-intake")
    def process_intake(payload: ProcessIntakeRequest) -> dict[str, Any]:
        result = process_staged_intake(app.state.output_root, PROPERTY_ID, use_ai=payload.use_ai)
        if result.get("status") == "blocked":
            raise HTTPException(status_code=404, detail=result.get("reason", "Run bootstrap first."))
        return result

    return app


def context_file(output_root: Path) -> Path:
    return output_root / "properties" / PROPERTY_ID / "context.md"


def read_status(output_root: Path) -> dict[str, Any]:
    property_dir = output_root / "properties" / PROPERTY_ID
    meta_path = property_dir / "context.meta.json"
    context_path = property_dir / "context.md"
    patch_dir = property_dir / "patches"
    intake_dir = output_root / "intake"
    patch_files = sorted(patch_dir.glob("*.patch.json")) if patch_dir.exists() else []
    if meta_path.exists():
        meta = read_json(meta_path)
    else:
        meta = {"property_id": PROPERTY_ID, "watermark": "not generated", "metrics": {}}
    watermark = meta.get("watermark", "not generated")
    latest_patch = patch_files[-1].name if patch_files else None
    latest_patch_watermark = latest_patch.replace(".patch.json", "") if latest_patch else None
    status_note = ""
    if latest_patch_watermark and watermark != "not generated" and latest_patch_watermark != watermark:
        status_note = f"metadata watermark is {watermark}, latest patch log is {latest_patch_watermark}"
    return {
        "property_id": meta.get("property_id", PROPERTY_ID),
        "watermark": watermark,
        "metrics": meta.get("metrics", {}),
        "context_exists": context_path.exists(),
        "context_path": str(context_path),
        "patch_count": len(patch_files),
        "latest_patch": latest_patch,
        "status_note": status_note,
        "user_edits": count_user_blocks(context_path),
        "staged_resources": len(list(intake_dir.glob("*.resource.json"))) if intake_dir.exists() else 0,
        "ai_configured": gemini_configured(),
        "ai_provider": os.getenv("AI_PROVIDER", "academiccloud").strip() or "academiccloud",
    }


def summarize_state(state: dict[str, Any]) -> dict[str, Any]:
    data = state.get("data", {})
    return {
        "context_path": state.get("context_path"),
        "watermark": data.get("watermark"),
        "metrics": data.get("metrics", {}),
        "patches": state.get("patch_log", {}).get("patches_applied", []),
        "human_notes_preserved": state.get("patch_log", {}).get("human_notes_preserved"),
        "langgraph_available": state.get("langgraph_available", False),
        "agentic_note": state.get("llm_advice", ""),
    }


def mark_user_context_changes(current: str, edited: str, author: str) -> str:
    if current == edited:
        return current
    created_at = datetime.now(timezone.utc).isoformat()
    edit_id = f"USEREDIT-{datetime.now(timezone.utc).strftime('%Y%m%d%H%M%S')}"
    safe_author = sanitize_attr(author or "frontend-user")
    current_lines = current.splitlines()
    edited_lines = edited.splitlines()
    matcher = difflib.SequenceMatcher(a=current_lines, b=edited_lines)
    output: list[str] = []
    edit_count = 0
    for tag, current_start, current_end, edited_start, edited_end in matcher.get_opcodes():
        if tag == "equal":
            output.extend(edited_lines[edited_start:edited_end])
            continue
        edit_count += 1
        if tag == "delete":
            deleted = "\n".join(current_lines[current_start:current_end]).strip()
            if deleted:
                output.extend(user_block_lines(edit_id, edit_count, safe_author, created_at, "delete", f"Deleted generated context:\n\n{deleted}"))
            continue
        replacement = "\n".join(edited_lines[edited_start:edited_end]).strip()
        if replacement:
            output.extend(user_block_lines(edit_id, edit_count, safe_author, created_at, tag, replacement))
    result = "\n".join(output)
    if edited.endswith("\n"):
        result += "\n"
    return result


def user_block_lines(edit_id: str, index: int, author: str, created_at: str, action: str, content: str) -> list[str]:
    safe_content = sanitize_user_text(content)
    return [
        f'<user id="{edit_id}-{index}" author="{author}" created_at="{created_at}" action="{action}">',
        *safe_content.splitlines(),
        "</user>",
    ]


def sanitize_user_text(value: str) -> str:
    return value.replace("</user>", "</ user>").strip()


def sanitize_attr(value: str) -> str:
    return re.sub(r"[^A-Za-z0-9_.@-]+", "-", value).strip("-")[:80] or "frontend-user"


def slugify(value: str) -> str:
    slug = re.sub(r"[^A-Za-z0-9_.-]+", "-", value.strip().lower()).strip("-")
    return slug[:80] or "resource"


def count_user_blocks(context_path: Path) -> int:
    if not context_path.exists():
        return 0
    return len(re.findall(r"<user\b[^>]*>.*?</user>", read_text(context_path), flags=re.S))
