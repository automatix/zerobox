"""In-app updater routes (#136).

``GET /update/check`` reports whether a newer public GitHub Release exists.
"""

from __future__ import annotations

import httpx
from fastapi import APIRouter, HTTPException

from zerobox import __version__, updates

router = APIRouter()


def _client() -> httpx.Client:
    # Factory indirection so tests can swap in an ``httpx.MockTransport`` client.
    return httpx.Client(timeout=updates.REQUEST_TIMEOUT)


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
