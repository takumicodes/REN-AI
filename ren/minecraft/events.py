"""
REN-AI Minecraft Priority-Based Event System 12.0
Dispatches and handles world events categorized by strict priority levels:
CRITICAL (Imminent death/danger) -> HIGH (Hunger/Shelter/Failure) -> MEDIUM (Resources/Exploration) -> LOW (Curiosity/Chat).
Ensures critical threats instantly interrupt low-priority behaviors.
"""

import time
from enum import Enum
from dataclasses import dataclass, field
from typing import Dict, Any, List, Optional, Callable


class EventType(str, Enum):
    PLAYER_JOINED = "PLAYER_JOINED"
    PLAYER_LEFT = "PLAYER_LEFT"
    PLAYER_SPOKE = "PLAYER_SPOKE"
    DAMAGE_TAKEN = "DAMAGE_TAKEN"
    LOW_HEALTH = "LOW_HEALTH"
    LOW_HUNGER = "LOW_HUNGER"
    FOOD_FOUND = "FOOD_FOUND"
    RESOURCE_FOUND = "RESOURCE_FOUND"
    RARE_RESOURCE_FOUND = "RARE_RESOURCE_FOUND"
    HOSTILE_NEARBY = "HOSTILE_NEARBY"
    NIGHT_STARTED = "NIGHT_STARTED"
    DAY_STARTED = "DAY_STARTED"
    NEW_AREA_DISCOVERED = "NEW_AREA_DISCOVERED"
    TASK_STARTED = "TASK_STARTED"
    TASK_PROGRESS = "TASK_PROGRESS"
    TASK_COMPLETED = "TASK_COMPLETED"
    TASK_FAILED = "TASK_FAILED"
    ACTION_FAILED = "ACTION_FAILED"
    BOT_STUCK = "BOT_STUCK"
    DEATH = "DEATH"
    RESPAWN = "RESPAWN"


class EventPriority(str, Enum):
    CRITICAL = "CRITICAL"  # Imminent death, lava, fire, drowning, severe danger
    HIGH = "HIGH"          # Hunger, nighttime without shelter, task failure
    MEDIUM = "MEDIUM"      # Resources, exploration, building progress
    LOW = "LOW"            # Curiosity, optional behavior, conversation


@dataclass
class MinecraftEvent:
    """Typed event instance."""
    event_type: EventType
    priority: EventPriority
    data: Dict[str, Any] = field(default_factory=dict)
    timestamp: float = field(default_factory=time.time)
    source: str = "world"
    handled: bool = False

    def to_dict(self) -> Dict[str, Any]:
        return {
            "event_type": self.event_type.value,
            "priority": self.priority.value,
            "data": self.data,
            "timestamp": self.timestamp,
            "source": self.source,
            "handled": self.handled
        }


class MinecraftEventBus:
    """
    Thread-safe event dispatch and subscription engine.
    """

    def __init__(self):
        self._subscribers: Dict[EventType, List[Callable[[MinecraftEvent], None]]] = {}
        self._priority_subscribers: Dict[EventPriority, List[Callable[[MinecraftEvent], None]]] = {
            EventPriority.CRITICAL: [],
            EventPriority.HIGH: [],
            EventPriority.MEDIUM: [],
            EventPriority.LOW: []
        }
        self._event_history: List[MinecraftEvent] = []
        self._max_history: int = 100

    def subscribe(self, event_type: EventType, handler: Callable[[MinecraftEvent], None]):
        """Subscribes a callback to a specific event type."""
        if event_type not in self._subscribers:
            self._subscribers[event_type] = []
        self._subscribers[event_type].append(handler)

    def subscribe_priority(self, priority: EventPriority, handler: Callable[[MinecraftEvent], None]):
        """Subscribes a callback to any event of a specific priority level."""
        self._priority_subscribers[priority].append(handler)

    def publish(self, event: MinecraftEvent):
        """Dispatches an event to all relevant handlers."""
        self._event_history.append(event)
        if len(self._event_history) > self._max_history:
            self._event_history.pop(0)

        # 1. Type-specific subscribers
        if event.event_type in self._subscribers:
            for handler in self._subscribers[event.event_type]:
                try:
                    handler(event)
                except Exception as e:
                    pass

        # 2. Priority subscribers
        if event.priority in self._priority_subscribers:
            for handler in self._priority_subscribers[event.priority]:
                try:
                    handler(event)
                except Exception as e:
                    pass

    def get_recent_events(self, limit: int = 10, min_priority: Optional[EventPriority] = None) -> List[MinecraftEvent]:
        """Returns recent filtered events."""
        events = self._event_history
        if min_priority:
            priority_ranks = {EventPriority.CRITICAL: 4, EventPriority.HIGH: 3, EventPriority.MEDIUM: 2, EventPriority.LOW: 1}
            min_rank = priority_ranks.get(min_priority, 1)
            events = [e for e in events if priority_ranks.get(e.priority, 1) >= min_rank]
        return events[-limit:]

    def clear(self):
        self._event_history.clear()
