"""
Task Planning and Decomposition Engine
Classifies task complexity, generates multi-step plans, and tracks plan execution.
"""

import json
import re
from typing import Optional, List, Dict, Any

from ren.sessions.models import Plan, PlanStep
from ren.models import get_model_provider
from ren.monitoring.logger import agent_logger


class TaskPlanner:
    """Creates structured multi-step execution plans for complex user requests."""

    @classmethod
    def is_complex_task(cls, query: str) -> bool:
        """Determines whether a user prompt requires multi-step planning."""
        text = query.lower().strip()

        # Simple conversational queries
        simple_patterns = [
            r"^what('s| is) \d+",
            r"^calculate ",
            r"^hello",
            r"^hi\b",
            r"^how are you",
            r"^who are you",
            r"^what is your name",
            r"^open (calculator|notepad|explorer|youtube)",
            r"^sleep$",
            r"^wake( up)?$",
        ]
        for pat in simple_patterns:
            if re.search(pat, text):
                return False

        # Complexity triggers
        complex_triggers = [
            "create", "build", "debug", "fix", "inspect", "refactor",
            "git", "commit", "test", "install", "download", "organize",
            "search and", "find all", "script to", "program to"
        ]
        return any(trig in text for trig in complex_triggers) or len(text.split()) > 10

    @classmethod
    def generate_plan(cls, query: str) -> Optional[Plan]:
        """Generates a structured multi-step Plan for complex user requests."""
        if not cls.is_complex_task(query):
            return None

        prompt = f"""You are Ren's task planner. Break down the following request into 2 to 4 concise actionable steps.
Request: "{query}"

Respond strictly with a JSON object in this format:
{{
  "goal": "{query}",
  "steps": [
    {{"step_number": 1, "description": "Step description", "tool_name": "tool_to_use_if_any"}},
    {{"step_number": 2, "description": "Step description", "tool_name": "tool_to_use_if_any"}}
  ]
}}
JSON:"""

        try:
            provider = get_model_provider()
            resp = provider.generate(prompt, max_tokens=256, temperature=0.2)
            
            clean_resp = re.sub(r'<(?:thought|scratchpad)>.*?</(?:thought|scratchpad)>', '', resp, flags=re.DOTALL | re.IGNORECASE).strip()
            
            # Extract JSON block
            json_match = re.search(r'\{.*\}', clean_resp or resp, re.DOTALL)
            if json_match:
                data = json.loads(json_match.group(0))
                plan = Plan.from_dict(data)
                agent_logger.info(f"Generated plan with {len(plan.steps)} steps for: {query}")
                return plan
        except Exception as e:
            agent_logger.error(f"Plan generation failed: {e}")

        # Fallback to single step default plan
        return Plan(
            goal=query,
            steps=[PlanStep(step_number=1, description=f"Execute: {query}")]
        )
