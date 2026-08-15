"""
Python Execution Tool
Executes Python scripts and code snippets in an isolated child process sandbox.
"""

import ast
import time
from typing import Dict, Any, Optional

from ren.tools.base import BaseTool, ToolResult
from ren.security.permissions import PermissionCategory
from ren.security.sandbox import ExecutionSandbox


class PythonRunnerTool(BaseTool):
    name = "python_execute"
    description = "Execute a standalone Python script safely in an isolated child process."
    required_permissions = [PermissionCategory.TERMINAL_EXECUTE]
    parameters_schema = {
        "type": "object",
        "properties": {
            "code": {"type": "string", "description": "Valid Python code to execute."},
            "timeout": {"type": "integer", "description": "Timeout in seconds (default: 30)."}
        },
        "required": ["code"]
    }

    def run(self, code: str, timeout: int = 30, **kwargs) -> ToolResult:
        start_t = time.perf_counter()

        # Step 1: Static AST validation to check syntax
        try:
            ast.parse(code)
        except SyntaxError as e:
            return ToolResult(
                success=False,
                error=f"Python Syntax Error on line {e.lineno}: {e.msg}",
                exit_code=1,
                duration=time.perf_counter() - start_t
            )

        # Step 2: Execute in subprocess sandbox
        success, stdout, stderr, exit_code = ExecutionSandbox.execute_python_code(
            code=code,
            timeout=timeout,
        )
        duration = time.perf_counter() - start_t

        output = stdout
        if stderr:
            if output:
                output += f"\n[Errors / Tracebacks]:\n{stderr}"
            else:
                output = stderr

        return ToolResult(
            success=success,
            output=output,
            error=stderr if not success else None,
            exit_code=exit_code,
            duration=duration,
        )
