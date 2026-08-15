"""
REN Event System
Thread-safe publish/subscribe event bus for real-time telemetry, HUD updates, and decoupled logging.
"""

from enum import Enum
from typing import Callable, Dict, List, Any
import threading
from ren.monitoring.logger import agent_logger


class EventType(str, Enum):
    USER_MESSAGE = "user.message"
    AGENT_STARTED = "agent.started"
    AGENT_PLANNING = "agent.planning"
    SKILL_SELECTED = "skill.selected"
    TOOL_STARTED = "tool.started"
    TOOL_COMPLETED = "tool.completed"
    TOOL_FAILED = "tool.failed"
    MEMORY_CREATED = "memory.created"
    MEMORY_UPDATED = "memory.updated"
    SKILL_CREATED = "skill.created"
    SKILL_UPDATED = "skill.updated"
    AGENT_ERROR = "agent.error"
    AGENT_COMPLETED = "agent.completed"
    SESSION_CREATED = "session.created"
    PIPELINE_STAGE = "pipeline.stage"
    POPUP_NOTIFICATION = "popup.notification"


class EventBus:
    """Thread-safe event bus."""

    def __init__(self):
        self._subscribers: Dict[str, List[Callable[[str, Any], None]]] = {}
        self._lock = threading.Lock()

    def subscribe(self, event_type: str, callback: Callable[[str, Any], None]) -> None:
        """Subscribes a listener callback to an event type (or '*' for all events)."""
        with self._lock:
            if event_type not in self._subscribers:
                self._subscribers[event_type] = []
            self._subscribers[event_type].append(callback)

    def publish(self, event_type: str, data: Any = None) -> None:
        """Broadcasts an event to all registered listeners."""
        with self._lock:
            listeners = list(self._subscribers.get(event_type, []))
            all_listeners = list(self._subscribers.get("*", []))

        for cb in listeners + all_listeners:
            try:
                cb(event_type, data)
            except Exception as e:
                agent_logger.error(f"Error in event callback for '{event_type}': {e}")


# Global event bus singleton
event_bus = EventBus()
