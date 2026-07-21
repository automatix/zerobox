"""LLM provider registry and factory (FR-08)."""

from __future__ import annotations

from typing import TYPE_CHECKING

from zerobox.classifier.providers.base import LLMProvider

if TYPE_CHECKING:
    from zerobox.config import LLMConfig

_PROVIDERS: dict[str, type[LLMProvider]] = {}


def register(name: str):
    """Class decorator that registers an LLM provider under *name*.

    Usage::

        @register("anthropic")
        class AnthropicProvider(LLMProvider):
            ...
    """

    def decorator(cls: type[LLMProvider]) -> type[LLMProvider]:
        _PROVIDERS[name] = cls
        return cls

    return decorator


def create_provider(config: LLMConfig) -> LLMProvider:
    """Instantiate the LLM provider specified in *config*.

    Raises:
        ValueError: If the requested provider name is not registered.
    """
    if config.provider not in _PROVIDERS:
        available = list(_PROVIDERS.keys())
        raise ValueError(
            f"Unknown LLM provider: {config.provider!r}. "
            f"Available: {available}"
        )
    return _PROVIDERS[config.provider](config)


# Import the built-in provider modules so their @register decorators run on package
# import — without this the registry is empty at runtime and create_provider fails
# with "Unknown LLM provider" (#147). Must stay at the bottom: the modules import
# `register` from this package.
from zerobox.classifier.providers import anthropic as _anthropic  # noqa: E402, F401
