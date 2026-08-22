"""
REN Configuration and Settings Module
Provides centralized, strongly typed configuration with environment overrides and Pathlib support.
"""

import os
from dataclasses import dataclass, field
from pathlib import Path
from typing import List, Optional


@dataclass
class PathSettings:
    """Workspace and data directory paths."""
    ROOT_DIR: Path = field(default_factory=lambda: Path(__file__).resolve().parent.parent.parent)
    DATA_DIR: Path = field(init=False)
    LOGS_DIR: Path = field(init=False)
    SKILLS_DIR: Path = field(init=False)
    ACTIVE_SKILLS_DIR: Path = field(init=False)
    QUARANTINE_SKILLS_DIR: Path = field(init=False)
    BACKUP_SKILLS_DIR: Path = field(init=False)
    SESSIONS_DIR: Path = field(init=False)
    BOOKS_DIR: Path = field(init=False)
    CHATS_DIR: Path = field(init=False)
    DB_PATH: Path = field(init=False)
    LEGACY_MEMORY_FILE: Path = field(init=False)
    ERROR_LOG_FILE: Path = field(init=False)
    DREAM_LOG_FILE: Path = field(init=False)

    def __post_init__(self):
        self.DATA_DIR = self.ROOT_DIR / "data"
        self.LOGS_DIR = self.ROOT_DIR / "logs"
        self.SKILLS_DIR = self.ROOT_DIR / "skills"
        self.ACTIVE_SKILLS_DIR = self.SKILLS_DIR / "active"
        self.QUARANTINE_SKILLS_DIR = self.SKILLS_DIR / "quarantine"
        self.BACKUP_SKILLS_DIR = self.SKILLS_DIR / "backups"
        self.SESSIONS_DIR = self.DATA_DIR / "sessions"
        self.BOOKS_DIR = self.ROOT_DIR / "books"
        self.CHATS_DIR = self.ROOT_DIR / "chats"
        self.DB_PATH = self.DATA_DIR / "ren_memory.db"
        self.LEGACY_MEMORY_FILE = self.ROOT_DIR / "memory.json"
        self.ERROR_LOG_FILE = self.ROOT_DIR / "error_log.json"
        self.DREAM_LOG_FILE = self.ROOT_DIR / "dream_history.log"

        # Ensure essential directories exist
        for d in [
            self.DATA_DIR,
            self.LOGS_DIR,
            self.SKILLS_DIR,
            self.ACTIVE_SKILLS_DIR,
            self.QUARANTINE_SKILLS_DIR,
            self.BACKUP_SKILLS_DIR,
            self.SESSIONS_DIR,
            self.BOOKS_DIR,
            self.CHATS_DIR,
        ]:
            d.mkdir(parents=True, exist_ok=True)


@dataclass
class ModelSettings:
    """Model provider configuration."""
    PROVIDER: str = os.getenv("REN_MODEL_PROVIDER", "ollama")
    OLLAMA_HOST: str = os.getenv("REN_OLLAMA_HOST", "http://localhost:11434")
    OLLAMA_GENERATE_ENDPOINT: str = os.getenv("REN_OLLAMA_ENDPOINT", "http://localhost:11434/api/generate")
    MODEL_NAME: str = os.getenv("REN_MODEL_NAME", "qwen2.5-coder:1.5b")
    DEFAULT_TEMPERATURE: float = float(os.getenv("REN_TEMPERATURE", "0.4"))
    MAX_TOKENS_SIMPLE: int = int(os.getenv("REN_MAX_TOKENS_SIMPLE", "96"))
    MAX_TOKENS_AGENT: int = int(os.getenv("REN_MAX_TOKENS_AGENT", "192"))
    MAX_TOKENS_PLANNING: int = int(os.getenv("REN_MAX_TOKENS_PLANNING", "128"))
    NUM_CTX: int = int(os.getenv("REN_NUM_CTX", "1024"))
    TIMEOUT_SECONDS: int = int(os.getenv("REN_LLM_TIMEOUT", "60"))


@dataclass
class AgentSettings:
    """Autonomous agent loop and context settings."""
    MAX_LOOP_ITERATIONS: int = int(os.getenv("REN_MAX_LOOP_STEPS", "6"))
    STEP_TIMEOUT_SECONDS: int = int(os.getenv("REN_STEP_TIMEOUT", "45"))
    MAX_REPEATED_FAILURES: int = 2
    LOOP_DETECTION_WINDOW: int = 3
    CONTEXT_BUDGET_TOKENS: int = int(os.getenv("REN_CONTEXT_BUDGET", "800"))
    MEMORY_BUDGET_TOKENS: int = int(os.getenv("REN_MEMORY_BUDGET", "200"))
    SKILLS_BUDGET_TOKENS: int = int(os.getenv("REN_SKILLS_BUDGET", "200"))
    HISTORY_BUDGET_TOKENS: int = int(os.getenv("REN_HISTORY_BUDGET", "300"))
    ENABLE_SELF_HEALING: bool = True
    ENABLE_DRY_RUN: bool = False


@dataclass
class SecuritySettings:
    """Permission and sandboxing security levels."""
    AUTO_APPROVE_SAFE: bool = True
    REQUIRE_CONFIRMATION_FOR_MODIFICATIONS: bool = True
    ALLOW_SHELL_COMMANDS: bool = True
    ALLOW_ARBITRARY_PYTHON: bool = False  # Prefer structured tools & validated skills
    RESTRICT_TO_WORKSPACE: bool = False
    BLOCKED_COMMANDS: List[str] = field(default_factory=lambda: [
        "rmdir /s /q c:\\",
        "rmdir /s /q c:\\windows",
        "format",
        "del /f /s /q c:\\windows",
        ":(){ :|:& };:",
        "mkfs",
        "dd if=/dev/zero",
        "aircrack-ng",
        "airodump-ng",
        "airmon-ng",
        "wifite",
        "reaver",
        "pixiewps",
        "hydra",
        "hashcat",
    ])


@dataclass
class SystemSettings:
    """Overall system settings and persona."""
    ASSISTANT_NAME: str = "Ren"
    CREATOR_NAME: str = "Sadiq"
    CREATOR_NICKNAME: str = "Cyan Code"
    VERSION: str = "2.5.0"
    LOG_LEVEL: str = os.getenv("REN_LOG_LEVEL", "INFO")
    PATHS: PathSettings = field(default_factory=PathSettings)
    MODEL: ModelSettings = field(default_factory=ModelSettings)
    AGENT: AgentSettings = field(default_factory=AgentSettings)
    SECURITY: SecuritySettings = field(default_factory=SecuritySettings)


# Global singleton settings instance
settings = SystemSettings()
