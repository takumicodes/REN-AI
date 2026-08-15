"""
Terminal Tool
Executes shell commands in a bounded sandbox with timeout and output capture.
"""

import time
from typing import Dict, Any, Optional

from ren.tools.base import BaseTool, ToolResult
from ren.security.permissions import PermissionCategory
from ren.security.sandbox import ExecutionSandbox


class TerminalTool(BaseTool):
    name = "terminal"
    description = "Execute a shell command in the workspace directory with timeout safety."
    required_permissions = [PermissionCategory.TERMINAL_EXECUTE]
    parameters_schema = {
        "type": "object",
        "properties": {
            "command": {"type": "string", "description": "Shell command to execute."},
            "timeout": {"type": "integer", "description": "Timeout in seconds (default: 30)."}
        },
        "required": ["command"]
    }

    def run(self, command: str, timeout: int = 30, **kwargs) -> ToolResult:
        start_t = time.perf_counter()
        success, stdout, stderr, exit_code = ExecutionSandbox.execute_command(
            command=command,
            timeout=timeout,
        )
        duration = time.perf_counter() - start_t

        output = stdout
        if stderr:
            if output:
                output += f"\n[Stderr Output]:\n{stderr}"
            else:
                output = stderr

        return ToolResult(
            success=success,
            output=output,
            error=stderr if not success else None,
            exit_code=exit_code,
            duration=duration,
        )
