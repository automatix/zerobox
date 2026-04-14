"""Unit tests for the Anthropic LLM provider (T-08)."""

from __future__ import annotations

from pathlib import Path
from unittest.mock import AsyncMock, MagicMock, patch

import pytest

from zerobox.classifier.models import ClassificationContext, ClassificationResult, UserCorrection
from zerobox.classifier.providers import _PROVIDERS
from zerobox.config import LLMConfig
from zerobox.rules.models import Rule


# ---------------------------------------------------------------------------
# Helpers
# ---------------------------------------------------------------------------

def _make_config(**overrides) -> LLMConfig:
    defaults = {"provider": "anthropic", "model": "claude-sonnet-4-20250514", "temperature": 0.0}
    defaults.update(overrides)
    return LLMConfig(**defaults)


def _make_context() -> ClassificationContext:
    return ClassificationContext(
        original_path=Path("/inbox/scan001.pdf"),
        original_name="scan001.pdf",
        file_type=".pdf",
    )


def _make_correction() -> UserCorrection:
    return UserCorrection(
        original_text="Invoice from Acme Corp",
        original_proposal_name="document",
        original_proposal_folder="Unsorted",
        corrected_name="2024-01_invoice_acme",
        corrected_folder="Finance/Invoices",
    )


def _mock_response(text: str) -> MagicMock:
    content_block = MagicMock()
    content_block.text = text
    response = MagicMock()
    response.content = [content_block]
    return response


def _make_rules() -> list[Rule]:
    return [
        Rule(
            id="r-01",
            profile_id="p-1",
            patterns=["invoice", "rechnung"],
            target_name_template="{date}_{type}_{sender}",
            target_folder_template="Finance/Invoices",
            priority=10,
        ),
    ]


# ---------------------------------------------------------------------------
# Fixtures
# ---------------------------------------------------------------------------

@pytest.fixture()
def _import_provider():
    """Import the provider module to trigger registration."""
    import zerobox.classifier.providers.anthropic  # noqa: F401


# ---------------------------------------------------------------------------
# Tests — registration
# ---------------------------------------------------------------------------

class TestRegistration:
    def test_provider_is_registered(self, _import_provider) -> None:
        assert "anthropic" in _PROVIDERS

    def test_registered_class_name(self, _import_provider) -> None:
        from zerobox.classifier.providers.anthropic import AnthropicProvider

        assert _PROVIDERS["anthropic"] is AnthropicProvider


# ---------------------------------------------------------------------------
# Tests — classify
# ---------------------------------------------------------------------------

class TestClassify:
    @pytest.fixture(autouse=True)
    def _setup(self, _import_provider) -> None:
        pass

    async def test_returns_classification_result(self) -> None:
        response_json = (
            '{"proposed_name": "2024-01_invoice_acme", '
            '"proposed_folder": "Finance/Invoices", '
            '"confidence": 0.92, '
            '"matched_rule_id": "r-01", '
            '"reasoning": "Matched invoice pattern"}'
        )
        with patch("zerobox.classifier.providers.anthropic.anthropic") as mock_mod:
            mock_client = AsyncMock()
            mock_mod.AsyncAnthropic.return_value = mock_client
            mock_client.messages.create.return_value = _mock_response(response_json)

            from zerobox.classifier.providers.anthropic import AnthropicProvider

            provider = AnthropicProvider(_make_config())
            result = await provider.classify("Invoice text", [], _make_context())

        assert isinstance(result, ClassificationResult)
        assert result.proposed_name == "2024-01_invoice_acme"
        assert result.proposed_folder == "Finance/Invoices"
        assert result.confidence == pytest.approx(0.92)
        assert result.matched_rule_id == "r-01"
        assert result.reasoning == "Matched invoice pattern"

    async def test_passes_model_and_temperature(self) -> None:
        response_json = (
            '{"proposed_name": "x", "proposed_folder": "y", '
            '"confidence": 0.5, "matched_rule_id": null, "reasoning": ""}'
        )
        config = _make_config(model="claude-opus-4-20250514", temperature=0.7)

        with patch("zerobox.classifier.providers.anthropic.anthropic") as mock_mod:
            mock_client = AsyncMock()
            mock_mod.AsyncAnthropic.return_value = mock_client
            mock_client.messages.create.return_value = _mock_response(response_json)

            from zerobox.classifier.providers.anthropic import AnthropicProvider

            provider = AnthropicProvider(config)
            await provider.classify("text", [], _make_context())

        call_kwargs = mock_client.messages.create.call_args.kwargs
        assert call_kwargs["model"] == "claude-opus-4-20250514"
        assert call_kwargs["temperature"] == pytest.approx(0.7)

    async def test_includes_rules_in_prompt(self) -> None:
        response_json = (
            '{"proposed_name": "x", "proposed_folder": "y", '
            '"confidence": 0.5, "matched_rule_id": null, "reasoning": ""}'
        )
        rules = _make_rules()

        with patch("zerobox.classifier.providers.anthropic.anthropic") as mock_mod:
            mock_client = AsyncMock()
            mock_mod.AsyncAnthropic.return_value = mock_client
            mock_client.messages.create.return_value = _mock_response(response_json)

            from zerobox.classifier.providers.anthropic import AnthropicProvider

            provider = AnthropicProvider(_make_config())
            await provider.classify("text", rules, _make_context())

        call_kwargs = mock_client.messages.create.call_args.kwargs
        user_message = call_kwargs["messages"][0]["content"]
        assert "r-01" in user_message
        assert "invoice" in user_message

    async def test_empty_rules_list(self) -> None:
        response_json = (
            '{"proposed_name": "x", "proposed_folder": "y", '
            '"confidence": 0.5, "matched_rule_id": null, "reasoning": ""}'
        )
        with patch("zerobox.classifier.providers.anthropic.anthropic") as mock_mod:
            mock_client = AsyncMock()
            mock_mod.AsyncAnthropic.return_value = mock_client
            mock_client.messages.create.return_value = _mock_response(response_json)

            from zerobox.classifier.providers.anthropic import AnthropicProvider

            provider = AnthropicProvider(_make_config())
            await provider.classify("text", [], _make_context())

        call_kwargs = mock_client.messages.create.call_args.kwargs
        user_message = call_kwargs["messages"][0]["content"]
        assert "(no active rules)" in user_message

    async def test_handles_json_in_code_fence(self) -> None:
        response_json = (
            '```json\n{"proposed_name": "x", "proposed_folder": "y", '
            '"confidence": 0.8, "matched_rule_id": null, "reasoning": ""}\n```'
        )
        with patch("zerobox.classifier.providers.anthropic.anthropic") as mock_mod:
            mock_client = AsyncMock()
            mock_mod.AsyncAnthropic.return_value = mock_client
            mock_client.messages.create.return_value = _mock_response(response_json)

            from zerobox.classifier.providers.anthropic import AnthropicProvider

            provider = AnthropicProvider(_make_config())
            result = await provider.classify("text", [], _make_context())

        assert result.proposed_name == "x"
        assert result.confidence == pytest.approx(0.8)


# ---------------------------------------------------------------------------
# Tests — extract_rule
# ---------------------------------------------------------------------------

class TestExtractRule:
    @pytest.fixture(autouse=True)
    def _setup(self, _import_provider) -> None:
        pass

    async def test_returns_rule(self) -> None:
        response_json = (
            '{"patterns": ["invoice", "acme"], '
            '"target_name_template": "{date}_invoice_{sender}", '
            '"target_folder_template": "Finance/Invoices", '
            '"priority": 5, '
            '"examples": ["Invoice from Acme Corp"]}'
        )
        with patch("zerobox.classifier.providers.anthropic.anthropic") as mock_mod:
            mock_client = AsyncMock()
            mock_mod.AsyncAnthropic.return_value = mock_client
            mock_client.messages.create.return_value = _mock_response(response_json)

            from zerobox.classifier.providers.anthropic import AnthropicProvider

            provider = AnthropicProvider(_make_config())
            rule = await provider.extract_rule("Invoice from Acme", _make_correction())

        assert isinstance(rule, Rule)
        assert rule.patterns == ["invoice", "acme"]
        assert rule.target_name_template == "{date}_invoice_{sender}"
        assert rule.target_folder_template == "Finance/Invoices"
        assert rule.priority == 5
        assert rule.examples == ["Invoice from Acme Corp"]

    async def test_generates_rule_id(self) -> None:
        response_json = (
            '{"patterns": ["test"], '
            '"target_name_template": "t", '
            '"target_folder_template": "t", '
            '"priority": 0, '
            '"examples": []}'
        )
        with patch("zerobox.classifier.providers.anthropic.anthropic") as mock_mod:
            mock_client = AsyncMock()
            mock_mod.AsyncAnthropic.return_value = mock_client
            mock_client.messages.create.return_value = _mock_response(response_json)

            from zerobox.classifier.providers.anthropic import AnthropicProvider

            provider = AnthropicProvider(_make_config())
            rule = await provider.extract_rule("text", _make_correction())

        assert len(rule.id) == 8
        assert rule.id.isalnum()

    async def test_rule_has_empty_profile_id(self) -> None:
        response_json = (
            '{"patterns": ["test"], '
            '"target_name_template": "t", '
            '"target_folder_template": "t", '
            '"priority": 0, '
            '"examples": []}'
        )
        with patch("zerobox.classifier.providers.anthropic.anthropic") as mock_mod:
            mock_client = AsyncMock()
            mock_mod.AsyncAnthropic.return_value = mock_client
            mock_client.messages.create.return_value = _mock_response(response_json)

            from zerobox.classifier.providers.anthropic import AnthropicProvider

            provider = AnthropicProvider(_make_config())
            rule = await provider.extract_rule("text", _make_correction())

        assert rule.profile_id == ""


# ---------------------------------------------------------------------------
# Tests — error handling
# ---------------------------------------------------------------------------

class TestErrorHandling:
    @pytest.fixture(autouse=True)
    def _setup(self, _import_provider) -> None:
        pass

    async def test_api_error_propagates(self) -> None:
        with patch("zerobox.classifier.providers.anthropic.anthropic") as mock_mod:
            mock_client = AsyncMock()
            mock_mod.AsyncAnthropic.return_value = mock_client
            mock_mod.APIError = type("APIError", (Exception,), {})
            mock_client.messages.create.side_effect = mock_mod.APIError("rate limited")

            from zerobox.classifier.providers.anthropic import AnthropicProvider

            provider = AnthropicProvider(_make_config())
            with pytest.raises(Exception, match="rate limited"):
                await provider.classify("text", [], _make_context())

    async def test_invalid_json_raises(self) -> None:
        with patch("zerobox.classifier.providers.anthropic.anthropic") as mock_mod:
            mock_client = AsyncMock()
            mock_mod.AsyncAnthropic.return_value = mock_client
            mock_client.messages.create.return_value = _mock_response("not valid json")

            from zerobox.classifier.providers.anthropic import AnthropicProvider

            provider = AnthropicProvider(_make_config())
            with pytest.raises(Exception):
                await provider.classify("text", [], _make_context())
