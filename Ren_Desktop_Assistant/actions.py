"""
Human-Driven Action & Recommendation Engine for REN Desktop Assistant
Enforces:
- 100% Human-in-the-loop control (no unsolicited background mutations).
- Anti-spam & Cooldown tracking: Never nags or behaves like annoying AI slop (e.g. Copilot).
- Clear transparency: Every recommendation has an exact rationale and measurable impact.
"""

import time
from typing import Dict, List, Any, Optional, Callable
try:
    from .preferences import preferences
    from .history import change_history
except ImportError:
    from preferences import preferences
    try:
        from history import change_history
    except ImportError:
        change_history = None


class Recommendation:
    """Represents an actionable system optimization proposal."""

    def __init__(
        self,
        rec_id: str,
        title: str,
        description: str,
        category: str,
        impact: str,
        action_fn: Optional[Callable[[], Any]] = None,
        command_preview: Optional[str] = None,
    ):
        self.id = rec_id
        self.title = title
        self.description = description
        self.category = category
        self.impact = impact
        self.action_fn = action_fn
        self.command_preview = command_preview
        self.created_at = time.time()

    def to_dict(self) -> Dict[str, Any]:
        return {
            "id": self.id,
            "title": self.title,
            "description": self.description,
            "category": self.category,
            "impact": self.impact,
            "command_preview": self.command_preview,
            "created_at": self.created_at,
        }


class ActionQueue:
    """Maintains non-intrusive recommendation queue with cooldown and human approval."""

    def __init__(self):
        self._pending: Dict[str, Recommendation] = {}
        self._cooldowns: Dict[str, float] = {}  # rec_id -> last_shown_timestamp
        self._cooldown_duration = preferences.get("notification_cooldown_seconds", 300)

    def propose(self, rec: Recommendation) -> bool:
        """
        Submits a recommendation for human review.
        Returns False if suppressed by cooldown or quiet hours.
        """
        if preferences.is_quiet_hours():
            return False

        now = time.time()
        last_time = self._cooldowns.get(rec.id, 0)
        if (now - last_time) < self._cooldown_duration:
            return False  # Suppressed by anti-spam cooldown

        self._pending[rec.id] = rec
        self._cooldowns[rec.id] = now
        return True

    def get_pending(self) -> List[Recommendation]:
        """Returns all current pending recommendations."""
        return list(self._pending.values())

    def get(self, rec_id: str) -> Optional[Recommendation]:
        """Retrieves recommendation by ID."""
        return self._pending.get(rec_id)

    def approve(self, rec_id: str) -> Dict[str, Any]:
        """
        Executes approved recommendation. Records user feedback dynamically.
        """
        rec = self._pending.pop(rec_id, None)
        if not rec:
            return {"success": False, "message": f"Recommendation '{rec_id}' not found."}

        result = {"success": True, "message": f"Approved '{rec.title}'"}
        if rec.action_fn:
            try:
                fn_res = rec.action_fn()
                if isinstance(fn_res, dict):
                    result.update(fn_res)
                elif fn_res is not None:
                    result["details"] = str(fn_res)
            except Exception as e:
                result = {"success": False, "message": f"Action execution failed: {e}"}

        # Dynamically learn that user approves this category
        preferences.record_decision(rec.category, approved=result.get("success", True))

        # Record in Change History audit trail
        if change_history is not None:
            try:
                change_history.record_action(
                    action_id=rec.id,
                    title=rec.title,
                    category=rec.category,
                    status="executed" if result.get("success", True) else "failed",
                    verified=True,
                    verification_message=result.get("message", "Approved and applied"),
                    reversible=True,
                    details=result,
                )
            except Exception:
                pass

        return result

    def dismiss(self, rec_id: str) -> bool:
        """Dismisses recommendation and records rejection preference."""
        rec = self._pending.pop(rec_id, None)
        if rec:
            preferences.record_decision(rec.category, approved=False)
            return True
        return False

    def clear(self):
        """Clears pending recommendations."""
        self._pending.clear()


action_queue = ActionQueue()
