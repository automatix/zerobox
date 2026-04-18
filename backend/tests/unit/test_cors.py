"""Tests for CORS middleware configuration (#43)."""

from __future__ import annotations

import pytest
from fastapi.testclient import TestClient

from zerobox.app import ALLOWED_ORIGINS, create_app


@pytest.fixture
def client() -> TestClient:
    return TestClient(create_app())


class TestCorsAllowedOrigins:
    @pytest.mark.parametrize("origin", ALLOWED_ORIGINS)
    def test_preflight_returns_allow_origin(self, client: TestClient, origin: str) -> None:
        resp = client.options(
            "/setup/status",
            headers={
                "Origin": origin,
                "Access-Control-Request-Method": "GET",
            },
        )
        assert resp.status_code == 200
        assert resp.headers.get("access-control-allow-origin") == origin

    @pytest.mark.parametrize("origin", ALLOWED_ORIGINS)
    def test_simple_request_returns_allow_origin(self, client: TestClient, origin: str) -> None:
        resp = client.get("/health", headers={"Origin": origin})
        assert resp.status_code == 200
        assert resp.headers.get("access-control-allow-origin") == origin


class TestCorsDisallowedOrigin:
    def test_preflight_from_unknown_origin_has_no_allow_origin(self, client: TestClient) -> None:
        resp = client.options(
            "/setup/status",
            headers={
                "Origin": "http://evil.example.com",
                "Access-Control-Request-Method": "GET",
            },
        )
        assert resp.headers.get("access-control-allow-origin") is None
