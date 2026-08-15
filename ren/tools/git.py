"""
Git Version Control Tools
Inspects repositories, branch heads, diffs, logs, and creates commits safely.
"""

import time
from typing import Dict, Any, Optional

from ren.tools.base import BaseTool, ToolResult
from ren.security.permissions import PermissionCategory
from ren.security.sandbox import ExecutionSandbox


class GitStatusTool(BaseTool):
    name = "git_status"
    description = "Check git repository status, current branch, staged and modified files."
    required_permissions = [PermissionCategory.FILESYSTEM_READ]
    parameters_schema = {"type": "object", "properties": {}}

    def run(self, **kwargs) -> ToolResult:
        start_t = time.perf_counter()
        success, stdout, stderr, exit_code = ExecutionSandbox.execute_command("git status --short --branch")
        return ToolResult(
            success=success,
            output=stdout or "No changes in working tree.",
            error=stderr if not success else None,
            exit_code=exit_code,
            duration=time.perf_counter() - start_t
        )


class GitDiffTool(BaseTool):
    name = "git_diff"
    description = "View uncommitted changes or diff against HEAD."
    required_permissions = [PermissionCategory.FILESYSTEM_READ]
    parameters_schema = {
        "type": "object",
        "properties": {
            "staged": {"type": "boolean", "description": "If true, show staged diff (--cached)."}
        }
    }

    def run(self, staged: bool = False, **kwargs) -> ToolResult:
        start_t = time.perf_counter()
        cmd = "git diff --cached" if staged else "git diff"
        success, stdout, stderr, exit_code = ExecutionSandbox.execute_command(cmd)
        return ToolResult(
            success=success,
            output=stdout or "No diff detected.",
            error=stderr if not success else None,
            exit_code=exit_code,
            duration=time.perf_counter() - start_t
        )


class GitCommitTool(BaseTool):
    name = "git_commit"
    description = "Stage files and create a git commit with a message."
    required_permissions = [PermissionCategory.GIT_WRITE]
    parameters_schema = {
        "type": "object",
        "properties": {
            "message": {"type": "string", "description": "Commit message."},
            "all_files": {"type": "boolean", "description": "If true, auto stages all modified files (git add -A)."}
        },
        "required": ["message"]
    }

    def run(self, message: str, all_files: bool = True, **kwargs) -> ToolResult:
        start_t = time.perf_counter()
        if all_files:
            add_succ, _, add_err, _ = ExecutionSandbox.execute_command("git add -A")
            if not add_succ:
                return ToolResult(
                    success=False,
                    error=f"git add failed: {add_err}",
                    exit_code=1,
                    duration=time.perf_counter() - start_t
                )

        # Escape quotes in commit message
        safe_msg = message.replace('"', '\\"')
        cmd = f'git commit -m "{safe_msg}"'
        success, stdout, stderr, exit_code = ExecutionSandbox.execute_command(cmd)
        return ToolResult(
            success=success,
            output=stdout,
            error=stderr if not success else None,
            exit_code=exit_code,
            duration=time.perf_counter() - start_t
        )


class GitLogTool(BaseTool):
    name = "git_log"
    description = "Inspect recent commit history."
    required_permissions = [PermissionCategory.FILESYSTEM_READ]
    parameters_schema = {
        "type": "object",
        "properties": {
            "limit": {"type": "integer", "description": "Number of commits to return (default: 5)."}
        }
    }

    def run(self, limit: int = 5, **kwargs) -> ToolResult:
        start_t = time.perf_counter()
        cmd = f"git log -n {limit} --oneline"
        success, stdout, stderr, exit_code = ExecutionSandbox.execute_command(cmd)
        return ToolResult(
            success=success,
            output=stdout or "No commits found.",
            error=stderr if not success else None,
            exit_code=exit_code,
            duration=time.perf_counter() - start_t
        )
