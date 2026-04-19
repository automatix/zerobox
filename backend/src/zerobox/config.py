"""Centralized configuration using pydantic-settings (FR-07).

Config and secrets live in an OS-conventional per-user directory (see
`zerobox.paths`, `DD-07`). Data folders (inbox, archive, profiles,
audit DB) continue to follow whatever `config.json` specifies.
"""

import json
from pathlib import Path
from typing import Literal

from pydantic import BaseModel, SecretStr, field_validator
from pydantic_settings import BaseSettings, SettingsConfigDict

from zerobox.paths import config_file, env_file


def _expand(v: str | Path | None) -> Path | None:
    """Expand `~` in a path. Returns None unchanged so optional fields stay optional."""
    if v is None:
        return None
    return Path(v).expanduser()


class IntakeConfig(BaseModel):
    input_folder: Path = Path.home() / "zerobox" / "inbox"
    file_types: list[str] = [".pdf", ".tiff", ".tif", ".png", ".jpg", ".jpeg"]

    @field_validator("input_folder", mode="before")
    @classmethod
    def _expand_input_folder(cls, v: str | Path) -> Path:
        return _expand(v)


class OcrConfig(BaseModel):
    language: str = "deu+eng"
    deskew: bool = True
    optimize: int = 1
    tesseract_path: Path | None = None
    ghostscript_path: Path | None = None

    @field_validator("tesseract_path", "ghostscript_path", mode="before")
    @classmethod
    def _expand_optional(cls, v: str | Path | None) -> Path | None:
        return _expand(v)


class LLMConfig(BaseModel):
    provider: Literal["anthropic", "openai", "ollama"] = "anthropic"
    model: str = "claude-sonnet-4-6"
    temperature: float = 0.0


class FileManagerConfig(BaseModel):
    output_root: Path = Path.home() / "zerobox" / "archive"
    conflict_strategy: Literal["rename", "overwrite", "skip"] = "rename"

    @field_validator("output_root", mode="before")
    @classmethod
    def _expand_output_root(cls, v: str | Path) -> Path:
        return _expand(v)


class AuditConfig(BaseModel):
    db_path: Path = Path.home() / "zerobox" / "audit.db"

    @field_validator("db_path", mode="before")
    @classmethod
    def _expand_db_path(cls, v: str | Path) -> Path:
        return _expand(v)


class AppConfig(BaseSettings):
    model_config = SettingsConfigDict(
        env_file=".env",
        env_file_encoding="utf-8",
        extra="ignore",
    )

    intake: IntakeConfig = IntakeConfig()
    ocr: OcrConfig = OcrConfig()
    llm: LLMConfig = LLMConfig()
    filemanager: FileManagerConfig = FileManagerConfig()
    audit: AuditConfig = AuditConfig()
    profiles_dir: Path = Path.home() / "zerobox" / "profiles"

    # Secrets from .env — wrapped in SecretStr so model_dump() masks them
    # automatically (returns '**********' instead of the raw key) and so
    # accidental repr/log/JSON dumps cannot leak credentials. Consumers that
    # really need the raw value must call .get_secret_value() explicitly.
    anthropic_api_key: SecretStr = SecretStr("")
    openai_api_key: SecretStr = SecretStr("")
    ollama_base_url: str = "http://localhost:11434"

    @field_validator("profiles_dir", mode="before")
    @classmethod
    def expand_profiles_dir(cls, v: str | Path) -> Path:
        return _expand(v)


def load_config(config_path: Path | None = None) -> AppConfig:
    """Load configuration from a JSON file, falling back to defaults.

    Values from ``config.json`` are merged with environment variables and
    ``.env`` secrets. Keys not present in the file keep their defaults.

    By default the config and `.env` paths resolve via
    :func:`zerobox.paths.config_file` / :func:`zerobox.paths.env_file` —
    an OS-conventional per-user location (or `$ZEROBOX_CONFIG_DIR` when
    set). Callers may override `config_path` explicitly (tests, scripts).
    """
    overrides: dict = {}

    if config_path is None:
        config_path = config_file()

    if config_path.exists():
        with open(config_path, encoding="utf-8") as f:
            overrides = json.load(f)

    env_path = env_file()
    init_kwargs = {"_env_file": str(env_path)} if env_path.exists() else {}

    return AppConfig(**init_kwargs, **overrides)
