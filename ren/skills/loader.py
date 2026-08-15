"""
Skill Loader & Runner
Executes skills in bounded sandbox environments with output capture.
"""

from typing import Tuple, Optional
from ren.skills.registry import Skill
from ren.security.sandbox import ExecutionSandbox
from ren.monitoring.logger import skills_logger


class SkillLoader:
    """Safely loads and executes skill code."""

    @staticmethod
    def execute_skill(skill: Skill, timeout: int = 30) -> Tuple[bool, str, str, int]:
        """Runs the skill script inside the execution sandbox."""
        skills_logger.info(f"Executing skill: {skill.name}")
        return ExecutionSandbox.execute_python_code(
            code=skill.code_content,
            timeout=timeout,
        )
