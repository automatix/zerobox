"""Unit tests for the classifier service."""

from __future__ import annotations

from datetime import datetime
from pathlib import Path
from unittest.mock import AsyncMock, MagicMock

import pytest

from zerobox.classifier.models import ClassificationResult, Proposal, UserCorrection
from zerobox.classifier.service import ClassifierService
from zerobox.intake.models import IntakeFile
from zerobox.rules.models import Rule


# ── Fixtures ────────────────────────────────────────────────────────


def _make_intake_file(name: str = "scan_001.pdf") -> IntakeFile:
    return IntakeFile(
        path=Path(f"/tmp/intake/{name}"),
        file_type="pdf",
        size_bytes=12345,
        modified_at=datetime(2026, 1, 15, 10, 30),
    )


def _make_result(**overrides) -> ClassificationResult:
    defaults = {
        "proposed_name": "2026-01-15_Invoice_Acme.pdf",
        "proposed_folder": "Finance/Invoices",
        "confidence": 0.92,
        "matched_rule_id": "rule-1",
        "reasoning": "Matched invoice pattern",
    }
    defaults.update(overrides)
    return ClassificationResult(**defaults)


def _make_correction(**overrides) -> UserCorrection:
    defaults = {
        "original_text": "invoice text",
        "original_proposal_name": "scan_001.pdf",
        "original_proposal_folder": "Unsorted",
        "corrected_name": "2026-01-15_Invoice_Acme.pdf",
        "corrected_folder": "Finance/Invoices",
    }
    defaults.update(overrides)
    return UserCorrection(**defaults)


def _make_rule(rule_id: str = "rule-1") -> Rule:
    return Rule(
        id=rule_id,
        profile_id="default",
        patterns=["invoice"],
        target_name_template="{date}_{type}_{sender}",
        target_folder_template="Finance/Invoices",
    )


@pytest.fixture
def mock_provider() -> AsyncMock:
    provider = AsyncMock()
    provider.classify.return_value = _make_result()
    return provider


@pytest.fixture
def mock_rules() -> MagicMock:
    rules = MagicMock()
    rules.match_rules.return_value = [_make_rule()]
    return rules


@pytest.fixture
def mock_audit() -> MagicMock:
    return MagicMock()


@pytest.fixture
def service(mock_provider, mock_rules) -> ClassifierService:
    return ClassifierService(provider=mock_provider, rules=mock_rules)


@pytest.fixture
def service_with_audit(mock_provider, mock_rules, mock_audit) -> ClassifierService:
    return ClassifierService(provider=mock_provider, rules=mock_rules, audit=mock_audit)


# ── Tests ───────────────────────────────────────────────────────────


@pytest.mark.asyncio
async def test_classify_returns_proposal_with_correct_fields(service, mock_provider):
    file = _make_intake_file()
    proposal = await service.classify("invoice text", file)

    assert isinstance(proposal, Proposal)
    assert proposal.original_path == file.path
    assert proposal.original_name == "scan_001.pdf"
    assert proposal.proposed_name == "2026-01-15_Invoice_Acme.pdf"
    assert proposal.proposed_folder == Path("Finance/Invoices")
    assert proposal.confidence == 0.92
    assert proposal.matched_rule == "rule-1"


@pytest.mark.asyncio
async def test_classify_passes_matched_rules_to_provider(service, mock_provider, mock_rules):
    file = _make_intake_file()
    await service.classify("invoice text", file)

    mock_rules.match_rules.assert_called_once_with("invoice text")
    call_args = mock_provider.classify.call_args
    rules_arg = call_args[0][1]
    assert len(rules_arg) == 1
    assert rules_arg[0].id == "rule-1"


@pytest.mark.asyncio
async def test_classify_with_no_matching_rules(service, mock_provider, mock_rules):
    mock_rules.match_rules.return_value = []
    file = _make_intake_file()
    await service.classify("unknown text", file)

    call_args = mock_provider.classify.call_args
    rules_arg = call_args[0][1]
    assert rules_arg == []


@pytest.mark.asyncio
async def test_classify_generates_unique_ids(service):
    file = _make_intake_file()
    p1 = await service.classify("text a", file)
    p2 = await service.classify("text b", file)

    assert p1.id != p2.id
    assert len(p1.id) == 12
    assert len(p2.id) == 12


@pytest.mark.asyncio
async def test_classify_logs_to_audit_service(service_with_audit, mock_audit):
    file = _make_intake_file()
    proposal = await service_with_audit.classify("invoice text", file)

    mock_audit.log.assert_called_once()
    call_kwargs = mock_audit.log.call_args[1]
    assert call_kwargs["action"] == "classified"
    assert call_kwargs["source"] == str(file.path)
    assert call_kwargs["details"]["proposal_id"] == proposal.id
    assert call_kwargs["details"]["proposed_name"] == proposal.proposed_name


@pytest.mark.asyncio
async def test_classify_without_audit_service_works(service):
    file = _make_intake_file()
    proposal = await service.classify("invoice text", file)

    assert isinstance(proposal, Proposal)
    assert proposal.proposed_name == "2026-01-15_Invoice_Acme.pdf"


@pytest.mark.asyncio
async def test_classify_batch_processes_multiple_files(service):
    pairs = [
        ("text a", _make_intake_file("a.pdf")),
        ("text b", _make_intake_file("b.pdf")),
        ("text c", _make_intake_file("c.pdf")),
    ]
    proposals = await service.classify_batch(pairs)

    assert len(proposals) == 3
    assert all(isinstance(p, Proposal) for p in proposals)


@pytest.mark.asyncio
async def test_classify_batch_continues_on_single_failure(service, mock_provider):
    mock_provider.classify.side_effect = [
        _make_result(),
        RuntimeError("LLM timeout"),
        _make_result(),
    ]
    pairs = [
        ("text a", _make_intake_file("a.pdf")),
        ("text b", _make_intake_file("b.pdf")),
        ("text c", _make_intake_file("c.pdf")),
    ]
    proposals = await service.classify_batch(pairs)

    assert len(proposals) == 2
    assert proposals[0].original_name == "a.pdf"
    assert proposals[1].original_name == "c.pdf"


@pytest.mark.asyncio
async def test_proposal_status_is_always_pending(service):
    file = _make_intake_file()
    proposal = await service.classify("some text", file)

    assert proposal.status == "pending"


# ── learn_from_correction tests ────────────────────────────────────


@pytest.mark.asyncio
async def test_learn_from_correction_returns_rule(service, mock_provider):
    mock_provider.extract_rule.return_value = _make_rule("new-rule")
    correction = _make_correction()

    result = await service.learn_from_correction("invoice text", correction, "default")

    assert isinstance(result, Rule)
    assert result.id == "new-rule"


@pytest.mark.asyncio
async def test_learn_from_correction_calls_provider_extract_rule(service, mock_provider):
    mock_provider.extract_rule.return_value = _make_rule("new-rule")
    correction = _make_correction()

    await service.learn_from_correction("invoice text", correction, "default")

    mock_provider.extract_rule.assert_called_once_with("invoice text", correction)


@pytest.mark.asyncio
async def test_learn_from_correction_sets_profile_id(service, mock_provider):
    rule = _make_rule("new-rule")
    rule.profile_id = "wrong-profile"
    mock_provider.extract_rule.return_value = rule
    correction = _make_correction()

    result = await service.learn_from_correction("invoice text", correction, "target-profile")

    assert result.profile_id == "target-profile"


@pytest.mark.asyncio
async def test_learn_from_correction_persists_rule(service, mock_provider, mock_rules):
    rule = _make_rule("new-rule")
    mock_provider.extract_rule.return_value = rule
    correction = _make_correction()

    await service.learn_from_correction("invoice text", correction, "default")

    mock_rules.add_rule.assert_called_once_with("default", rule)


@pytest.mark.asyncio
async def test_learn_from_correction_logs_to_audit(
    service_with_audit, mock_provider, mock_audit,
):
    mock_provider.extract_rule.return_value = _make_rule("new-rule")
    correction = _make_correction()

    await service_with_audit.learn_from_correction("invoice text", correction, "default")

    mock_audit.log.assert_called_once()
    call_kwargs = mock_audit.log.call_args[1]
    assert call_kwargs["action"] == "rule_learned"
    assert call_kwargs["source"] == "default"
    assert call_kwargs["details"]["profile_id"] == "default"
    assert call_kwargs["details"]["rule_id"] == "new-rule"
    assert "scan_001.pdf" in call_kwargs["details"]["correction"]
    assert "2026-01-15_Invoice_Acme.pdf" in call_kwargs["details"]["correction"]


@pytest.mark.asyncio
async def test_learn_from_correction_without_audit_works(service, mock_provider):
    mock_provider.extract_rule.return_value = _make_rule("new-rule")
    correction = _make_correction()

    result = await service.learn_from_correction("invoice text", correction, "default")

    assert isinstance(result, Rule)
    assert result.id == "new-rule"
