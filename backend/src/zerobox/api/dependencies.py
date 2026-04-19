"""FastAPI dependency injection wiring (#15)."""

from functools import lru_cache

from zerobox.audit.service import AuditService
from zerobox.classifier.providers import create_provider
from zerobox.classifier.providers.base import LLMProvider
from zerobox.classifier.service import ClassifierService
from zerobox.config import AppConfig, load_config
from zerobox.filemanager.service import FileManagerService
from zerobox.intake.service import IntakeService
from zerobox.ocr.service import OcrService
from zerobox.pipeline.service import PipelineService
from zerobox.rules.service import RuleService


@lru_cache
def get_config() -> AppConfig:
    return load_config()


@lru_cache
def get_audit() -> AuditService:
    config = get_config()
    return AuditService(config.audit.db_path)


@lru_cache
def get_intake() -> IntakeService:
    return IntakeService(get_config().intake, get_audit())


@lru_cache
def get_ocr() -> OcrService:
    config = get_config()
    return OcrService(
        config.ocr,
        output_dir=config.intake.input_folder.parent / "ocr_output",
        audit=get_audit(),
    )


@lru_cache
def get_rules() -> RuleService:
    return RuleService(get_config().profiles_dir, get_audit())


@lru_cache
def get_provider() -> LLMProvider:
    return create_provider(get_config().llm)


@lru_cache
def get_classifier() -> ClassifierService:
    return ClassifierService(get_provider(), get_rules(), get_audit())


@lru_cache
def get_filemanager() -> FileManagerService:
    return FileManagerService(get_config().filemanager, get_audit())


@lru_cache
def get_pipeline() -> PipelineService:
    return PipelineService(
        get_intake(), get_ocr(), get_classifier(), get_filemanager(), get_audit()
    )


_CACHED_GETTERS = (
    get_config,
    get_audit,
    get_intake,
    get_ocr,
    get_rules,
    get_provider,
    get_classifier,
    get_filemanager,
    get_pipeline,
)


def reload_config() -> None:
    """Invalidate every cached getter so the next call rebuilds from `config.json` / `.env`.

    Call this after `config.json` or `.env` is written (e.g. from the wizard's
    `/setup/save` handler) so subsequent `/config` reads and pipeline calls
    reflect the new values without a process restart.
    """
    for getter in _CACHED_GETTERS:
        getter.cache_clear()
