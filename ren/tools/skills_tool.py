"""
Skill Management Tools
Allows agent to query, inspect, and execute registered skills.
"""

import time
from typing import Dict, Any, Optional

from ren.tools.base import BaseTool, ToolResult
from ren.security.permissions import PermissionCategory


class ListSkillsTool(BaseTool):
    name = "list_skills"
    description = "List all active registered skills and their capabilities."
    required_permissions = [PermissionCategory.FILESYSTEM_READ]
    parameters_schema = {"type": "object", "properties": {}}

    def run(self, **kwargs) -> ToolResult:
        start_t = time.perf_counter()
        from ren.skills.registry import skill_registry
        skills = skill_registry.get_active_skills()
        
        if not skills:
            return ToolResult(
                success=True,
                output="No active skills registered yet.",
                duration=time.perf_counter() - start_t
            )

        lines = []
        for s in skills:
            lines.append(f"- `{s.name}` ({s.risk_level} risk): {s.description}")

        return ToolResult(
            success=True,
            output="\n".join(lines),
            duration=time.perf_counter() - start_t
        )


class InspectSkillTool(BaseTool):
    name = "inspect_skill"
    description = "Inspect the code and metadata of a specific skill."
    required_permissions = [PermissionCategory.FILESYSTEM_READ]
    parameters_schema = {
        "type": "object",
        "properties": {
            "name": {"type": "string", "description": "Skill name."}
        },
        "required": ["name"]
    }

    def run(self, name: str, **kwargs) -> ToolResult:
        start_t = time.perf_counter()
        from ren.skills.registry import skill_registry
        skill = skill_registry.get_skill(name)

        if not skill:
            return ToolResult(
                success=False,
                error=f"Skill '{name}' not found in registry.",
                exit_code=1,
                duration=time.perf_counter() - start_t
            )

        output = (
            f"Skill: {skill.name}\n"
            f"Version: {skill.version}\n"
            f"Risk Level: {skill.risk_level}\n"
            f"Description: {skill.description}\n"
            f"Capabilities: {', '.join(skill.capabilities)}\n"
            f"Code:\n```python\n{skill.code_content}\n```"
        )

        return ToolResult(
            success=True,
            output=output,
            duration=time.perf_counter() - start_t
        )


class ExecuteSkillTool(BaseTool):
    name = "execute_skill"
    description = "Executes an existing registered skill by name with optional parameters."
    required_permissions = [PermissionCategory.TERMINAL_EXECUTE]
    parameters_schema = {
        "type": "object",
        "properties": {
            "skill_name": {"type": "string", "description": "Name of the skill to execute."},
            "arguments": {"type": "object", "description": "Optional dictionary of arguments for the skill."}
        },
        "required": ["skill_name"]
    }

    def run(self, skill_name: str, arguments: Optional[Dict[str, Any]] = None, **kwargs) -> ToolResult:
        from ren.skills.registry import skill_registry
        return skill_registry.execute_skill(name=skill_name, args=arguments or {})
