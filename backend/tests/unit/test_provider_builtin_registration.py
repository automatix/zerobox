"""Regression tests: built-in providers register on package import (#147).

Kept separate from test_provider_registry.py, whose autouse fixture clears the
global registry for every test in that module.
"""

from zerobox.classifier.providers import _PROVIDERS, create_provider
from zerobox.config import LLMConfig


def test_anthropic_is_registered_on_package_import():
    assert "anthropic" in _PROVIDERS


def test_create_provider_builds_anthropic_from_default_config():
    provider = create_provider(LLMConfig(provider="anthropic"))
    assert type(provider).__name__ == "AnthropicProvider"
