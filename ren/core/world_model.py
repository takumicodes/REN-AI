"""
REN World Model
Maintains a persistent, structured representation of:
- User (goals, preferences, projects, routines)
- Projects (status, tasks, dependencies, knowledge)
- Devices (state, capabilities, permissions, connection)
- Tasks (active, waiting, completed, failed)
- Skills (versions, dependencies, confidence)
- Knowledge (concepts, relationships, evidence)

Allows querying structured state (e.g., "What am I working on?") instead of relying only on raw conversation tokens.
"""

import json
import threading
import time
from pathlib import Path
from dataclasses import dataclass, field, asdict
from typing import Dict, List, Optional, Any

from ren.config.settings import settings
from ren.monitoring.logger import agent_logger


@dataclass
class UserWorldEntity:
    user_id: str = "default"
    goals: List[str] = field(default_factory=list)
    preferences: Dict[str, Any] = field(default_factory=dict)
    active_projects: List[str] = field(default_factory=list)
    routines: List[str] = field(default_factory=list)


@dataclass
class ProjectWorldEntity:
    name: str
    status: str = "active"
    tasks: List[Dict[str, Any]] = field(default_factory=list)
    dependencies: List[str] = field(default_factory=list)
    knowledge: List[str] = field(default_factory=list)
    updated_at: float = field(default_factory=time.time)


@dataclass
class TaskWorldEntity:
    task_id: str
    user_id: str
    description: str
    status: str = "active"  # active, waiting, completed, failed
    assigned_device: str = "pc_host"
    created_at: float = field(default_factory=time.time)
    completed_at: Optional[float] = None
    result: Optional[str] = None


@dataclass
class KnowledgeWorldEntity:
    concept: str
    relationships: List[str] = field(default_factory=list)
    evidence: List[str] = field(default_factory=list)
    confidence: float = 1.0
    provenance: str = "user"
    updated_at: float = field(default_factory=time.time)


class WorldModel:
    """Thread-safe persistent world state manager."""

    def __init__(self, state_file: Optional[Path] = None):
        self.state_file = state_file or (settings.PATHS.ROOT_DIR / "data" / "world_model.json")
        self.state_file.parent.mkdir(parents=True, exist_ok=True)
        self._lock = threading.Lock()

        self.users: Dict[str, UserWorldEntity] = {}
        self.projects: Dict[str, ProjectWorldEntity] = {}
        self.tasks: Dict[str, TaskWorldEntity] = {}
        self.knowledge: Dict[str, KnowledgeWorldEntity] = {}

        self._load_state()

    def _load_state(self):
        """Loads persistent world state from disk."""
        if not self.state_file.exists():
            # Initialize with default developer state
            self.users["default"] = UserWorldEntity(
                user_id="default",
                goals=["Evolve REN 2.0 persistent autonomous agent", "Create Cyanox AI operating ecosystem"],
                preferences={"favorite_language": "Python", "agent_mode": "autonomous"},
                active_projects=["REN-AI", "Cyanox"],
                routines=["Daily system sync", "Autonomous dream consolidation"]
            )
            self.projects["REN-AI"] = ProjectWorldEntity(
                name="REN-AI",
                status="active",
                tasks=[{"desc": "Upgrade to REN 2.0 persistent architecture", "status": "active"}],
                dependencies=["Python 3.10", "Ollama", "Pygame", "FastAPI"],
                knowledge=["Local-first modular companion with persistent SQLite memory and Hermes Agent"]
            )
            self._save_state()
            return

        try:
            with open(self.state_file, "r", encoding="utf-8") as f:
                data = json.load(f)

            for uid, udata in data.get("users", {}).items():
                self.users[uid] = UserWorldEntity(**udata)
            for pname, pdata in data.get("projects", {}).items():
                self.projects[pname] = ProjectWorldEntity(**pdata)
            for tid, tdata in data.get("tasks", {}).items():
                self.tasks[tid] = TaskWorldEntity(**tdata)
            for cname, kdata in data.get("knowledge", {}).items():
                self.knowledge[cname] = KnowledgeWorldEntity(**kdata)
        except Exception as e:
            agent_logger.error(f"Failed loading WorldModel state: {e}")

    def _save_state(self):
        """Persists world state atomically to disk."""
        try:
            data = {
                "users": {k: asdict(v) for k, v in self.users.items()},
                "projects": {k: asdict(v) for k, v in self.projects.items()},
                "tasks": {k: asdict(v) for k, v in self.tasks.items()},
                "knowledge": {k: asdict(v) for k, v in self.knowledge.items()},
            }
            tmp_file = self.state_file.with_suffix(".tmp")
            with open(tmp_file, "w", encoding="utf-8") as f:
                json.dump(data, f, indent=2)
            tmp_file.replace(self.state_file)
        except Exception as e:
            agent_logger.error(f"Failed saving WorldModel state: {e}")

    def get_user(self, user_id: str = "default") -> UserWorldEntity:
        with self._lock:
            if user_id not in self.users:
                self.users[user_id] = UserWorldEntity(user_id=user_id)
                self._save_state()
            return self.users[user_id]

    def add_user_goal(self, goal: str, user_id: str = "default") -> None:
        with self._lock:
            user = self.get_user(user_id)
            if goal not in user.goals:
                user.goals.append(goal)
                self._save_state()

    def set_user_preference(self, key: str, value: Any, user_id: str = "default") -> None:
        with self._lock:
            user = self.get_user(user_id)
            user.preferences[key] = value
            self._save_state()

    def upsert_project(
        self,
        name: str,
        status: str = "active",
        tasks: Optional[List[Dict[str, Any]]] = None,
        dependencies: Optional[List[str]] = None,
        knowledge: Optional[List[str]] = None
    ) -> ProjectWorldEntity:
        with self._lock:
            if name in self.projects:
                proj = self.projects[name]
                proj.status = status
                if tasks is not None: proj.tasks = tasks
                if dependencies is not None: proj.dependencies = dependencies
                if knowledge is not None: proj.knowledge = knowledge
                proj.updated_at = time.time()
            else:
                proj = ProjectWorldEntity(
                    name=name,
                    status=status,
                    tasks=tasks or [],
                    dependencies=dependencies or [],
                    knowledge=knowledge or []
                )
                self.projects[name] = proj
            self._save_state()
            return proj

    def get_project(self, name: str) -> Optional[ProjectWorldEntity]:
        with self._lock:
            return self.projects.get(name)

    def create_task(
        self,
        description: str,
        user_id: str = "default",
        assigned_device: str = "pc_host",
        status: str = "active"
    ) -> TaskWorldEntity:
        with self._lock:
            task_id = f"task_{int(time.time()*1000)}_{len(self.tasks)+1}"
            task = TaskWorldEntity(
                task_id=task_id,
                user_id=user_id,
                description=description,
                status=status,
                assigned_device=assigned_device
            )
            self.tasks[task_id] = task
            self._save_state()
            return task

    def update_task_status(self, task_id: str, status: str, result: Optional[str] = None) -> bool:
        with self._lock:
            if task_id in self.tasks:
                t = self.tasks[task_id]
                t.status = status
                if result:
                    t.result = result
                if status in ["completed", "failed"]:
                    t.completed_at = time.time()
                self._save_state()
                return True
            return False

    def list_active_tasks(self, user_id: str = "default") -> List[TaskWorldEntity]:
        with self._lock:
            return [t for t in self.tasks.values() if t.user_id == user_id and t.status in ["active", "waiting"]]

    def record_knowledge(
        self,
        concept: str,
        relationships: Optional[List[str]] = None,
        evidence: Optional[List[str]] = None,
        confidence: float = 1.0,
        provenance: str = "observation"
    ) -> KnowledgeWorldEntity:
        with self._lock:
            k = KnowledgeWorldEntity(
                concept=concept,
                relationships=relationships or [],
                evidence=evidence or [],
                confidence=confidence,
                provenance=provenance,
                updated_at=time.time()
            )
            self.knowledge[concept] = k
            self._save_state()
            return k

    def what_am_i_working_on(self, user_id: str = "default") -> str:
        """
        Synthesizes a structured answer directly from current world model state.
        Never relies purely on chat token hallucinations.
        """
        user = self.get_user(user_id)
        active_tasks = self.list_active_tasks(user_id)
        active_projects = [p for p in self.projects.values() if p.status == "active"]

        lines = ["Here is your current structured work state, Sir:"]

        if active_projects:
            proj_descs = [f"**{p.name}** ({len(p.tasks)} tracked tasks)" for p in active_projects]
            lines.append(f"- **Active Projects**: {', '.join(proj_descs)}")

        if active_tasks:
            lines.append("- **Current Active Tasks**:")
            for t in active_tasks[:5]:
                lines.append(f"  • [{t.status.upper()}] {t.description} (Device: {t.assigned_device})")
        else:
            lines.append("- **Current Active Tasks**: No pending tasks queued.")

        if user.goals:
            lines.append(f"- **Primary Goals**: {', '.join(user.goals[:3])}")

        return "\n".join(lines)

    def get_world_context_summary(self, user_id: str = "default") -> str:
        """Compact summary formatted for prompt injection into ContextBuilder."""
        user = self.get_user(user_id)
        active_tasks = self.list_active_tasks(user_id)
        active_projects = [p.name for p in self.projects.values() if p.status == "active"]

        parts = []
        if active_projects:
            parts.append(f"Projects: {', '.join(active_projects[:3])}")
        if active_tasks:
            task_snippets = [t.description[:30] for t in active_tasks[:3]]
            parts.append(f"Active Tasks: {'; '.join(task_snippets)}")
        if user.goals:
            parts.append(f"Goals: {'; '.join(user.goals[:2])}")

        if not parts:
            return ""
        return "[Structured World Model State]\n" + "\n".join(f"- {p}" for p in parts)


# Global singleton
world_model = WorldModel()
