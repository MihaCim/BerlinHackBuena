from __future__ import annotations

import argparse
import os
import re
from pathlib import Path

from .agent import run_engine
from .ai import gemini_configured
from .intake_agent import process_staged_intake
from .qa import answer_from_context
from .utils import read_json, read_text


def main(argv: list[str] | None = None) -> None:
    load_local_env(Path.cwd() / ".env")

    parser = argparse.ArgumentParser(description="Buena Context Engine")
    sub = parser.add_subparsers(dest="command", required=True)

    bootstrap = sub.add_parser("bootstrap", help="Compile the historical property context.")
    add_common(bootstrap)

    delta = sub.add_parser("apply-delta", help="Apply one incremental day as a surgical patch.")
    add_common(delta)
    delta.add_argument("--delta", required=True, type=Path)

    replay = sub.add_parser("replay-deltas", help="Replay all incremental days in order.")
    add_common(replay)

    ask = sub.add_parser("ask", help="Answer from the compiled markdown context.")
    ask.add_argument("--context", type=Path, default=Path("outputs/properties/LIE-001/context.md"))
    ask.add_argument("--question", required=True)
    ask.add_argument("--use-ai", action="store_true", help="Use the configured AI provider to synthesize the answer.")

    status = sub.add_parser("status", help="Show latest compiled metrics.")
    status.add_argument("--output", type=Path, default=Path("outputs"))
    status.add_argument("--property", default="LIE-001")

    intake = sub.add_parser("process-intake", help="Validate staged resources and write accepted evidence into context.md.")
    intake.add_argument("--output", type=Path, default=Path("outputs"))
    intake.add_argument("--property", default="LIE-001")
    intake.add_argument("--use-ai", action="store_true", help="Allow configured AI to assist within schema guardrails.")

    serve = sub.add_parser("serve", help="Start the web dashboard.")
    serve.add_argument("--host", default="127.0.0.1")
    serve.add_argument("--port", type=int, default=8765)
    serve.add_argument("--source", type=Path, default=Path("data"))
    serve.add_argument("--output", type=Path, default=Path("outputs"))

    args = parser.parse_args(argv)

    if args.command == "bootstrap":
        state = run_engine(args.source, args.output, args.property, "bootstrap", use_ai=args.use_ai)
        print_result(state)
    elif args.command == "apply-delta":
        state = run_engine(args.source, args.output, args.property, "delta", delta_path=args.delta, use_ai=args.use_ai)
        print_result(state)
    elif args.command == "replay-deltas":
        source = args.source
        days = sorted(path for path in (source / "incremental").glob("day-*") if path.is_dir())
        state = run_engine(source, args.output, args.property, "bootstrap", use_ai=args.use_ai)
        print_result(state)
        for day in days:
            state = run_engine(source, args.output, args.property, "delta", delta_path=day, use_ai=args.use_ai)
            print_result(state)
    elif args.command == "ask":
        print(answer_from_context(args.context, args.question, use_ai=args.use_ai))
    elif args.command == "status":
        print_status(args.output, args.property)
    elif args.command == "process-intake":
        result = process_staged_intake(args.output, args.property, use_ai=args.use_ai)
        print(f"status={result.get('status')}")
        if result.get("reason"):
            print(f"reason={result.get('reason')}")
        for item in result.get("processed", []):
            print(item)
    elif args.command == "serve":
        import uvicorn

        from .web import create_app

        app = create_app(args.source, args.output)
        uvicorn.run(app, host=args.host, port=args.port)


def add_common(parser: argparse.ArgumentParser) -> None:
    parser.add_argument("--source", type=Path, default=Path("data"))
    parser.add_argument("--output", type=Path, default=Path("outputs"))
    parser.add_argument("--property", default="LIE-001")
    parser.add_argument("--use-ai", action="store_true", help="Use the configured AI provider for advisory and answer synthesis.")


def print_result(state: dict) -> None:
    metrics = state.get("data", {}).get("metrics", {})
    print(f"context_path={state.get('context_path')}")
    print(f"watermark={state.get('data', {}).get('watermark')}")
    print(f"langgraph_available={state.get('langgraph_available')}")
    print(f"patches={state.get('patch_log', {}).get('patches_applied')}")
    print(f"metrics={metrics}")


def print_status(output: Path, property_id: str) -> None:
    property_dir = output / "properties" / property_id
    meta_path = property_dir / "context.meta.json"
    context_path = property_dir / "context.md"
    patch_dir = property_dir / "patches"
    intake_dir = output / "intake"
    patch_files = sorted(patch_dir.glob("*.patch.json")) if patch_dir.exists() else []
    meta = read_json(meta_path) if meta_path.exists() else {"property_id": property_id, "watermark": "not generated", "metrics": {}}
    print(f"Property: {meta.get('property_id', property_id)}")
    print(f"Watermark: {meta.get('watermark', 'not generated')}")
    print(f"Context exists: {context_path.exists()}")
    print(f"Latest patch: {patch_files[-1].name if patch_files else 'none'}")
    print(f"Patch count: {len(patch_files)}")
    print(f"Protected user edits: {count_user_blocks(context_path)}")
    print(f"Staged resources: {len(list(intake_dir.glob('*.resource.json'))) if intake_dir.exists() else 0}")
    print(f"AI configured: {gemini_configured()}")
    for key, value in (meta.get("metrics") or {}).items():
        print(f"{key}: {value}")


def count_user_blocks(context_path: Path) -> int:
    if not context_path.exists():
        return 0
    return len(re.findall(r"<user\b[^>]*>.*?</user>", read_text(context_path), flags=re.S))


def load_local_env(path: Path) -> None:
    if not path.exists():
        return
    for raw_line in path.read_text(encoding="utf-8").splitlines():
        line = raw_line.strip()
        if not line or line.startswith("#"):
            continue
        if line.lower().startswith("export "):
            line = line[7:].strip()
        if "=" not in line:
            continue
        key, value = line.split("=", 1)
        key = key.strip()
        value = value.strip().strip("'").strip('"')
        if key and key not in os.environ:
            os.environ[key] = value
