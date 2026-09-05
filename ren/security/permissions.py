"""
REN Security & Permission System (Risk-Based Policy Engine)
Classifies operations into deterministic risk tiers (LOW, MEDIUM, HIGH, BLOCKED),
enforces permission gates outside the LLM, and protects host safety without unnecessary friction.
"""

import os
from enum import Enum
from typing import List, Set, Dict, Any, Optional
from dataclasses import dataclass

from ren.config.settings import settings
from ren.monitoring.logger import security_logger


class PermissionRisk(str, Enum):
    LOW = "LOW"
    MEDIUM = "MEDIUM"
    HIGH = "HIGH"
    BLOCKED = "BLOCKED"

    # Aliases for backwards compatibility
    SAFE = "LOW"
    CONFIRM = "MEDIUM"
    HIGH_RISK = "HIGH"


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


# Deterministic risk mapping
RISK_MAP: Dict[PermissionCategory, PermissionRisk] = {
    PermissionCategory.FILESYSTEM_READ: PermissionRisk.LOW,
    PermissionCategory.NETWORK_REQUEST: PermissionRisk.LOW,
    PermissionCategory.BROWSER_CONTROL: PermissionRisk.LOW,
    
    PermissionCategory.FILESYSTEM_WRITE: PermissionRisk.MEDIUM,
    PermissionCategory.GIT_WRITE: PermissionRisk.MEDIUM,
    PermissionCategory.TERMINAL_EXECUTE: PermissionRisk.MEDIUM,
    PermissionCategory.PROCESS_START: PermissionRisk.MEDIUM,
    PermissionCategory.SKILL_INSTALL: PermissionRisk.MEDIUM,

    PermissionCategory.FILESYSTEM_DELETE: PermissionRisk.HIGH,
    PermissionCategory.PROCESS_STOP: PermissionRisk.HIGH,
    PermissionCategory.SYSTEM_MODIFY: PermissionRisk.HIGH,
    PermissionCategory.REN_MODIFY: PermissionRisk.HIGH,
}


@dataclass
class PermissionCheckResult:
    allowed: bool
    risk: PermissionRisk
    reason: str = ""
    requires_user_confirmation: bool = False


class PermissionManager:
    """Evaluates and enforces risk-based security policies across tool and skill invocations."""

    def __init__(self):
        self.blocked_patterns = settings.SECURITY.BLOCKED_COMMANDS

    def evaluate_permissions(
        self,
        required_permissions: List[PermissionCategory],
        operation_desc: str = "",
        details: Optional[Dict[str, Any]] = None,
    ) -> PermissionCheckResult:
        """
        Determines permission risk tier and whether action is allowed or requires confirmation.
        The backend permission layer is authoritative and completely independent of the LLM.
        """
        # 1. Blacklist check (Immediate hard block)
        if details and "command" in details:
            cmd = str(details["command"]).lower()
            for blocked in self.blocked_patterns:
                if blocked in cmd:
                    security_logger.warning(f"BLOCKED command matched blacklist pattern '{blocked}': {cmd}")
                    return PermissionCheckResult(
                        allowed=False,
                        risk=PermissionRisk.BLOCKED,
                        reason=f"Command matches destructive blocked blacklist pattern: {blocked}",
                        requires_user_confirmation=False,
                    )

        # 2. Determine highest risk tier from required permissions
        highest_risk = PermissionRisk.LOW
        for perm in required_permissions:
            risk = RISK_MAP.get(perm, PermissionRisk.MEDIUM)
            if risk == PermissionRisk.HIGH:
                highest_risk = PermissionRisk.HIGH
            elif risk == PermissionRisk.MEDIUM and highest_risk != PermissionRisk.HIGH:
                highest_risk = PermissionRisk.MEDIUM

        # 3. Path-based sensitivity checks
        if details and "path" in details:
            target_path = str(details["path"]).lower()
            # Deleting or modifying outside project workspace elevates risk
            if any(p in target_path for p in ["c:\\windows", "/etc", "/usr", "c:\\program files"]):
                highest_risk = PermissionRisk.HIGH

        # 4. Low-Risk: Auto-approve without asking confirmation
        if highest_risk == PermissionRisk.LOW:
            return PermissionCheckResult(
                allowed=True,
                risk=highest_risk,
                reason="Low-risk operation allowed automatically.",
                requires_user_confirmation=False,
            )

        # 5. Medium-Risk: Allowed when requested, configurable confirmation
        if highest_risk == PermissionRisk.MEDIUM:
            req_confirm = settings.SECURITY.REQUIRE_CONFIRMATION_FOR_MODIFICATIONS
            return PermissionCheckResult(
                allowed=True,
                risk=highest_risk,
                reason=f"Medium-risk operation ({operation_desc})",
                requires_user_confirmation=req_confirm,
            )

        # 6. High-Risk: Requires explicit user confirmation
        return PermissionCheckResult(
            allowed=True,
            risk=PermissionRisk.HIGH,
            reason=f"High-risk operation requested ({operation_desc}). Requires explicit confirmation.",
            requires_user_confirmation=True,
        )


# Global permission manager singleton
permission_manager = PermissionManager()
