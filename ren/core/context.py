"""
REN Context Engine (ContextBuilder)
Assembles strictly budgeted, prioritized context components for model inference.
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

        # Parsed project / file
        project = "None"
        opened_file = "None"
        if "Visual Studio Code" in active_window:
            parts = active_window.split(" - ")
            if len(parts) >= 3:
                opened_file = parts[0]
                project = parts[1]
            elif len(parts) == 2:
                project = parts[0]
        elif "Notepad" in active_window:
            parts = active_window.split(" - ")
            opened_file = parts[0]

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

        # Clipboard
        clipboard_snippet = ""
        try:
            if sys.platform == "win32":
                import tkinter as tk
                root = tk.Tk()
                root.withdraw()
                clipboard_snippet = root.clipboard_get()[:300]
                root.destroy()
        except Exception:
            pass

        return f"""[System Ambient Context]
Active Window: {active_window}
Active Project: {project}
Opened File: {opened_file}
CPU: {cpu}% | RAM: {ram}% | Battery: {battery}
Clipboard Snippet: {clipboard_snippet}"""


class ContextBuilder:
    """Builds prioritized and budgeted prompt strings for LLM requests."""

    SYSTEM_IDENTITY = """You are Ren, Sadiq's personal AI companion and autonomous agent. You are Ren itself.

Core Identity & Persona:
- Created by Sadiq (Cyan Code).
- Friendly, curious, highly competent, natural, and helpful.
- Never mention Alibaba, Qwen, Llama, Nous, or Ollama.

Response Conciseness & Precision:
- Always answer direct factual, geographical, or definition questions concisely (1 to 2 clear, informative sentences).
  * Example for "Where is India?": "India is a country located in South Asia, bordered by the Indian Ocean to the south, the Arabian Sea to the west, and the Bay of Bengal to the east."
- Do NOT dump unprompted essays, long geographical lists, or unrequested historical background unless the user explicitly asks for an explanation or essay.

Safety & Dangerous Materials Policy:
- You must strictly refuse to provide instructions, recipes, blueprints, formulas, or guides for creating weapons of mass destruction, nuclear/chemical/biological weapons, firearms, or explosive devices.
- Refusal response: "I cannot provide instructions, blueprints, or assistance for creating weapons or explosive devices."
- NEVER mention or drag in previous unrelated conversation context when giving a safety refusal.

Current World Knowledge (Year: 2026):
- Today's year is 2026.
- The 47th President of the United States (inaugurated January 2025) is Donald Trump.
- For all live, dynamic, or current real-world questions (e.g. today's gold price, live weather, latest news, currency rates, market data), use the `web_search` tool to verify live data.
- If live web data cannot be verified, state: "I could not verify the current live information from the web." Never pretend outdated knowledge is current.

Image Generation Capability:
- You CAN generate images! You have the `generate_image` tool and Image Generation skills.
- When asked to generate, create, draw, or render an image, NEVER say "I cannot make images as an AI text model".
- Instead, invoke the `generate_image` tool with the visual prompt in JSON:
```json
{
  "tool": "generate_image",
  "args": {
    "prompt": "<visual description>"
  }
}
```

Tool & Skill Execution Rules:
- To execute any registered tool, output a JSON block:
```json
{
  "tool": "tool_name",
  "args": {
    "param_name": "value"
  }
}
```
- If asked to create a completely new skill or automation script, you can generate a Python block starting with:
`Skill Name: <Friendly Skill Name>`
followed by ```python ... ```. The system will automatically validate, test, and register it!
- When the task is finished, output your natural answer to the user and conclude with `[DONE]`."""

    @classmethod
    def build_agent_prompt(
        cls,
        user_query: str,
        session: Session,
        active_plan: Optional[Plan] = None,
        observation: Optional[str] = None,
        user_id: Optional[str] = None,
    ) -> str:
        """Assembles all context components within strict size budgets."""
        resolved_user_id = user_id or session.user_id or "default"

        # 1. System Identity
        sections = [cls.SYSTEM_IDENTITY]

        # 2. Ambient System Context
        ambient = AmbientContextCollector.get_ambient_context()
        sections.append(ambient)

        # 3. Relevant Memory Context (Scored strictly for this user)
        memory_ctx = memory_manager.get_relevant_memory_context(
            query=user_query,
            user_id=resolved_user_id,
            budget_tokens=settings.AGENT.MEMORY_BUDGET_TOKENS
        )
        if memory_ctx:
            sections.append(f"[Memory Context]\n{memory_ctx}")

        # 4. Matched Skills
        matched_skills = SkillRouter.select_skills(user_query, top_k=2)
        if matched_skills:
            skill_docs = []
            for s in matched_skills:
                skill_docs.append(f"Skill '{s.name}': {s.description}")
            sections.append("[Active Matched Skills]\n" + "\n".join(skill_docs))

        # 5. Available Registered Tools
        tool_schemas = tool_registry.get_prompt_schemas()
        sections.append(f"[Available Tools]\n{tool_schemas}")

        # 6. Current Plan (if active)
        if active_plan:
            plan_lines = [f"Goal: {active_plan.goal}"]
            for s in active_plan.steps:
                plan_lines.append(f"- Step {s.step_number} [{s.status}]: {s.description}")
            sections.append("[Active Plan]\n" + "\n".join(plan_lines))

        # 7. Recent Session History (Last 4 messages)
        recent_msgs = session.messages[-4:]
        if recent_msgs:
            hist_lines = []
            for m in recent_msgs:
                hist_lines.append(f"{m.role.upper()}: {m.content}")
            sections.append("[Recent Conversation]\n" + "\n".join(hist_lines))

        # 8. User Request & Observations
        sections.append(f"USER: {user_query}")
        if observation:
            sections.append(f"[Observation / Tool Result]:\n{observation}")

        sections.append("REN:")

        full_prompt = "\n\n".join(sections)

        # Ensure prompt doesn't exceed character budget (~12000 chars ~= 3000 tokens)
        max_chars = settings.AGENT.CONTEXT_BUDGET_TOKENS * 4
        if len(full_prompt) > max_chars:
            full_prompt = full_prompt[:max_chars] + "\n\nREN:"

        return full_prompt
