"""
Unified Tool Registry
Central dispatcher for tool lookup, argument validation, permission checks, telemetry, and logging.
"""

import time
from typing import Dict, Any, List, Optional

from ren.tools.base import BaseTool, ToolResult
from ren.tools.filesystem import ReadFileTool, WriteFileTool, ListDirectoryTool, SearchFilesTool, DeleteFileTool
from ren.tools.terminal import TerminalTool
from ren.tools.python_runner import PythonRunnerTool
from ren.tools.system import SystemStatusTool, BatteryStatusTool, ProcessListTool
from ren.tools.project import InspectProjectTool
from ren.tools.git import GitStatusTool, GitDiffTool, GitCommitTool, GitLogTool
from ren.tools.skills_tool import ListSkillsTool, InspectSkillTool
from ren.tools.memory_tool import QueryMemoryTool, RememberFactTool
from ren.tools.web_search import WebSearchTool
from ren.tools.generate_image import GenerateImageTool

from ren.security.permissions import permission_manager, PermissionRisk
from ren.security.confirmations import confirmation_manager
from ren.monitoring.logger import tools_logger, error_logger
from ren.monitoring.performance import perf_monitor


class ToolRegistry:
    """Central registry and execution manager for tools."""

    def __init__(self):
        self._tools: Dict[str, BaseTool] = {}
        self._register_default_tools()

    def register_tool(self, tool: BaseTool) -> None:
        """Registers a tool instance."""
        self._tools[tool.name] = tool
        tools_logger.debug(f"Registered tool: {tool.name}")

    def get_tool(self, name: str) -> Optional[BaseTool]:
        """Retrieves tool by name."""
        return self._tools.get(name)

    def list_tools(self) -> List[BaseTool]:
        """Returns all registered tool instances."""
        return list(self._tools.values())

    def _register_default_tools(self):
        """Initializes all built-in system, filesystem, git, project, and python tools."""
        default_tools = [
            ReadFileTool(),
            WriteFileTool(),
            ListDirectoryTool(),
            SearchFilesTool(),
            DeleteFileTool(),
            TerminalTool(),
            PythonRunnerTool(),
            SystemStatusTool(),
            BatteryStatusTool(),
            ProcessListTool(),
            InspectProjectTool(),
            GitStatusTool(),
            GitDiffTool(),
            GitCommitTool(),
            GitLogTool(),
            ListSkillsTool(),
            InspectSkillTool(),
            QueryMemoryTool(),
            RememberFactTool(),
            WebSearchTool(),
            GenerateImageTool(),
        ]
        for t in default_tools:
            self.register_tool(t)

    def execute_tool(
        self,
        name: str,
        args: Optional[Dict[str, Any]] = None,
        dry_run: bool = False,
    ) -> ToolResult:
        """
        Executes a registered tool with full validation, permission checks, and logging.
        """
        start_t = time.perf_counter()
        args = args or {}
        tool = self.get_tool(name)

        if not tool:
            err = f"Tool '{name}' is not registered."
            tools_logger.error(err)
            return ToolResult(success=False, error=err, exit_code=1, duration=0.0)

        # 1. Parameter Validation
        valid, val_err = tool.validate_args(args)
        if not valid:
            tools_logger.warning(f"Validation failed for tool '{name}': {val_err}")
            return ToolResult(
                success=False,
                error=val_err,
                exit_code=1,
                duration=time.perf_counter() - start_t
            )

        # 2. Permission Evaluation
        check = permission_manager.evaluate_permissions(
            required_permissions=tool.required_permissions,
            operation_desc=f"{name}({args})",
            details=args,
        )

        if not check.allowed:
            err = f"Permission denied for '{name}': {check.reason}"
            tools_logger.warning(err)
            return ToolResult(
                success=False,
                error=err,
                exit_code=1,
                duration=time.perf_counter() - start_t
            )

        # 3. User Confirmation Gate (if required)
        if check.requires_user_confirmation:
            confirmed = confirmation_manager.confirm_action(
                action_name=name,
                description=f"Tool {name} with args {args}",
                risk=check.risk,
                dry_run=dry_run,
            )
            if not confirmed:
                err = f"User confirmation was denied for '{name}'."
                tools_logger.warning(err)
                return ToolResult(
                    success=False,
                    error=err,
                    exit_code=1,
                    duration=time.perf_counter() - start_t
                )

        # 4. Execution
        tools_logger.info(f"Executing tool '{name}' with args {args}...")
        try:
            result = tool.run(**args)
            duration = time.perf_counter() - start_t
            result.duration = duration

            perf_monitor.record_tool_call(name, duration, result.success)

            if result.success:
                tools_logger.info(f"Tool '{name}' completed successfully in {duration:.3f}s")
            else:
                tools_logger.warning(f"Tool '{name}' failed in {duration:.3f}s: {result.error}")

            return result

        except Exception as e:
            duration = time.perf_counter() - start_t
            error_logger.error(f"Unexpected exception running tool '{name}': {e}", exc_info=True)
            perf_monitor.record_tool_call(name, duration, False)
            return ToolResult(
                success=False,
                error=f"Tool execution exception: {str(e)}",
                exit_code=1,
                duration=duration
            )

    def get_prompt_schemas(self, query: Optional[str] = None) -> str:
        """Builds a compact string describing relevant tools for the LLM."""
        core_tools = {"web_search", "generate_image", "python_execute", "read_file", "write_file", "terminal", "system_status"}
        clean_q = (query or "").lower()

        selected_tools = []
        for name, tool in sorted(self._tools.items()):
            # Always include core tools
            if name in core_tools:
                selected_tools.append((name, tool))
            elif clean_q and (name.lower() in clean_q or any(w in clean_q for w in tool.description.lower().split()[:5])):
                selected_tools.append((name, tool))

        # If no query filter, default to core tools + memory tools
        if not selected_tools:
            selected_tools = [(name, tool) for name, tool in sorted(self._tools.items()) if name in core_tools or "memory" in name]

        lines = []
        for name, tool in selected_tools:
            params = []
            props = tool.parameters_schema.get("properties", {})
            reqs = tool.parameters_schema.get("required", [])
            for p_name in props.keys():
                req_marker = "*" if p_name in reqs else ""
                params.append(f"{p_name}{req_marker}")
            param_str = f"({', '.join(params)})" if params else "()"
            lines.append(f"- `{name}{param_str}`: {tool.description}")
        return "\n".join(lines)


# Global registry singleton
tool_registry = ToolRegistry()
