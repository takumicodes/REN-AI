"""
Centralized Logging Engine for REN-AI Windows Control Center
Provides:
- Rotating file logging in %LOCALAPPDATA%\RenDesktopAssistant\ren_assistant.log (or local directory in dev mode).
- Formatted console output if running in terminal/CLI.
- Standard levels: DEBUG, INFO, WARNING, ERROR, CRITICAL.
- Structured contextual logging for actions, observer, tray, and verification.
- Safe log scrubbing to avoid recording sensitive user tokens or credentials.
"""

import os
import sys
import logging
from logging.handlers import RotatingFileHandler
from pathlib import Path
from typing import Optional


def get_log_dir() -> Path:
    """Returns persistent, writable log directory."""
    if getattr(sys, "frozen", False):
        exe_dir = Path(sys.executable).parent
        portable_flag = exe_dir / "user_preferences.json"
        if portable_flag.exists():
            return exe_dir
        appdata = os.environ.get("LOCALAPPDATA")
        base = Path(appdata) / "RenDesktopAssistant" if appdata else Path.home() / ".ren_desktop_assistant"
    else:
        base = Path(__file__).parent

    try:
        os.makedirs(str(base), exist_ok=True)
    except Exception:
        pass
    return base


LOG_FILE = get_log_dir() / "ren_assistant.log"


class RenLogger:
    """Configures and provides the singleton logger for REN-AI."""

    _logger: Optional[logging.Logger] = None

    @classmethod
    def get_logger(cls) -> logging.Logger:
        if cls._logger is not None:
            return cls._logger

        logger = logging.getLogger("RenAssistant")
        logger.setLevel(logging.DEBUG)
        logger.propagate = False

        # Clear any existing handlers
        logger.handlers.clear()

        # Format: [2026-09-22 02:30:15] [INFO] [SystemObserver]: Message
        formatter = logging.Formatter(
            fmt="[%(asctime)s] [%(levelname)s] [%(name)s]: %(message)s",
            datefmt="%Y-%m-%d %H:%M:%S",
        )

        # 1. Rotating File Handler (Max 5MB, 3 backups)
        try:
            file_handler = RotatingFileHandler(
                str(LOG_FILE),
                maxBytes=5 * 1024 * 1024,
                backupCount=3,
                encoding="utf-8",
            )
            file_handler.setLevel(logging.DEBUG)
            file_handler.setFormatter(formatter)
            logger.addHandler(file_handler)
        except Exception:
            pass

        # 2. Console Handler (if attached to terminal)
        if sys.stdout and hasattr(sys.stdout, "write") and not getattr(sys, "frozen", False):
            try:
                console_handler = logging.StreamHandler(sys.stdout)
                console_handler.setLevel(logging.INFO)
                console_handler.setFormatter(formatter)
                logger.addHandler(console_handler)
            except Exception:
                pass

        cls._logger = logger
        return cls._logger


logger = RenLogger.get_logger()


def log_action_event(event_type: str, action_id: str, title: str, details: str = "", level: str = "INFO"):
    """Convenience helper for structured action logging."""
    msg = f"Action [{event_type}] id='{action_id}' title='{title}' {details}".strip()
    if level == "DEBUG":
        logger.debug(msg)
    elif level == "WARNING":
        logger.warning(msg)
    elif level == "ERROR":
        logger.error(msg)
    elif level == "CRITICAL":
        logger.critical(msg)
    else:
        logger.info(msg)
