"""
REN Thinking Modes & Reasoning Configuration
Provides structured cognitive depth levels (FAST, MEDIUM, HIGH) with dynamic token budgets,
sampling temperature, reasoning prompts, and think-hard override capabilities.
"""

from enum import Enum
from dataclasses import dataclass
from typing import Dict, Any, Optional

from ren.config.settings import settings


class ThinkingMode(str, Enum):
    FAST = "FAST"
    MEDIUM = "MEDIUM"
    HIGH = "HIGH"

    @classmethod
    def from_string(cls, val: Optional[str]) -> "ThinkingMode":
        if not val:
            return cls.MEDIUM
        v = str(val).strip().upper()
        if v in cls.__members__:
            return cls[v]
        if "FAST" in v:
            return cls.FAST
        if "HIGH" in v or "HARD" in v or "DEEP" in v:
            return cls.HIGH
        return cls.MEDIUM


@dataclass
class ThinkingConfig:
    mode: ThinkingMode
    max_tokens: int
    temperature: float
    reasoning_depth_prompt: str
    status_label: str
    is_deep_thinking: bool = False

    def to_dict(self) -> Dict[str, Any]:
        return {
            "mode": self.mode.value,
            "max_tokens": self.max_tokens,
            "temperature": self.temperature,
            "status_label": self.status_label,
            "is_deep_thinking": self.is_deep_thinking,
        }


class ThinkingManager:
    """Configures and resolves reasoning parameters based on active ThinkingMode."""

    @staticmethod
    def get_config(mode: ThinkingMode = ThinkingMode.MEDIUM, think_hard: bool = False) -> ThinkingConfig:
        """Resolves runtime configuration for a requested thinking mode."""
        effective_mode = ThinkingMode.HIGH if think_hard else mode

        if effective_mode == ThinkingMode.FAST:
            return ThinkingConfig(
                mode=ThinkingMode.FAST,
                max_tokens=settings.MODEL.MAX_TOKENS_SIMPLE,
                temperature=0.2,
                reasoning_depth_prompt="Provide a direct, concise, and high-speed response with minimal preamble.",
                status_label="⚡ Fast Response",
                is_deep_thinking=False,
            )

        elif effective_mode == ThinkingMode.HIGH:
            return ThinkingConfig(
                mode=ThinkingMode.HIGH,
                max_tokens=settings.MODEL.MAX_TOKENS_AGENT,
                temperature=0.4,
                reasoning_depth_prompt=(
                    "Engage in deep, comprehensive multi-step reasoning. Structure internal cognitive deliberations "
                    "inside <thought>...</thought> tags, systematically examining edge cases, architecture, verification, "
                    "and optimal solutions before delivering your final authoritative output."
                ),
                status_label="🧠 Deep Thinking" if think_hard else "🔬 High Reasoning",
                is_deep_thinking=True,
            )

        else:  # MEDIUM (Default)
            return ThinkingConfig(
                mode=ThinkingMode.MEDIUM,
                max_tokens=min(settings.MODEL.MAX_TOKENS_AGENT, 2048),
                temperature=settings.MODEL.DEFAULT_TEMPERATURE,
                reasoning_depth_prompt="Provide thorough, step-by-step reasoning and complete solutions.",
                status_label="🎯 Balanced",
                is_deep_thinking=False,
            )


thinking_manager = ThinkingManager()
