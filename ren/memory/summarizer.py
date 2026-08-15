"""
Conversation and Memory Summarizer
Provides lightweight condensation of older dialog turns to prevent context window overflow.
"""

from typing import List, Dict, Any, Optional
from ren.models import get_model_provider
from ren.monitoring.logger import memory_logger


class MemorySummarizer:
    """Condenses old messages into compact persistent summaries."""

    @staticmethod
    def heuristic_summarize(messages: List[Dict[str, str]]) -> str:
        """Fast, 0-cost heuristic extraction of key points without invoking LLM."""
        if not messages:
            return ""

        summary_points = []
        for msg in messages:
            role = msg.get("role", "user").capitalize()
            content = msg.get("content", "").strip()
            if not content:
                continue

            # First sentence or up to 80 chars
            first_sentence = content.split(".")[0].strip()
            if len(first_sentence) > 90:
                first_sentence = first_sentence[:87] + "..."
            summary_points.append(f"{role}: {first_sentence}")

        return " | ".join(summary_points[-6:])

    @classmethod
    def llm_summarize(cls, messages: List[Dict[str, str]], max_words: int = 60) -> str:
        """Uses local LLM to generate a concise structured summary of the conversation."""
        if not messages:
            return ""

        # Format conversation text
        convo_lines = []
        for m in messages:
            convo_lines.append(f"{m.get('role', 'user')}: {m.get('content', '')}")
        convo_text = "\n".join(convo_lines)

        prompt = (
            f"You are Ren. Summarize the key user goals, decisions, and outcomes in this conversation "
            f"in at most {max_words} words. Be dense and factual:\n\n"
            f"{convo_text}\n\nSummary:"
        )

        try:
            provider = get_model_provider()
            summary = provider.generate(prompt, max_tokens=128, temperature=0.3)
            return summary.strip()
        except Exception as e:
            memory_logger.error(f"LLM summarization failed: {e}")
            return cls.heuristic_summarize(messages)
