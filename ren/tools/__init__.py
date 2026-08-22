"""Tool execution and registry package."""

from ren.tools.base import BaseTool, ToolResult
from ren.tools.registry import tool_registry, ToolRegistry
from ren.tools.filesystem import ReadFileTool, WriteFileTool, ListDirectoryTool, SearchFilesTool, DeleteFileTool
from ren.tools.terminal import TerminalTool
from ren.tools.python_runner import PythonRunnerTool
from ren.tools.system import SystemStatusTool, BatteryStatusTool, ProcessListTool
from ren.tools.project import InspectProjectTool
from ren.tools.git import GitStatusTool, GitDiffTool, GitCommitTool, GitLogTool
from ren.tools.web_search import WebSearchTool
from ren.tools.generate_image import GenerateImageTool

__all__ = [
    "BaseTool",
    "ToolResult",
    "tool_registry",
    "ToolRegistry",
    "ReadFileTool",
    "WriteFileTool",
    "ListDirectoryTool",
    "SearchFilesTool",
    "DeleteFileTool",
    "TerminalTool",
    "PythonRunnerTool",
    "SystemStatusTool",
    "BatteryStatusTool",
    "ProcessListTool",
    "InspectProjectTool",
    "GitStatusTool",
    "GitDiffTool",
    "GitCommitTool",
    "GitLogTool",
    "WebSearchTool",
    "GenerateImageTool",
]
