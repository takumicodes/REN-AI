"""
Base Tool Interface and ToolResult Specification
Defines standard schema, structured results, and execution contracts for all agent tools.
"""

from abc import ABC, abstractmethod
from dataclasses import dataclass, asdict
from typing import Dict, Any, List, Optional, Tuple
import time

from ren.security.permissions import PermissionCategory


@dataclass
class ToolResult:
    """Structured execution result returned by all tools."""
    success: bool
    output: str = ""
    error: Optional[str] = None
    exit_code: int = 0
    duration: float = 0.0

    def to_dict(self) -> Dict[str, Any]:
        return {
            "success": self.success,
            "output": self.output,
            "error": self.error,
            "exit_code": self.exit_code,
            "duration": round(self.duration, 3),
        }

    def __str__(self) -> str:
        if self.success:
            return self.output
        return f"Error: {self.error or 'Unknown failure'}"


class BaseTool(ABC):
    """Abstract base class for all REN tools."""

    name: str = ""
    description: str = ""
    parameters_schema: Dict[str, Any] = {}
    required_permissions: List[PermissionCategory] = []
    timeout: int = 30

    @abstractmethod
    def run(self, **kwargs) -> ToolResult:
        """Executes the tool logic with given validated arguments."""
        pass

    def validate_args(self, kwargs: Dict[str, Any]) -> Tuple[bool, Optional[str]]:
        """Validates that required parameters exist."""
        required = self.parameters_schema.get("required", [])
        for req in required:
            if req not in kwargs:
                return False, f"Missing required parameter '{req}' for tool '{self.name}'"
        return True, None
