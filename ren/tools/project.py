"""
Autonomous Project Awareness Tools
Detects project frameworks, entrypoints, Git repositories, and creates compact project summaries.
"""

import os
import time
from pathlib import Path
from typing import Dict, Any, List, Optional

from ren.tools.base import BaseTool, ToolResult
from ren.security.permissions import PermissionCategory
from ren.config.settings import settings
from ren.memory.manager import memory_manager


class ProjectInspector:
    """Detects languages, frameworks, and architecture patterns of software projects."""

    @staticmethod
    def inspect(directory: Path) -> Dict[str, Any]:
        result = {
            "name": directory.name,
            "path": str(directory),
            "is_git": (directory / ".git").exists(),
            "languages": [],
            "frameworks": [],
            "key_files": [],
            "entrypoints": [],
        }

        # Language signatures
        if any(directory.glob("*.py")) or (directory / "requirements.txt").exists() or (directory / "pyproject.toml").exists():
            result["languages"].append("Python")
        if (directory / "package.json").exists() or (directory / "tsconfig.json").exists():
            result["languages"].append("JavaScript/TypeScript")
        if (directory / "Cargo.toml").exists():
            result["languages"].append("Rust")
        if (directory / "CMakeLists.txt").exists() or any(directory.glob("*.cpp")):
            result["languages"].append("C/C++")
        if (directory / "project.godot").exists():
            result["frameworks"].append("Godot Engine")

        # Framework detection
        if (directory / "requirements.txt").exists():
            try:
                with open(directory / "requirements.txt", "r", encoding="utf-8", errors="ignore") as f:
                    reqs = f.read().lower()
                    if "pywebview" in reqs:
                        result["frameworks"].append("PyWebView")
                    if "fastapi" in reqs:
                        result["frameworks"].append("FastAPI")
                    if "flask" in reqs:
                        result["frameworks"].append("Flask")
                    if "django" in reqs:
                        result["frameworks"].append("Django")
                    if "torch" in reqs or "pytorch" in reqs:
                        result["frameworks"].append("PyTorch")
                    if "opencv" in reqs:
                        result["frameworks"].append("OpenCV")
            except Exception:
                pass

        # Identify key entrypoints and files
        candidates = [
            "gui.py", "main.py", "app.py", "index.py", "back_end.py",
            "index.html", "package.json", "requirements.txt", "pyproject.toml",
            "README.md", "memory.json"
        ]
        for c in candidates:
            if (directory / c).exists():
                result["key_files"].append(c)
                if c.endswith((".py", ".js", ".ts", ".html")) and c not in ["package.json", "requirements.txt"]:
                    result["entrypoints"].append(c)

        return result


class InspectProjectTool(BaseTool):
    name = "inspect_project"
    description = "Inspect a codebase directory to automatically identify language, framework, key files, and git status."
    required_permissions = [PermissionCategory.FILESYSTEM_READ]
    parameters_schema = {
        "type": "object",
        "properties": {
            "path": {"type": "string", "description": "Path to project folder (default: root directory)."}
        }
    }

    def run(self, path: str = ".", **kwargs) -> ToolResult:
        start_t = time.perf_counter()
        target = Path(path).expanduser()
        if not target.is_absolute():
            target = settings.PATHS.ROOT_DIR / target

        if not target.exists() or not target.is_dir():
            return ToolResult(
                success=False,
                error=f"Directory not found: {path}",
                exit_code=1,
                duration=time.perf_counter() - start_t
            )

        try:
            info = ProjectInspector.inspect(target)
            
            # Format report
            lines = [
                f"PROJECT: {info['name']}",
                f"Location: {info['path']}",
                f"Git Repository: {'Yes' if info['is_git'] else 'No'}",
                f"Languages: {', '.join(info['languages']) or 'Generic'}",
                f"Frameworks: {', '.join(info['frameworks']) or 'Standard'}",
                f"Key Files: {', '.join(info['key_files'])}",
                f"Entrypoints: {', '.join(info['entrypoints']) or 'None detected'}",
            ]

            # Upsert into persistent project memory
            memory_manager.upsert_project(
                name=info['name'],
                path=info['path'],
                language=", ".join(info['languages']),
                framework=", ".join(info['frameworks']),
                important_files=info['key_files'],
            )

            return ToolResult(
                success=True,
                output="\n".join(lines),
                duration=time.perf_counter() - start_t
            )
        except Exception as e:
            return ToolResult(
                success=False,
                error=f"Project inspection error: {e}",
                exit_code=1,
                duration=time.perf_counter() - start_t
            )
