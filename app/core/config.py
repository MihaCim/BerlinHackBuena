from __future__ import annotations

from functools import lru_cache
from pathlib import Path
from typing import Literal

from pydantic import Field, SecretStr
from pydantic_settings import BaseSettings, SettingsConfigDict

REPO_ROOT = Path(__file__).resolve().parents[2]


class Settings(BaseSettings):
    model_config = SettingsConfigDict(
        env_file=".env",
        env_file_encoding="utf-8",
        case_sensitive=False,
        extra="ignore",
    )

    app_name: str = "buena-context"
    version: str = "0.1.0"
    env: Literal["dev", "staging", "prod"] = "dev"
    log_level: Literal["DEBUG", "INFO", "WARNING", "ERROR"] = "INFO"

    repo_root: Path = Field(default=REPO_ROOT)
    data_dir: Path = Field(default=REPO_ROOT / "data")
    normalize_dir: Path = Field(default=REPO_ROOT / "normalize")
    output_dir: Path = Field(default=REPO_ROOT / "output")
    ingestion_db_path: Path = Field(default=REPO_ROOT / ".local" / "ingestion.sqlite3")
    context_agent_model: str = "gpt-5.4-mini"
    tub_api_key: SecretStr | None = None
    tub_api_base: str = "https://ki-toolbox.tu-braunschweig.de"
    tub_chat_endpoint: str = "/api/v1/chat/send"
    tub_custom_instructions: str = ""
    tub_hide_custom_instructions: bool = True


@lru_cache(maxsize=1)
def get_settings() -> Settings:
    return Settings()
