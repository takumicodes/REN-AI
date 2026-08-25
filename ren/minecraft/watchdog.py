"""
REN-AI Minecraft Stuck Detection & Watchdog Recovery Engine
Monitors position deltas, action duration, failure streaks, and generates recovery strategies.
"""

import time
from typing import Dict, Any, Optional, List, Tuple
from ren.monitoring.logger import agent_logger


class MinecraftStuckWatchdog:
    """
    Watchdog monitor that detects pathfinding stalls, action timeouts, and execution loops.
    """

    def __init__(
        self,
        position_stall_seconds: float = 12.0,
        max_consecutive_failures: int = 3,
        action_timeout_seconds: float = 45.0
    ):
        self.position_stall_seconds = position_stall_seconds
        self.max_consecutive_failures = max_consecutive_failures
        self.action_timeout_seconds = action_timeout_seconds

        # State tracking
        self.last_pos: Optional[Dict[str, float]] = None
        self.last_move_time: float = time.time()
        self.current_action: Optional[str] = None
        self.action_start_time: float = 0.0
        self.consecutive_failures: int = 0
        self.failure_history: List[Dict[str, Any]] = []

    def start_action_monitor(self, action: str, current_pos: Dict[str, float]):
        """Begins tracking a new action."""
        self.current_action = action
        self.action_start_time = time.time()
        self.last_pos = current_pos
        self.last_move_time = time.time()

    def update_position(self, current_pos: Dict[str, float]):
        """Updates position tracking to detect stalls."""
        if not self.last_pos:
            self.last_pos = current_pos
            self.last_move_time = time.time()
            return

        dx = current_pos.get("x", 0) - self.last_pos.get("x", 0)
        dy = current_pos.get("y", 0) - self.last_pos.get("y", 0)
        dz = current_pos.get("z", 0) - self.last_pos.get("z", 0)
        dist_sq = dx * dx + dy * dy + dz * dz

        # If moved at least 0.5 blocks, reset move timer
        if dist_sq > 0.25:
            self.last_pos = current_pos
            self.last_move_time = time.time()

    def check_is_stuck(self, current_pos: Dict[str, float]) -> Tuple[bool, Optional[str]]:
        """
        Evaluates whether the bot is currently stuck or timed out.
        Returns: (is_stuck: bool, reason: Optional[str])
        """
        now = time.time()
        self.update_position(current_pos)

        # 1. Action Timeout Check
        if self.current_action and (now - self.action_start_time) > self.action_timeout_seconds:
            return True, f"Action '{self.current_action}' timed out after {int(now - self.action_start_time)}s."

        # 2. Movement Stall Check (only if performing a moving action)
        if self.current_action in ["follow", "goTo", "move_to", "gather", "hunt", "attack"]:
            if (now - self.last_move_time) > self.position_stall_seconds:
                return True, f"Movement stalled: position unchanged for {int(now - self.last_move_time)}s."

        # 3. Repeated Failure Check
        if self.consecutive_failures >= self.max_consecutive_failures:
            return True, f"Consecutive failure limit reached ({self.consecutive_failures} failures)."

        return False, None

    def record_action_result(self, success: bool, action: str, reason: Optional[str] = None):
        """Updates failure streaks."""
        if success:
            self.consecutive_failures = 0
        else:
            self.consecutive_failures += 1
            self.failure_history.append({
                "action": action,
                "reason": reason,
                "timestamp": time.time()
            })
            if len(self.failure_history) > 20:
                self.failure_history.pop(0)

    def generate_recovery_plan(self, action: str, parameters: Dict[str, Any]) -> List[Dict[str, Any]]:
        """
        Generates structured recovery steps when an action gets stuck:
        1. Stop current movement.
        2. Micro-jump & clear immediate obstacle.
        3. Re-sample alternate target or alternative path.
        """
        agent_logger.info(f"[WATCHDOG] Generating recovery plan for stuck action '{action}'")
        recovery_steps: List[Dict[str, Any]] = [
            {"cmd": "stop", "args": {}}
        ]

        if action in ["gather", "mine_block"]:
            # If wood/stone gathering failed, try gathering dirt/cobblestone nearby as fallback
            res = parameters.get("block_type", "wood")
            if "stone" in res:
                recovery_steps.append({"cmd": "gather", "args": {"block_type": "dirt", "count": 4}})
            else:
                recovery_steps.append({"cmd": "gather", "args": {"block_type": "oak_log", "count": 2}})

        elif action in ["follow", "goTo"]:
            # Small random offset to un-wedge pathfinder
            recovery_steps.append({"cmd": "goTo", "args": {"x": 1, "y": 0, "z": 1}})

        self.consecutive_failures = 0
        self.last_move_time = time.time()
        self.action_start_time = time.time()

        return recovery_steps
