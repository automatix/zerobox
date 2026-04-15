"""Tests for the /setup endpoints (First-Run-Wizard API)."""

from __future__ import annotations

import json
from pathlib import Path
from unittest.mock import patch

import pytest
from fastapi.testclient import TestClient

from zerobox.app import create_app


@pytest.fixture
def client(tmp_path, monkeypatch):
    """Create a test client with a temporary config directory."""
    monkeypatch.chdir(tmp_path)
    app = create_app()
    return TestClient(app)


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
