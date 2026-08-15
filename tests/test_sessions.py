"""
Unit Tests for Session Management and Compaction
"""

import unittest
import tempfile
import shutil
from pathlib import Path

from ren.sessions.manager import SessionManager
from ren.sessions.models import Session, Message, Plan, PlanStep


class TestSessionManager(unittest.TestCase):
    def setUp(self):
        self.temp_dir = tempfile.mkdtemp()
        self.manager = SessionManager(sessions_dir=Path(self.temp_dir))

    def tearDown(self):
        shutil.rmtree(self.temp_dir, ignore_errors=True)

    def test_create_and_resume_session(self):
        session = self.manager.create_session(title="Unit Test Session", project="TestProj")
        session.add_message(role="user", content="Hello test!")
        self.manager.save_session(session)

        resumed = self.manager.resume_session(session.session_id)
        self.assertIsNotNone(resumed)
        self.assertEqual(resumed.title, "Unit Test Session")
        self.assertEqual(len(resumed.messages), 1)

    def test_list_and_archive_session(self):
        s1 = self.manager.create_session(title="Session 1")
        s2 = self.manager.create_session(title="Session 2")
        all_sessions = self.manager.list_sessions(include_archived=True)
        session_ids = [s["session_id"] for s in all_sessions]
        self.assertIn(s1.session_id, session_ids)
        self.assertIn(s2.session_id, session_ids)

        self.manager.archive_session(s1.session_id)
        active_sessions = self.manager.list_sessions(include_archived=False)
        active_ids = [s["session_id"] for s in active_sessions]
        self.assertNotIn(s1.session_id, active_ids)
        self.assertIn(s2.session_id, active_ids)

    def test_session_compaction(self):
        session = self.manager.create_session(title="Long Session")
        for i in range(12):
            session.add_message(role="user" if i % 2 == 0 else "assistant", content=f"Message step {i}")
        self.manager.save_session(session)

        self.manager.compact_session_if_needed(session, max_messages=8, keep_recent=3)
        self.assertEqual(len(session.messages), 3)
        self.assertTrue(len(session.summary) > 0)


if __name__ == "__main__":
    unittest.main()
