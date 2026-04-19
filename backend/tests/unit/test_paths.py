"""Tests for config-dir resolution (#80 / DD-07)."""

from __future__ import annotations

from pathlib import Path

import pytest

from zerobox.paths import CONFIG_DIR_ENV, config_dir, config_file, env_file


class TestConfigDirResolution:
    def test_zerobox_config_dir_env_overrides_everything(
        self, tmp_path, monkeypatch
    ) -> None:
        monkeypatch.setenv(CONFIG_DIR_ENV, str(tmp_path / "custom"))
        # Even with a platform-specific env var present, the override wins.
        monkeypatch.setenv("APPDATA", str(tmp_path / "roaming"))
        monkeypatch.setenv("XDG_CONFIG_HOME", str(tmp_path / "xdg"))
        monkeypatch.setattr("zerobox.paths.sys.platform", "win32")
        assert config_dir() == tmp_path / "custom"

    def test_windows_uses_appdata(self, tmp_path, monkeypatch) -> None:
        monkeypatch.delenv(CONFIG_DIR_ENV, raising=False)
        monkeypatch.setenv("APPDATA", str(tmp_path / "roaming"))
        monkeypatch.setattr("zerobox.paths.sys.platform", "win32")
        assert config_dir() == tmp_path / "roaming" / "zerobox"

    def test_windows_without_appdata_falls_back_to_dot_zerobox(
        self, tmp_path, monkeypatch
    ) -> None:
        monkeypatch.delenv(CONFIG_DIR_ENV, raising=False)
        monkeypatch.delenv("APPDATA", raising=False)
        monkeypatch.setattr("zerobox.paths.sys.platform", "win32")
        assert config_dir() == Path.home() / ".zerobox"

    def test_macos_uses_application_support(self, monkeypatch) -> None:
        monkeypatch.delenv(CONFIG_DIR_ENV, raising=False)
        monkeypatch.setattr("zerobox.paths.sys.platform", "darwin")
        assert (
            config_dir()
            == Path.home() / "Library" / "Application Support" / "zerobox"
        )

    def test_linux_uses_xdg_config_home_when_set(
        self, tmp_path, monkeypatch
    ) -> None:
        monkeypatch.delenv(CONFIG_DIR_ENV, raising=False)
        monkeypatch.setenv("XDG_CONFIG_HOME", str(tmp_path / "xdg"))
        monkeypatch.setattr("zerobox.paths.sys.platform", "linux")
        assert config_dir() == tmp_path / "xdg" / "zerobox"

    def test_linux_falls_back_to_dot_config_when_xdg_absent(
        self, monkeypatch
    ) -> None:
        monkeypatch.delenv(CONFIG_DIR_ENV, raising=False)
        monkeypatch.delenv("XDG_CONFIG_HOME", raising=False)
        monkeypatch.setattr("zerobox.paths.sys.platform", "linux")
        assert config_dir() == Path.home() / ".config" / "zerobox"

    def test_config_file_lives_in_config_dir(self, tmp_path, monkeypatch) -> None:
        monkeypatch.setenv(CONFIG_DIR_ENV, str(tmp_path))
        assert config_file() == tmp_path / "config.json"

    def test_env_file_lives_in_config_dir(self, tmp_path, monkeypatch) -> None:
        monkeypatch.setenv(CONFIG_DIR_ENV, str(tmp_path))
        assert env_file() == tmp_path / ".env"
