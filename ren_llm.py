"""
REN LLM Interface Bridge (Backward Compatible)
Routes legacy LLM calls through ModelProvider and MemoryManager with adaptive token limits.
"""

from ren.models import get_model_provider
from ren.memory.manager import memory_manager
from ren.core.context import ContextBuilder
from ren.config.settings import settings


def build_memory_context() -> str:
    """Builds compact memory context for prompt injection."""
    return memory_manager.get_relevant_memory_context(query="")


def ask_ren(user_prompt: str) -> str:
    """Legacy interface for simple Q&A queries."""
    provider = get_model_provider()
    memory_ctx = memory_manager.get_relevant_memory_context(user_prompt)

    prompt = f"""{ContextBuilder.SYSTEM_IDENTITY}

MEMORY:
{memory_ctx}

USER:
{user_prompt}

REN:"""

    return provider.generate(prompt, max_tokens=settings.MODEL.MAX_TOKENS_SIMPLE)


def ask_ren_agent(full_prompt: str) -> str:
    """Legacy interface for direct agent prompt generation."""
    provider = get_model_provider()
    return provider.generate(full_prompt, max_tokens=settings.MODEL.MAX_TOKENS_AGENT)
