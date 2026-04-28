from __future__ import annotations

from pathlib import Path


class BuildingMemoryService:
    def __init__(self, output_dir: Path) -> None:
        self.output_dir = output_dir
        self.output_dir.mkdir(parents=True, exist_ok=True)

    def path(self, building_id: str) -> Path:
        flat = self.output_dir / f"{building_id}.md"
        nested = self.output_dir / "properties" / building_id / "context.md"
        if nested.exists():
            return nested
        return flat

    def list_buildings(self) -> list[str]:
        flat = {path.stem for path in self.output_dir.glob("*.md")}
        nested = {
            path.parent.name
            for path in (self.output_dir / "properties").glob("*/context.md")
            if path.is_file()
        }
        return sorted(flat | nested)

    def load(self, building_id: str) -> str | None:
        path = self.path(building_id)
        if not path.exists():
            return None
        return path.read_text(encoding="utf-8")

    def write(self, building_id: str, markdown: str) -> None:
        self.path(building_id).write_text(markdown, encoding="utf-8")
