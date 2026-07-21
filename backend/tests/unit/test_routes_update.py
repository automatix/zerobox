"""Unit tests for the updater API routes (#136, #137)."""

import threading

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


class TestInstallUpdate:
    """POST /update/install."""

    ASSET_URL = "https://github.com/automatix/zerobox/releases/download/v99.0.0/zerobox-setup.exe"

    def _handler(self, request: httpx.Request) -> httpx.Response:
        if request.url.path.endswith("/releases/latest"):
            return httpx.Response(200, json=_release("v99.0.0"))
        return httpx.Response(200, content=b"MZ fake installer")

    def test_downloads_launches_and_schedules_shutdown(self, monkeypatch, tmp_path):
        monkeypatch.setenv("ZEROBOX_CONFIG_DIR", str(tmp_path))
        monkeypatch.setattr(update, "_client", lambda **kw: _mock_client(self._handler))
        launched = []
        monkeypatch.setattr(update.updates, "launch_installer", lambda p: launched.append(p))
        shutdowns = []
        monkeypatch.setattr(update, "schedule_shutdown", lambda **kw: shutdowns.append(True))
        client = TestClient(create_app())

        response = client.post("/update/install")

        assert response.status_code == 200
        body = response.json()
        assert body["launched"] is True
        assert body["version"] == "99.0.0"
        installer = tmp_path / "updates" / "zerobox-setup.exe"
        assert installer.read_bytes() == b"MZ fake installer"
        assert launched == [installer]
        assert shutdowns == [True]

    def test_no_newer_release_returns_409(self, monkeypatch, tmp_path):
        monkeypatch.setenv("ZEROBOX_CONFIG_DIR", str(tmp_path))
        monkeypatch.setattr(
            update,
            "_client",
            lambda **kw: _mock_client(
                lambda r: httpx.Response(200, json=_release(f"v{zerobox.__version__}"))
            ),
        )
        client = TestClient(create_app())

        response = client.post("/update/install")

        assert response.status_code == 409

    def test_untrusted_asset_host_returns_400(self, monkeypatch, tmp_path):
        monkeypatch.setenv("ZEROBOX_CONFIG_DIR", str(tmp_path))
        release = _release("v99.0.0")
        release["assets"][0]["browser_download_url"] = "https://evil.example.com/x-setup.exe"
        monkeypatch.setattr(
            update,
            "_client",
            lambda **kw: _mock_client(lambda r: httpx.Response(200, json=release)),
        )
        client = TestClient(create_app())

        response = client.post("/update/install")

        assert response.status_code == 400
        assert "untrusted" in response.json()["detail"]

    def test_download_failure_returns_502(self, monkeypatch, tmp_path):
        monkeypatch.setenv("ZEROBOX_CONFIG_DIR", str(tmp_path))

        def handler(request: httpx.Request) -> httpx.Response:
            if request.url.path.endswith("/releases/latest"):
                return httpx.Response(200, json=_release("v99.0.0"))
            raise httpx.ConnectError("download failed", request=request)

        monkeypatch.setattr(update, "_client", lambda **kw: _mock_client(handler))
        client = TestClient(create_app())

        response = client.post("/update/install")

        assert response.status_code == 502
        assert "installer" in response.json()["detail"]


class TestScheduleShutdown:
    def test_fires_terminate_after_delay(self, monkeypatch):
        fired = threading.Event()
        monkeypatch.setattr(update, "_terminate", fired.set)

        update.schedule_shutdown(delay=0.01)

        assert fired.wait(timeout=2)


class TestAppVersion:
    def test_app_version_matches_package(self):
        app = create_app()
        assert app.version == zerobox.__version__
