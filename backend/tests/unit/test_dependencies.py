"""Tests for FastAPI dependency injection wiring (#15)."""

from unittest.mock import patch

import pytest

from zerobox.api.dependencies import (
    _CACHED_GETTERS,
    get_audit,
    get_classifier,
    get_config,
    get_filemanager,
    get_intake,
    get_ocr,
    get_pipeline,
    get_provider,
    get_rules,
    reload_config,
)
from zerobox.audit.service import AuditService
from zerobox.classifier.service import ClassifierService
from zerobox.config import (
    AppConfig,
    AuditConfig,
    FileManagerConfig,
    IntakeConfig,
)
from zerobox.filemanager.service import FileManagerService
from zerobox.intake.service import IntakeService
from zerobox.ocr.service import OcrService
from zerobox.pipeline.service import PipelineService
from zerobox.rules.service import RuleService

ALL_CACHED_FNS = [
    get_config,
    get_audit,
    get_intake,
    get_ocr,
    get_rules,
    get_provider,
    get_classifier,
    get_filemanager,
    get_pipeline,
]


@pytest.fixture(autouse=True)
def clear_caches():
    """Clear lru_cache between tests to prevent state leaking."""
    yield
    for fn in ALL_CACHED_FNS:
        fn.cache_clear()


def _make_config(tmp_path):
    """Return an AppConfig with all paths pointing into tmp_path."""
    return AppConfig(
        intake=IntakeConfig(input_folder=tmp_path / "inbox"),
        audit=AuditConfig(db_path=tmp_path / "audit.db"),
        filemanager=FileManagerConfig(output_root=tmp_path / "archive"),
        profiles_dir=tmp_path / "profiles",
    )


@pytest.fixture()
def mock_config(tmp_path):
    """Patch load_config to return a tmp_path-based config."""
    config = _make_config(tmp_path)
    with patch("zerobox.api.dependencies.load_config", return_value=config):
        yield config


# ── get_config ──────────────────────────────────────────────────────


def test_get_config_returns_app_config(mock_config):
    result = get_config()
    assert isinstance(result, AppConfig)


# ── get_audit ───────────────────────────────────────────────────────


def test_get_audit_returns_audit_service(mock_config):
    result = get_audit()
    assert isinstance(result, AuditService)


# ── get_intake ──────────────────────────────────────────────────────


def test_get_intake_returns_intake_service(mock_config):
    result = get_intake()
    assert isinstance(result, IntakeService)


# ── get_ocr ─────────────────────────────────────────────────────────


def test_get_ocr_returns_ocr_service(mock_config):
    result = get_ocr()
    assert isinstance(result, OcrService)


# ── get_rules ───────────────────────────────────────────────────────


def test_get_rules_returns_rule_service(mock_config):
    result = get_rules()
    assert isinstance(result, RuleService)


# ── get_filemanager ─────────────────────────────────────────────────


def test_get_filemanager_returns_file_manager_service(mock_config):
    result = get_filemanager()
    assert isinstance(result, FileManagerService)


# ── get_pipeline ────────────────────────────────────────────────────


def test_get_pipeline_returns_pipeline_service(mock_config):
    with patch(
        "zerobox.api.dependencies.create_provider",
    ):
        result = get_pipeline()
    assert isinstance(result, PipelineService)


# ── lru_cache returns same instance ────────────────────────────────


def test_lru_cache_returns_same_instance(mock_config):
    config_a = get_config()
    config_b = get_config()
    assert config_a is config_b

    audit_a = get_audit()
    audit_b = get_audit()
    assert audit_a is audit_b


# ── reload_config invalidates cached getters ───────────────────────


def test_reload_config_clears_all_cached_getters(mock_config):
    # Prime every cache so each getter has an entry to clear.
    with patch("zerobox.api.dependencies.create_provider"):
        for getter in _CACHED_GETTERS:
            getter()
        for getter in _CACHED_GETTERS:
            assert getter.cache_info().currsize == 1, f"{getter.__name__} not primed"

        reload_config()

        for getter in _CACHED_GETTERS:
            assert getter.cache_info().currsize == 0, (
                f"{getter.__name__} cache not cleared"
            )


def test_reload_config_makes_next_get_config_see_new_disk_state(
    tmp_path, monkeypatch
):
    """/setup/save writes config.json and then calls reload_config();
    the next get_config() call must reflect the new file."""
    monkeypatch.setenv("ZEROBOX_CONFIG_DIR", str(tmp_path))
    reload_config()  # start from a clean cache

    (tmp_path / "config.json").write_text(
        '{"ocr": {"language": "deu+eng+rus"}}'
    )
    first = get_config()
    assert first.ocr.language == "deu+eng+rus"

    # Overwrite with a different value, then reload.
    (tmp_path / "config.json").write_text(
        '{"ocr": {"language": "fra+ita"}}'
    )
    # Without reload_config(), the cached value would still be deu+eng+rus.
    assert get_config().ocr.language == "deu+eng+rus"

    reload_config()
    assert get_config().ocr.language == "fra+ita"
