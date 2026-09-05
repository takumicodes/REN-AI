"""
Unit Tests for Thinking Modes & Reasoning Configuration
Tests FAST, MEDIUM, HIGH thinking modes, Think Hard override, and context prompt guidance.
"""

import unittest
from ren.core.thinking import ThinkingMode, ThinkingConfig, thinking_manager
from ren.core.context import ContextBuilder
from ren.sessions.models import Session


class TestThinkingModes(unittest.TestCase):

    def test_fast_mode_configuration(self):
        cfg = thinking_manager.get_config(ThinkingMode.FAST)
        self.assertEqual(cfg.mode, ThinkingMode.FAST)
        self.assertFalse(cfg.is_deep_thinking)
        self.assertEqual(cfg.temperature, 0.2)
        self.assertIn("concise", cfg.reasoning_depth_prompt.lower())

    def test_medium_mode_configuration(self):
        cfg = thinking_manager.get_config(ThinkingMode.MEDIUM)
        self.assertEqual(cfg.mode, ThinkingMode.MEDIUM)
        self.assertFalse(cfg.is_deep_thinking)
        self.assertIn("step-by-step", cfg.reasoning_depth_prompt.lower())

    def test_high_mode_configuration(self):
        cfg = thinking_manager.get_config(ThinkingMode.HIGH)
        self.assertEqual(cfg.mode, ThinkingMode.HIGH)
        self.assertTrue(cfg.is_deep_thinking)
        self.assertIn("<thought>", cfg.reasoning_depth_prompt)

    def test_think_hard_override(self):
        # When think_hard=True, even FAST mode is elevated to HIGH deep reasoning
        cfg = thinking_manager.get_config(ThinkingMode.FAST, think_hard=True)
        self.assertEqual(cfg.mode, ThinkingMode.HIGH)
        self.assertTrue(cfg.is_deep_thinking)
        self.assertIn("Deep Thinking", cfg.status_label)

    def test_thinking_mode_string_parsing(self):
        self.assertEqual(ThinkingMode.from_string("fast"), ThinkingMode.FAST)
        self.assertEqual(ThinkingMode.from_string("MEDIUM"), ThinkingMode.MEDIUM)
        self.assertEqual(ThinkingMode.from_string("high"), ThinkingMode.HIGH)
        self.assertEqual(ThinkingMode.from_string("deep"), ThinkingMode.HIGH)
        self.assertEqual(ThinkingMode.from_string("unknown"), ThinkingMode.MEDIUM)

    def test_context_builder_with_thinking_mode(self):
        cfg = thinking_manager.get_config(ThinkingMode.HIGH, think_hard=True)
        session = Session(session_id="test_sess", user_id="test_usr")
        prompt = ContextBuilder.build_agent_prompt(
            user_query="Design a distributed consensus algorithm",
            session=session,
            thinking_config=cfg
        )
        self.assertIn("[Reasoning Mode: HIGH]", prompt)
        self.assertIn("<thought>", prompt)


if __name__ == "__main__":
    unittest.main()
