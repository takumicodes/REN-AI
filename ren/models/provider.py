"""
Model Provider Abstract Base Class
Provides model-agnostic interface for LLM inference.
"""

from abc import ABC, abstractmethod
from typing import Dict, Any, Optional, List


class ModelProvider(ABC):
    """Abstract interface for local or remote LLM backends."""

    @abstractmethod
    def generate(self, prompt: str, **kwargs) -> str:
        """Generates completion for a raw prompt."""
        pass

    @abstractmethod
    def chat(self, messages: List[Dict[str, str]], **kwargs) -> str:
        """Generates completion for structured chat history."""
        pass

    @abstractmethod
    def is_available(self) -> bool:
        """Returns True if the backend is reachable and ready."""
        pass

    @abstractmethod
    def health_check(self) -> Dict[str, Any]:
        """Returns status metadata regarding the model service."""
        pass
