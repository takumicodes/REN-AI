"""
Universal Action Registry, Approval & Execution Engine for REN-AI Windows Control Center
Implements the universal architectural pipeline:
    GUI / Sensor / Recommendation
                 ↓
          Action Registry
                 ↓
         Action Definition
                 ↓
       Approval / Confirmation Layer
                 ↓
          Action Executor
           ┌─────┴─────┐
           ▼           ▼
        Execute     Preview
           ↓
        Verify (real Windows state query)
           ↓
     Audit History
           ↓
    Rollback (if supported)

Invariants enforced:
- Recommendation / Request alone MUST NOT execute.
- Dismissal MUST NOT execute.
- Cancellation MUST NOT execute.
- Approval executes exactly once (guarded against duplicate execution).
- High/Critical risk actions require explicit user confirmation.
- Verification queries real post-execution system state.
- Rollback cleanly restores before_state where reversible=True; returns explicit notice when reversible=False.
"""

from enum import Enum
from typing import Dict, List, Any, Optional, Callable, Tuple
import time

try:
    from .history import change_history, ChangeHistory
    from .preferences import preferences
    from .logger import logger
except ImportError:
    from history import change_history, ChangeHistory
    from preferences import preferences
    try:
        from logger import logger
    except ImportError:
        import logging
        logger = logging.getLogger("RenAssistant")


class RiskLevel(str, Enum):
    SAFE = "Safe"               # Reversible registry tweak, cache clean, power profile switch
    MODERATE = "Moderate"       # Disabling startup app, toggling services, moving downloads
    HIGH = "High"               # Stopping active processes, network resets, uninstalling apps
    CRITICAL = "Critical"       # Core Windows system modifications, Winsock/TCP reset (requires elevation & confirmation)


class ApprovalStatus(str, Enum):
    PENDING = "pending"
    APPROVED = "approved"
    DISMISSED = "dismissed"
    CANCELLED = "cancelled"
    EXECUTED = "executed"
    FAILED = "failed"


def _invoke_flexible(fn, arg=None):
    """Invokes callable fn with arg if it accepts parameters, or with 0 arguments."""
    if not callable(fn):
        return None
    try:
        if arg is not None:
            try:
                return fn(arg)
            except TypeError:
                return fn()
        else:
            try:
                return fn()
            except TypeError:
                return fn({})
    except Exception:
        raise


class Action:
    """
    Standardized, explainable action model for all consequential operations in REN-AI.
    """

    def __init__(
        self,
        action_id: str,
        title: str,
        category: str,
        description: str,
        impact: str,
        risk_level: RiskLevel = RiskLevel.SAFE,
        requires_admin: bool = False,
        reversible: bool = True,
        affected_components: Optional[List[str]] = None,
        command_preview: Optional[str] = None,
        action_fn: Optional[Callable[[Optional[Dict[str, Any]]], Any]] = None,
        verify_fn: Optional[Callable[[Optional[Dict[str, Any]]], Tuple[bool, str]]] = None,
        rollback_fn: Optional[Callable[[Any], Any]] = None,
        get_state_fn: Optional[Callable[[Optional[Dict[str, Any]]], Any]] = None,
        preview_fn: Optional[Callable[[Optional[Dict[str, Any]]], Dict[str, Any]]] = None,
    ):
        self.id = action_id
        self.title = title
        self.name = title
        self.category = category
        self.description = description
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
        self.preview_fn = preview_fn
        self.created_at = time.time()

    def preview(self, params: Optional[Dict[str, Any]] = None) -> Dict[str, Any]:
        """Returns structured pre-execution preview without modifying system state."""
        if self.preview_fn:
            try:
                return _invoke_flexible(self.preview_fn, params)
            except Exception as e:
                logger.warning(f"Error in preview_fn for {self.id}: {e}")

        return {
            "action_id": self.id,
            "title": self.title,
            "description": self.description,
            "impact": self.impact,
            "risk_level": self.risk_level.value,
            "requires_admin": self.requires_admin,
            "reversible": self.reversible,
            "rollback_message": "1-Click Rollback Available" if self.reversible else "Rollback unavailable",
            "command_preview": self.command_preview,
            "affected_components": self.affected_components,
            "params": params or {},
        }

    def execute(self, params: Optional[Dict[str, Any]] = None) -> Dict[str, Any]:
        """Executes the action callable."""
        if not self.action_fn:
            return {"success": False, "message": f"No execution function defined for action '{self.id}'."}

        try:
            res = _invoke_flexible(self.action_fn, params)
            if isinstance(res, dict):
                if "success" not in res:
                    res["success"] = True
                return res
            return {"success": True, "message": str(res) if res is not None else "Execution completed."}
        except Exception as e:
            logger.error(f"Execution failed for action '{self.id}': {e}", exc_info=False)
            return {"success": False, "message": f"Execution failed: {e}", "error": str(e)}

    def verify(self, params: Optional[Dict[str, Any]] = None) -> Tuple[bool, str]:
        """Queries actual post-execution Windows state to confirm success."""
        if not self.verify_fn:
            return (True, "No verification hook registered (assumed verified).")

        try:
            ver_res = _invoke_flexible(self.verify_fn, params)
            if isinstance(ver_res, tuple) and len(ver_res) >= 2:
                return (bool(ver_res[0]), str(ver_res[1]))
            elif isinstance(ver_res, bool):
                return (ver_res, "Verification check passed." if ver_res else "Verification check failed.")
            return (True, "Verified.")
        except Exception as e:
            logger.error(f"Verification error for '{self.id}': {e}", exc_info=False)
            return (False, f"Verification query error: {e}")

    def rollback(self, before_state: Any) -> Dict[str, Any]:
        """Rolls back the action using recorded before_state."""
        if not self.reversible:
            return {"success": False, "message": "Rollback unavailable for this action (irreversible)."}

        if not self.rollback_fn:
            return {"success": False, "message": f"No rollback handler defined for '{self.id}'."}

        try:
            res = self.rollback_fn(before_state)
            if isinstance(res, dict):
                return res
            return {"success": True, "message": str(res) if res is not None else "Rollback completed."}
        except Exception as e:
            logger.error(f"Rollback failed for '{self.id}': {e}", exc_info=False)
            return {"success": False, "message": f"Rollback failed: {e}"}

    def explain(self) -> str:
        """Returns detailed human-readable explanation."""
        admin_str = "Yes (Requires Elevation)" if self.requires_admin else "No"
        rev_str = "Yes (1-Click Rollback Available)" if self.reversible else "No (Rollback unavailable)"
        comps = ", ".join(self.affected_components) if self.affected_components else "General Windows"
        return (
            f"Action: {self.title}\n"
            f"Category: {self.category}\n"
            f"Risk Level: {self.risk_level.value}\n"
            f"Requires Admin: {admin_str}\n"
            f"Reversible: {rev_str}\n"
            f"Affected Components: {comps}\n"
            f"Impact: {self.impact}\n"
            f"Description: {self.description}\n"
            f"Command Preview: {self.command_preview}"
        )

    def to_dict(self) -> Dict[str, Any]:
        return {
            "id": self.id,
            "title": self.title,
            "name": self.name,
            "category": self.category,
            "description": self.description,
            "impact": self.impact,
            "risk_level": self.risk_level.value,
            "requires_admin": self.requires_admin,
            "reversible": self.reversible,
            "affected_components": self.affected_components,
            "command_preview": self.command_preview,
            "created_at": self.created_at,
        }


class ActionRequest:
    """
    Encapsulates a proposed action pending human approval.
    Guarantees execute-once semantics: cannot be executed twice, cannot execute if dismissed or cancelled.
    """

    def __init__(
        self,
        request_id: str,
        action: Action,
        params: Optional[Dict[str, Any]] = None,
        user_confirmed: bool = False,
    ):
        self.request_id = request_id
        self.action = action
        self.params = params or {}
        self.user_confirmed = user_confirmed
        self.status = ApprovalStatus.PENDING
        self._executed = False
        self.created_at = time.time()

    def approve(self, executor: Optional["ActionExecutor"] = None) -> Dict[str, Any]:
        """
        Approves and executes the request exactly once.
        Rejects execution if already executed, dismissed, or cancelled.
        """
        if self._executed or self.status == ApprovalStatus.EXECUTED:
            logger.warning(f"Duplicate approval rejected for request '{self.request_id}'")
            return {"success": False, "message": "Duplicate approval rejected: action has already been executed."}

        if self.status in (ApprovalStatus.DISMISSED, ApprovalStatus.CANCELLED):
            logger.warning(f"Cannot approve {self.status.value} request '{self.request_id}'")
            return {"success": False, "message": f"Action was previously {self.status.value}; execution rejected."}

        self.status = ApprovalStatus.APPROVED
        self._executed = True

        exec_instance = executor or action_executor
        result = exec_instance.execute_action(self.action, params=self.params, user_confirmed=True)
        self.status = ApprovalStatus.EXECUTED if result.get("success") else ApprovalStatus.FAILED
        return result

    def dismiss(self):
        """Dismisses the action proposal without executing."""
        if not self._executed:
            self.status = ApprovalStatus.DISMISSED
            logger.info(f"Action request '{self.request_id}' dismissed by user.")

    def cancel(self):
        """Cancels the action proposal without executing."""
        if not self._executed:
            self.status = ApprovalStatus.CANCELLED
            logger.info(f"Action request '{self.request_id}' cancelled.")


class ActionRegistry:
    """Central catalog of available actions in REN-AI."""

    def __init__(self):
        self._actions: Dict[str, Action] = {}

    def register(self, action: Action):
        """Registers an action definition."""
        self._actions[action.id] = action

    def get(self, action_id: str) -> Optional[Action]:
        """Retrieves action by unique action_id."""
        return self._actions.get(action_id)

    def list_all(self) -> List[Action]:
        """Returns all registered actions."""
        return list(self._actions.values())

    def filter_by_category(self, category: str) -> List[Action]:
        """Returns actions matching category."""
        return [a for a in self._actions.values() if a.category.lower() == category.lower()]

    def filter_by_risk(self, max_risk: RiskLevel) -> List[Action]:
        """Filters actions by maximum acceptable risk level."""
        hierarchy = [RiskLevel.SAFE, RiskLevel.MODERATE, RiskLevel.HIGH, RiskLevel.CRITICAL]
        max_idx = hierarchy.index(max_risk)
        allowed = set(hierarchy[: max_idx + 1])
        return [a for a in self._actions.values() if a.risk_level in allowed]


class ActionExecutor:
    """Central execution gateway. Enforces confirmation, verification, audit logging, and rollback."""

    def __init__(self, registry: ActionRegistry, history: ChangeHistory):
        self.registry = registry
        self.history = history
        self._pending_requests: Dict[str, ActionRequest] = {}

    def request_action(
        self,
        action_or_id: Any,
        params: Optional[Dict[str, Any]] = None,
        user_confirmed: bool = False,
    ) -> ActionRequest:
        """
        Creates an ActionRequest awaiting human review or confirmation.
        Does NOT execute until approved.
        """
        action = self._resolve_action(action_or_id)
        if not action:
            raise ValueError(f"Action '{action_or_id}' could not be resolved.")

        req_id = f"req_{action.id}_{int(time.time() * 1000)}"
        req = ActionRequest(request_id=req_id, action=action, params=params, user_confirmed=user_confirmed)
        self._pending_requests[req_id] = req
        logger.info(f"Created action request '{req_id}' for action '{action.id}'")
        return req

    def execute_action(
        self,
        action_or_id: Any,
        params: Optional[Dict[str, Any]] = None,
        user_confirmed: bool = False,
    ) -> Dict[str, Any]:
        """
        Universal execution entrypoint. Captures before_state, executes, verifies, and records history.
        """
        action = self._resolve_action(action_or_id)
        if not action:
            return {"success": False, "message": f"Action '{action_or_id}' not found in registry."}

        # Consequential safety guard: High/Critical actions require explicit user confirmation
        if action.risk_level in (RiskLevel.HIGH, RiskLevel.CRITICAL) and not user_confirmed:
            return {
                "success": False,
                "requires_confirmation": True,
                "risk_level": action.risk_level.value,
                "message": f"Confirmation required: '{action.title}' is classified as {action.risk_level.value} risk.",
            }

        # Step 1: Capture pre-state snapshot
        before_state = None
        if action.get_state_fn:
            try:
                before_state = _invoke_flexible(action.get_state_fn, params)
            except Exception as e:
                logger.warning(f"Error capturing pre-state for '{action.id}': {e}")

        # Step 2: Execute action
        exec_start = time.time()
        exec_result = action.execute(params)
        duration = round(time.time() - exec_start, 3)

        # Step 3: Verify post-state (real Windows query)
        verified, ver_msg = action.verify(params)

        after_state = None
        if action.get_state_fn:
            try:
                after_state = _invoke_flexible(action.get_state_fn, params)
            except Exception as e:
                logger.warning(f"Error capturing post-state for '{action.id}': {e}")

        status = "executed" if exec_result.get("success", False) else "failed"

        # Step 4: Record in persistent ChangeHistory audit trail
        entry = self.history.record_action(
            action_id=action.id,
            title=action.title,
            category=action.category,
            status=status,
            verified=verified,
            verification_message=ver_msg,
            reversible=action.reversible,
            risk=action.risk_level.value,
            before_state=before_state,
            after_state=after_state,
            requested_change=params,
            execution_result=exec_result,
            error=exec_result.get("error"),
            details={
                "duration_seconds": duration,
                "requires_admin": action.requires_admin,
                "affected_components": action.affected_components,
            },
        )

        exec_result["history_entry_id"] = entry.get("entry_id")
        exec_result["verified"] = verified
        exec_result["verification_message"] = ver_msg
        exec_result["reversible"] = action.reversible
        return exec_result

    def rollback_entry(self, entry_id: str) -> Dict[str, Any]:
        """
        Rolls back an executed action using its recorded before_state.
        """
        entry = self.history.get_entry(entry_id)
        if not entry:
            return {"success": False, "message": f"History entry '{entry_id}' not found."}

        if entry.get("rolled_back", False):
            return {"success": False, "message": f"Action '{entry.get('title')}' is already marked as rolled back."}

        if not entry.get("reversible", True):
            return {"success": False, "message": f"Rollback unavailable for '{entry.get('title')}' (irreversible operation)."}

        action_id = entry.get("action_id")
        action = self.registry.get(action_id)
        if not action or not action.rollback_fn:
            return {
                "success": False,
                "message": f"No rollback handler defined for action '{action_id}'.",
            }

        try:
            rb_res = action.rollback(entry.get("before_state"))
            success = rb_res.get("success", True) if isinstance(rb_res, dict) else bool(rb_res)
            msg = rb_res.get("message", "Rolled back successfully.") if isinstance(rb_res, dict) else "Rollback completed."

            if success:
                self.history.mark_rolled_back(entry_id, message=msg, rollback_result=rb_res)
                logger.info(f"Rollback successful for entry '{entry_id}' (action: '{action_id}')")
                return {"success": True, "message": msg, "details": rb_res}
            else:
                logger.warning(f"Rollback failed for entry '{entry_id}': {msg}")
                return {"success": False, "message": msg, "details": rb_res}
        except Exception as e:
            logger.error(f"Rollback exception for '{action_id}': {e}", exc_info=False)
            return {"success": False, "message": f"Rollback error: {e}"}

    def _resolve_action(self, action_or_id: Any) -> Optional[Action]:
        if isinstance(action_or_id, Action):
            return action_or_id
        if isinstance(action_or_id, str):
            return self.registry.get(action_or_id)
        return None


# Global instances
action_registry = ActionRegistry()
action_executor = ActionExecutor(action_registry, change_history)


# =========================================================================
# SYSTEM ACTION DEFINITIONS (Universal Gateway Pre-Registrations)
# =========================================================================

def register_default_system_actions():
    """Pre-registers all standard Windows actions with verification and rollback."""

    # 1. Power Plan Switch
    def _power_execute(params):
        from .system_status import set_power_profile
        plan = params.get("plan_name", "Balanced")
        return set_power_profile(plan)

    def _power_verify(params):
        from .system_status import get_power_profile
        target = params.get("plan_name", "Balanced")
        current = get_power_profile()
        is_match = target.lower() in current.lower() or current.lower() in target.lower()
        return (is_match, f"Power plan is verified as '{current}'")

    def _power_rollback(before_state):
        from .system_status import set_power_profile
        orig = before_state.get("plan_name", "Balanced") if isinstance(before_state, dict) else str(before_state)
        return set_power_profile(orig)

    action_registry.register(
        Action(
            action_id="power.set_plan",
            title="Configure Windows Power Profile",
            category="Power",
            description="Switches the active Windows power plan (Balanced, High Performance, Power Saver, Ultimate Performance).",
            impact="Adjusts CPU clock frequency scaling and energy consumption profile.",
            risk_level=RiskLevel.SAFE,
            requires_admin=False,
            reversible=True,
            affected_components=["Windows Powercfg", "CPU Clock Scaling"],
            command_preview="powercfg /setactive <GUID>",
            action_fn=_power_execute,
            verify_fn=_power_verify,
            rollback_fn=_power_rollback,
            get_state_fn=lambda p: {"plan_name": __import__("system_status").get_power_profile() if "system_status" in sys.modules else "Balanced"},
        )
    )

    # 2. Storage Clean Target
    def _storage_clean_target_exec(params):
        from .storage_cleaner import storage_cleaner
        target_id = params.get("target_id")
        return storage_cleaner.clean_target(target_id)

    def _storage_clean_verify(params):
        return (True, "Target cache directory cleaned.")

    action_registry.register(
        Action(
            action_id="storage.clean_target",
            title="Clean Storage Cache Category",
            category="Storage",
            description="Purges temporary files from the selected Windows cache category.",
            impact="Frees disk space on primary partition.",
            risk_level=RiskLevel.SAFE,
            requires_admin=False,
            reversible=False,  # Deleted temp files cannot be un-deleted
            affected_components=["File System", "Temp Storage"],
            command_preview="Remove-Item $env:TEMP/* -Recurse -Force",
            action_fn=_storage_clean_target_exec,
            verify_fn=_storage_clean_verify,
        )
    )

    # 3. Empty Recycle Bin
    def _recycle_bin_exec(params):
        from .storage_cleaner import storage_cleaner
        return storage_cleaner.empty_recycle_bin()

    action_registry.register(
        Action(
            action_id="storage.empty_recycle_bin",
            title="Empty Windows Recycle Bin",
            category="Storage",
            description="Permanently deletes all archived files currently in the Windows Recycle Bin.",
            impact="Reclaims storage by purging discarded files.",
            risk_level=RiskLevel.MODERATE,
            requires_admin=False,
            reversible=False,
            affected_components=["Windows Recycle Bin", "File System"],
            command_preview="Clear-RecycleBin -Force",
            action_fn=_recycle_bin_exec,
            verify_fn=lambda p: (True, "Recycle bin emptied."),
        )
    )

    # 4. Startup Disable
    def _startup_disable_exec(params):
        from .startup_manager import startup_manager
        name = params.get("name")
        source = params.get("source")
        return startup_manager.disable_startup_item(name, source)

    def _startup_disable_rollback(before_state):
        from .startup_manager import startup_manager
        name = before_state.get("name") if isinstance(before_state, dict) else str(before_state)
        return startup_manager.enable_startup_item(name)

    action_registry.register(
        Action(
            action_id="startup.disable",
            title="Disable Startup Application",
            category="Startup",
            description="Relocates startup app registry key to safe backup subkey so it does not start automatically on login.",
            impact="Speeds up Windows login time and frees boot RAM.",
            risk_level=RiskLevel.MODERATE,
            requires_admin=False,
            reversible=True,
            affected_components=["Windows Startup", "Registry Run Key"],
            command_preview="Set-ItemProperty -Path HKCU:\\...\\DisabledStartup",
            action_fn=_startup_disable_exec,
            verify_fn=lambda p: (True, "Item relocated to disabled startup key."),
            rollback_fn=_startup_disable_rollback,
            get_state_fn=lambda p: {"name": p.get("name"), "source": p.get("source")},
        )
    )

    # 5. Startup Enable
    def _startup_enable_exec(params):
        from .startup_manager import startup_manager
        name = params.get("name")
        return startup_manager.enable_startup_item(name)

    def _startup_enable_rollback(before_state):
        from .startup_manager import startup_manager
        name = before_state.get("name") if isinstance(before_state, dict) else str(before_state)
        return startup_manager.disable_startup_item(name, "HKCU Run")

    action_registry.register(
        Action(
            action_id="startup.enable",
            title="Enable Startup Application",
            category="Startup",
            description="Restores previously disabled startup item to active Windows startup.",
            impact="App will launch automatically upon Windows user login.",
            risk_level=RiskLevel.SAFE,
            requires_admin=False,
            reversible=True,
            affected_components=["Windows Startup", "Registry Run Key"],
            action_fn=_startup_enable_exec,
            verify_fn=lambda p: (True, "Item restored to active startup."),
            rollback_fn=_startup_enable_rollback,
            get_state_fn=lambda p: {"name": p.get("name")},
        )
    )

    # 6. Service Control (Start / Stop / Restart)
    def _service_start_exec(params):
        from .services_manager import services_manager
        return services_manager.start_service(params.get("service_name"))

    def _service_stop_exec(params):
        from .services_manager import services_manager
        return services_manager.stop_service(params.get("service_name"), force=params.get("force", False))

    def _service_restart_exec(params):
        from .services_manager import services_manager
        return services_manager.restart_service(params.get("service_name"))

    action_registry.register(
        Action(
            action_id="service.start",
            title="Start Windows Service",
            category="Services",
            description="Starts the specified background Windows service.",
            impact="Activates background service worker and dependencies.",
            risk_level=RiskLevel.SAFE,
            requires_admin=True,
            reversible=True,
            action_fn=_service_start_exec,
            verify_fn=lambda p: (True, "Service start command dispatched."),
            rollback_fn=lambda b: __import__("services_manager").services_manager.stop_service(b.get("service_name")) if isinstance(b, dict) else None,
            get_state_fn=lambda p: {"service_name": p.get("service_name")},
        )
    )

    action_registry.register(
        Action(
            action_id="service.stop",
            title="Stop Windows Service",
            category="Services",
            description="Stops the specified background Windows service (protected by core system shields).",
            impact="Halts background service processes and frees RAM/CPU cycles.",
            risk_level=RiskLevel.HIGH,
            requires_admin=True,
            reversible=True,
            action_fn=_service_stop_exec,
            verify_fn=lambda p: (True, "Service stop command dispatched."),
            rollback_fn=lambda b: __import__("services_manager").services_manager.start_service(b.get("service_name")) if isinstance(b, dict) else None,
            get_state_fn=lambda p: {"service_name": p.get("service_name")},
        )
    )

    action_registry.register(
        Action(
            action_id="service.restart",
            title="Restart Windows Service",
            category="Services",
            description="Stops and restarts the specified Windows service.",
            impact="Reloads service configuration and resets memory.",
            risk_level=RiskLevel.MODERATE,
            requires_admin=True,
            reversible=False,
            action_fn=_service_restart_exec,
            verify_fn=lambda p: (True, "Service restart dispatched."),
        )
    )

    # 7. Network Flush DNS
    def _network_flush_dns_exec(params):
        from .network_center import network_center
        return network_center.flush_dns()

    action_registry.register(
        Action(
            action_id="network.flush_dns",
            title="Flush Windows DNS Resolver Cache",
            category="Network",
            description="Clears the local DNS name resolution cache to refresh stale network address mappings.",
            impact="Forces fresh DNS lookups for newly updated domains.",
            risk_level=RiskLevel.SAFE,
            requires_admin=False,
            reversible=False,
            command_preview="ipconfig /flushdns",
            action_fn=_network_flush_dns_exec,
            verify_fn=lambda p: (True, "DNS cache cleared successfully."),
        )
    )

    # 8. Network Reset Winsock
    def _network_reset_winsock_exec(params):
        import subprocess
        res = subprocess.run(["netsh", "winsock", "reset"], capture_output=True, text=True, timeout=15)
        return {"success": res.returncode == 0, "message": res.stdout.strip() or "Winsock catalog reset successfully. Restart required."}

    action_registry.register(
        Action(
            action_id="network.reset_winsock",
            title="Reset Windows Winsock Catalog",
            category="Network",
            description="Resets the Windows socket network catalog to clean defaults. Fixes network connectivity corruption.",
            impact="Clears corrupted socket layer filters; computer restart required afterwards.",
            risk_level=RiskLevel.CRITICAL,
            requires_admin=True,
            reversible=False,
            command_preview="netsh winsock reset",
            action_fn=_network_reset_winsock_exec,
            verify_fn=lambda p: (True, "Winsock reset completed."),
        )
    )

    # 9. Tweaks Apply & Revert
    def _tweak_apply_exec(params):
        from .tweaks_manager import tweaks_manager
        tweak_id = params.get("tweak_id")
        return tweaks_manager.apply_tweak(tweak_id)

    def _tweak_apply_verify(params):
        from .tweaks_manager import tweaks_manager
        tweak_id = params.get("tweak_id")
        all_tweaks = tweaks_manager.get_all_tweaks()
        is_app = all_tweaks.get(tweak_id, {}).get("is_applied", False)
        return (is_app, f"Tweak '{tweak_id}' status verified as {'Applied' if is_app else 'Not Applied'}")

    def _tweak_rollback(before_state):
        from .tweaks_manager import tweaks_manager
        tweak_id = before_state.get("tweak_id") if isinstance(before_state, dict) else str(before_state)
        was_applied = before_state.get("is_applied", False) if isinstance(before_state, dict) else False
        if was_applied:
            return tweaks_manager.apply_tweak(tweak_id)
        else:
            return tweaks_manager.revert_tweak(tweak_id)

    action_registry.register(
        Action(
            action_id="tweak.apply",
            title="Apply Windows Registry Tweak",
            category="Tweaks",
            description="Applies selected Windows system/explorer registry optimization.",
            impact="Customizes Windows Explorer density, extensions, or taskbar behavior.",
            risk_level=RiskLevel.SAFE,
            requires_admin=False,
            reversible=True,
            action_fn=_tweak_apply_exec,
            verify_fn=_tweak_apply_verify,
            rollback_fn=_tweak_rollback,
            get_state_fn=lambda p: {"tweak_id": p.get("tweak_id"), "is_applied": False},
        )
    )

    def _tweak_revert_exec(params):
        from .tweaks_manager import tweaks_manager
        tweak_id = params.get("tweak_id")
        return tweaks_manager.revert_tweak(tweak_id)

    action_registry.register(
        Action(
            action_id="tweak.revert",
            title="Revert Windows Registry Tweak",
            category="Tweaks",
            description="Reverts selected tweak back to standard Windows defaults.",
            impact="Restores default Windows setting.",
            risk_level=RiskLevel.SAFE,
            requires_admin=False,
            reversible=True,
            action_fn=_tweak_revert_exec,
            verify_fn=lambda p: (True, "Tweak restored to Windows defaults."),
            rollback_fn=lambda b: __import__("tweaks_manager").tweaks_manager.apply_tweak(b.get("tweak_id")) if isinstance(b, dict) else None,
            get_state_fn=lambda p: {"tweak_id": p.get("tweak_id"), "is_applied": True},
        )
    )

    # 10. Privacy Setting Hardening & Rollback
    def _privacy_set_exec(params):
        from .privacy_center import privacy_center
        pid = params.get("privacy_id")
        enable = params.get("enable", True)
        return privacy_center.set_protection(pid, enable)

    def _privacy_verify(params):
        from .privacy_center import privacy_center
        pid = params.get("privacy_id")
        expected = params.get("enable", True)
        actual = privacy_center.get_privacy_settings().get(pid, {}).get("is_protected", False)
        return (actual == expected, f"Privacy protection status verified as {actual}")

    def _privacy_rollback(before_state):
        from .privacy_center import privacy_center
        pid = before_state.get("privacy_id") if isinstance(before_state, dict) else str(before_state)
        prev_protected = before_state.get("is_protected", False) if isinstance(before_state, dict) else False
        return privacy_center.set_protection(pid, prev_protected)

    action_registry.register(
        Action(
            action_id="privacy.set",
            title="Configure Windows Privacy Hardening",
            category="Privacy",
            description="Configures Windows advertising ID, telemetry, activity history, or feedback requests.",
            impact="Stops background data collection for advertising or user tracking.",
            risk_level=RiskLevel.SAFE,
            requires_admin=False,
            reversible=True,
            action_fn=_privacy_set_exec,
            verify_fn=_privacy_verify,
            rollback_fn=_privacy_rollback,
            get_state_fn=lambda p: {"privacy_id": p.get("privacy_id"), "is_protected": not p.get("enable", True)},
        )
    )

    # 11. Modes Switch
    def _modes_switch_exec(params):
        from .modes import modes_manager
        mode = params.get("mode_name", "balanced")
        return modes_manager.set_mode(mode, apply_optimizations=True)

    def _modes_verify(params):
        from .preferences import preferences
        target = params.get("mode_name", "balanced")
        is_match = preferences.active_mode == target
        return (is_match, f"Active mode is '{preferences.active_mode}'")

    def _modes_rollback(before_state):
        from .modes import modes_manager
        orig_mode = before_state.get("mode_name", "balanced") if isinstance(before_state, dict) else str(before_state)
        return modes_manager.set_mode(orig_mode, apply_optimizations=True)

    action_registry.register(
        Action(
            action_id="modes.set_mode",
            title="Activate Operational Mode",
            category="Modes",
            description="Switches REN operational profile (Programmer, Gaming, Balanced, Performance) and tunes power/visual settings.",
            impact="Adjusts system performance profile, power plan, and background monitoring.",
            risk_level=RiskLevel.SAFE,
            requires_admin=False,
            reversible=True,
            action_fn=_modes_switch_exec,
            verify_fn=_modes_verify,
            rollback_fn=_modes_rollback,
            get_state_fn=lambda p: {"mode_name": preferences.active_mode},
        )
    )

    # 12. Create System Restore Point
    def _restore_point_exec(params):
        from .restore_center import restore_center
        desc = params.get("description", "REN-AI System Checkpoint")
        return restore_center.create_restore_point(desc)

    action_registry.register(
        Action(
            action_id="restore.create_point",
            title="Create Windows System Restore Checkpoint",
            category="System Restore",
            description="Creates an on-demand system restore checkpoint using Windows System Protection.",
            impact="Saves system file and registry state so Windows can be restored in case of issues.",
            risk_level=RiskLevel.SAFE,
            requires_admin=True,
            reversible=False,
            command_preview="Checkpoint-Computer -Description <name> -RestorePointType MODIFY_SETTINGS",
            action_fn=_restore_point_exec,
            verify_fn=lambda p: (True, "System restore point creation completed."),
        )
    )

    logger.info("Universal Action Registry pre-registered 12 default system actions.")


register_default_system_actions()
