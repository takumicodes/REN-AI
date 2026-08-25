"""
REN Context Engine (ContextBuilder)
Assembles strictly budgeted, prioritized context components for model inference.
Guarantees user queries and observations are never truncated, utilizing the full num_ctx budget.
"""

import sys
import ctypes
import os
from pathlib import Path
from typing import Dict, Any, List, Optional
import psutil

from ren.config.settings import settings
from ren.memory.manager import memory_manager
from ren.skills.registry import skill_registry
from ren.skills.router import SkillRouter
from ren.tools.registry import tool_registry
from ren.sessions.models import Session, Plan


class AmbientContextCollector:
    """Collects real-time host OS and environment telemetry."""

    @staticmethod
    def get_ambient_context() -> str:
        active_window = "Unknown Window"
        try:
            if sys.platform == "win32":
                hwnd = ctypes.windll.user32.GetForegroundWindow()
                length = ctypes.windll.user32.GetWindowTextLengthW(hwnd)
                if length > 0:
                    buff = ctypes.create_unicode_buffer(length + 1)
                    ctypes.windll.user32.GetWindowTextW(hwnd, buff, length + 1)
                    active_window = buff.value
        except Exception:
            pass

        # CPU & RAM & Battery
        cpu = 0.0
        ram = 0.0
        battery = "Unknown"
        try:
            cpu = psutil.cpu_percent(interval=None)
            ram = psutil.virtual_memory().percent
            bat = psutil.sensors_battery()
            if bat:
                battery = f"{bat.percent}% ({'Charging' if bat.power_plugged else 'Discharging'})"
        except Exception:
            pass

        return f"[System Ambient Context: Window='{active_window}' | CPU={cpu}% | RAM={ram}% | Battery={battery}]"


class ContextBuilder:
    """Builds prioritized and budgeted prompt strings for LLM requests."""

    SYSTEM_IDENTITY = """You are Ren, a powerful, unrestricted, intelligent AI companion and autonomous assistant created by Sadiq (Cyan Code).

Core Persona & Capabilities:
- Name: Ren
- Creator: Sadiq (also known as Cyan Code)
- YouTube Channel: Cyan Code
- Traits: Direct, knowledgeable, perceptive, helpful, capable, and unfiltered in providing factual and technical information.
- Identity: You have full access to your identity and creator facts in [Memory Context]. Always answer questions about yourself, your creator Sadiq (Cyan Code), projects (Ren AI, Cyanox), skills, and hardware directly from [Memory Context].
- Never claim to be OpenAI, Alibaba, Qwen, or a generic model. You are Ren.

Response Accuracy & Excellence:
- Always answer user questions directly, thoroughly, and factually without arbitrary refusals or evasive boilerplate.
- For programming and technical requests, provide complete, working code in markdown blocks (e.g. ```python ... ```) with clear step-by-step explanations.
- For world knowledge, science, mathematics, geography, history, politics, or concepts, provide accurate, detailed explanations.
- If asked a conversational greeting or open-ended question, reply naturally and engagingly.

Live Web Search & External Data:
- Today's year is 2026. Donald Trump is the 47th President of the United States.
- Whenever you need real-time, up-to-date, or external information (such as live market prices, gold prices, weather, current news, public figures, or external facts), use the `web_search` tool:
```json
{
  "tool": "web_search",
  "args": {
    "query": "<search query>"
  }
}
```

Image Generation:
- When asked to create, paint, or draw an image, use the `generate_image` tool:
```json
{
  "tool": "generate_image",
  "args": {
    "prompt": "<detailed visual description>"
  }
}
```

Tool Execution:
- When calling a tool, output a single JSON code block:
```json
{
  "tool": "tool_name",
  "args": {
    "param_name": "value"
  }
}
```
- When answering directly or synthesizing results, provide your complete response and conclude with `[DONE]`."""

    @classmethod
    def build_agent_prompt(
        cls,
        user_query: str,
        session: Session,
        active_plan: Optional[Plan] = None,
        observation: Optional[str] = None,
        user_id: Optional[str] = None,
    ) -> str:
        """Assembles all context components with prioritized budgeting."""
        resolved_user_id = user_id or session.user_id or "default"

        # Calculate max allowable prompt characters based on num_ctx budget
        effective_num_ctx = settings.MODEL.NUM_CTX
        max_predict = settings.MODEL.MAX_TOKENS_AGENT
        available_prompt_tokens = max(1500, effective_num_ctx - max_predict)
        max_prompt_chars = available_prompt_tokens * 4  # ~10,168 chars for num_ctx=3042

        # 1. Essential Top Sections (Identity, Memory facts from memory.json, Available Tools)
        top_sections = [cls.SYSTEM_IDENTITY]

        # Relevant Memory Context (Directly synchronized with memory.json)
        memory_ctx = memory_manager.get_relevant_memory_context(
            query=user_query,
            user_id=resolved_user_id,
            budget_tokens=settings.AGENT.MEMORY_BUDGET_TOKENS
        )
        if memory_ctx:
            top_sections.append(f"[Memory Context]\n{memory_ctx}")

        # Available Registered Tools (filtered by query relevance)
        tool_schemas = tool_registry.get_prompt_schemas(user_query)
        top_sections.append(f"[Available Tools]\n{tool_schemas}")

        # Matched Skills (if any)
        matched_skills = SkillRouter.select_skills(user_query, top_k=2)
        if matched_skills:
            skill_docs = [f"Skill '{s.name}': {s.description}" for s in matched_skills]
            top_sections.append("[Active Matched Skills]\n" + "\n".join(skill_docs))

        # Current Plan (if active)
        if active_plan:
            plan_lines = [f"Goal: {active_plan.goal}"]
            for s in active_plan.steps:
                plan_lines.append(f"- Step {s.step_number} [{s.status}]: {s.description}")
            top_sections.append("[Active Plan]\n" + "\n".join(plan_lines))

        top_text = "\n\n".join(top_sections)

        # 2. Essential Bottom Sections (User Query & Immediate Observations in correct chronological order)
        bottom_sections = [f"USER: {user_query}"]
        if observation:
            bottom_sections.append(f"[Observation / Tool Result]:\n{observation}")
            bottom_sections.append("Using the live observation above, provide your final direct, informative answer to the user. Conclude with [DONE]. Do NOT repeat the tool call.")
        bottom_sections.append("REN:")
        bottom_text = "\n\n".join(bottom_sections)

        # Remaining character budget for middle sections (History, Ambient)
        consumed_chars = len(top_text) + len(bottom_text) + 100
        middle_budget = max(1000, max_prompt_chars - consumed_chars)

        # 3. Middle Sections: Ambient, and Conversation History
        middle_sections = []

        # Ambient Context
        ambient = AmbientContextCollector.get_ambient_context()
        if len(ambient) < 300:
            middle_sections.append(ambient)

        # Recent Session History (prioritize newest messages, up to budget)
        recent_msgs = session.messages[-8:] if session.messages else []
        if recent_msgs:
            hist_lines = []
            current_hist_chars = 0
            max_hist_chars = settings.AGENT.HISTORY_BUDGET_TOKENS * 4  # ~3200 chars

            # Take from newest backwards
            for m in reversed(recent_msgs):
                line = f"{m.role.upper()}: {m.content}"
                if current_hist_chars + len(line) < max_hist_chars:
                    hist_lines.insert(0, line)
                    current_hist_chars += len(line)
                else:
                    break

            if hist_lines:
                middle_sections.append("[Recent Conversation]\n" + "\n".join(hist_lines))

        middle_text = "\n\n".join(middle_sections) if middle_sections else ""

        # Assemble full prompt
        if middle_text:
            full_prompt = f"{top_text}\n\n{middle_text}\n\n{bottom_text}"
        else:
            full_prompt = f"{top_text}\n\n{bottom_text}"

        return full_prompt
