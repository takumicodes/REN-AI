"""
REN-AI Minecraft Persistent Task Manager
Manages hierarchical tasks, subtask queues, execution state machines, and disk persistence.
"""

import json
import time
from pathlib import Path
from typing import Dict, Any, List, Optional

from ren.minecraft.types import Task, Subtask, Goal, TaskStatus
from ren.config.settings import settings
from ren.monitoring.logger import agent_logger


class MinecraftTaskManager:
    """
    Stateful manager for user and autonomous tasks with disk persistence.
    """

    def __init__(self, state_file_path: Optional[Path] = None):
        self.state_file_path = state_file_path or (settings.PATHS.DATA_DIR / "minecraft_task_state.json")
        self.active_task: Optional[Task] = None
        self.task_history: List[Task] = []
        self.task_queue: List[Task] = []
        self.load_state()

    def create_task(self, name: str, goal: Goal, subtasks: List[Subtask]) -> Task:
        """Instantiates a new Task and sets it as active."""
        task_id = f"task_{int(time.time() * 1000)}"
        task = Task(
            id=task_id,
            name=name,
            goal=goal,
            subtasks=subtasks,
            status=TaskStatus.IN_PROGRESS,
            current_subtask_index=0,
            created_at=time.time(),
            updated_at=time.time()
        )
        self.active_task = task
        self.save_state()
        agent_logger.info(f"[TASK CREATED] '{name}' with {len(subtasks)} subtasks. Progress: 0%")
        return task

    def advance_subtask(self) -> Optional[Subtask]:
        """Marks current subtask completed and advances to next."""
        if not self.active_task:
            return None

        current = self.active_task.current_subtask
        if current:
            current.status = TaskStatus.COMPLETED
            agent_logger.info(f"[SUBTASK OK] {current.action} ({current.id}) completed! Progress: {self.active_task.progress_percentage}%")

        self.active_task.current_subtask_index += 1
        self.active_task.updated_at = time.time()

        if self.active_task.current_subtask_index >= len(self.active_task.subtasks):
            self.active_task.status = TaskStatus.COMPLETED
            agent_logger.info(f"[TASK COMPLETED] '{self.active_task.name}' successfully finished! (100%)")
            self.task_history.append(self.active_task)
            completed_task = self.active_task
            self.active_task = None
            self.save_state()
            return None

        self.save_state()
        next_sub = self.active_task.current_subtask
        if next_sub:
            next_sub.status = TaskStatus.IN_PROGRESS
        return next_sub

    def fail_current_subtask(self, error: str) -> bool:
        """Handles subtask failure, incrementing attempts or failing the task."""
        if not self.active_task:
            return False

        current = self.active_task.current_subtask
        if not current:
            return False

        current.attempts += 1
        current.error = error
        agent_logger.warning(f"[SUBTASK FAIL] {current.action} ({current.id}) attempt {current.attempts}/{current.max_attempts}: {error}")

        if current.attempts >= current.max_attempts:
            current.status = TaskStatus.FAILED
            self.active_task.status = TaskStatus.FAILED
            self.active_task.failure_reason = f"Subtask '{current.action}' failed: {error}"
            self.task_history.append(self.active_task)
            agent_logger.error(f"[TASK FAILED] '{self.active_task.name}' failed: {error}")
            self.active_task = None
            self.save_state()
            return False

        current.status = TaskStatus.RETRYING
        self.save_state()
        return True

    def cancel_active_task(self, reason: str = "User cancelled"):
        """Cancels active task."""
        if self.active_task:
            self.active_task.status = TaskStatus.CANCELLED
            self.active_task.failure_reason = reason
            self.task_history.append(self.active_task)
            agent_logger.info(f"[TASK CANCELLED] '{self.active_task.name}': {reason}")
            self.active_task = None
            self.save_state()

    def save_state(self):
        """Persists task state to disk."""
        try:
            self.state_file_path.parent.mkdir(parents=True, exist_ok=True)
            payload = {
                "active_task": self.active_task.to_dict() if self.active_task else None,
                "history": [t.to_dict() for t in self.task_history[-10:]]
            }
            with open(self.state_file_path, "w", encoding="utf-8") as f:
                json.dump(payload, f, indent=2)
        except Exception as e:
            agent_logger.debug(f"Failed saving task state: {e}")

    def load_state(self):
        """Loads previous task state if available."""
        if not self.state_file_path.exists():
            return
        try:
            with open(self.state_file_path, "r", encoding="utf-8") as f:
                payload = json.load(f)
                active_d = payload.get("active_task")
                if active_d and active_d.get("status") in ["IN_PROGRESS", "RETRYING"]:
                    self.active_task = Task.from_dict(active_d)
                    agent_logger.info(f"Resumed persistent task '{self.active_task.name}' at step {self.active_task.current_subtask_index + 1}")
        except Exception as e:
            agent_logger.debug(f"Failed loading task state: {e}")
