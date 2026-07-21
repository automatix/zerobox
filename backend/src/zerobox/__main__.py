"""Entry point for `python -m zerobox`."""

import os
import sys

import uvicorn

# Import the app statically — NOT via uvicorn's "module:factory" string. PyInstaller's
# analysis follows this import to trace the backend's real dependency tree (fastapi,
# pydantic-settings, ocrmypdf, anthropic, httpx, ...); with the string form the frozen
# sidecar ships without them and dies on launch (#146).
from zerobox.app import create_app
from zerobox.paths import config_dir


def ensure_writable_streams() -> None:
    """Redirect ``sys.stdout``/``sys.stderr`` to a log file when they are ``None``.

    A ``--noconsole`` PyInstaller build has no console, so both streams are ``None``;
    anything that writes to them — uvicorn's log formatters call
    ``sys.stdout.isatty()`` at init — would crash the sidecar (#146). Point them at
    ``zerobox-backend.log`` in the per-user config dir (falling back to the null device).
    """
    if sys.stdout is not None and sys.stderr is not None:
        return
    try:
        config_dir().mkdir(parents=True, exist_ok=True)
        sink = open(  # noqa: SIM115 (kept open for the process lifetime)
            config_dir() / "zerobox-backend.log", "a", encoding="utf-8", buffering=1
        )
    except OSError:
        sink = open(os.devnull, "w")  # noqa: SIM115
    if sys.stdout is None:
        sys.stdout = sink
    if sys.stderr is None:
        sys.stderr = sink


def main() -> None:
    ensure_writable_streams()
    uvicorn.run(create_app(), host="127.0.0.1", port=8000)


if __name__ == "__main__":
    main()
