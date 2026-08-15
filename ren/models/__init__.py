"""Model provider factory and abstraction package."""

from typing import Optional
from ren.models.provider import ModelProvider
from ren.models.ollama_provider import OllamaProvider
from ren.models.mock_provider import MockProvider
from ren.config.settings import settings

_default_provider: Optional[ModelProvider] = None


def get_model_provider(force_provider: Optional[str] = None) -> ModelProvider:
    """Returns or creates the configured ModelProvider singleton."""
    global _default_provider
    provider_type = force_provider or settings.MODEL.PROVIDER.lower()

    if _default_provider is None or force_provider is not None:
        if provider_type == "mock":
            _default_provider = MockProvider()
        else:
            _default_provider = OllamaProvider()

    return _default_provider


def set_model_provider(provider: ModelProvider):
    """Overrides the global provider singleton (useful for testing)."""
    global _default_provider
    _default_provider = provider


__all__ = [
    "ModelProvider",
    "OllamaProvider",
    "MockProvider",
    "get_model_provider",
    "set_model_provider",
]
