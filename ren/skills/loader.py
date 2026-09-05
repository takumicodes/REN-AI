"""
REN Skill Loader & Runner
Executes skills in bounded sandbox environments with output capture, argument injection,
and structured exception handling.
"""

import json
from typing import Tuple, Optional, Dict, Any
from ren.security.sandbox import ExecutionSandbox
from ren.monitoring.logger import skills_logger, error_logger


class SkillLoader:
    """Safely loads and executes skill code with parameter injection."""

    @staticmethod
    def execute_skill(skill: Any, args: Optional[Dict[str, Any]] = None, timeout: int = 30) -> Tuple[bool, str, str, int]:
        """
        Runs the skill script inside the execution sandbox with runtime parameter injection.
        """
        skills_logger.info(f"Executing skill: {skill.name} (args: {args})")

        # Inject arguments and helper stubs into script execution context
        injected_preamble = (
            "import os, sys, json\n"
            f"SKILL_ARGS = {json.dumps(args or {})}\n"
            "def speak(text):\n"
            "    print(f'[SPEECH]: {text}')\n"
            "class SadiqMock:\n"
            "    def speak(self, text): print(f'[SPEECH]: {text}')\n"
            "sadiq = SadiqMock()\n"
        )

        full_code = injected_preamble + "\n" + skill.code_content

        return ExecutionSandbox.execute_python_code(
            code=full_code,
            timeout=timeout,
        )
