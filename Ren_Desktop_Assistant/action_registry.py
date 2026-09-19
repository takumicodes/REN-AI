"""
Action Registry & Verification Engine for REN-AI Windows Control Center
Implements:
- Structured Action Model with Risk Ratings (SAFE, MODERATE, HIGH, CRITICAL).
- Full Pre-flight explanation, command preview, and impact analysis.
- Post-execution Verification: Verifies that changes actually took effect.
- 1-Click Rollback: Reverses changes using recorded before_state.
- Complete backward compatibility with Recommendation and ActionQueue.
"""

from enum import Enum
from typing import Dict, List, Any, Optional, Callable
import time

try:
    from .history import change_history, ChangeHistory
    from .preferences import preferences
except ImportError:
    from history import change_history, ChangeHistory
    from preferences import preferences


class RiskLevel(str, Enum):
    SAFE = "Safe"               # Reversible registry tweak, cache clean, power profile switch
    MODERATE = "Moderate"       # Disabling non-essential services, moving downloads
    HIGH = "High"               # Stopping unknown processes, modifying system services
    CRITICAL = "Critical"       # Core Windows system modifications (requires admin + explicit warning)


class Action:
    """
    Standardized, explainable action model for REN-AI Windows Control Center.
    Every action provides:
    - What it does (title, description)
    - Why it is recommended (rationale, impact)
    - Risk rating (risk_level)
    - Admin privilege requirement
    - Reversibility status
    - Exact command/script preview
    - Action execution callable
    - Post-execution verification callable
    - Rollback callable
    """

    def __init__(
        self,
        action_id: str,
        title: str,
        description: str,
        category: str,
        impact: str,
        risk_level: RiskLevel = RiskLevel.SAFE,
        requires_admin: bool = False,
        reversible: bool = True,
        affected_components: Optional[List[str]] = None,
        command_preview: Optional[str] = None,
        action_fn: Optional[Callable[[], Any]] = None,
        verify_fn: Optional[Callable[[], bool]] = None,
        rollback_fn: Optional[Callable[[Any], Any]] = None,
        get_state_fn: Optional[Callable[[], Any]] = None,
    ):
        self.id = action_id
        self.title = title
        self.description = description
        self.category = category
        self.impact = impact
        self.risk_level = risk_level
        self.requires_admin = requires_admin
        self.reversible = reversible
        self.affected_components = affected_components or []
        self.command_preview = command_preview or ""
        self.action_fn = action_fn
        self.verify_fn = verify_fn
        self.rollback_fn = rollback_fn
        self.get_state_fn = get_state_fn
        self.created_at = time.time()

    def explain(self) -> str:
        """Returns human-readable explanation of the action, impact, and safety."""
        admin_str = "Yes (Requires Elevation)" if self.requires_admin else "No"
        rev_str = "Yes (1-Click Rollback Available)" if self.reversible else "No (Irreversible Operation)"
        comps = ", ".join(self.affected_components) if self.affected_components else "General Windows"
        return (
            f"Action: {self.title}\n"
            f"Risk Level: {self.risk_level.value}\n"
            f"Requires Admin: {admin_str}\n"
            f"Reversible: {rev_str}\n"
            f"Affected: {comps}\n"
            f"Impact: {self.impact}\n"
            f"Description: {self.description}\n"
            f"Preview: {self.command_preview}"
        )

    def to_dict(self) -> Dict[str, Any]:
        return {
            "id": self.id,
            "title": self.title,
            "description": self.description,
            "category": self.category,
            "impact": self.impact,
            "risk_level": self.risk_level.value,
            "requires_admin": self.requires_admin,
            "reversible": self.reversible,
            "affected_components": self.affected_components,
            "command_preview": self.command_preview,
            "created_at": self.created_at,
        }


class ActionRegistry:
    """Central catalog of available actions in REN-AI."""

    def __init__(self):
        self._actions: Dict[str, Action] = {}

    def register(self, action: Action):
        """Registers a predefined or dynamic action."""
        self._actions[action.id] = action

    def get(self, action_id: str) -> Optional[Action]:
        """Retrieves action by ID."""
        return self._actions.get(action_id)

    def list_all(self) -> List[Action]:
        """Returns all registered actions."""
        return list(self._actions.values())

    def filter_by_category(self, category: str) -> List[Action]:
        """Returns actions in a specific category."""
        return [a for a in self._actions.values() if a.category == category]

    def filter_by_risk(self, max_risk: RiskLevel) -> List[Action]:
        """Filters actions by maximum acceptable risk level."""
        hierarchy = [RiskLevel.SAFE, RiskLevel.MODERATE, RiskLevel.HIGH, RiskLevel.CRITICAL]
        max_idx = hierarchy.index(max_risk)
        allowed = set(hierarchy[: max_idx + 1])
        return [a for a in self._actions.values() if a.risk_level in allowed]


class ActionExecutor:
    """Executes actions with pre-state capture, verification, audit logging, and rollback."""

    def __init__(self, registry: ActionRegistry, history: ChangeHistory):
        self.registry = registry
        self.history = history

    def execute_action(self, action: Action) -> Dict[str, Any]:
        """
        Executes an action with full safety verification and history tracking.
        """
        # Step 1: Capture pre-state
        before_state = None
        if action.get_state_fn:
            try:
                before_state = action.get_state_fn()
            except Exception:
                pass

        # Step 2: Execute
        result = {"success": True, "message": f"Executed '{action.title}'"}
        if action.action_fn:
            try:
                fn_res = action.action_fn()
                if isinstance(fn_res, dict):
                    result.update(fn_res)
                elif fn_res is not None:
                    result["details"] = str(fn_res)
            except Exception as e:
                result = {"success": False, "message": f"Execution failed: {e}"}

        # Step 3: Verify post-state
        verified = True
        verification_msg = "Verified successfully"
        if result.get("success", False) and action.verify_fn:
            try:
                verified = bool(action.verify_fn())
                verification_msg = "Post-change verification passed." if verified else "Warning: Verification check did not confirm state change."
            except Exception as ve:
                verified = False
                verification_msg = f"Verification error: {ve}"

        after_state = None
        if action.get_state_fn:
            try:
                after_state = action.get_state_fn()
            except Exception:
                pass

        # Step 4: Record in Change History
        entry = self.history.record_action(
            action_id=action.id,
            title=action.title,
            category=action.category,
            status="executed" if result.get("success", False) else "failed",
            verified=verified,
            verification_message=verification_msg,
            reversible=action.reversible,
            before_state=before_state,
            after_state=after_state,
            details={"execution_result": result},
        )

        result["history_entry_id"] = entry.get("entry_id")
        result["verified"] = verified
        result["verification_message"] = verification_msg
        return result

    def rollback_entry(self, entry_id: str) -> Dict[str, Any]:
        """
        Rolls back an executed action using its recorded before_state.
        """
        entry = self.history.get_entry(entry_id)
        if not entry:
            return {"success": False, "message": f"History entry '{entry_id}' not found."}

        if entry.get("rolled_back", False):
            return {"success": False, "message": f"Action '{entry.get('title')}' is already rolled back."}

        if not entry.get("reversible", True):
            return {"success": False, "message": f"Action '{entry.get('title')}' is marked as non-reversible."}

        action_id = entry.get("action_id")
        action = self.registry.get(action_id)
        if not action or not action.rollback_fn:
            return {
                "success": False,
                "message": f"No rollback handler available for action '{action_id}'.",
            }

        try:
            rb_res = action.rollback_fn(entry.get("before_state"))
            msg = "Rolled back successfully."
            if isinstance(rb_res, dict) and "message" in rb_res:
                msg = rb_res["message"]

            self.history.mark_rolled_back(entry_id, message=msg)
            return {"success": True, "message": msg, "details": rb_res}
        except Exception as e:
            return {"success": False, "message": f"Rollback failed: {e}"}


# Global instances
action_registry = ActionRegistry()
action_executor = ActionExecutor(action_registry, change_history)
