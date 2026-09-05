"""
Unit Tests for Autonomous Initiative Engine
Tests proactive message gating, cooldowns, importance thresholds, duplicate suppression, and SQLite persistence.
"""

import unittest
import time
from ren.autonomy.engine import autonomy_engine
from ren.autonomy.store import autonomous_store, AutonomousMessage
from ren.config.settings import settings


class TestAutonomyEngine(unittest.TestCase):

    def setUp(self):
        autonomy_engine.set_enabled(True)
        # Reset last message time
        autonomy_engine._last_message_time = 0.0
        autonomy_engine._hourly_messages = []

    def test_low_importance_rejected(self):
        allowed, reason = autonomy_engine.can_initiate_message(
            importance=0.2, # below 0.7 threshold
            curiosity=0.8
        )
        self.assertFalse(allowed)
        self.assertIn("below threshold", reason.lower())

    def test_low_curiosity_rejected(self):
        allowed, reason = autonomy_engine.can_initiate_message(
            importance=0.9,
            curiosity=0.1 # below 0.6 threshold
        )
        self.assertFalse(allowed)
        self.assertIn("below threshold", reason.lower())

    def test_disabled_engine_rejected(self):
        autonomy_engine.set_enabled(False)
        allowed, reason = autonomy_engine.can_initiate_message(importance=0.95, curiosity=0.95)
        self.assertFalse(allowed)
        self.assertIn("disabled", reason.lower())
        autonomy_engine.set_enabled(True)

    def test_propose_and_store_initiative(self):
        unique_text = f"Proactive optimization suggestion {time.time()}"
        msg = autonomy_engine.propose_initiative(
            content=unique_text,
            source="test_runner",
            importance=0.88,
            curiosity_score=0.85,
            reason="Test verification",
            title="Performance Tip"
        )
        self.assertIsNotNone(msg)
        self.assertEqual(msg.content, unique_text)
        self.assertFalse(msg.delivered)

        # Verify pending list contains it
        pending = autonomous_store.get_pending_messages()
        found = any(m.message_id == msg.message_id for m in pending)
        self.assertTrue(found)

        # Mark as delivered
        success = autonomous_store.mark_as_delivered(msg.message_id)
        self.assertTrue(success)

    def test_cooldown_enforced(self):
        # Dispatch first message
        m1 = autonomy_engine.propose_initiative(
            content=f"Initial proactive message {time.time()}",
            importance=0.9,
            curiosity_score=0.9,
            title="Tip 1"
        )
        self.assertIsNotNone(m1)

        # Immediate second message should be rejected due to cooldown
        allowed, reason = autonomy_engine.can_initiate_message(importance=0.95, curiosity=0.95)
        self.assertFalse(allowed)
        self.assertIn("cooldown active", reason.lower())


if __name__ == "__main__":
    unittest.main()
