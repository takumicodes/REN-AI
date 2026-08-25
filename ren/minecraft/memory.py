"""
REN-AI Minecraft Multi-Store Persistent Memory System 12.0
Implements structured, persistent memory stores for embodied autonomy:
- Episodic: chronological key events with importance scoring and spatial tags
- Spatial: points of interest (bases, shelters, caves, lava pools, portals, death points)
- Semantic: learned rules, recipes, and environmental dynamics
- Skill: successful strategies, execution records, and timing metrics
- Failure: diagnosed execution failures and remedies to prevent loop repetition
- Entity: known players, pets, hostile patterns
- Structure: verified construction coordinates, blueprints, and materials
- Goal: history of completed, interrupted, and active tasks
"""

import os
import json
import time
from pathlib import Path
from dataclasses import dataclass, field
from typing import Dict, Any, List, Optional, Tuple
from ren.monitoring.logger import agent_logger


@dataclass
class MemoryEntry:
    id: str
    category: str
    content: Dict[str, Any]
    importance: float = 0.5
    timestamp: float = field(default_factory=time.time)
    location: Optional[Dict[str, float]] = None
    tags: List[str] = field(default_factory=list)

    def to_dict(self) -> Dict[str, Any]:
        return {
            "id": self.id,
            "category": self.category,
            "content": self.content,
            "importance": self.importance,
            "timestamp": self.timestamp,
            "location": self.location,
            "tags": self.tags
        }


class MinecraftMemorySystem:
    """
    Unified multi-store memory system for Minecraft agent.
    Persists across sessions to data/minecraft_memory.json.
    """

    def __init__(self, memory_file: Optional[str] = None):
        if memory_file:
            self.memory_file = Path(memory_file)
        else:
            self.memory_file = Path(__file__).resolve().parent.parent.parent / "data" / "minecraft_memory.json"
        
        self.episodic_memory: List[MemoryEntry] = []
        self.spatial_memory: Dict[str, Dict[str, Any]] = {}
        self.semantic_memory: Dict[str, Any] = {}
        self.skill_memory: Dict[str, List[Dict[str, Any]]] = {}
        self.failure_memory: List[Dict[str, Any]] = []
        self.entity_memory: Dict[str, Dict[str, Any]] = {}
        self.structure_memory: Dict[str, Dict[str, Any]] = {}
        self.goal_memory: List[Dict[str, Any]] = []

        self._max_episodic = 200
        self._max_failures = 100
        self.load_memory()

    # -------------------------------------------------------------
    # 1. Episodic Memory
    # -------------------------------------------------------------
    def record_episode(
        self,
        event_name: str,
        summary: str,
        importance: float = 0.5,
        location: Optional[Dict[str, float]] = None,
        details: Optional[Dict[str, Any]] = None,
        tags: Optional[List[str]] = None
    ):
        """Records an important episodic event."""
        entry = MemoryEntry(
            id=f"ep_{int(time.time() * 1000)}",
            category="episodic",
            content={"event": event_name, "summary": summary, "details": details or {}},
            importance=importance,
            timestamp=time.time(),
            location=location,
            tags=tags or [event_name]
        )
        self.episodic_memory.append(entry)
        if len(self.episodic_memory) > self._max_episodic:
            # Keep highest importance memories
            self.episodic_memory.sort(key=lambda m: m.importance, reverse=True)
            self.episodic_memory = self.episodic_memory[:self._max_episodic]

    # -------------------------------------------------------------
    # 2. Spatial Memory
    # -------------------------------------------------------------
    def set_location(self, name: str, x: float, y: float, z: float, metadata: Optional[Dict[str, Any]] = None):
        """Stores a named point of interest (e.g. 'home_base', 'death_point', 'cave_entrance')."""
        self.spatial_memory[name.lower()] = {
            "pos": {"x": round(x, 1), "y": round(y, 1), "z": round(z, 1)},
            "updated_at": time.time(),
            "metadata": metadata or {}
        }

    def get_location(self, name: str) -> Optional[Dict[str, float]]:
        """Retrieves coordinates for a named location."""
        entry = self.spatial_memory.get(name.lower())
        return entry.get("pos") if entry else None

    def find_nearest_poi(self, current_pos: Dict[str, float], poi_type: Optional[str] = None) -> Optional[Tuple[str, Dict[str, float], float]]:
        """Finds the closest recorded spatial point of interest."""
        best_name = None
        best_pos = None
        min_dist = float("inf")

        cx, cz = current_pos.get("x", 0), current_pos.get("z", 0)
        for name, data in self.spatial_memory.items():
            if poi_type and poi_type.lower() not in name:
                continue
            pos = data.get("pos", {})
            px, pz = pos.get("x", 0), pos.get("z", 0)
            dist = ((cx - px) ** 2 + (cz - pz) ** 2) ** 0.5
            if dist < min_dist:
                min_dist = dist
                best_name = name
                best_pos = pos

        if best_name and best_pos:
            return best_name, best_pos, round(min_dist, 1)
        return None

    # -------------------------------------------------------------
    # 3. Structure & Construction Memory
    # -------------------------------------------------------------
    def record_structure(self, structure_name: str, origin: Dict[str, float], dimensions: Dict[str, int], block_count: int):
        """Saves a built house or structure to memory."""
        self.structure_memory[structure_name.lower()] = {
            "origin": origin,
            "dimensions": dimensions,
            "block_count": block_count,
            "built_at": time.time()
        }
        self.set_location(f"structure_{structure_name}", origin.get("x", 0), origin.get("y", 64), origin.get("z", 0))

    # -------------------------------------------------------------
    # 4. Failure & Recovery Memory
    # -------------------------------------------------------------
    def record_failure(self, action: str, reason: str, context: Dict[str, Any]):
        """Records a failure so the agent learns to avoid repeating the same mistake."""
        self.failure_memory.append({
            "action": action,
            "reason": reason,
            "context": context,
            "timestamp": time.time()
        })
        if len(self.failure_memory) > self._max_failures:
            self.failure_memory.pop(0)

    def is_action_frequently_failing(self, action: str, threshold: int = 3, within_seconds: float = 60.0) -> bool:
        """Checks if an action has repeatedly failed recently."""
        now = time.time()
        recent_fails = sum(
            1 for f in self.failure_memory
            if f.get("action") == action and (now - f.get("timestamp", 0)) <= within_seconds
        )
        return recent_fails >= threshold

    # -------------------------------------------------------------
    # 5. Goal & Task Memory
    # -------------------------------------------------------------
    def record_goal_completion(self, goal_name: str, duration_sec: float, success: bool):
        self.goal_memory.append({
            "goal": goal_name,
            "duration": round(duration_sec, 1),
            "success": success,
            "timestamp": time.time()
        })

    # -------------------------------------------------------------
    # Persistence
    # -------------------------------------------------------------
    def save_memory(self):
        """Persists all memory stores to JSON file."""
        try:
            self.memory_file.parent.mkdir(parents=True, exist_ok=True)
            payload = {
                "spatial": self.spatial_memory,
                "semantic": self.semantic_memory,
                "skill": self.skill_memory,
                "structures": self.structure_memory,
                "failures": self.failure_memory[-50:],
                "goals": self.goal_memory[-50:],
                "episodic": [e.to_dict() for e in self.episodic_memory[-50:]]
            }
            with open(self.memory_file, "w", encoding="utf-8") as f:
                json.dump(payload, f, indent=2)
        except Exception as e:
            agent_logger.warning(f"Failed to save Minecraft memory: {e}")

    def load_memory(self):
        """Loads memory stores from JSON file if present."""
        if not self.memory_file.exists():
            return
        try:
            with open(self.memory_file, "r", encoding="utf-8") as f:
                data = json.load(f)
            self.spatial_memory = data.get("spatial", {})
            self.semantic_memory = data.get("semantic", {})
            self.skill_memory = data.get("skill", {})
            self.structure_memory = data.get("structures", {})
            self.failure_memory = data.get("failures", [])
            self.goal_memory = data.get("goals", [])
            self.episodic_memory = [
                MemoryEntry(
                    id=e.get("id", ""),
                    category=e.get("category", "episodic"),
                    content=e.get("content", {}),
                    importance=e.get("importance", 0.5),
                    timestamp=e.get("timestamp", 0.0),
                    location=e.get("location"),
                    tags=e.get("tags", [])
                )
                for e in data.get("episodic", [])
            ]
        except Exception as e:
            agent_logger.warning(f"Failed to load Minecraft memory: {e}")
