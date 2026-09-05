"""
Model Provider Abstract Base Class
Provides model-agnostic interface for LLM & multimodal inference.
"""

from abc import ABC, abstractmethod
from typing import Dict, Any, Optional, List


class ModelProvider(ABC):
    """Abstract interface for local or remote LLM backends."""

    @abstractmethod
    def generate(
        self,
        prompt: str,
        images: Optional[List[str]] = None,
        **kwargs
    ) -> str:
        """Generates completion for a raw prompt with optional multimodal image inputs."""
        pass

    @abstractmethod
    def chat(
        self,
        messages: List[Dict[str, Any]],
        images: Optional[List[str]] = None,
        **kwargs
    ) -> str:
        """Generates completion for structured chat history."""
        pass

    @abstractmethod
    def is_available(self) -> bool:
        """Returns True if the backend is reachable and ready."""
        pass

    @abstractmethod
    def supports_vision(self) -> bool:
        """Returns True if the active model supports vision/multimodal inputs."""
        pass

    @abstractmethod
    def health_check(self) -> Dict[str, Any]:
        """Returns status metadata regarding the model service."""
        pass
