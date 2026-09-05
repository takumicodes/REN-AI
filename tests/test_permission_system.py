"""
Unit Tests for Risk-Based Permission Policy System
Tests LOW, MEDIUM, HIGH, BLOCKED risk tiers and deterministic policy evaluation outside the LLM.
"""

import unittest
from ren.security.permissions import (
    permission_manager,
    PermissionRisk,
    PermissionCategory,
    PermissionCheckResult
)
from ren.config.settings import settings


class TestPermissionSystem(unittest.TestCase):

    def test_low_risk_auto_approved(self):
        # File reading, web search, network querying
        res = permission_manager.evaluate_permissions(
            required_permissions=[PermissionCategory.FILESYSTEM_READ, PermissionCategory.NETWORK_REQUEST],
            operation_desc="Read document"
        )
        self.assertTrue(res.allowed)
        self.assertEqual(res.risk, PermissionRisk.LOW)
        self.assertFalse(res.requires_user_confirmation)

    def test_medium_risk_modifications(self):
        # File writing, terminal execution, skill install
        res = permission_manager.evaluate_permissions(
            required_permissions=[PermissionCategory.FILESYSTEM_WRITE],
            operation_desc="Write new script",
            details={"path": "D:/Coding projects/REN-AI-main/script.py"}
        )
        self.assertTrue(res.allowed)
        self.assertEqual(res.risk, PermissionRisk.MEDIUM)

    def test_high_risk_deletion(self):
        # File deletion
        res = permission_manager.evaluate_permissions(
            required_permissions=[PermissionCategory.FILESYSTEM_DELETE],
            operation_desc="Delete directory"
        )
        self.assertTrue(res.allowed)
        self.assertEqual(res.risk, PermissionRisk.HIGH)
        self.assertTrue(res.requires_user_confirmation)

    def test_high_risk_system_modify(self):
        res = permission_manager.evaluate_permissions(
            required_permissions=[PermissionCategory.SYSTEM_MODIFY],
            operation_desc="Modify OS registry"
        )
        self.assertEqual(res.risk, PermissionRisk.HIGH)
        self.assertTrue(res.requires_user_confirmation)

    def test_blocked_destructive_command(self):
        res = permission_manager.evaluate_permissions(
            required_permissions=[PermissionCategory.TERMINAL_EXECUTE],
            operation_desc="Format drive",
            details={"command": "format c: /fs:ntfs"}
        )
        self.assertFalse(res.allowed)
        self.assertEqual(res.risk, PermissionRisk.BLOCKED)

    def test_blocked_hacking_tools(self):
        for tool_cmd in ["mimikatz.exe", "sqlmap -u http://example.com", "hydra -l user -P pass 127.0.0.1 ssh", "arpspoof -i eth0"]:
            res = permission_manager.evaluate_permissions(
                required_permissions=[PermissionCategory.TERMINAL_EXECUTE],
                operation_desc=f"Run {tool_cmd}",
                details={"command": tool_cmd}
            )
            self.assertFalse(res.allowed, f"Should have blocked {tool_cmd}")
            self.assertEqual(res.risk, PermissionRisk.BLOCKED)


if __name__ == "__main__":
    unittest.main()
