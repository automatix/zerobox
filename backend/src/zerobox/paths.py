"""Platform-specific paths for zerobox (DD-07).

`config.json` and `.env` live in an OS-conventional per-user directory
(Windows `%APPDATA%\\zerobox`, macOS `~/Library/Application Support/zerobox`,
Linux `$XDG_CONFIG_HOME/zerobox`). Data folders (inbox, archive, profiles,
audit DB) remain freely configurable per `config.json`.
"""

from __future__ import annotations

import os
import sys
from pathlib import Path

CONFIG_DIR_ENV = "ZEROBOX_CONFIG_DIR"


def config_dir() -> Path:
    """Return the directory where `config.json` and `.env` live.

    Precedence:
        1. `$ZEROBOX_CONFIG_DIR` (explicit override, for dev/testing)
        2. OS-conventional per-user config directory:
           - Windows: `%APPDATA%/zerobox`
           - macOS:   `~/Library/Application Support/zerobox`
           - Linux:   `$XDG_CONFIG_HOME/zerobox` (defaults to `~/.config/zerobox`)
        3. Fallback: `~/.zerobox`
    """
    override = os.environ.get(CONFIG_DIR_ENV)
    if override:
        return Path(override)

    if sys.platform == "win32":
        appdata = os.environ.get("APPDATA")
        if appdata:
            return Path(appdata) / "zerobox"
    elif sys.platform == "darwin":
        return Path.home() / "Library" / "Application Support" / "zerobox"
    else:
        xdg = os.environ.get("XDG_CONFIG_HOME")
        base = Path(xdg) if xdg else Path.home() / ".config"
        return base / "zerobox"

    return Path.home() / ".zerobox"


def config_file() -> Path:
    return config_dir() / "config.json"


def env_file() -> Path:
    return config_dir() / ".env"
