"""
User Confirmation and Dry-Run Handler
Handles user approvals for high-risk system operations and dry-run execution modes.
"""

from typing import Callable, Optional, Dict, Any
from ren.security.permissions import PermissionRisk, PermissionCheckResult
from ren.monitoring.logger import security_logger
from ren.config.settings import settings


class ConfirmationManager:
    """Coordinates user authorization for high-risk tool operations."""

    def __init__(self):
        self._custom_handler: Optional[Callable[[str, str, PermissionRisk], bool]] = None

    def set_confirmation_callback(self, handler: Callable[[str, str, PermissionRisk], bool]):
        """Sets custom interactive callback (e.g. PyWebView modal or prompt)."""
        self._custom_handler = handler

    def confirm_action(
        self,
        action_name: str,
        description: str,
        risk: PermissionRisk,
        dry_run: bool = False,
    ) -> bool:
        """Evaluates whether the requested action is permitted to proceed."""
        if dry_run or settings.AGENT.ENABLE_DRY_RUN:
            security_logger.info(f"[DRY-RUN SIMULATION] Action '{action_name}' simulated: {description}")
            return True

        if risk == PermissionRisk.SAFE:
            return True

        if risk == PermissionRisk.BLOCKED:
            security_logger.warning(f"Action '{action_name}' is blocked by security policy.")
            return False

        if self._custom_handler:
            try:
                allowed = self._custom_handler(action_name, description, risk)
                security_logger.info(f"User confirmation for '{action_name}': {allowed}")
                return allowed
            except Exception as e:
                security_logger.error(f"Error in confirmation handler: {e}")
                return False

        # Default fallback: If auto-approve modifications is enabled, allow CONFIRM tier, else require explicit callback
        if risk == PermissionRisk.CONFIRM and not settings.SECURITY.REQUIRE_CONFIRMATION_FOR_MODIFICATIONS:
            return True

        # In autonomous/headless background mode without UI callback, allow CONFIRM if configured, but block HIGH_RISK
        if risk == PermissionRisk.HIGH_RISK:
            security_logger.warning(f"HIGH_RISK action '{action_name}' denied: No confirmation handler attached.")
            return False

        return True


confirmation_manager = ConfirmationManager()
