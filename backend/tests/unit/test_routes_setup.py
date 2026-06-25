"""Tests for the /setup endpoints (First-Run-Wizard API)."""

from __future__ import annotations

import json
from pathlib import Path
from unittest.mock import patch

import pytest
from fastapi.testclient import TestClient

from zerobox.api.routes.setup import _find_executable
from zerobox.app import create_app


@pytest.fixture
def client(tmp_path, monkeypatch):
    """Create a test client with a temporary config directory.

    Points `$ZEROBOX_CONFIG_DIR` at `tmp_path` so `config.json` / `.env`
    writes/reads stay isolated (see DD-07).
    """
    monkeypatch.setenv("ZEROBOX_CONFIG_DIR", str(tmp_path))
    app = create_app()
    return TestClient(app)


class TestFindExecutable:
    def test_returns_path_hit_when_on_path(self, monkeypatch):
        monkeypatch.setattr(
            "zerobox.api.routes.setup.shutil.which",
            lambda _: r"C:\some\path\tesseract.exe",
        )
        result = _find_executable("tesseract")
        assert result == r"C:\some\path\tesseract.exe"

    def test_falls_back_to_well_known_glob_when_not_on_path(
        self, tmp_path, monkeypatch
    ):
        exe = tmp_path / "Tesseract-OCR" / "tesseract.exe"
        exe.parent.mkdir()
        exe.write_text("")
        monkeypatch.setattr("zerobox.api.routes.setup.shutil.which", lambda _: None)
        result = _find_executable(
            "tesseract",
            well_known_globs=[str(tmp_path / "Tesseract-OCR" / "tesseract.exe")],
        )
        assert result == str(exe)

    def test_glob_matches_versioned_install(self, tmp_path, monkeypatch):
        bin_dir = tmp_path / "gs" / "gs10.07.0" / "bin"
        bin_dir.mkdir(parents=True)
        exe = bin_dir / "gswin64c.exe"
        exe.write_text("")
        monkeypatch.setattr("zerobox.api.routes.setup.shutil.which", lambda _: None)
        result = _find_executable(
            "gswin64c",
            well_known_globs=[str(tmp_path / "gs" / "gs*" / "bin" / "gswin64c.exe")],
        )
        assert result == str(exe)

    def test_returns_none_when_nothing_found(self, tmp_path, monkeypatch):
        monkeypatch.setattr("zerobox.api.routes.setup.shutil.which", lambda _: None)
        result = _find_executable(
            "tesseract",
            well_known_globs=[str(tmp_path / "does-not-exist" / "tesseract.exe")],
        )
        assert result is None

    def test_portable_takes_priority_over_path(self, tmp_path, monkeypatch):
        portable = tmp_path / "resources" / "tesseract" / "tesseract.exe"
        portable.parent.mkdir(parents=True)
        portable.write_text("")
        monkeypatch.setattr(
            "zerobox.api.routes.setup._resources_dir",
            lambda: tmp_path / "resources",
        )
        monkeypatch.setattr(
            "zerobox.api.routes.setup.shutil.which",
            lambda _: r"C:\different\path\tesseract.exe",
        )
        result = _find_executable("tesseract", "tesseract/tesseract.exe")
        assert result == str(portable)


class TestGetStatus:
    def test_returns_setup_status(self, client):
        resp = client.get("/setup/status")
        assert resp.status_code == 200
        data = resp.json()
        assert "setup_complete" in data
        assert "has_config" in data
        assert "has_env" in data
        assert "tesseract_available" in data
        assert "ghostscript_available" in data

    def test_no_config_means_not_complete(self, client):
        resp = client.get("/setup/status")
        data = resp.json()
        assert data["setup_complete"] is False
        assert data["has_config"] is False

    def test_config_without_flag_means_not_complete(self, client, tmp_path):
        (tmp_path / "config.json").write_text('{"intake": {}}')
        resp = client.get("/setup/status")
        data = resp.json()
        assert data["has_config"] is True
        assert data["setup_complete"] is False

    def test_config_with_flag_means_complete(self, client, tmp_path):
        (tmp_path / "config.json").write_text('{"setup_complete": true}')
        resp = client.get("/setup/status")
        data = resp.json()
        assert data["setup_complete"] is True


class TestValidate:
    def test_anthropic_without_key_fails(self, client):
        resp = client.post(
            "/setup/validate",
            json={"provider": "anthropic", "api_key": ""},
        )
        data = resp.json()
        assert data["provider_ok"] is False
        assert "required" in data["provider_error"].lower()

    def test_openai_without_key_fails(self, client):
        resp = client.post(
            "/setup/validate",
            json={"provider": "openai", "api_key": ""},
        )
        data = resp.json()
        assert data["provider_ok"] is False
        assert "required" in data["provider_error"].lower()

    def test_ollama_unreachable(self, client):
        resp = client.post(
            "/setup/validate",
            json={
                "provider": "ollama",
                "ollama_base_url": "http://localhost:99999",
            },
        )
        data = resp.json()
        assert data["provider_ok"] is False
        assert data["provider_error"] is not None


class TestSaveConfig:
    def test_creates_config_and_env(self, client, tmp_path):
        resp = client.post(
            "/setup/save",
            json={
                "input_folder": str(tmp_path / "inbox"),
                "output_root": str(tmp_path / "archive"),
                "profiles_dir": str(tmp_path / "profiles"),
                "language": "deu+eng",
                "provider": "anthropic",
                "api_key": "sk-ant-test",
            },
        )
        assert resp.status_code == 200
        data = resp.json()
        assert data["status"] == "ok"

        config = json.loads((tmp_path / "config.json").read_text())
        assert config["setup_complete"] is True
        assert config["intake"]["input_folder"] == str(tmp_path / "inbox")
        assert config["llm"]["provider"] == "anthropic"

        env = (tmp_path / ".env").read_text()
        assert "ANTHROPIC_API_KEY=sk-ant-test" in env

    def test_creates_directories(self, client, tmp_path):
        inbox = tmp_path / "inbox"
        archive = tmp_path / "archive"
        profiles = tmp_path / "profiles"

        client.post(
            "/setup/save",
            json={
                "input_folder": str(inbox),
                "output_root": str(archive),
                "profiles_dir": str(profiles),
            },
        )

        assert inbox.is_dir()
        assert archive.is_dir()
        assert profiles.is_dir()

    def test_ollama_writes_base_url(self, client, tmp_path):
        client.post(
            "/setup/save",
            json={
                "input_folder": str(tmp_path / "inbox"),
                "output_root": str(tmp_path / "archive"),
                "profiles_dir": str(tmp_path / "profiles"),
                "provider": "ollama",
                "ollama_base_url": "http://myhost:11434",
            },
        )

        env = (tmp_path / ".env").read_text()
        assert "OLLAMA_BASE_URL=http://myhost:11434" in env

    def test_save_expands_tilde_paths_instead_of_creating_literal_dir(
        self, client, tmp_path, monkeypatch
    ):
        """Regression for #75: paths with `~` must be expanded before mkdir,
        otherwise a literal `~` directory is created in the backend CWD."""
        # Pretend $HOME points into the test tmp_path so we don't pollute the
        # real user home with test directories.
        monkeypatch.setenv("USERPROFILE", str(tmp_path / "home"))  # Windows
        monkeypatch.setenv("HOME", str(tmp_path / "home"))  # POSIX fallback

        resp = client.post(
            "/setup/save",
            json={
                "input_folder": "~/zerobox/inbox",
                "output_root": "~/zerobox/archive",
                "profiles_dir": "~/zerobox/profiles",
                "provider": "anthropic",
                "api_key": "sk-ant-test",
            },
        )
        assert resp.status_code == 200

        # No literal `~` directory should have been created in the CWD.
        assert not (tmp_path / "~").exists()

        # The expanded directories should exist under the patched home.
        for sub in ("inbox", "archive", "profiles"):
            assert (tmp_path / "home" / "zerobox" / sub).is_dir()

    def test_get_config_does_not_leak_api_keys(self, client, tmp_path):
        """Regression for #74: /config response must mask secrets."""
        client.post(
            "/setup/save",
            json={
                "input_folder": str(tmp_path / "inbox"),
                "output_root": str(tmp_path / "archive"),
                "profiles_dir": str(tmp_path / "profiles"),
                "provider": "anthropic",
                "api_key": "sk-ant-supersecret-value",
            },
        )

        config_resp = client.get("/config")
        assert config_resp.status_code == 200
        body = config_resp.text
        assert "sk-ant-supersecret-value" not in body
        config = config_resp.json()
        assert config["anthropic_api_key"] == "**********"

    def test_save_makes_get_config_reflect_new_values(self, client, tmp_path):
        """Regression test for #72: wizard save must invalidate the cached
        config so the next /config (and pipeline services) see the new values,
        not the defaults captured at startup."""
        resp = client.post(
            "/setup/save",
            json={
                "input_folder": str(tmp_path / "inbox"),
                "output_root": str(tmp_path / "archive"),
                "profiles_dir": str(tmp_path / "profiles"),
                "language": "deu+eng+rus",
                "provider": "anthropic",
                "api_key": "sk-ant-test",
            },
        )
        assert resp.status_code == 200

        config_resp = client.get("/config")
        assert config_resp.status_code == 200
        config = config_resp.json()
        assert config["ocr"]["language"] == "deu+eng+rus"
        assert config["filemanager"]["output_root"].endswith("archive")
        assert config["intake"]["input_folder"].endswith("inbox")
