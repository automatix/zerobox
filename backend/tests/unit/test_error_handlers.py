"""Tests for global exception handlers (#28)."""

from __future__ import annotations

from fastapi import APIRouter
from fastapi.testclient import TestClient

from zerobox.app import create_app


def _app_with_error_routes():
    """Create an app with routes that raise specific exceptions."""
    app = create_app()
    router = APIRouter()

    @router.get("/raise-file-not-found")
    async def raise_fnf():
        raise FileNotFoundError("file.pdf not found")

    @router.get("/raise-value-error")
    async def raise_ve():
        raise ValueError("invalid input value")

    @router.get("/raise-generic")
    async def raise_generic():
        raise RuntimeError("something went wrong")

    app.include_router(router, prefix="/test-errors")
    return app


class TestFileNotFoundHandler:
    def test_returns_404(self) -> None:
        client = TestClient(_app_with_error_routes(), raise_server_exceptions=False)
        resp = client.get("/test-errors/raise-file-not-found")
        assert resp.status_code == 404
        body = resp.json()
        assert body["error"] == "file.pdf not found"


class TestValueErrorHandler:
    def test_returns_400(self) -> None:
        client = TestClient(_app_with_error_routes(), raise_server_exceptions=False)
        resp = client.get("/test-errors/raise-value-error")
        assert resp.status_code == 400
        body = resp.json()
        assert body["error"] == "invalid input value"


class TestGeneralExceptionHandler:
    def test_returns_500(self) -> None:
        client = TestClient(_app_with_error_routes(), raise_server_exceptions=False)
        resp = client.get("/test-errors/raise-generic")
        assert resp.status_code == 500
        body = resp.json()
        assert body["error"] == "Internal server error"
        assert body["detail"] == "something went wrong"
