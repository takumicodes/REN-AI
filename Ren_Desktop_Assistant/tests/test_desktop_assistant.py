"""
Comprehensive Test Suite for REN Desktop Assistant
Tests:
- Hardware and OS status metrics (safe desktop/laptop battery handling).
- Backward compatibility of current_system().
- Persistent user preferences & dynamic learning.
- Downloads organizer (preview, organization, collision safety, undo rollback).
- Windows debloat manager and temp cache cleaning.
- 3 Modes manager (Programmer Mode, dev tools detection, winget command generation).
- Action queue (anti-spam cooldowns, human approval flow).
- Background observer daemon lifecycle and evaluation passes.
"""

import os
import sys
import time
import shutil
import tempfile
import unittest
from pathlib import Path

# Add Ren_Desktop_Assistant directory to path for testing
ASSISTANT_DIR = Path(__file__).resolve().parent.parent
sys.path.insert(0, str(ASSISTANT_DIR))

from system_status import (
    get_cpu_info,
    current_ram_usage,
    percentage_ram_left,
    get_ram_details,
    disk_usage,
    get_all_disks,
    current_battery,
    get_battery_info,
    get_power_status,
    get_power_profile,
    get_foreground_context,
    get_system_snapshot,
)
from system_info import current_system, format_system_summary
from preferences import UserPreferences, DEFAULT_PREFERENCES
from downloads_organizer import DownloadsOrganizer, CATEGORIES
from debloat import DebloatManager
from modes import ModesManager, DEV_TOOLS_CATALOG
from actions import ActionQueue, Recommendation
from system_observer import (
    SystemObserver,
    battery_logic,
    ram_logic,
    power_logic,
)


class TestSystemStatus(unittest.TestCase):
    """Tests system status metrics collection."""

    def test_cpu_and_ram(self):
        cpu = get_cpu_info()
        self.assertIsInstance(cpu, float)
        self.assertGreaterEqual(cpu, 0.0)
        self.assertLessEqual(cpu, 100.0)

        ram = current_ram_usage()
        self.assertIsInstance(ram, float)
        self.assertGreater(ram, 0.0)

        ram_left = percentage_ram_left()
        self.assertIsInstance(ram_left, float)

        details = get_ram_details()
        self.assertIn("percent_used", details)
        self.assertIn("available_gb", details)

    def test_disk_usage(self):
        disk = disk_usage()
        self.assertIsInstance(disk, float)
        self.assertGreater(disk, 0.0)
        self.assertLessEqual(disk, 100.0)

        all_disks = get_all_disks()
        self.assertIsInstance(all_disks, dict)

    def test_battery_and_power_safety(self):
        """Ensures desktop PCs without battery do not throw exceptions."""
        bat = current_battery()
        self.assertTrue(isinstance(bat, (int, float)) or bat == "No battery detected")

        bat_info = get_battery_info()
        self.assertIn("has_battery", bat_info)
        self.assertIn("is_plugged", bat_info)
        self.assertIsInstance(bat_info["is_plugged"], bool)

        pwr_status = get_power_status()
        self.assertTrue(isinstance(pwr_status, bool) or pwr_status == "No battery detected")

        profile = get_power_profile()
        self.assertIsInstance(profile, str)
        self.assertTrue(len(profile) > 0)

    def test_foreground_context(self):
        ctx = get_foreground_context()
        self.assertIn("category", ctx)
        self.assertIn("is_programming", ctx)
        self.assertIn(ctx["category"], ("programming", "browsing", "gaming", "media", "general"))

    def test_full_snapshot(self):
        snap = get_system_snapshot()
        self.assertIn("cpu_percent", snap)
        self.assertIn("ram", snap)
        self.assertIn("battery", snap)
        self.assertIn("power_profile", snap)
        self.assertIn("context", snap)


class TestSystemInfo(unittest.TestCase):
    """Tests legacy current_system() and formatters."""

    def test_current_system_legacy_tuple(self):
        res = current_system()
        self.assertEqual(len(res), 7)
        cpu, ram_usage, ram_left, disk_use, battery, power_profile, power_status = res
        self.assertIsInstance(cpu, float)
        self.assertIsInstance(ram_usage, float)
        self.assertIsInstance(disk_use, float)
        self.assertIsInstance(power_profile, str)

    def test_format_system_summary(self):
        summary = format_system_summary()
        self.assertIn("CPU:", summary)
        self.assertIn("RAM:", summary)
        self.assertIn("Disk:", summary)


class TestUserPreferences(unittest.TestCase):
    """Tests preferences persistence and dynamic habits learning."""

    def setUp(self):
        self.test_dir = tempfile.mkdtemp()
        self.pref_file = Path(self.test_dir) / "test_prefs.json"
        self.prefs = UserPreferences(self.pref_file)

    def tearDown(self):
        shutil.rmtree(self.test_dir, ignore_errors=True)

    def test_defaults_and_save(self):
        self.assertEqual(self.prefs.active_mode, "programmer")
        self.assertTrue(self.prefs.human_driven)

        self.prefs.active_mode = "performance"
        self.assertEqual(self.prefs.active_mode, "performance")

        # Reload from disk
        reloaded = UserPreferences(self.pref_file)
        self.assertEqual(reloaded.active_mode, "performance")

    def test_record_decision_learning(self):
        self.prefs.record_decision("power_switch", approved=True)
        self.prefs.record_decision("power_switch", approved=True)
        self.prefs.record_decision("power_switch", approved=False)

        patterns = self.prefs.get("learned_patterns")
        self.assertEqual(patterns["power_switch_approvals"], 2)
        self.assertEqual(patterns["power_switch_rejections"], 1)


class TestDownloadsOrganizer(unittest.TestCase):
    """Tests Downloads folder scanning, category mapping, safe movement, and undo."""

    def setUp(self):
        self.test_dir = tempfile.mkdtemp()
        self.downloads = Path(self.test_dir) / "Downloads"
        os.makedirs(str(self.downloads), exist_ok=True)
        self.organizer = DownloadsOrganizer(self.downloads)

    def tearDown(self):
        shutil.rmtree(self.test_dir, ignore_errors=True)

    def test_categories_mapping(self):
        self.assertEqual(self.organizer.get_category_for_ext(".py"), "Code_and_Dev")
        self.assertEqual(self.organizer.get_category_for_ext(".pdf"), "Documents")
        self.assertEqual(self.organizer.get_category_for_ext(".png"), "Images")
        self.assertEqual(self.organizer.get_category_for_ext(".zip"), "Archives")
        self.assertEqual(self.organizer.get_category_for_ext(".exe"), "Installers")
        self.assertIsNone(self.organizer.get_category_for_ext(".unknownext"))

    def test_organize_and_undo_flow(self):
        # Create test files
        code_file = self.downloads / "script.py"
        code_file.write_text("print('hello')", encoding="utf-8")
        doc_file = self.downloads / "document.pdf"
        doc_file.write_text("%PDF-1.4 dummy", encoding="utf-8")

        # Backdate mtime so recent-download guard doesn't filter them
        old_time = time.time() - 3600
        os.utime(code_file, (old_time, old_time))
        os.utime(doc_file, (old_time, old_time))

        # Preview
        preview = self.organizer.preview_organization(ignore_recent_minutes=0)
        self.assertEqual(preview["total_files"], 2)

        # Organize
        result = self.organizer.organize(dry_run=False, ignore_recent_minutes=0)
        self.assertTrue(result["success"])
        self.assertEqual(result["moved_count"], 2)

        # Verify files moved to categories
        self.assertTrue((self.downloads / "Code_and_Dev" / "script.py").exists())
        self.assertTrue((self.downloads / "Documents" / "document.pdf").exists())
        self.assertFalse(code_file.exists())
        self.assertFalse(doc_file.exists())

        # Undo
        undo_res = self.organizer.undo_last()
        self.assertTrue(undo_res["success"])
        self.assertEqual(undo_res["restored_count"], 2)

        # Verify files restored to original locations
        self.assertTrue(code_file.exists())
        self.assertTrue(doc_file.exists())


class TestDebloatManager(unittest.TestCase):
    """Tests debloat definitions and safe temp file cleaning."""

    def setUp(self):
        self.debloat = DebloatManager()

    def test_tweak_definitions(self):
        tweaks = self.debloat.get_tweak_definitions()
        self.assertIn("disable_search_bing", tweaks)
        self.assertIn("disable_copilot", tweaks)
        self.assertIn("optimize_visual_effects", tweaks)
        self.assertIn("clean_temp_caches", tweaks)

    def test_clean_temp_caches(self):
        res = self.debloat.clean_temp_caches()
        self.assertTrue(res["success"])
        self.assertIn("freed_mb", res)


class TestModesManager(unittest.TestCase):
    """Tests 3 modes definitions, dev tools checking, and winget commands."""

    def setUp(self):
        self.modes = ModesManager()

    def test_mode_descriptions(self):
        for m in ("programmer", "balanced", "performance"):
            desc = self.modes.get_mode_description(m)
            self.assertIn("name", desc)
            self.assertIn("tagline", desc)

    def test_check_developer_tools(self):
        tools = self.modes.check_developer_tools()
        self.assertEqual(tools["total_tools"], len(DEV_TOOLS_CATALOG))
        self.assertIn("installed", tools)
        self.assertIn("missing", tools)

    def test_winget_command_generation(self):
        cmd = self.modes.generate_winget_install_command(["git", "vscode"])
        self.assertIsInstance(cmd, str)
        if cmd:
            self.assertIn("winget install", cmd)


class TestActionQueue(unittest.TestCase):
    """Tests human-driven recommendation queue and anti-spam cooldowns."""

    def setUp(self):
        self.queue = ActionQueue()
        self.queue.clear()

    def test_propose_and_cooldown(self):
        rec = Recommendation(
            rec_id="test_rec_1",
            title="Test Recommendation",
            description="Testing queue logic",
            category="test",
            impact="Test impact",
            action_fn=lambda: {"done": True},
        )
        self.assertTrue(self.queue.propose(rec))
        self.assertEqual(len(self.queue.get_pending()), 1)

        # Propose same rec immediately -> should be blocked by cooldown
        self.assertFalse(self.queue.propose(rec))

    def test_approve_and_feedback(self):
        executed = []
        rec = Recommendation(
            rec_id="test_rec_2",
            title="Approve Test",
            description="Testing approval",
            category="test",
            impact="None",
            action_fn=lambda: executed.append(True) or {"action": "ran"},
        )
        self.queue.propose(rec)
        res = self.queue.approve("test_rec_2")
        self.assertTrue(res["success"])
        self.assertEqual(len(executed), 1)
        self.assertEqual(len(self.queue.get_pending()), 0)


class TestSystemObserver(unittest.TestCase):
    """Tests SystemObserver observation pass and backward-compatible helpers."""

    def setUp(self):
        self.obs = SystemObserver(check_interval=1)

    def test_observe_once(self):
        snapshot = self.obs.observe_once()
        self.assertIsNotNone(snapshot)
        self.assertIn("cpu_percent", snapshot)
        self.assertIn("ram", snapshot)

    def test_legacy_helpers(self):
        b_res = battery_logic()
        self.assertIsInstance(b_res, str)

        r_res = ram_logic()
        self.assertIn(r_res, ("High RAM usage", "Low RAM usage"))

        p_res = power_logic()
        self.assertIn(p_res, ("Performance-oriented power configuration", "Balanced power configuration"))

    def test_daemon_lifecycle(self):
        self.obs.start_background()
        self.assertTrue(self.obs.is_running)
        time.sleep(0.5)
        self.obs.stop()
        self.assertFalse(self.obs.is_running)


if __name__ == "__main__":
    unittest.main()
