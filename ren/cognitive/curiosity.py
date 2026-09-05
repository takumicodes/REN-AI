"""
REN Curiosity Engine
Identifies knowledge gaps, repeated failures, contradictions, missing skills, and cross-project transfer opportunities.
Generates machine-readable curiosity objectives with topic, reason, priority, and confidence.
Engineering optimization mechanism — not simulated consciousness.
"""

import time
import uuid
from dataclasses import dataclass, field, asdict
from typing import List, Dict, Any, Optional
import threading

from ren.monitoring.logger import agent_logger
from ren.memory.manager import memory_manager
from ren.core.world_model import world_model


@dataclass
class CuriosityObjective:
    id: str
    topic: str
    reason: str
    priority: float  # 0.0 to 1.0
    confidence: float  # 0.0 to 1.0
    category: str  # "knowledge_gap", "repeated_failure", "missing_skill", "transfer_opportunity"
    created_at: float = field(default_factory=time.time)
    resolved: bool = False
    resolution: Optional[str] = None

    def to_dict(self) -> Dict[str, Any]:
        return asdict(self)


class CuriosityEngine:
    """Discovers and manages targeted investigation objectives."""

    def __init__(self):
        self._objectives: Dict[str, CuriosityObjective] = {}
        self._lock = threading.Lock()

    def generate_objective(
        self,
        topic: str,
        reason: str,
        category: str = "knowledge_gap",
        priority: float = 0.7,
        confidence: float = 0.8
    ) -> CuriosityObjective:
        """Registers a machine-readable curiosity objective."""
        obj_id = f"cur_{uuid.uuid4().hex[:8]}"
        obj = CuriosityObjective(
            id=obj_id,
            topic=topic,
            reason=reason,
            priority=min(1.0, max(0.0, priority)),
            confidence=min(1.0, max(0.0, confidence)),
            category=category
        )
        with self._lock:
            self._objectives[obj_id] = obj

        agent_logger.info(f"CuriosityEngine: New objective [{obj.category}] '{topic}' (Priority: {priority:.2f})")
        return obj

    def inspect_knowledge_gaps(self, user_id: str = "default") -> List[CuriosityObjective]:
        """Analyzes episodic failures and unresolved queries to generate investigation objectives."""
        discovered = []
        recent_episodes = memory_manager.get_recent_episodes(limit=10, user_id=user_id)
        
        # Check repeated failures
        failures = [e for e in recent_episodes if "fail" in str(e.get("outcome", "")).lower()]
        if len(failures) >= 2:
            topics = [f.get("task", "Unknown Task") for f in failures]
            obj = self.generate_objective(
                topic=f"Repeated Task Difficulties: {topics[0]}",
                reason=f"Detected {len(failures)} recent execution failures on similar tasks.",
                category="repeated_failure",
                priority=0.85,
                confidence=0.90
            )
            discovered.append(obj)

        # Check missing skills in active projects
        active_tasks = world_model.list_active_tasks(user_id=user_id)
        for t in active_tasks:
            if any(w in t.description.lower() for w in ["parse", "convert", "scrape", "format", "automate"]):
                obj = self.generate_objective(
                    topic=f"Automation Candidate for: {t.description[:40]}",
                    reason="Active task matches high-leverage procedural automation pattern.",
                    category="missing_skill",
                    priority=0.75,
                    confidence=0.80
                )
                discovered.append(obj)

        return discovered

    def list_active_objectives(self) -> List[CuriosityObjective]:
        with self._lock:
            return [o for o in self._objectives.values() if not o.resolved]

    def resolve_objective(self, objective_id: str, resolution: str) -> bool:
        with self._lock:
            if objective_id in self._objectives:
                self._objectives[objective_id].resolved = True
                self._objectives[objective_id].resolution = resolution
                return True
            return False


# Global singleton
curiosity_engine = CuriosityEngine()
