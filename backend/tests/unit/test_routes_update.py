"""Unit tests for the updater API routes (#136)."""

import httpx
from fastapi.testclient import TestClient

import zerobox
from zerobox.api.routes import update
from zerobox.app import create_app


def _mock_client(handler) -> httpx.Client:
    return httpx.Client(transport=httpx.MockTransport(handler))


def _release(tag: str, *, with_asset: bool = True) -> dict:
    assets = []
    if with_asset:
        assets = [
            {
                "name": f"zerobox_{tag.lstrip('v')}_x64-setup.exe",
                "browser_download_url": f"https://github.com/automatix/zerobox/releases/download/{tag}/zerobox-setup.exe",
            }
        ]
    return {
        "tag_name": tag,
        "html_url": f"https://github.com/automatix/zerobox/releases/tag/{tag}",
        "assets": assets,
    }


class TestCheckUpdate:
    """GET /update/check."""

    def test_newer_release_reports_available(self, monkeypatch):
        monkeypatch.setattr(
            update,
            "_client",
            lambda: _mock_client(lambda r: httpx.Response(200, json=_release("v99.0.0"))),
        )
        client = TestClient(create_app())

        response = client.get("/update/check")

        assert response.status_code == 200
        body = response.json()
        assert body["current"] == zerobox.__version__
        assert body["latest"] == "99.0.0"
        assert body["update_available"] is True
        assert body["asset_url"].endswith("zerobox-setup.exe")
        assert body["notes_url"].endswith("v99.0.0")

    def test_same_version_is_up_to_date(self, monkeypatch):
        monkeypatch.setattr(
            update,
            "_client",
            lambda: _mock_client(
                lambda r: httpx.Response(200, json=_release(f"v{zerobox.__version__}"))
            ),
        )
        client = TestClient(create_app())

        response = client.get("/update/check")

        assert response.status_code == 200
        assert response.json()["update_available"] is False

    def test_missing_asset_reports_none(self, monkeypatch):
        monkeypatch.setattr(
            update,
            "_client",
            lambda: _mock_client(
                lambda r: httpx.Response(200, json=_release("v99.0.0", with_asset=False))
            ),
        )
        client = TestClient(create_app())

        response = client.get("/update/check")

        assert response.status_code == 200
        body = response.json()
        assert body["update_available"] is True
        assert body["asset_url"] is None

    def test_network_error_returns_502(self, monkeypatch):
        def raise_error(request: httpx.Request) -> httpx.Response:
            raise httpx.ConnectError("no network", request=request)

        monkeypatch.setattr(update, "_client", lambda: _mock_client(raise_error))
        client = TestClient(create_app())

        response = client.get("/update/check")

        assert response.status_code == 502
        assert "update server" in response.json()["detail"]


class TestAppVersion:
    def test_app_version_matches_package(self):
        app = create_app()
        assert app.version == zerobox.__version__
