"""In-app updater routes (#136, #137).

``GET /update/check`` reports whether a newer public GitHub Release exists.
``POST /update/install`` downloads that release's installer, launches it, and exits the
backend so the (UAC-gated) installer can replace the files. The Tauri frontend closes its
window after a successful install call — together both processes are gone before the
installer touches the install directory.
"""

from __future__ import annotations

import os
import threading

import httpx
from fastapi import APIRouter, HTTPException

from zerobox import __version__, paths, updates

router = APIRouter()

# Give the HTTP response time to flush before the backend process exits.
SHUTDOWN_DELAY_SECONDS = 0.7


def _client(*, follow_redirects: bool = False) -> httpx.Client:
    # Factory indirection so tests can swap in an ``httpx.MockTransport`` client.
    return httpx.Client(timeout=updates.REQUEST_TIMEOUT, follow_redirects=follow_redirects)


def _terminate() -> None:  # pragma: no cover - would kill the test process
    os._exit(0)


def schedule_shutdown(*, delay: float | None = None) -> None:
    """Exit the backend after a short delay (lets the install response flush first).

    The backend runs as a Tauri sidecar: the frontend closes the window, this exits the
    sidecar, and the installer can then replace both binaries.
    """
    timer = threading.Timer(SHUTDOWN_DELAY_SECONDS if delay is None else delay, _terminate)
    timer.daemon = True
    timer.start()


@router.get("/check")
def check_update() -> dict:
    """Compare the running version against the latest public release."""
    try:
        with _client() as client:
            info = updates.check_for_update(__version__, client=client)
    except httpx.HTTPError as exc:
        raise HTTPException(
            status_code=502, detail="Could not reach the update server"
        ) from exc
    return info.as_dict()


@router.post("/install")
def install_update() -> dict:
    """Download the latest installer and launch it, then exit the backend.

    The asset URL is re-resolved server-side (never trusted from the client) and must be a
    GitHub host. This launches an interactive, UAC-gated installer — it does **not** install
    silently or without the user having confirmed in the GUI.
    """
    try:
        with _client(follow_redirects=True) as client:
            info = updates.check_for_update(__version__, client=client)
            if not info.update_available or not info.asset_url:
                raise HTTPException(
                    status_code=409, detail="No newer installer is available"
                )
            if not updates.is_trusted_asset_url(info.asset_url):
                raise HTTPException(
                    status_code=400, detail="Refusing to download from an untrusted host"
                )
            dest = updates.download_installer(
                info.asset_url, paths.config_dir() / "updates", client=client
            )
    except httpx.HTTPError as exc:
        raise HTTPException(
            status_code=502, detail="Could not download the installer"
        ) from exc

    updates.launch_installer(dest)
    schedule_shutdown()
    return {"launched": True, "version": info.latest, "installer": str(dest)}
