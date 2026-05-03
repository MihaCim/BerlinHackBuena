from __future__ import annotations

from pathlib import Path
from typing import Any, TypedDict
from uuid import uuid4

from .ai import get_agentic_advice
from .parsers import build_context_data
from .patcher import PATCHABLE_SECTIONS, apply_context_patch
from .renderer import render_context
from .store import persist_outputs


class EngineState(TypedDict, total=False):
    source_root: str
    output_root: str
    property_id: str
    mode: str
    delta_path: str
    include_all_deltas: bool
    use_ai: bool
    run_id: str
    data_key: str
    data: dict[str, Any]
    llm_advice: str
    proposed_context: str
    context_path: str
    patch_log: dict[str, Any]
    langgraph_available: bool


RUN_CACHE: dict[str, dict[str, Any]] = {}
GRAPH_CACHE: Any | None = None


def get_cached_data(state: EngineState) -> dict[str, Any]:
    key = state.get("data_key") or state.get("run_id")
    if not key or key not in RUN_CACHE:
        raise RuntimeError("Workflow data cache is missing for this run.")
    return RUN_CACHE[key]


def ingest_node(state: EngineState) -> EngineState:
    source_root = Path(state["source_root"])
    delta = Path(state["delta_path"]) if state.get("delta_path") else None
    data = build_context_data(source_root, delta, bool(state.get("include_all_deltas")))
    data["langgraph"] = {"workflow": "buena_context_engine", "mode": state.get("mode", "bootstrap")}
    run_id = state.get("run_id") or str(uuid4())
    RUN_CACHE[run_id] = data
    return {**state, "run_id": run_id, "data_key": run_id, "data": {"watermark": data.get("watermark"), "metrics": data.get("metrics")}}


def agentic_review_node(state: EngineState) -> EngineState:
    advice = get_agentic_advice(get_cached_data(state), bool(state.get("use_ai")))
    return {**state, "llm_advice": advice}


def compile_node(state: EngineState) -> EngineState:
    proposed = render_context(get_cached_data(state), state.get("llm_advice", ""))
    return {**state, "proposed_context": proposed}


def patch_node(state: EngineState) -> EngineState:
    output_root = Path(state["output_root"])
    property_id = state.get("property_id", "LIE-001")
    property_dir = output_root / "properties" / property_id
    context_path = property_dir / "context.md"
    patch_dir = property_dir / "patches"
    patch_dir.mkdir(parents=True, exist_ok=True)
    watermark = state["data"].get("watermark", "bootstrap")
    patch_log_path = patch_dir / f"{watermark}.patch.json"
    sections = PATCHABLE_SECTIONS if state.get("mode") != "bootstrap" else None
    patch_log = apply_context_patch(context_path, state["proposed_context"], patch_log_path, sections)
    return {**state, "context_path": str(context_path), "patch_log": patch_log}


def persist_node(state: EngineState) -> EngineState:
    persist_outputs(Path(state["output_root"]), get_cached_data(state), state.get("patch_log"))
    return state


def build_graph():
    global GRAPH_CACHE
    if GRAPH_CACHE is not None:
        return GRAPH_CACHE
    try:
        from langgraph.graph import END, StateGraph
    except Exception:
        return None

    graph = StateGraph(EngineState)
    graph.add_node("ingest", ingest_node)
    graph.add_node("agentic_review", agentic_review_node)
    graph.add_node("compile", compile_node)
    graph.add_node("patch", patch_node)
    graph.add_node("persist", persist_node)
    graph.set_entry_point("ingest")
    graph.add_edge("ingest", "agentic_review")
    graph.add_edge("agentic_review", "compile")
    graph.add_edge("compile", "patch")
    graph.add_edge("patch", "persist")
    graph.add_edge("persist", END)
    GRAPH_CACHE = graph.compile()
    return GRAPH_CACHE


def run_engine(
    source_root: Path,
    output_root: Path,
    property_id: str = "LIE-001",
    mode: str = "bootstrap",
    delta_path: Path | None = None,
    include_all_deltas: bool = False,
    use_ai: bool = False,
) -> EngineState:
    initial: EngineState = {
        "source_root": str(source_root),
        "output_root": str(output_root),
        "property_id": property_id,
        "mode": mode,
        "delta_path": str(delta_path) if delta_path else "",
        "include_all_deltas": include_all_deltas,
        "use_ai": use_ai,
    }
    graph = build_graph()
    if graph is not None:
        result = graph.invoke(initial)
        result["langgraph_available"] = True
        return result

    state = ingest_node(initial)
    state = agentic_review_node(state)
    state = compile_node(state)
    state = patch_node(state)
    state = persist_node(state)
    state["langgraph_available"] = False
    return state
