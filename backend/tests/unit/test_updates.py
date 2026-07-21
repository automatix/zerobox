"""Unit tests for the updater core module (#136, #137)."""

from unittest.mock import MagicMock, patch

import httpx
import pytest

from zerobox import updates


class TestParseVersion:
    def test_plain(self):
        assert updates.parse_version("1.2.3") == (1, 2, 3)

    def test_leading_v(self):
        assert updates.parse_version("v0.7.0") == (0, 7, 0)

    def test_prerelease_suffix_ignored(self):
        assert updates.parse_version("1.2.3-rc1") == (1, 2, 3)

    def test_build_metadata_ignored(self):
        assert updates.parse_version("1.2.3+build.5") == (1, 2, 3)

    def test_garbage_degrades_to_zero(self):
        assert updates.parse_version("not-a-version") == (0,)


class TestIsNewer:
    @pytest.mark.parametrize(
        ("latest", "current", "expected"),
        [
            ("0.8.0", "0.7.0", True),
            ("1.0.0", "0.7.0", True),
            ("0.7.0", "0.7.0", False),
            ("0.6.0", "0.7.0", False),
            ("0.7.1", "0.7.0", True),
        ],
    )
    def test_compare(self, latest, current, expected):
        assert updates.is_newer(latest, current) is expected


class TestRepo:
    def test_default(self, monkeypatch):
        monkeypatch.delenv(updates.ENV_REPO, raising=False)
        assert updates.repo() == updates.DEFAULT_REPO

    def test_env_override(self, monkeypatch):
        monkeypatch.setenv(updates.ENV_REPO, "someone/fork")
        assert updates.repo() == "someone/fork"


class TestSelectInstallerAsset:
    def test_selects_setup_exe(self):
        release = {
            "assets": [
                {"name": "zerobox_0.8.0_x64_en-US.msi", "browser_download_url": "https://x/msi"},
                {"name": "zerobox_0.8.0_x64-setup.exe", "browser_download_url": "https://x/exe"},
            ]
        }
        assert updates.select_installer_asset(release) == "https://x/exe"

    def test_missing_asset(self):
        release = {"assets": [{"name": "docs.zip", "browser_download_url": "https://x/zip"}]}
        assert updates.select_installer_asset(release) is None

    def test_no_assets(self):
        assert updates.select_installer_asset({}) is None


def _release(tag: str, *, asset_url: str | None = "https://github.com/x-setup.exe") -> dict:
    assets = []
    if asset_url:
        assets = [{"name": "zerobox-setup.exe", "browser_download_url": asset_url}]
    return {
        "tag_name": tag,
        "html_url": f"https://github.com/automatix/zerobox/releases/tag/{tag}",
        "assets": assets,
    }


class TestBuildUpdateInfo:
    def test_newer(self):
        info = updates.build_update_info("0.7.0", _release("v0.8.0"))
        assert info.update_available is True
        assert info.latest == "0.8.0"
        assert info.current == "0.7.0"
        assert info.asset_url == "https://github.com/x-setup.exe"
        assert info.notes_url.endswith("v0.8.0")

    def test_equal(self):
        info = updates.build_update_info("0.7.0", _release("v0.7.0"))
        assert info.update_available is False

    def test_older(self):
        info = updates.build_update_info("0.7.0", _release("v0.6.0"))
        assert info.update_available is False

    def test_missing_tag(self):
        info = updates.build_update_info("0.7.0", {"assets": []})
        assert info.latest is None
        assert info.update_available is False


class TestCheckForUpdate:
    def test_fetches_and_compares(self):
        def handler(request: httpx.Request) -> httpx.Response:
            assert request.url.path == "/repos/automatix/zerobox/releases/latest"
            return httpx.Response(200, json=_release("v9.9.9"))

        client = httpx.Client(transport=httpx.MockTransport(handler))
        info = updates.check_for_update("0.7.0", client=client, repo_name="automatix/zerobox")
        assert info.update_available is True
        assert info.latest == "9.9.9"

    def test_http_error_raises(self):
        def handler(request: httpx.Request) -> httpx.Response:
            return httpx.Response(500)

        client = httpx.Client(transport=httpx.MockTransport(handler))
        with pytest.raises(httpx.HTTPStatusError):
            updates.check_for_update("0.7.0", client=client)


class TestIsTrustedAssetUrl:
    @pytest.mark.parametrize(
        ("url", "expected"),
        [
            ("https://github.com/automatix/zerobox/releases/download/v1/x-setup.exe", True),
            ("https://objects.githubusercontent.com/abc", True),
            ("https://evil.example.com/x-setup.exe", False),
            ("https://github.com.evil.example.com/x-setup.exe", False),
        ],
    )
    def test_hosts(self, url, expected):
        assert updates.is_trusted_asset_url(url) is expected


class TestDownloadInstaller:
    def test_writes_file(self, tmp_path):
        payload = b"MZ fake installer bytes"

        def handler(request: httpx.Request) -> httpx.Response:
            return httpx.Response(200, content=payload)

        client = httpx.Client(transport=httpx.MockTransport(handler))
        dest = updates.download_installer(
            "https://github.com/x/y/releases/download/v1/zerobox_1.0.0_x64-setup.exe",
            tmp_path / "updates",
            client=client,
        )

        assert dest.name == "zerobox_1.0.0_x64-setup.exe"
        assert dest.read_bytes() == payload

    def test_http_error_raises(self, tmp_path):
        def handler(request: httpx.Request) -> httpx.Response:
            return httpx.Response(404)

        client = httpx.Client(transport=httpx.MockTransport(handler))
        with pytest.raises(httpx.HTTPStatusError):
            updates.download_installer("https://github.com/gone.exe", tmp_path, client=client)


class TestLaunchInstaller:
    def test_spawns_detached_process(self, tmp_path):
        installer = tmp_path / "zerobox-setup.exe"
        installer.write_bytes(b"MZ")

        with patch.object(updates.subprocess, "Popen", return_value=MagicMock()) as popen:
            updates.launch_installer(installer)

        popen.assert_called_once()
        assert popen.call_args.args[0] == [str(installer)]
