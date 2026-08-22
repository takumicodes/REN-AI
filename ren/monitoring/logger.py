"""
REN Structured Logging System
Provides category-specific structured loggers with safe formatting and sensitive data redaction.
"""

import logging
import re
from pathlib import Path
from typing import Optional
from ren.config.settings import settings

# Regex patterns for sanitizing sensitive data
SECRET_PATTERNS = [
    re.compile(r'(api[_-]?key|password|secret|token|bearer)\s*[:=]\s*["\']?([^"\'\s]+)["\']?', re.IGNORECASE),
    re.compile(r'(sk-[a-zA-Z0-9]{20,})', re.IGNORECASE),
    re.compile(r'(ghp_[a-zA-Z0-9]{20,})', re.IGNORECASE),
]


class SensitiveDataFilter(logging.Filter):
    """Redacts secrets and sensitive information from log messages."""

    def filter(self, record: logging.LogRecord) -> bool:
        if isinstance(record.msg, str):
            record.msg = self.sanitize(record.msg)
        if record.args:
            if isinstance(record.args, dict):
                record.args = {k: self.sanitize(str(v)) for k, v in record.args.items()}
            elif isinstance(record.args, tuple):
                record.args = tuple(self.sanitize(str(arg)) for arg in record.args)
        return True

    @staticmethod
    def sanitize(text: str) -> str:
        if not isinstance(text, str):
            return str(text)
        try:
            text = re.sub(r'(?i)(api[_-]?key|password|secret|token|bearer)\s*[:=]\s*["\']?[^"\'\s\n]+["\']?', r'\1: [REDACTED]', text)
            text = re.sub(r'(?i)sk-[a-zA-Z0-9]{20,}', '[REDACTED_KEY]', text)
            text = re.sub(r'(?i)ghp_[a-zA-Z0-9]{20,}', '[REDACTED_TOKEN]', text)
        except Exception:
            pass
        return text


_loggers_configured = False


def setup_loggers():
    """Initializes dedicated file loggers for each subsystem."""
    global _loggers_configured
    if _loggers_configured:
        return

    logs_dir = settings.PATHS.LOGS_DIR
    logs_dir.mkdir(parents=True, exist_ok=True)

    log_format = logging.Formatter(
        "[%(asctime)s] [%(levelname)s] [%(name)s]: %(message)s",
        datefmt="%Y-%m-%d %H:%M:%S"
    )
    secret_filter = SensitiveDataFilter()

    # Logger categories
    categories = {
        "ren.agent": logs_dir / "agent.log",
        "ren.tools": logs_dir / "tools.log",
        "ren.memory": logs_dir / "memory.log",
        "ren.errors": logs_dir / "errors.log",
        "ren.performance": logs_dir / "performance.log",
        "ren.skills": logs_dir / "skills.log",
        "ren.security": logs_dir / "security.log",
    }

    for name, file_path in categories.items():
        logger = logging.getLogger(name)
        logger.setLevel(getattr(logging, settings.LOG_LEVEL.upper(), logging.INFO))
        logger.addFilter(secret_filter)

        # File handler
        fh = logging.FileHandler(file_path, encoding="utf-8")
        fh.setFormatter(log_format)
        fh.addFilter(secret_filter)
        logger.addHandler(fh)

        # Console handler for main agent and errors
        if name in ["ren.agent", "ren.errors"]:
            ch = logging.StreamHandler()
            ch.setFormatter(log_format)
            ch.addFilter(secret_filter)
            logger.addHandler(ch)

    _loggers_configured = True


# Initialize at import
setup_loggers()

# Helper accessors
agent_logger = logging.getLogger("ren.agent")
tools_logger = logging.getLogger("ren.tools")
memory_logger = logging.getLogger("ren.memory")
error_logger = logging.getLogger("ren.errors")
perf_logger = logging.getLogger("ren.performance")
skills_logger = logging.getLogger("ren.skills")
security_logger = logging.getLogger("ren.security")
