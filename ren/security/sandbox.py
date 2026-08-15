"""
REN Execution Sandbox
Provides controlled subprocess execution layer with timeouts, working directory restrictions,
environment variable sanitization, and resource limits.
"""

import os
import sys
import subprocess
import tempfile
from pathlib import Path
from typing import Dict, Any, Optional, Tuple

from ren.config.settings import settings
from ren.monitoring.logger import security_logger, tools_logger


class ExecutionSandbox:
    """Bounded subprocess execution sandbox for local operations."""

    SENSITIVE_ENV_KEYS = {
        "AWS_SECRET_ACCESS_KEY",
        "GITHUB_TOKEN",
        "GH_TOKEN",
        "OPENAI_API_KEY",
        "ANTHROPIC_API_KEY",
        "TOKEN",
        "PASSWORD",
        "SECRET",
    }

    @classmethod
    def get_sanitized_env(cls) -> Dict[str, str]:
        """Returns environment dictionary filtered of high-risk secrets."""
        safe_env = os.environ.copy()
        for key in list(safe_env.keys()):
            upper_key = key.upper()
            if any(s in upper_key for s in cls.SENSITIVE_ENV_KEYS):
                safe_env.pop(key, None)
        # Ensure UTF-8 Python output
        safe_env["PYTHONIOENCODING"] = "utf-8"
        return safe_env

    @classmethod
    def execute_command(
        cls,
        command: str,
        cwd: Optional[Path] = None,
        timeout: Optional[int] = None,
        max_output_chars: int = 8000,
    ) -> Tuple[bool, str, str, int]:
        """
        Runs a shell command within a restricted subprocess.
        Returns: (success: bool, stdout: str, stderr: str, exit_code: int)
        """
        working_dir = str(cwd or settings.PATHS.ROOT_DIR)
        exec_timeout = timeout or settings.AGENT.STEP_TIMEOUT_SECONDS
        env = cls.get_sanitized_env()

        tools_logger.info(f"Sandbox executing command: '{command}' in {working_dir} (timeout={exec_timeout}s)")

        try:
            # On Windows use shell=True for standard built-ins (dir, echo) or list for executables
            process = subprocess.Popen(
                command,
                cwd=working_dir,
                env=env,
                shell=True,
                stdout=subprocess.PIPE,
                stderr=subprocess.PIPE,
                text=True,
                encoding="utf-8",
                errors="replace",
            )

            try:
                stdout, stderr = process.communicate(timeout=exec_timeout)
                exit_code = process.returncode
                success = (exit_code == 0)
            except subprocess.TimeoutExpired:
                process.kill()
                stdout, stderr = process.communicate()
                tools_logger.warning(f"Process timed out after {exec_timeout}s: {command}")
                return False, "", f"Execution timed out after {exec_timeout} seconds.", -1

            # Truncate if excessively large to protect RAM and context budget
            if len(stdout) > max_output_chars:
                stdout = stdout[:max_output_chars] + f"\n\n[... Output truncated ({len(stdout)} chars) ...]"
            if len(stderr) > max_output_chars:
                stderr = stderr[:max_output_chars] + f"\n\n[... Stderr truncated ({len(stderr)} chars) ...]"

            return success, stdout.strip(), stderr.strip(), exit_code

        except Exception as e:
            security_logger.error(f"Sandbox execution error for '{command}': {e}")
            return False, "", str(e), -1

    @classmethod
    def execute_python_code(
        cls,
        code: str,
        cwd: Optional[Path] = None,
        timeout: Optional[int] = None,
    ) -> Tuple[bool, str, str, int]:
        """
        Executes Python code in an isolated child process via python executable,
        preventing crashing or polluting the main runtime process.
        """
        with tempfile.NamedTemporaryFile(
            mode="w",
            suffix=".py",
            delete=False,
            encoding="utf-8"
        ) as tmp:
            tmp.write(code)
            tmp_path = tmp.name

        try:
            cmd = f'"{sys.executable}" "{tmp_path}"'
            return cls.execute_command(cmd, cwd=cwd, timeout=timeout)
        finally:
            try:
                if os.path.exists(tmp_path):
                    os.unlink(tmp_path)
            except Exception:
                pass
