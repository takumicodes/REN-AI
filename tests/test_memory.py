"""
Unit Tests for Memory System (SQLite Persistence, Relevance Retrieval, Backups, Recovery)
"""

import unittest
import tempfile
import os
import shutil
from pathlib import Path

from ren.memory.store import MemoryStore
from ren.memory.retrieval import MemoryRetrieval
from ren.memory.summarizer import MemorySummarizer
from ren.memory.manager import MemoryManager


class TestMemoryStore(unittest.TestCase):
    def setUp(self):
        self.temp_dir = tempfile.mkdtemp()
        self.db_path = Path(self.temp_dir) / "test_memory.db"
        self.store = MemoryStore(db_path=self.db_path)

    def tearDown(self):
        shutil.rmtree(self.temp_dir, ignore_errors=True)

    def test_system_facts_crud(self):
        self.store.set_system_fact("creator", "Sadiq")
        self.assertEqual(self.store.get_system_fact("creator"), "Sadiq")
        self.assertEqual(self.store.get_system_fact("nonexistent", default="none"), "none")

    def test_long_term_memories_crud(self):
        mem_id = self.store.add_long_term_memory(
            content="User loves Python and OpenCV",
            category="preference",
            importance=3,
            tags="python,opencv,user"
        )
        self.assertGreater(mem_id, 0)
        mems = self.store.get_all_long_term_memories(category="preference")
        self.assertEqual(len(mems), 1)
        self.assertEqual(mems[0]["content"], "User loves Python and OpenCV")

    def test_episodic_memory(self):
        ep_id = self.store.record_episode(
            task="Fix PyAudio import",
            outcome="Success",
            actions_taken="pip install PyAudio",
            solution="Installed wheels for Windows"
        )
        self.assertGreater(ep_id, 0)
        episodes = self.store.get_recent_episodes()
        self.assertEqual(len(episodes), 1)
        self.assertEqual(episodes[0]["task"], "Fix PyAudio import")

    def test_project_memory(self):
        self.store.upsert_project(
            name="REN-AI",
            path="/workspace/ren",
            language="Python",
            framework="PyWebView",
            important_files=["back_end.py", "gui.py"]
        )
        proj = self.store.get_project("REN-AI")
        self.assertIsNotNone(proj)
        self.assertEqual(proj["language"], "Python")
        self.assertIn("back_end.py", proj["important_files"])

    def test_database_backup_and_recovery(self):
        self.store.set_system_fact("test_key", "test_value")
        backup = self.store.backup_database()
        self.assertIsNotNone(backup)
        self.assertTrue(backup.exists())

        # Simulate recovery
        self.store.recover_corrupted_db()
        self.assertEqual(self.store.get_system_fact("test_key"), "test_value")


class TestMemoryRetrieval(unittest.TestCase):
    def test_relevance_ranking(self):
        memories = [
            {"content": "Sadiq loves building autonomous AI robots", "importance": 3, "tags": "robots,ai"},
            {"content": "The weather in Seattle is rainy", "importance": 1, "tags": "weather"},
            {"content": "Python is used for backend agent development", "importance": 2, "tags": "python,backend"},
        ]
        results = MemoryRetrieval.rank_memories("Tell me about robots and AI", memories, top_k=2)
        self.assertGreater(len(results), 0)
        self.assertIn("robots", results[0]["content"].lower())

    def test_tokenization_and_stop_words(self):
        tokens = MemoryRetrieval.tokenize("What is the best way to execute Python?")
        self.assertIn("python", tokens)
        self.assertIn("execute", tokens)
        self.assertNotIn("is", tokens)
        self.assertNotIn("the", tokens)


class TestMemorySummarizer(unittest.TestCase):
    def test_heuristic_summarize(self):
        messages = [
            {"role": "user", "content": "Please inspect my Git commits."},
            {"role": "assistant", "content": "Found 3 commits on main branch."},
            {"role": "user", "content": "Create a new branch for testing."},
        ]
        summary = MemorySummarizer.heuristic_summarize(messages)
        self.assertIn("Git", summary)
        self.assertIn("branch", summary)


if __name__ == "__main__":
    unittest.main()
