"""Common BDD fixtures for Zerobox behavioral tests."""

from __future__ import annotations

from pathlib import Path
from unittest.mock import AsyncMock

import pytest

from zerobox.audit.service import AuditService
from zerobox.classifier.models import ClassificationResult
from zerobox.classifier.providers.base import LLMProvider
from zerobox.classifier.service import ClassifierService
from zerobox.config import FileManagerConfig, IntakeConfig
from zerobox.filemanager.service import FileManagerService
from zerobox.intake.service import IntakeService
from zerobox.ocr.models import OcrResult
from zerobox.rules.models import Rule
from zerobox.rules.service import RuleService


# ------------------------------------------------------------------
# Temporary directories
# ------------------------------------------------------------------


@pytest.fixture()
def tmp_inbox(tmp_path: Path) -> Path:
    """Temporary inbox directory for file intake."""
    inbox = tmp_path / "inbox"
    inbox.mkdir()
    return inbox


@pytest.fixture()
def tmp_output(tmp_path: Path) -> Path:
    """Temporary output directory for filed documents."""
    output = tmp_path / "output"
    output.mkdir()
    return output


@pytest.fixture()
def tmp_profiles(tmp_path: Path) -> Path:
    """Temporary profiles directory for rule profiles."""
    profiles = tmp_path / "profiles"
    profiles.mkdir()
    return profiles


# ------------------------------------------------------------------
# Services
# ------------------------------------------------------------------


@pytest.fixture()
def audit_service(tmp_path: Path) -> AuditService:
    """AuditService backed by a temporary SQLite database."""
    return AuditService(tmp_path / "audit.db")


@pytest.fixture()
def intake_config(tmp_inbox: Path) -> IntakeConfig:
    """IntakeConfig pointing to a temporary inbox."""
    return IntakeConfig(input_folder=tmp_inbox, file_types=[".pdf"])


@pytest.fixture()
def intake_service(intake_config: IntakeConfig, audit_service: AuditService) -> IntakeService:
    """IntakeService wired to the tmp inbox and audit."""
    return IntakeService(intake_config, audit_service)


@pytest.fixture()
def rule_service(tmp_profiles: Path, audit_service: AuditService) -> RuleService:
    """RuleService wired to a temporary profiles directory."""
    return RuleService(tmp_profiles, audit_service)


@pytest.fixture()
def filemanager_config(tmp_output: Path) -> FileManagerConfig:
    """FileManagerConfig pointing to a temporary output root."""
    return FileManagerConfig(output_root=tmp_output, conflict_strategy="rename")


@pytest.fixture()
def filemanager_service(
    filemanager_config: FileManagerConfig,
    audit_service: AuditService,
) -> FileManagerService:
    """FileManagerService wired to tmp output and audit."""
    return FileManagerService(filemanager_config, audit_service)


# ------------------------------------------------------------------
# Mock LLM provider
# ------------------------------------------------------------------


class MockLLMProvider(LLMProvider):
    """Deterministic LLM provider for testing — returns fixed classification results."""

    async def classify(
        self,
        text: str,
        rules: list[Rule],
        context: object,
    ) -> ClassificationResult:
        return ClassificationResult(
            proposed_name="classified_doc.pdf",
            proposed_folder="Documents/Classified",
            confidence=0.92,
            matched_rule_id=rules[0].id if rules else None,
            reasoning="Mock classification",
        )

    async def extract_rule(self, text: str, correction: object) -> Rule:
        return Rule(
            id="mock-rule",
            profile_id="",
            patterns=["mock"],
            target_name_template="{date}_mock",
            target_folder_template="Mock/Folder",
        )


@pytest.fixture()
def mock_llm_provider() -> MockLLMProvider:
    """A deterministic mock LLM provider."""
    return MockLLMProvider()


@pytest.fixture()
def classifier_service(
    mock_llm_provider: MockLLMProvider,
    rule_service: RuleService,
    audit_service: AuditService,
) -> ClassifierService:
    """ClassifierService using the mock LLM provider."""
    return ClassifierService(mock_llm_provider, rule_service, audit_service)


# ------------------------------------------------------------------
# Mock OCR service
# ------------------------------------------------------------------


class MockOcrService:
    """Deterministic OCR service that returns fixed text for any file."""

    FIXED_TEXT = "Rechnung Nr. 12345 von Stadtwerke GmbH vom 01.01.2026"

    async def process(self, file: object) -> OcrResult:
        return OcrResult(
            source_path=file.path,
            output_path=file.path.with_suffix(".ocr.pdf"),
            text=self.FIXED_TEXT,
            language="deu+eng",
            pages=1,
            success=True,
        )

    async def process_batch(self, files: list) -> list[OcrResult]:
        results = []
        for f in files:
            results.append(await self.process(f))
        return results


@pytest.fixture()
def mock_ocr_service() -> MockOcrService:
    """A deterministic mock OCR service."""
    return MockOcrService()
