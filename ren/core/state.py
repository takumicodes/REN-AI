"""
Agent State and Execution Context
Tracks runtime execution lifecycle, loop bounds, and active conversation state.
"""

from enum import Enum
from dataclasses import dataclass, field
from typing import List, Dict, Any, Optional
from datetime import datetime

from ren.sessions.models import Session, Plan, PlanStep


class AgentLifecycle(str, Enum):
    IDLE = "idle"
    PROMPT = "prompt"
    INTENT = "intent"
    PLAN = "plan"
    TOOLS = "tools"
    EXEC = "exec"
    VERIFY = "verify"
    ERROR = "error"
    COMPLETED = "completed"


@dataclass
class ExecutionContext:
    user_query: str
    session: Session
    state: AgentLifecycle = AgentLifecycle.IDLE
    current_iteration: int = 0
    max_iterations: int = 8
    active_plan: Optional[Plan] = None
    selected_skills: List[str] = field(default_factory=list)
    last_tool_name: Optional[str] = None
    last_tool_args: Optional[Dict[str, Any]] = None
    last_tool_output: Optional[str] = None
    consecutive_failures: int = 0
    executed_actions_history: List[str] = field(default_factory=list)
    is_cancelled: bool = False
    started_at: str = field(default_factory=lambda: datetime.utcnow().isoformat())

    def record_action(self, action_signature: str):
        self.executed_actions_history.append(action_signature)

    def is_looping(self, window: int = 3) -> bool:
        """Detects if the last N actions were identical."""
        if len(self.executed_actions_history) < window:
            return False
        recent = self.executed_actions_history[-window:]
        return len(set(recent)) == 1
