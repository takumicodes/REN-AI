"""
Tests for Phase 2: Memory Categories & Structured World Model.
"""

import unittest
from ren.memory.manager import memory_manager
from ren.core.world_model import WorldModel, world_model
from ren.core.context import ContextBuilder
from ren.sessions.models import Session
from ren.core.router import IntentRouter


class TestMemoryAndWorldModel(unittest.TestCase):

    def test_structured_memory_categories_and_provenance(self):
        # Store semantic
        id1 = memory_manager.store_semantic("Python 3.10 is the core runtime", tags="python,version", confidence=0.98, provenance="system")
        self.assertGreater(id1, 0)

        # Store procedural
        id2 = memory_manager.store_procedural("To deploy, start Cloudflare tunnel and launch API", tags="deploy", confidence=0.95, provenance="runbook")
        self.assertGreater(id2, 0)

        # Store goal
        id3 = memory_manager.store_goal("Reach autonomous persistent state", tags="agi,evolution", confidence=1.0, provenance="user")
        self.assertGreater(id3, 0)

        # Store learning
        id4 = memory_manager.store_learning("High-risk operations must prompt user confirmation", tags="safety", confidence=0.99, provenance="evaluation")
        self.assertGreater(id4, 0)

        # Retrieve and verify confidence/provenance preserved
        all_mems = memory_manager.store.get_all_long_term_memories(category="learning")
        matched = [m for m in all_mems if m.get("id") == id4]
        self.assertTrue(len(matched) > 0)
        self.assertAlmostEqual(matched[0].get("confidence", 0), 0.99)
        self.assertEqual(matched[0].get("provenance"), "evaluation")

    def test_world_model_task_and_project_lifecycle(self):
        wm = WorldModel()
        task = wm.create_task("Test task for automated testing", user_id="test_user", assigned_device="pc_host")
        self.assertEqual(task.status, "active")

        # Query active tasks
        active = wm.list_active_tasks("test_user")
        self.assertEqual(len(active), 1)
        self.assertEqual(active[0].task_id, task.task_id)

        # Update task status
        wm.update_task_status(task.task_id, "completed", result="Test verified successfully")
        active_after = wm.list_active_tasks("test_user")
        self.assertEqual(len(active_after), 0)

    def test_what_am_i_working_on_query(self):
        # Test query routing to world model
        handled, msg = IntentRouter.try_fast_route("what am I working on")
        self.assertTrue(handled)
        self.assertIn("Here is your current structured work state", msg)
        self.assertIn("Active Projects", msg)

    def test_world_model_prompt_injection(self):
        session = Session(session_id="wm_test_sess", user_id="default")
        prompt = ContextBuilder.build_agent_prompt(
            user_query="Status check",
            session=session
        )
        self.assertIn("[Structured World Model State]", prompt)


if __name__ == "__main__":
    unittest.main()
