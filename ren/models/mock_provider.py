"""
Mock Model Provider
Used for automated testing, dry-runs, and deterministic unit tests.
"""

from typing import Dict, Any, Optional, List
from ren.models.provider import ModelProvider


class MockProvider(ModelProvider):
    """Deterministic mock provider returning queued or patterned responses."""

    def __init__(self, default_response: str = "Mocked Ren response."):
        self.default_response = default_response
        self.response_queue: List[str] = []
        self.prompt_history: List[str] = []

    def set_responses(self, responses: List[str]):
        """Queues deterministic responses in sequence."""
        self.response_queue = list(responses)

    def is_available(self) -> bool:
        return True

    def health_check(self) -> Dict[str, Any]:
        return {"online": True, "active_model": "mock", "latency": 0.001}

    def generate(self, prompt: str, **kwargs) -> str:
        self.prompt_history.append(prompt)
        if self.response_queue:
            return self.response_queue.pop(0)
        return self.default_response

    def chat(self, messages: List[Dict[str, str]], **kwargs) -> str:
        text = "\n".join(f"{m.get('role')}: {m.get('content')}" for m in messages)
        return self.generate(text, **kwargs)
