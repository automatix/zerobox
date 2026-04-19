"""Tests for path expansion (#75) and secret masking (#74) in config."""

from __future__ import annotations

import json
from pathlib import Path

from pydantic import SecretStr

from zerobox.config import (
    AppConfig,
    AuditConfig,
    FileManagerConfig,
    IntakeConfig,
    OcrConfig,
    load_config,
)


HOME = Path.home()


class TestPathExpansion:
    def test_intake_input_folder_expands_tilde(self) -> None:
        cfg = IntakeConfig(input_folder="~/zerobox/inbox")
        assert cfg.input_folder == HOME / "zerobox" / "inbox"
        assert "~" not in str(cfg.input_folder)

    def test_filemanager_output_root_expands_tilde(self) -> None:
        cfg = FileManagerConfig(output_root="~/zerobox/archive")
        assert cfg.output_root == HOME / "zerobox" / "archive"

    def test_audit_db_path_expands_tilde(self) -> None:
        cfg = AuditConfig(db_path="~/zerobox/audit.db")
        assert cfg.db_path == HOME / "zerobox" / "audit.db"

    def test_ocr_optional_paths_expand_tilde(self) -> None:
        cfg = OcrConfig(
            tesseract_path="~/tools/tesseract.exe",
            ghostscript_path="~/tools/gs.exe",
        )
        assert cfg.tesseract_path == HOME / "tools" / "tesseract.exe"
        assert cfg.ghostscript_path == HOME / "tools" / "gs.exe"

    def test_ocr_optional_paths_keep_none(self) -> None:
        cfg = OcrConfig()
        assert cfg.tesseract_path is None
        assert cfg.ghostscript_path is None

    def test_app_profiles_dir_expands_tilde(self) -> None:
        cfg = AppConfig(profiles_dir="~/zerobox/profiles")
        assert cfg.profiles_dir == HOME / "zerobox" / "profiles"


class TestSecretMasking:
    def test_api_keys_are_secret_str(self) -> None:
        cfg = AppConfig(
            anthropic_api_key="sk-ant-secret",
            openai_api_key="sk-openai-secret",
        )
        assert isinstance(cfg.anthropic_api_key, SecretStr)
        assert isinstance(cfg.openai_api_key, SecretStr)
        assert cfg.anthropic_api_key.get_secret_value() == "sk-ant-secret"
        assert cfg.openai_api_key.get_secret_value() == "sk-openai-secret"

    def test_model_dump_json_masks_api_keys(self) -> None:
        cfg = AppConfig(
            anthropic_api_key="sk-ant-secret-value",
            openai_api_key="sk-openai-secret-value",
        )
        dumped = cfg.model_dump(mode="json")
        assert "sk-ant-secret-value" not in json.dumps(dumped)
        assert "sk-openai-secret-value" not in json.dumps(dumped)
        assert dumped["anthropic_api_key"] == "**********"
        assert dumped["openai_api_key"] == "**********"

    def test_repr_masks_api_keys(self) -> None:
        cfg = AppConfig(anthropic_api_key="sk-ant-leaks-in-stack-traces")
        assert "sk-ant-leaks-in-stack-traces" not in repr(cfg)


class TestLoadConfigExpansion:
    def test_load_config_expands_all_paths_from_json(
        self, tmp_path, monkeypatch
    ) -> None:
        """Regression for #75: every Path field with `~` must be expanded
        on load, so consumers never see literal `~` paths."""
        monkeypatch.chdir(tmp_path)
        (tmp_path / "config.json").write_text(
            json.dumps(
                {
                    "intake": {"input_folder": "~/zerobox/inbox"},
                    "ocr": {
                        "language": "deu+eng",
                        "tesseract_path": "~/tools/tesseract.exe",
                    },
                    "filemanager": {"output_root": "~/zerobox/archive"},
                    "audit": {"db_path": "~/zerobox/audit.db"},
                    "profiles_dir": "~/zerobox/profiles",
                }
            )
        )
        cfg = load_config()

        assert cfg.intake.input_folder == HOME / "zerobox" / "inbox"
        assert cfg.ocr.tesseract_path == HOME / "tools" / "tesseract.exe"
        assert cfg.filemanager.output_root == HOME / "zerobox" / "archive"
        assert cfg.audit.db_path == HOME / "zerobox" / "audit.db"
        assert cfg.profiles_dir == HOME / "zerobox" / "profiles"

        for path_str in (
            str(cfg.intake.input_folder),
            str(cfg.filemanager.output_root),
            str(cfg.audit.db_path),
            str(cfg.profiles_dir),
            str(cfg.ocr.tesseract_path),
        ):
            assert "~" not in path_str
