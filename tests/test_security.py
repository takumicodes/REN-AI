"""
Unit Tests for Security Model, Permissions, and Sandboxing
"""

import unittest
from ren.security.permissions import permission_manager, PermissionCategory, PermissionRisk
from ren.security.confirmations import confirmation_manager
from ren.security.sandbox import ExecutionSandbox


class TestSecurity(unittest.TestCase):
    def test_blocked_destructive_command(self):
        check = permission_manager.evaluate_permissions(
            required_permissions=[PermissionCategory.TERMINAL_EXECUTE],
            operation_desc="Destructive delete test",
            details={"command": "rmdir /s /q C:\\Windows"}
        )
        self.assertFalse(check.allowed)
        self.assertEqual(check.risk, PermissionRisk.BLOCKED)

    def test_permission_risk_tiers(self):
        # Read operations should be SAFE
        check_read = permission_manager.evaluate_permissions([PermissionCategory.FILESYSTEM_READ])
        self.assertEqual(check_read.risk, PermissionRisk.SAFE)
        self.assertTrue(check_read.allowed)

        # Delete operations should be HIGH_RISK
        check_del = permission_manager.evaluate_permissions([PermissionCategory.FILESYSTEM_DELETE])
        self.assertEqual(check_del.risk, PermissionRisk.HIGH_RISK)

    def test_sandbox_env_sanitization(self):
        import os
        os.environ["SECRET_API_KEY"] = "super_secret_12345"
        safe_env = ExecutionSandbox.get_sanitized_env()
        self.assertNotIn("SECRET_API_KEY", safe_env)


if __name__ == "__main__":
    unittest.main()
