"""Tests for the dev-uninstall CLI (#81)."""

from __future__ import annotations

import json
from pathlib import Path

import pytest

from zerobox.dev_uninstall import (
    TARGET_DESCRIPTIONS,
    _delete,
    _resolve_targets,
    run,
)


@pytest.fixture
def config_env(tmp_path, monkeypatch):
    monkeypatch.setenv("ZEROBOX_CONFIG_DIR", str(tmp_path))
    return tmp_path


def _write_config(cfg_dir: Path, **paths) -> None:
    (cfg_dir / "config.json").write_text(
        json.dumps(
            {
                "intake": {"input_folder": paths["inbox"]},
                "filemanager": {"output_root": paths["output"]},
                "profiles_dir": paths["profiles"],
                "audit": {"db_path": paths["audit"]},
            }
        )
    )


class TestResolveTargets:
    def test_uses_config_json_paths_when_present(self, config_env, tmp_path):
        data = tmp_path / "data"
        _write_config(
            config_env,
            inbox=str(data / "in"),
            output=str(data / "out"),
            profiles=str(data / "prof"),
            audit=str(data / "audit.db"),
        )
        targets = _resolve_targets()
        assert targets["config"] == config_env / "config.json"
        assert targets["env"] == config_env / ".env"
        assert targets["data-inbox"] == data / "in"
        assert targets["data-output"] == data / "out"
        assert targets["profiles"] == data / "prof"
        assert targets["audit"] == data / "audit.db"

    def test_falls_back_to_defaults_without_config(self, config_env):
        home = Path.home()
        targets = _resolve_targets()
        assert targets["data-inbox"] == home / "zerobox" / "inbox"
        assert targets["data-output"] == home / "zerobox" / "archive"
        assert targets["profiles"] == home / "zerobox" / "profiles"
        assert targets["audit"] == home / "zerobox" / "audit.db"


class TestDelete:
    def test_delete_file(self, tmp_path):
        f = tmp_path / "config.json"
        f.write_text("{}")
        assert _delete(f) is True
        assert not f.exists()

    def test_delete_directory(self, tmp_path):
        d = tmp_path / "profiles"
        d.mkdir()
        (d / "a.json").write_text("{}")
        assert _delete(d) is True
        assert not d.exists()

    def test_delete_missing_returns_false(self, tmp_path):
        assert _delete(tmp_path / "does-not-exist") is False


class TestRun:
    def test_all_yes_deletes_everything_present(self, config_env, tmp_path):
        data = tmp_path / "data"
        data.mkdir()
        _write_config(
            config_env,
            inbox=str(data / "in"),
            output=str(data / "out"),
            profiles=str(data / "prof"),
            audit=str(data / "audit.db"),
        )
        (config_env / ".env").write_text("ANTHROPIC_API_KEY=sk-test")
        for sub in ("in", "out", "prof"):
            (data / sub).mkdir()
            (data / sub / "file.txt").write_text("x")
        (data / "audit.db").write_text("")

        rc = run(["--all", "--yes"])
        assert rc == 0
        assert not (config_env / "config.json").exists()
        assert not (config_env / ".env").exists()
        for sub in ("in", "out", "prof"):
            assert not (data / sub).exists()
        assert not (data / "audit.db").exists()

    def test_single_flag_only_removes_that_target(self, config_env, tmp_path):
        data = tmp_path / "data"
        data.mkdir()
        _write_config(
            config_env,
            inbox=str(data / "in"),
            output=str(data / "out"),
            profiles=str(data / "prof"),
            audit=str(data / "audit.db"),
        )
        (config_env / ".env").write_text("x")
        (data / "in").mkdir()

        rc = run(["--config", "--yes"])
        assert rc == 0
        assert not (config_env / "config.json").exists()
        # Unselected targets untouched
        assert (config_env / ".env").exists()
        assert (data / "in").exists()

    def test_confirm_prompt_aborts_on_no(self, config_env, capsys):
        (config_env / "config.json").write_text("{}")
        rc = run(["--config"], input_fn=lambda _: "n")
        assert rc == 0
        assert (config_env / "config.json").exists()
        assert "Aborted." in capsys.readouterr().out

    def test_confirm_prompt_proceeds_on_yes(self, config_env):
        (config_env / "config.json").write_text("{}")
        rc = run(["--config"], input_fn=lambda _: "y")
        assert rc == 0
        assert not (config_env / "config.json").exists()

    def test_interactive_collects_y_answers(self, config_env):
        (config_env / "config.json").write_text("{}")
        (config_env / ".env").write_text("x")

        answers = iter(
            [
                "y",  # config
                "n",  # env
                "n",  # data-inbox
                "n",  # data-output
                "n",  # profiles
                "n",  # audit
                "y",  # final confirm
            ]
        )
        rc = run([], input_fn=lambda _: next(answers))
        assert rc == 0
        assert not (config_env / "config.json").exists()
        assert (config_env / ".env").exists()

    def test_nothing_selected_exits_cleanly(self, config_env, capsys):
        answers = iter(["n"] * 6)  # decline every interactive question
        rc = run([], input_fn=lambda _: next(answers))
        assert rc == 0
        assert "Nothing selected" in capsys.readouterr().out

    def test_all_targets_have_descriptions(self):
        # Guard against adding a target without documenting it.
        targets = set(_resolve_targets().keys())
        assert targets == set(TARGET_DESCRIPTIONS.keys())
