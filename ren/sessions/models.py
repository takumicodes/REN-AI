"""
Session Data Models
Defines strongly-typed dataclasses for persistent conversation sessions, messages, and plans.
"""

import uuid
from dataclasses import dataclass, field, asdict
from datetime import datetime
from typing import List, Dict, Any, Optional


@dataclass
class Message:
    role: str  # 'user', 'assistant', 'system', 'tool'
    content: str
    timestamp: str = field(default_factory=lambda: datetime.utcnow().isoformat())
    tool_name: Optional[str] = None
    tool_result: Optional[str] = None
    metadata: Dict[str, Any] = field(default_factory=dict)

    def to_dict(self) -> Dict[str, Any]:
        return asdict(self)

    @classmethod
    def from_dict(cls, data: Dict[str, Any]) -> "Message":
        return cls(**data)


@dataclass
class PlanStep:
    step_number: int
    description: str
    tool_name: Optional[str] = None
    status: str = "pending"  # pending, in_progress, completed, failed, skipped
    result: Optional[str] = None
    error: Optional[str] = None

    def to_dict(self) -> Dict[str, Any]:
        return asdict(self)

    @classmethod
    def from_dict(cls, data: Dict[str, Any]) -> "PlanStep":
        return cls(**data)


@dataclass
class Plan:
    goal: str
    steps: List[PlanStep] = field(default_factory=list)
    created_at: str = field(default_factory=lambda: datetime.utcnow().isoformat())
    status: str = "active"  # active, completed, failed, cancelled

    def to_dict(self) -> Dict[str, Any]:
        return {
            "goal": self.goal,
            "steps": [s.to_dict() for s in self.steps],
            "created_at": self.created_at,
            "status": self.status,
        }

    @classmethod
    def from_dict(cls, data: Dict[str, Any]) -> "Plan":
        steps = [PlanStep.from_dict(s) for s in data.get("steps", [])]
        return cls(
            goal=data.get("goal", ""),
            steps=steps,
            created_at=data.get("created_at", datetime.utcnow().isoformat()),
            status=data.get("status", "active"),
        )


@dataclass
class Session:
    session_id: str = field(default_factory=lambda: str(uuid.uuid4())[:8])
    title: str = "New Conversation"
    project: str = "default"
    created_at: str = field(default_factory=lambda: datetime.utcnow().isoformat())
    updated_at: str = field(default_factory=lambda: datetime.utcnow().isoformat())
    messages: List[Message] = field(default_factory=list)
    summary: str = ""
    active_plan: Optional[Plan] = None
    is_archived: bool = False
    metadata: Dict[str, Any] = field(default_factory=dict)

    def add_message(self, role: str, content: str, **kwargs) -> Message:
        msg = Message(role=role, content=content, **kwargs)
        self.messages.append(msg)
        self.updated_at = datetime.utcnow().isoformat()
        return msg

    def to_dict(self) -> Dict[str, Any]:
        return {
            "session_id": self.session_id,
            "title": self.title,
            "project": self.project,
            "created_at": self.created_at,
            "updated_at": self.updated_at,
            "messages": [m.to_dict() for m in self.messages],
            "summary": self.summary,
            "active_plan": self.active_plan.to_dict() if self.active_plan else None,
            "is_archived": self.is_archived,
            "metadata": self.metadata,
        }

    @classmethod
    def from_dict(cls, data: Dict[str, Any]) -> "Session":
        messages = [Message.from_dict(m) for m in data.get("messages", [])]
        active_plan = None
        if data.get("active_plan"):
            active_plan = Plan.from_dict(data["active_plan"])

        return cls(
            session_id=data.get("session_id", str(uuid.uuid4())[:8]),
            title=data.get("title", "New Conversation"),
            project=data.get("project", "default"),
            created_at=data.get("created_at", datetime.utcnow().isoformat()),
            updated_at=data.get("updated_at", datetime.utcnow().isoformat()),
            messages=messages,
            summary=data.get("summary", ""),
            active_plan=active_plan,
            is_archived=data.get("is_archived", False),
            metadata=data.get("metadata", {}),
        )
