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


from history import ChangeHistory
from action_registry import Action, RiskLevel, ActionRegistry, ActionExecutor
from process_manager import ProcessManager
from startup_manager import StartupManager
from services_manager import ServicesManager
from storage_cleaner import StorageCleaner
from storage_analyzer import StorageAnalyzer
from app_manager import AppManager
from tweaks_manager import TweaksManager
from privacy_center import PrivacyCenter
from network_center import NetworkCenter
from health_diagnostics import HealthDiagnostics
from restore_center import RestoreCenter
from benchmark import BenchmarkCenter


class TestChangeHistory(unittest.TestCase):
    """Tests ChangeHistory audit trail and rollback tracking."""

    def setUp(self):
        self.test_dir = tempfile.mkdtemp()
        self.hist_file = Path(self.test_dir) / "test_history.json"
        self.history = ChangeHistory(self.hist_file)

    def tearDown(self):
        shutil.rmtree(self.test_dir, ignore_errors=True)

    def test_record_and_get_history(self):
        entry = self.history.record_action(
            action_id="test_act_1",
            title="Clean Temp",
            category="Storage",
            status="executed",
            verified=True,
            verification_message="Freed 50 MB",
            before_state={"bytes": 100},
            after_state={"bytes": 50},
        )
        self.assertIsNotNone(entry["entry_id"])
        self.assertEqual(entry["title"], "Clean Temp")
        self.assertTrue(entry["verified"])

        entries = self.history.get_history()
        self.assertEqual(len(entries), 1)

        # Test rollback marking
        res = self.history.mark_rolled_back(entry["entry_id"], message="Rolled back test")
        self.assertTrue(res)
        updated = self.history.get_entry(entry["entry_id"])
        self.assertTrue(updated["rolled_back"])
        self.assertEqual(updated["status"], "rolled_back")


class TestActionRegistryAndExecutor(unittest.TestCase):
    """Tests ActionRegistry, RiskLevel, verification, and rollback."""

    def setUp(self):
        self.test_dir = tempfile.mkdtemp()
        self.hist_file = Path(self.test_dir) / "exec_history.json"
        self.history = ChangeHistory(self.hist_file)
        self.registry = ActionRegistry()
        self.executor = ActionExecutor(self.registry, self.history)

    def tearDown(self):
        shutil.rmtree(self.test_dir, ignore_errors=True)

    def test_action_execution_and_rollback(self):
        state = {"value": "initial"}

        def do_action():
            state["value"] = "updated"
            return {"success": True}

        def verify():
            return state["value"] == "updated"

        def rollback(prev_state):
            state["value"] = prev_state["value"]
            return {"success": True}

        act = Action(
            action_id="act_val_update",
            title="Update State",
            description="Updates test state value",
            category="Test",
            impact="Changes test state",
            risk_level=RiskLevel.SAFE,
            action_fn=do_action,
            verify_fn=verify,
            rollback_fn=rollback,
            get_state_fn=lambda: {"value": state["value"]},
        )
        self.registry.register(act)

        # Execute
        res = self.executor.execute_action(act)
        self.assertTrue(res["success"])
        self.assertTrue(res["verified"])
        self.assertEqual(state["value"], "updated")

        entry_id = res["history_entry_id"]
        # Rollback
        rb_res = self.executor.rollback_entry(entry_id)
        self.assertTrue(rb_res["success"])
        self.assertEqual(state["value"], "initial")


class TestControlCenterModules(unittest.TestCase):
    """Tests all new v1.3.0 modules for safety, queries, and stability."""

    def test_process_manager(self):
        pm = ProcessManager()
        self.assertTrue(pm.is_critical_process("csrss.exe"))
        self.assertTrue(pm.is_critical_process("explorer.exe"))
        self.assertFalse(pm.is_critical_process("notepad.exe"))

        procs = pm.get_processes(limit=10)
        self.assertIsInstance(procs, list)
        self.assertGreater(len(procs), 0)
        first = procs[0]
        self.assertIsInstance(first.pid, int)
        self.assertIsInstance(first.name, str)
        self.assertIsInstance(first.memory_mb, float)

        # Critical guard
        crit_res = pm.terminate_process(pid=4, force=False)
        self.assertFalse(crit_res["success"])

    def test_startup_manager(self):
        sm = StartupManager()
        items = sm.get_startup_items()
        self.assertIsInstance(items, list)

    def test_services_manager(self):
        svm = ServicesManager()
        services = svm.get_services(limit=15)
        self.assertIsInstance(services, list)
        self.assertGreater(len(services), 0)
        # Verify core service shield
        shield_res = svm.stop_service("RpcSs", force=False)
        self.assertFalse(shield_res["success"])
        self.assertTrue(shield_res.get("is_core", False))

    def test_storage_cleaner(self):
        sc = StorageCleaner()
        items = sc.scan_all()
        self.assertIn("user_temp", items)
        self.assertIn("system_temp", items)
        self.assertIn("crash_dumps", items)
        self.assertIsInstance(items["user_temp"].total_mb, float)

    def test_storage_analyzer(self):
        sa = StorageAnalyzer()
        drives = sa.get_drives()
        self.assertIsInstance(drives, list)
        self.assertGreater(len(drives), 0)
        c_drive = drives[0]
        self.assertGreater(c_drive.total_gb, 0.0)

    def test_app_manager(self):
        am = AppManager()
        apps = am.get_installed_apps(limit=10)
        self.assertIsInstance(apps, list)

    def test_tweaks_manager(self):
        tm = TweaksManager()
        all_tweaks = tm.get_all_tweaks()
        self.assertIn("show_file_extensions", all_tweaks)
        self.assertIn("show_hidden_files", all_tweaks)
        self.assertIn("compact_view", all_tweaks)
        self.assertIn("end_task_taskbar", all_tweaks)

    def test_privacy_center(self):
        pc = PrivacyCenter()
        settings = pc.get_privacy_settings()
        self.assertIn("advertising_id", settings)
        self.assertIn("tailored_experiences", settings)
        self.assertIn("activity_history", settings)

    def test_network_center(self):
        nc = NetworkCenter()
        adapters = nc.get_adapter_info()
        self.assertIsInstance(adapters, list)
        conns = nc.get_active_connections(limit=10)
        self.assertIsInstance(conns, list)

    def test_health_diagnostics(self):
        hd = HealthDiagnostics()
        dirty = hd.check_drive_dirty("C:")
        self.assertIn("is_dirty", dirty)
        recs = hd.get_integrity_recommendations()
        self.assertEqual(len(recs), 2)

    def test_restore_center(self):
        rc = RestoreCenter()
        pts = rc.get_restore_points()
        self.assertIsInstance(pts, list)

    def test_benchmark_center(self):
        bc = BenchmarkCenter()
        res = bc.run_benchmark()
        self.assertIn("composite_score", res)
        self.assertIn("cpu_score", res)
        self.assertIn("memory_score", res)
        self.assertIn("disk_score", res)
        self.assertGreater(res["composite_score"], 0)

    def test_gaming_mode(self):
        mm = ModesManager()
        self.assertIn("gaming", mm.modes)
        desc = mm.get_mode_description("gaming")
        self.assertEqual(desc["name"], "Gaming Mode")


if __name__ == "__main__":
    unittest.main()
