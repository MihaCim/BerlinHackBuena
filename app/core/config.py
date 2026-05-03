from __future__ import annotations

import os
from functools import lru_cache
from pathlib import Path

from pydantic import BaseModel

REPO_ROOT = Path(__file__).resolve().parents[2]


class Settings(BaseModel):
    app_name: str = "buena-context-agents"
    version: str = "0.2.0"
    env: str = "dev"
    output_dir: Path = REPO_ROOT / "outputs"


@lru_cache(maxsize=1)
def get_settings() -> Settings:
    return Settings(
        app_name=os.getenv("APP_NAME", "buena-context-agents"),
        version=os.getenv("APP_VERSION", "0.2.0"),
        env=os.getenv("APP_ENV", "dev"),
        output_dir=Path(os.getenv("APP_OUTPUT_DIR", str(REPO_ROOT / "outputs"))),
    )
