"""Centralized configuration using pydantic-settings (FR-07)."""

import json
from pathlib import Path
from typing import Literal

from pydantic import BaseModel, field_validator
from pydantic_settings import BaseSettings, SettingsConfigDict


class ScannerConfig(BaseModel):
    input_folder: Path = Path.home() / "zerobox" / "inbox"
    file_types: list[str] = [".pdf", ".tiff", ".tif", ".png", ".jpg", ".jpeg"]


class OcrConfig(BaseModel):
    language: str = "deu+eng"
    deskew: bool = True
    optimize: int = 1


class LLMConfig(BaseModel):
    provider: Literal["anthropic", "openai", "ollama"] = "anthropic"
    model: str = "claude-sonnet-4-20250514"
    temperature: float = 0.0


class FileManagerConfig(BaseModel):
    output_root: Path = Path.home() / "zerobox" / "archive"
    conflict_strategy: Literal["rename", "overwrite", "skip"] = "rename"


class AuditConfig(BaseModel):
    db_path: Path = Path.home() / "zerobox" / "audit.db"


class AppConfig(BaseSettings):
    model_config = SettingsConfigDict(
        env_file=".env",
        env_file_encoding="utf-8",
        extra="ignore",
    )

    scanner: ScannerConfig = ScannerConfig()
    ocr: OcrConfig = OcrConfig()
    llm: LLMConfig = LLMConfig()
    filemanager: FileManagerConfig = FileManagerConfig()
    audit: AuditConfig = AuditConfig()
    profiles_dir: Path = Path.home() / "zerobox" / "profiles"

    # Secrets from .env
    anthropic_api_key: str = ""
    openai_api_key: str = ""
    ollama_base_url: str = "http://localhost:11434"

    @field_validator("profiles_dir", mode="before")
    @classmethod
    def expand_profiles_dir(cls, v: str | Path) -> Path:
        return Path(v).expanduser()


def load_config(config_path: Path | None = None) -> AppConfig:
    """Load configuration from a JSON file, falling back to defaults.

    Values from ``config.json`` are merged with environment variables and
    ``.env`` secrets.  Keys not present in the file keep their defaults.
    """
    overrides: dict = {}

    if config_path is None:
        config_path = Path("config.json")

    if config_path.exists():
        with open(config_path, encoding="utf-8") as f:
            overrides = json.load(f)

    return AppConfig(**overrides)
