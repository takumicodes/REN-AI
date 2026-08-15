"""
Filesystem Tools
Safe file reading, writing, directory listing, searching, and deleting.
"""

import os
import time
from pathlib import Path
from typing import Dict, Any, List, Optional

from ren.tools.base import BaseTool, ToolResult
from ren.security.permissions import PermissionCategory
from ren.config.settings import settings


class ReadFileTool(BaseTool):
    name = "read_file"
    description = "Read UTF-8 text content from a file path."
    required_permissions = [PermissionCategory.FILESYSTEM_READ]
    parameters_schema = {
        "type": "object",
        "properties": {
            "path": {"type": "string", "description": "Absolute or relative file path to read."},
            "max_lines": {"type": "integer", "description": "Optional line limit (default: 300)."}
        },
        "required": ["path"]
    }

    def run(self, path: str, max_lines: int = 300, **kwargs) -> ToolResult:
        start_t = time.perf_counter()
        target = Path(path).expanduser()
        if not target.is_absolute():
            target = settings.PATHS.ROOT_DIR / target

        if not target.exists():
            return ToolResult(
                success=False,
                error=f"File not found: {path}",
                exit_code=1,
                duration=time.perf_counter() - start_t
            )

        if not target.is_file():
            return ToolResult(
                success=False,
                error=f"Path is a directory, not a file: {path}",
                exit_code=1,
                duration=time.perf_counter() - start_t
            )

        try:
            with open(target, "r", encoding="utf-8", errors="replace") as f:
                lines = f.readlines()

            total_lines = len(lines)
            content = "".join(lines[:max_lines])
            if total_lines > max_lines:
                content += f"\n\n[... Truncated: Showing {max_lines} of {total_lines} total lines ...]"

            return ToolResult(
                success=True,
                output=content,
                duration=time.perf_counter() - start_t
            )
        except Exception as e:
            return ToolResult(
                success=False,
                error=f"Error reading file: {e}",
                exit_code=1,
                duration=time.perf_counter() - start_t
            )


class WriteFileTool(BaseTool):
    name = "write_file"
    description = "Write or overwrite text content to a file path safely."
    required_permissions = [PermissionCategory.FILESYSTEM_WRITE]
    parameters_schema = {
        "type": "object",
        "properties": {
            "path": {"type": "string", "description": "File path to create or write."},
            "content": {"type": "string", "description": "Text content to write."}
        },
        "required": ["path", "content"]
    }

    def run(self, path: str, content: str, **kwargs) -> ToolResult:
        start_t = time.perf_counter()
        target = Path(path).expanduser()
        if not target.is_absolute():
            target = settings.PATHS.ROOT_DIR / target

        try:
            target.parent.mkdir(parents=True, exist_ok=True)
            with open(target, "w", encoding="utf-8") as f:
                f.write(content)

            return ToolResult(
                success=True,
                output=f"Successfully wrote {len(content)} bytes to {target.name}",
                duration=time.perf_counter() - start_t
            )
        except Exception as e:
            return ToolResult(
                success=False,
                error=f"Failed writing file: {e}",
                exit_code=1,
                duration=time.perf_counter() - start_t
            )


class ListDirectoryTool(BaseTool):
    name = "list_directory"
    description = "List files and subdirectories at a given directory path."
    required_permissions = [PermissionCategory.FILESYSTEM_READ]
    parameters_schema = {
        "type": "object",
        "properties": {
            "path": {"type": "string", "description": "Directory path (default: current directory)."}
        }
    }

    def run(self, path: str = ".", **kwargs) -> ToolResult:
        start_t = time.perf_counter()
        target = Path(path).expanduser()
        if not target.is_absolute():
            target = settings.PATHS.ROOT_DIR / target

        if not target.exists():
            return ToolResult(
                success=False,
                error=f"Directory does not exist: {path}",
                exit_code=1,
                duration=time.perf_counter() - start_t
            )

        try:
            entries = []
            for item in target.iterdir():
                if item.name.startswith(".") and item.name not in [".gitignore"]:
                    continue
                type_label = "<DIR>" if item.is_dir() else f"{item.stat().st_size} B"
                entries.append(f"{item.name:<30} {type_label}")

            entries.sort()
            output = f"Directory listing for: {target}\n" + "\n".join(entries[:100])
            if len(entries) > 100:
                output += f"\n... and {len(entries) - 100} more items."

            return ToolResult(
                success=True,
                output=output,
                duration=time.perf_counter() - start_t
            )
        except Exception as e:
            return ToolResult(
                success=False,
                error=f"Failed listing directory: {e}",
                exit_code=1,
                duration=time.perf_counter() - start_t
            )


class SearchFilesTool(BaseTool):
    name = "search_files"
    description = "Search for files matching a pattern or containing text."
    required_permissions = [PermissionCategory.FILESYSTEM_READ]
    parameters_schema = {
        "type": "object",
        "properties": {
            "directory": {"type": "string", "description": "Root directory to search in."},
            "pattern": {"type": "string", "description": "Glob pattern (e.g. '*.py' or '*test*')."},
            "query": {"type": "string", "description": "Optional text to grep within files."}
        },
        "required": ["pattern"]
    }

    def run(self, pattern: str, directory: str = ".", query: Optional[str] = None, **kwargs) -> ToolResult:
        start_t = time.perf_counter()
        target = Path(directory).expanduser()
        if not target.is_absolute():
            target = settings.PATHS.ROOT_DIR / target

        matches = []
        try:
            for p in target.rglob(pattern):
                if any(part.startswith(".") or part in ["node_modules", "__pycache__", "venv", ".venv", "dist", "build"] for part in p.parts):
                    continue
                if p.is_file():
                    if query:
                        try:
                            with open(p, "r", encoding="utf-8", errors="ignore") as f:
                                if query.lower() in f.read().lower():
                                    matches.append(str(p.relative_to(target)))
                        except Exception:
                            pass
                    else:
                        matches.append(str(p.relative_to(target)))
                if len(matches) >= 50:
                    break

            if not matches:
                output = f"No files matched pattern '{pattern}'"
            else:
                output = f"Found {len(matches)} matching files:\n" + "\n".join(matches)

            return ToolResult(
                success=True,
                output=output,
                duration=time.perf_counter() - start_t
            )
        except Exception as e:
            return ToolResult(
                success=False,
                error=f"Search failed: {e}",
                exit_code=1,
                duration=time.perf_counter() - start_t
            )


class DeleteFileTool(BaseTool):
    name = "delete_file"
    description = "Delete a specified file permanently. Requires high-risk confirmation."
    required_permissions = [PermissionCategory.FILESYSTEM_DELETE]
    parameters_schema = {
        "type": "object",
        "properties": {
            "path": {"type": "string", "description": "Path to file to delete."}
        },
        "required": ["path"]
    }

    def run(self, path: str, **kwargs) -> ToolResult:
        start_t = time.perf_counter()
        target = Path(path).expanduser()
        if not target.is_absolute():
            target = settings.PATHS.ROOT_DIR / target

        if not target.exists():
            return ToolResult(
                success=False,
                error=f"Target file does not exist: {path}",
                exit_code=1,
                duration=time.perf_counter() - start_t
            )

        try:
            if target.is_dir():
                import shutil
                shutil.rmtree(target)
            else:
                target.unlink()

            return ToolResult(
                success=True,
                output=f"Successfully deleted {path}",
                duration=time.perf_counter() - start_t
            )
        except Exception as e:
            return ToolResult(
                success=False,
                error=f"Failed to delete {path}: {e}",
                exit_code=1,
                duration=time.perf_counter() - start_t
            )
