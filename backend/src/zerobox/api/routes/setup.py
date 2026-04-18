"""First-Run-Wizard API endpoints (FR-36)."""

from __future__ import annotations

import json
import logging
import os
import shutil
import sys
from pathlib import Path
from typing import Literal

from fastapi import APIRouter
from pydantic import BaseModel

logger = logging.getLogger(__name__)

router = APIRouter()


# ---------------------------------------------------------------------------
# Request / response models
# ---------------------------------------------------------------------------

class SetupStatus(BaseModel):
    setup_complete: bool
    has_config: bool
    has_env: bool
    tesseract_available: bool
    tesseract_path: str | None
    ghostscript_available: bool
    ghostscript_path: str | None


class ValidateRequest(BaseModel):
    provider: Literal["anthropic", "openai", "ollama"]
    api_key: str = ""
    ollama_base_url: str = "http://localhost:11434"


class ValidateResponse(BaseModel):
    provider_ok: bool
    provider_error: str | None = None
    tesseract_ok: bool
    ghostscript_ok: bool


class SaveConfigRequest(BaseModel):
    input_folder: str
    output_root: str
    profiles_dir: str
    language: str = "deu+eng"
    provider: Literal["anthropic", "openai", "ollama"] = "anthropic"
    model: str = "claude-sonnet-4-6"
    api_key: str = ""
    ollama_base_url: str = "http://localhost:11434"


# ---------------------------------------------------------------------------
# Helpers
# ---------------------------------------------------------------------------

def _config_dir() -> Path:
    """Return the directory where config.json and .env live."""
    if getattr(sys, "frozen", False):
        return Path(sys.executable).parent
    return Path.cwd()


def _resources_dir() -> Path | None:
    """Return the app's resources/ directory (production only)."""
    if getattr(sys, "frozen", False):
        return Path(sys.executable).parent / "resources"
    return None


def _find_executable(
    name: str,
    portable_subpath: str | None = None,
) -> str | None:
    """Find an executable: portable resources/ > system PATH."""
    res = _resources_dir()
    if res and portable_subpath:
        portable = res / portable_subpath
        if portable.exists():
            return str(portable)

    found = shutil.which(name)
    return found


def _is_setup_complete() -> bool:
    """Check if the setup has been completed previously."""
    config_path = _config_dir() / "config.json"
    if not config_path.exists():
        return False
    try:
        with open(config_path, encoding="utf-8") as f:
            data = json.load(f)
        return data.get("setup_complete", False)
    except (json.JSONDecodeError, OSError):
        return False


# ---------------------------------------------------------------------------
# Endpoints
# ---------------------------------------------------------------------------

@router.get("/status", response_model=SetupStatus)
async def get_setup_status() -> SetupStatus:
    """Check what is configured and what is missing."""
    base = _config_dir()

    tesseract = _find_executable("tesseract", "tesseract/tesseract.exe")
    ghostscript = _find_executable("gswin64c", "ghostscript/bin/gswin64c.exe")

    return SetupStatus(
        setup_complete=_is_setup_complete(),
        has_config=(base / "config.json").exists(),
        has_env=(base / ".env").exists(),
        tesseract_available=tesseract is not None,
        tesseract_path=tesseract,
        ghostscript_available=ghostscript is not None,
        ghostscript_path=ghostscript,
    )


@router.post("/validate", response_model=ValidateResponse)
async def validate_setup(req: ValidateRequest) -> ValidateResponse:
    """Test that the chosen LLM provider and dependencies are accessible."""
    provider_ok = False
    provider_error = None

    if req.provider == "anthropic":
        if not req.api_key:
            provider_error = "API key is required for Anthropic"
        else:
            try:
                import anthropic

                client = anthropic.Anthropic(api_key=req.api_key)
                client.models.list(limit=1)
                provider_ok = True
            except Exception as exc:
                provider_error = str(exc)

    elif req.provider == "openai":
        if not req.api_key:
            provider_error = "API key is required for OpenAI"
        else:
            try:
                import openai

                client = openai.OpenAI(api_key=req.api_key)
                client.models.list()
                provider_ok = True
            except Exception as exc:
                provider_error = str(exc)

    elif req.provider == "ollama":
        try:
            import httpx

            resp = httpx.get(f"{req.ollama_base_url}/api/tags", timeout=5)
            provider_ok = resp.status_code == 200
            if not provider_ok:
                provider_error = f"Ollama returned status {resp.status_code}"
        except Exception as exc:
            provider_error = str(exc)

    tesseract = _find_executable("tesseract", "tesseract/tesseract.exe")
    ghostscript = _find_executable("gswin64c", "ghostscript/bin/gswin64c.exe")

    return ValidateResponse(
        provider_ok=provider_ok,
        provider_error=provider_error,
        tesseract_ok=tesseract is not None,
        ghostscript_ok=ghostscript is not None,
    )


@router.post("/save")
async def save_config(req: SaveConfigRequest) -> dict[str, str]:
    """Write config.json and .env based on wizard input."""
    base = _config_dir()

    # Build config.json
    config_data = {
        "setup_complete": True,
        "intake": {
            "input_folder": req.input_folder,
        },
        "ocr": {
            "language": req.language,
        },
        "llm": {
            "provider": req.provider,
            "model": req.model,
        },
        "filemanager": {
            "output_root": req.output_root,
        },
        "profiles_dir": req.profiles_dir,
    }

    config_path = base / "config.json"
    with open(config_path, "w", encoding="utf-8") as f:
        json.dump(config_data, f, indent=2)

    logger.info("Config written to %s", config_path)

    # Build .env
    env_lines = []
    if req.provider == "anthropic" and req.api_key:
        env_lines.append(f"ANTHROPIC_API_KEY={req.api_key}")
    elif req.provider == "openai" and req.api_key:
        env_lines.append(f"OPENAI_API_KEY={req.api_key}")
    elif req.provider == "ollama":
        env_lines.append(f"OLLAMA_BASE_URL={req.ollama_base_url}")

    env_path = base / ".env"
    with open(env_path, "w", encoding="utf-8") as f:
        f.write("\n".join(env_lines) + "\n")

    logger.info(".env written to %s", env_path)

    # Create directories if they don't exist
    for folder in [req.input_folder, req.output_root, req.profiles_dir]:
        Path(folder).mkdir(parents=True, exist_ok=True)

    return {"status": "ok", "config_path": str(config_path)}
