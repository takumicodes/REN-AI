"""
REN-AI Minecraft Types and Data Structures
Defines typed models for Goals, Tasks, Subtasks, Action Results, Perception, and Priorities.
"""

from enum import Enum
from dataclasses import dataclass, field
from typing import Dict, Any, List, Optional


class TaskStatus(str, Enum):
    PENDING = "PENDING"
    IN_PROGRESS = "IN_PROGRESS"
    COMPLETED = "COMPLETED"
    FAILED = "FAILED"
    CANCELLED = "CANCELLED"
    RETRYING = "RETRYING"


class SurvivalPriority(str, Enum):
    CRITICAL = "CRITICAL"    # Life preservation, combat defense, emergency eating
    HIGH = "HIGH"            # Shelter before night, tool acquisition, food supply
    MEDIUM = "MEDIUM"        # Resource mining, iron tech, base building
    LOW = "LOW"              # Curiosity, exploration, idle chat


@dataclass
class Goal:
    """Structured high-level goal parsed from natural language or autonomy."""
    goal_type: str
    parameters: Dict[str, Any] = field(default_factory=dict)
    raw_text: str = ""
    target_player: Optional[str] = None
    priority: int = 100
    created_at: float = 0.0

    def to_dict(self) -> Dict[str, Any]:
        return {
            "goal_type": self.goal_type,
            "parameters": self.parameters,
            "raw_text": self.raw_text,
            "target_player": self.target_player,
            "priority": self.priority,
            "created_at": self.created_at
        }

    @classmethod
    def from_dict(cls, d: Dict[str, Any]) -> "Goal":
        return cls(
            goal_type=d.get("goal_type", "UNKNOWN"),
            parameters=d.get("parameters", {}),
            raw_text=d.get("raw_text", ""),
            target_player=d.get("target_player"),
            priority=d.get("priority", 100),
            created_at=d.get("created_at", 0.0)
        )


@dataclass
class Subtask:
    """Atomic executable action step in a larger Task plan."""
    id: str
    action: str
    parameters: Dict[str, Any] = field(default_factory=dict)
    status: TaskStatus = TaskStatus.PENDING
    attempts: int = 0
    max_attempts: int = 3
    error: Optional[str] = None
    result_details: Dict[str, Any] = field(default_factory=dict)

    def to_dict(self) -> Dict[str, Any]:
        return {
            "id": self.id,
            "action": self.action,
            "parameters": self.parameters,
            "status": self.status.value,
            "attempts": self.attempts,
            "max_attempts": self.max_attempts,
            "error": self.error,
            "result_details": self.result_details
        }

    @classmethod
    def from_dict(cls, d: Dict[str, Any]) -> "Subtask":
        return cls(
            id=d.get("id", ""),
            action=d.get("action", ""),
            parameters=d.get("parameters", {}),
            status=TaskStatus(d.get("status", "PENDING")),
            attempts=d.get("attempts", 0),
            max_attempts=d.get("max_attempts", 3),
            error=d.get("error"),
            result_details=d.get("result_details", {})
        )


@dataclass
class Task:
    """Persistent hierarchical task consisting of sequentially verified subtasks."""
    id: str
    name: str
    goal: Goal
    subtasks: List[Subtask] = field(default_factory=list)
    status: TaskStatus = TaskStatus.PENDING
    current_subtask_index: int = 0
    created_at: float = 0.0
    updated_at: float = 0.0
    failure_reason: Optional[str] = None

    @property
    def progress_percentage(self) -> float:
        if not self.subtasks:
            return 0.0
        completed = sum(1 for s in self.subtasks if s.status == TaskStatus.COMPLETED)
        return round((completed / len(self.subtasks)) * 100.0, 1)

    @property
    def current_subtask(self) -> Optional[Subtask]:
        if 0 <= self.current_subtask_index < len(self.subtasks):
            return self.subtasks[self.current_subtask_index]
        return None

    def to_dict(self) -> Dict[str, Any]:
        return {
            "id": self.id,
            "name": self.name,
            "goal": self.goal.to_dict(),
            "subtasks": [s.to_dict() for s in self.subtasks],
            "status": self.status.value,
            "current_subtask_index": self.current_subtask_index,
            "created_at": self.created_at,
            "updated_at": self.updated_at,
            "failure_reason": self.failure_reason,
            "progress_percentage": self.progress_percentage
        }

    @classmethod
    def from_dict(cls, d: Dict[str, Any]) -> "Task":
        return cls(
            id=d.get("id", ""),
            name=d.get("name", "Task"),
            goal=Goal.from_dict(d.get("goal", {})),
            subtasks=[Subtask.from_dict(s) for s in d.get("subtasks", [])],
            status=TaskStatus(d.get("status", "PENDING")),
            current_subtask_index=d.get("current_subtask_index", 0),
            created_at=d.get("created_at", 0.0),
            updated_at=d.get("updated_at", 0.0),
            failure_reason=d.get("failure_reason")
        )


@dataclass
class ActionResult:
    """Structured result returned by the Minecraft execution engine."""
    success: bool
    action: str
    reason: Optional[str] = None
    details: Dict[str, Any] = field(default_factory=dict)
    task_id: Optional[str] = None
    verification: Optional[Dict[str, Any]] = None

    def to_dict(self) -> Dict[str, Any]:
        return {
            "success": self.success,
            "action": self.action,
            "reason": self.reason,
            "details": self.details,
            "task_id": self.task_id,
            "verification": self.verification
        }


@dataclass
class PerceptionSummary:
    """Compact, structured representation of the world state for decision making."""
    hp: int = 20
    food: int = 20
    pos: Dict[str, float] = field(default_factory=lambda: {"x": 0.0, "y": 64.0, "z": 0.0})
    inventory: Dict[str, int] = field(default_factory=dict)
    total_logs: int = 0
    total_planks: int = 0
    total_cobblestone: int = 0
    total_iron: int = 0
    total_food: int = 0
    total_building_blocks: int = 0
    entities: List[Dict[str, Any]] = field(default_factory=list)
    hostile_entities: List[Dict[str, Any]] = field(default_factory=list)
    passive_entities: List[Dict[str, Any]] = field(default_factory=list)
    nearest_player: Optional[str] = None
    nearest_player_distance: float = 999.0
    time_of_day: str = "day"
    threat_level: str = "SAFE"
    has_weapon: bool = False
    has_pickaxe: bool = False
    has_axe: bool = False
    has_shield: bool = False
    has_shelter: bool = False
    equipped_weapon: Optional[str] = None
