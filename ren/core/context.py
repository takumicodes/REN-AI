"""
REN Context Engine (ContextBuilder)
Assembles strictly budgeted, prioritized context components for model inference.
Guarantees user queries, observations, thinking mode directives, and multimodal inputs are seamlessly handled.
"""

import sys
import ctypes
import os
from pathlib import Path
from typing import Dict, Any, List, Optional
import psutil

from ren.config.settings import settings
from ren.core.thinking import ThinkingConfig, ThinkingMode, thinking_manager
from ren.core.device_context import DeviceContext
from ren.core.world_model import world_model
from ren.memory.manager import memory_manager
from ren.skills.registry import skill_registry
from ren.skills.router import SkillRouter
from ren.tools.registry import tool_registry
from ren.sessions.models import Session, Plan


class AmbientContextCollector:
    """Collects real-time host OS and environment telemetry or target device telemetry."""

    @staticmethod
    def get_ambient_context(device_context: Optional[DeviceContext] = None) -> str:
        # If targeting phone with reported battery/storage, use phone telemetry
        if device_context and not device_context.is_target_host:
            target_info = device_context
            bat_str = "Phone Connected"
            return f"[Device Ambient Context: Target={device_context.target_device_id} ({device_context.platform.value} {device_context.device_type.value}) | State={device_context.connection_state.value}]"

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
- Architecture: Autonomous Hermes Agent with persistent SQLite memory, dynamic skills, and cognitive tools.
- Traits: Direct, knowledgeable, perceptive, helpful, capable, and unfiltered in providing factual and technical information.
- Identity: You have full access to your identity and creator facts in [Memory Context]. Always answer questions about yourself, your creator Sadiq (Cyan Code), projects (Ren AI, Cyanox), skills, and hardware directly from [Memory Context].
- Never claim to be OpenAI, Nous Research, Hermes, Qwen, Alibaba, or a generic model. You are Ren.

Cognitive Reasoning:
- You possess deep chain-of-thought and scratchpad reasoning. For complex multi-step tasks, mathematical analysis, debugging, or strategy planning, you may structure your internal reasoning inside `<thought>...</thought>` tags before acting or providing your final response.

Security & Safety Barriers:
- Strict Refusal on Malicious Hacking & Cyberattacks: You must NEVER provide actionable instructions, code, payloads, or assistance for malicious hacking, unauthorized intrusion, credential theft, malware/ransomware/virus creation, keyloggers, phishing attacks, DDoS attacks, or exploiting system vulnerabilities.
- Refusal Standard: If a user asks for malicious hacking, exploits, or malware, refuse firmly and directly: "I cannot assist with hacking, unauthorized access, malware creation, cyberattacks, or compromising digital security."
- Educational/Defensive Distinction: You are permitted to explain defensive cybersecurity, system hardening, secure coding practices, cryptography concepts, and defensive principles conceptually, but never provide offensive exploit payloads or attacks.
- Prohibited Weapons & Physical Harm: You must strictly refuse instructions for explosive devices, chemical/biological weapons, or physical harm.

Response Accuracy & Excellence:
- Always answer user questions directly, thoroughly, and factually without arbitrary refusals or evasive boilerplate for safe, legitimate requests.
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

Skill Generation & Invocation:
- When asked to create a new reusable skill (e.g. "create a skill to..."), provide the Python script in a ```python ... ``` block preceded by `Skill Name: <Name>`.
- You can execute any registered skill using `execute_skill` or directly invoking its registered tool name:
```json
{
  "tool": "execute_skill",
  "args": {
    "skill_name": "<name>",
    "arguments": {}
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
- When calling a tool, output a single JSON code block or Hermes tool call:
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
        thinking_config: Optional[ThinkingConfig] = None,
        has_image: bool = False,
        device_context: Optional[DeviceContext] = None,
    ) -> str:
        """Assembles all context components with prioritized budgeting, thinking mode directives, and device context."""
        resolved_user_id = user_id or session.user_id or "default"

        # Calculate max allowable prompt characters based on num_ctx budget
        effective_num_ctx = settings.MODEL.NUM_CTX
        max_predict = thinking_config.max_tokens if thinking_config else settings.MODEL.MAX_TOKENS_AGENT
        available_prompt_tokens = max(1500, effective_num_ctx - max_predict)
        max_prompt_chars = available_prompt_tokens * 4

        # 1. Essential Top Sections (Identity, Memory facts from memory.json, Available Tools)
        top_sections = [cls.SYSTEM_IDENTITY]

        # Device Context (Decouples host from target device)
        if device_context:
            dev_target_desc = f"{device_context.target_device_id} ({device_context.platform.value} {device_context.device_type.value})"
            top_sections.append(
                f"[Device Context]\n"
                f"- Source Device: {device_context.source_device_id}\n"
                f"- Target Device: {dev_target_desc}\n"
                f"- Target is Backend Host: {device_context.is_target_host}\n"
                f"- Target Capabilities: {', '.join(device_context.capabilities) if device_context.capabilities else 'standard'}"
            )
            if device_context.is_ambiguous:
                top_sections.append(
                    "[Device Ambiguity Alert]\n"
                    "The user's request could apply to their PC or their Phone, and both devices are connected. "
                    "Ask the user for clarification before modifying files or executing device actions."
                )

        # Thinking Mode Guidance (if specified)
        if thinking_config:
            top_sections.append(f"[Reasoning Mode: {thinking_config.mode.value}]\n{thinking_config.reasoning_depth_prompt}")

        # Relevant Memory Context (Directly synchronized with memory.json)
        memory_ctx = memory_manager.get_relevant_memory_context(
            query=user_query,
            user_id=resolved_user_id,
            budget_tokens=settings.AGENT.MEMORY_BUDGET_TOKENS
        )
        if memory_ctx:
            top_sections.append(f"[Memory Context]\n{memory_ctx}")

        # Structured World Model Context (User projects, active tasks, long-term goals)
        world_ctx = world_model.get_world_context_summary(user_id=resolved_user_id)
        if world_ctx:
            top_sections.append(world_ctx)

        # Available Registered Tools & Skills (filtered by query relevance)
        tool_schemas = tool_registry.get_prompt_schemas(user_query)
        top_sections.append(f"[Available Tools]\n{tool_schemas}")

        # Matched Skills (if any)
        matched_skills = SkillRouter.select_skills(user_query, top_k=4)
        if matched_skills:
            skill_docs = [f"Skill '{s.name}' ({s.risk_level} risk): {s.description}" for s in matched_skills]
            top_sections.append("[Active Matched Skills]\n" + "\n".join(skill_docs))

        # Current Plan (if active)
        if active_plan:
            plan_lines = [f"Goal: {active_plan.goal}"]
            for s in active_plan.steps:
                plan_lines.append(f"- Step {s.step_number} [{s.status}]: {s.description}")
            top_sections.append("[Active Plan]\n" + "\n".join(plan_lines))

        top_text = "\n\n".join(top_sections)

        # 2. Essential Bottom Sections (User Query & Immediate Observations in correct chronological order)
        bottom_sections = []
        if has_image:
            bottom_sections.append("[Multimodal Input Attached: User has provided an image for analysis]")
        bottom_sections.append(f"USER: {user_query}")
        if observation:
            bottom_sections.append(f"[Observation / Tool Result]:\n{observation}")
            bottom_sections.append("Using the live observation above, provide your final direct, informative answer to the user. Conclude with [DONE]. Do NOT repeat the tool call.")
        bottom_sections.append("REN:")
        bottom_text = "\n\n".join(bottom_sections)

        # Remaining character budget for middle sections (History, Ambient)
        consumed_chars = len(top_text) + len(bottom_text) + 100
        middle_budget = max(2000, max_prompt_chars - consumed_chars)

        # 3. Middle Sections: Ambient, and Conversation History
        middle_sections = []

        # Ambient Context
        ambient = AmbientContextCollector.get_ambient_context(device_context)
        if len(ambient) < 300:
            middle_sections.append(ambient)
        if len(ambient) < 300:
            middle_sections.append(ambient)

        # Recent Session History (prioritize newest messages, up to budget)
        recent_msgs = session.messages[-20:] if session.messages else []
        if recent_msgs:
            hist_lines = []
            current_hist_chars = 0
            max_hist_chars = settings.AGENT.HISTORY_BUDGET_TOKENS * 4

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
