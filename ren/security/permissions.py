"""
REN Security & Permission System
Classifies operations into risk tiers, enforces permission gates, and protects host safety.
"""

from enum import Enum
from typing import List, Set, Dict, Any, Optional
from dataclasses import dataclass

from ren.config.settings import settings
from ren.monitoring.logger import security_logger


class PermissionRisk(Enum):
    SAFE = "SAFE"
    CONFIRM = "CONFIRM"
    HIGH_RISK = "HIGH_RISK"
    BLOCKED = "BLOCKED"


class PermissionCategory(str, Enum):
    FILESYSTEM_READ = "filesystem.read"
    FILESYSTEM_WRITE = "filesystem.write"
    FILESYSTEM_DELETE = "filesystem.delete"
    TERMINAL_EXECUTE = "terminal.execute"
    PROCESS_START = "process.start"
    PROCESS_STOP = "process.stop"
    NETWORK_REQUEST = "network.request"
    BROWSER_CONTROL = "browser.control"
    GIT_WRITE = "git.write"
    SYSTEM_MODIFY = "system.modify"
    SKILL_INSTALL = "skill.install"
    REN_MODIFY = "ren.modify"


# Default classification mapping
RISK_MAP: Dict[PermissionCategory, PermissionRisk] = {
    PermissionCategory.FILESYSTEM_READ: PermissionRisk.SAFE,
    PermissionCategory.NETWORK_REQUEST: PermissionRisk.SAFE,
    PermissionCategory.BROWSER_CONTROL: PermissionRisk.SAFE,
    
    PermissionCategory.FILESYSTEM_WRITE: PermissionRisk.CONFIRM,
    PermissionCategory.GIT_WRITE: PermissionRisk.CONFIRM,
    PermissionCategory.TERMINAL_EXECUTE: PermissionRisk.CONFIRM,
    PermissionCategory.PROCESS_START: PermissionRisk.CONFIRM,
    PermissionCategory.SKILL_INSTALL: PermissionRisk.CONFIRM,

    PermissionCategory.FILESYSTEM_DELETE: PermissionRisk.HIGH_RISK,
    PermissionCategory.PROCESS_STOP: PermissionRisk.HIGH_RISK,
    PermissionCategory.SYSTEM_MODIFY: PermissionRisk.HIGH_RISK,
    PermissionCategory.REN_MODIFY: PermissionRisk.HIGH_RISK,
}


@dataclass
class PermissionCheckResult:
    allowed: bool
    risk: PermissionRisk
    reason: str = ""
    requires_user_confirmation: bool = False


class PermissionManager:
    """Evaluates and enforces permission policies across tool and skill invocations."""

    def __init__(self):
        self.blocked_patterns = settings.SECURITY.BLOCKED_COMMANDS

    def evaluate_permissions(
        self,
        required_permissions: List[PermissionCategory],
        operation_desc: str = "",
        details: Optional[Dict[str, Any]] = None,
    ) -> PermissionCheckResult:
        """Evaluates whether an action requires confirmation or is blocked."""
        # 1. Check for explicitly blocked commands or patterns
        if details and "command" in details:
            cmd = str(details["command"]).lower()
            for blocked in self.blocked_patterns:
                if blocked in cmd:
                    security_logger.warning(f"BLOCKED command matched pattern '{blocked}': {cmd}")
                    return PermissionCheckResult(
                        allowed=False,
                        risk=PermissionRisk.BLOCKED,
                        reason=f"Command matches destructive blocked blacklist pattern: {blocked}",
                    )

        highest_risk = PermissionRisk.SAFE
        for perm in required_permissions:
            risk = RISK_MAP.get(perm, PermissionRisk.CONFIRM)
            if risk == PermissionRisk.HIGH_RISK:
                highest_risk = PermissionRisk.HIGH_RISK
            elif risk == PermissionRisk.CONFIRM and highest_risk != PermissionRisk.HIGH_RISK:
                highest_risk = PermissionRisk.CONFIRM

        if highest_risk == PermissionRisk.SAFE:
            return PermissionCheckResult(allowed=True, risk=highest_risk)

        if highest_risk == PermissionRisk.CONFIRM:
            req_confirm = settings.SECURITY.REQUIRE_CONFIRMATION_FOR_MODIFICATIONS
            return PermissionCheckResult(
                allowed=True,
                risk=highest_risk,
                reason=f"Operation requires write/execute permission ({operation_desc})",
                requires_user_confirmation=req_confirm,
            )

        # High Risk
        return PermissionCheckResult(
            allowed=True,
            risk=highest_risk,
            reason=f"High-risk operation requested ({operation_desc}). Requires explicit confirmation.",
            requires_user_confirmation=True,
        )


permission_manager = PermissionManager()
