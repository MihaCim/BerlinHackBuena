from __future__ import annotations

from pathlib import Path
from typing import Any

from fastapi import FastAPI, HTTPException
from fastapi.responses import FileResponse, PlainTextResponse
from fastapi.staticfiles import StaticFiles
from pydantic import BaseModel

from .agent import run_engine
from .cli import load_local_env
from .qa import answer_from_context
from .utils import read_json, read_text


PROPERTY_ID = "LIE-001"
STATIC_DIR = Path(__file__).parent / "web_static"


class RunRequest(BaseModel):
    use_ai: bool = False


class DeltaRequest(BaseModel):
    day: str = "day-01"
    use_ai: bool = False


class AskRequest(BaseModel):
    question: str
    use_ai: bool = False


def create_app(source_root: Path | str = Path("data"), output_root: Path | str = Path("outputs")) -> FastAPI:
    load_local_env(Path.cwd() / ".env")
    app = FastAPI(title="Buena Context Engine")
    app.state.source_root = Path(source_root)
    app.state.output_root = Path(output_root)
    app.mount("/static", StaticFiles(directory=STATIC_DIR), name="static")

    @app.get("/")
    def index() -> FileResponse:
        return FileResponse(STATIC_DIR / "index.html")

    @app.get("/api/status")
    def status() -> dict[str, Any]:
        return read_status(app.state.output_root)

    @app.get("/api/context", response_class=PlainTextResponse)
    def context() -> str:
        context_path = context_file(app.state.output_root)
        if not context_path.exists():
            raise HTTPException(status_code=404, detail="Context has not been generated yet.")
        return read_text(context_path)

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
    def ask(payload: AskRequest) -> dict[str, str]:
        context_path = context_file(app.state.output_root)
        if not context_path.exists():
            raise HTTPException(status_code=404, detail="Run bootstrap first.")
        return {"answer": answer_from_context(context_path, payload.question, use_ai=payload.use_ai)}

    return app


def context_file(output_root: Path) -> Path:
    return output_root / "properties" / PROPERTY_ID / "context.md"


def read_status(output_root: Path) -> dict[str, Any]:
    property_dir = output_root / "properties" / PROPERTY_ID
    meta_path = property_dir / "context.meta.json"
    context_path = property_dir / "context.md"
    patch_dir = property_dir / "patches"
    patch_files = sorted(patch_dir.glob("*.patch.json")) if patch_dir.exists() else []
    if meta_path.exists():
        meta = read_json(meta_path)
    else:
        meta = {"property_id": PROPERTY_ID, "watermark": "not generated", "metrics": {}}
    return {
        "property_id": meta.get("property_id", PROPERTY_ID),
        "watermark": meta.get("watermark", "not generated"),
        "metrics": meta.get("metrics", {}),
        "context_exists": context_path.exists(),
        "context_path": str(context_path),
        "patch_count": len(patch_files),
        "latest_patch": patch_files[-1].name if patch_files else None,
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
