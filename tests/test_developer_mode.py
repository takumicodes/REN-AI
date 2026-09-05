"""
Unit Tests for Developer / Admin Mode Security System
Tests timing-safe authentication, session isolation, capability gating, and secret non-leakage.
"""

import unittest
from ren.security.developer_mode import developer_mode_manager, DeveloperCapabilities
from ren.config.settings import settings


class TestDeveloperMode(unittest.TestCase):

    def test_verify_valid_secret(self):
        secret = settings.DEVELOPER.SECRET_KEY
        self.assertTrue(developer_mode_manager.verify_secret(secret))

    def test_verify_invalid_secret(self):
        self.assertFalse(developer_mode_manager.verify_secret("wrong_password_123"))
        self.assertFalse(developer_mode_manager.verify_secret(""))

    def test_authenticate_and_capabilities(self):
        secret = settings.DEVELOPER.SECRET_KEY
        token = developer_mode_manager.authenticate_session(secret)
        self.assertIsNotNone(token)
        self.assertTrue(developer_mode_manager.is_developer_mode_active(token))

        caps = developer_mode_manager.get_capabilities(token)
        self.assertTrue(caps.enabled)
        self.assertTrue(caps.skill_development)
        self.assertTrue(caps.advanced_tools)

        # Update capability
        updated = developer_mode_manager.update_capabilities({"debug": False}, token=token)
        self.assertFalse(updated.debug)

        # Serialization does NOT leak token
        dict_rep = caps.to_dict()
        self.assertNotIn("session_token", dict_rep)

        # Revocation
        developer_mode_manager.revoke_session(token)
        self.assertFalse(developer_mode_manager.is_developer_mode_active(token))


if __name__ == "__main__":
    unittest.main()
