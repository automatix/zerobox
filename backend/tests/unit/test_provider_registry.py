"""Unit tests for the LLM provider registry and factory (FR-08)."""

from __future__ import annotations

import pytest

from zerobox.classifier.models import ClassificationContext, ClassificationResult, UserCorrection
from zerobox.classifier.providers import _PROVIDERS, create_provider, register
from zerobox.classifier.providers.base import LLMProvider
from zerobox.config import LLMConfig
from zerobox.rules.models import Rule


# ---------------------------------------------------------------------------
# Helpers
# ---------------------------------------------------------------------------

class _DummyProvider(LLMProvider):
    """Minimal concrete provider for testing."""

    def __init__(self, config: LLMConfig) -> None:
        self.config = config

    async def classify(
        self,
        text: str,
        rules: list[Rule],
        context: ClassificationContext,
    ) -> ClassificationResult:
        return ClassificationResult(
            proposed_name="test",
            proposed_folder="test",
            confidence=1.0,
        )

    async def extract_rule(
        self,
        text: str,
        correction: UserCorrection,
    ) -> Rule:
        return Rule(
            id="r-1",
            profile_id="p-1",
            patterns=["test"],
            target_name_template="test",
            target_folder_template="test",
        )


# ---------------------------------------------------------------------------
# Fixtures
# ---------------------------------------------------------------------------

@pytest.fixture(autouse=True)
def _clean_registry():
    """Ensure the global registry is clean before and after each test."""
    saved = dict(_PROVIDERS)
    _PROVIDERS.clear()
    yield
    _PROVIDERS.clear()
    _PROVIDERS.update(saved)


# ---------------------------------------------------------------------------
# Tests
# ---------------------------------------------------------------------------

class TestRegisterDecorator:
    def test_registers_provider(self) -> None:
        register("dummy")(_DummyProvider)
        assert "dummy" in _PROVIDERS
        assert _PROVIDERS["dummy"] is _DummyProvider

    def test_returns_class_unchanged(self) -> None:
        result = register("dummy")(_DummyProvider)
        assert result is _DummyProvider

    def test_multiple_providers(self) -> None:
        register("alpha")(_DummyProvider)
        register("beta")(_DummyProvider)
        assert "alpha" in _PROVIDERS
        assert "beta" in _PROVIDERS


class TestCreateProvider:
    def test_creates_registered_provider(self) -> None:
        register("anthropic")(_DummyProvider)
        config = LLMConfig(provider="anthropic")
        provider = create_provider(config)
        assert isinstance(provider, _DummyProvider)
        assert provider.config is config

    def test_unknown_provider_raises(self) -> None:
        config = LLMConfig(provider="openai")
        with pytest.raises(ValueError, match="Unknown LLM provider"):
            create_provider(config)

    def test_error_lists_available_providers(self) -> None:
        register("anthropic")(_DummyProvider)
        config = LLMConfig(provider="openai")
        with pytest.raises(ValueError, match="anthropic"):
            create_provider(config)


class TestLLMProviderABC:
    def test_cannot_instantiate_abstract(self) -> None:
        with pytest.raises(TypeError):
            LLMProvider()  # type: ignore[abstract]
