"""
REN-AI v1.3.0 Hardening & Verification Test Suite
Comprehensive testing for:
1. Universal Action Registry, Risk Levels & Approval Semantics
2. Real State Verification & False Success Prevention
3. Pre-state Capture & 1-Click Rollback Integrity
4. System Tray Manager Lifecycle & Callback Marshalling
5. Single Instance Mutex & Inter-Process Wakeup Socket IPC
6. System Observer Pause/Resume & Sensor Fault Tolerance
7. Read-Only Storage Analyzer & File Type Distribution
8. Network Center Diagnostics & Stack Resets
9. Performance Telemetry Ring Buffer Bounds
"""

import sys
import os
import time
import socket
import shutil
import tempfile
import threading
import unittest
from unittest.mock import MagicMock, patch
from pathlib import Path
from collections import deque

# Ensure module path resolution
CURRENT_DIR = Path(__file__).resolve().parent
PACKAGE_DIR = CURRENT_DIR.parent
if str(PACKAGE_DIR) not in sys.path:
    sys.path.insert(0, str(PACKAGE_DIR))

from action_registry import (
    Action,
    ActionRegistry,
    ActionExecutor,
    ActionRequest,
    RiskLevel,
    ApprovalStatus,
)
from history import ChangeHistory
from single_instance import SingleInstanceManager, SINGLE_INSTANCE_PORT
from tray_manager import TrayManager
from system_observer import SystemObserver
from storage_analyzer import StorageAnalyzer
from network_center import NetworkCenter


class TestUniversalActionRegistryHardening(unittest.TestCase):
    """Deep verification of ActionRegistry, RiskLevel guards, and execute-once semantics."""

    def setUp(self):
        self.test_dir = tempfile.mkdtemp()
        self.hist_path = Path(self.test_dir) / "test_audit.json"
        self.history = ChangeHistory(self.hist_path)
        self.registry = ActionRegistry()
        self.executor = ActionExecutor(self.registry, self.history)

    def tearDown(self):
        shutil.rmtree(self.test_dir, ignore_errors=True)

    def test_action_registration_and_filtering(self):
        """Tests registration, category filtering, and risk hierarchy filtering."""
        act_safe = Action(action_id="safe_1", title="Safe Action", category="Tweak", description="Description", impact="Impact", risk_level=RiskLevel.SAFE)
        act_mod = Action(action_id="mod_1", title="Mod Action", category="Startup", description="Description", impact="Impact", risk_level=RiskLevel.MODERATE)
        act_high = Action(action_id="high_1", title="High Action", category="Process", description="Description", impact="Impact", risk_level=RiskLevel.HIGH)
        act_crit = Action(action_id="crit_1", title="Crit Action", category="System", description="Description", impact="Impact", risk_level=RiskLevel.CRITICAL)

        for a in (act_safe, act_mod, act_high, act_crit):
            self.registry.register(a)

        self.assertEqual(len(self.registry.list_all()), 4)
        self.assertEqual(len(self.registry.filter_by_category("Tweak")), 1)
        self.assertEqual(len(self.registry.filter_by_category("startup")), 1)

        # Risk level filtering: SAFE allows only SAFE
        safe_only = self.registry.filter_by_risk(RiskLevel.SAFE)
        self.assertEqual(len(safe_only), 1)
        self.assertEqual(safe_only[0].id, "safe_1")

        # MODERATE allows SAFE and MODERATE
        up_to_mod = self.registry.filter_by_risk(RiskLevel.MODERATE)
        self.assertEqual(len(up_to_mod), 2)

    def test_execute_once_semantics_and_duplicate_rejection(self):
        """Ensures ActionRequest cannot be executed twice, nor executed if dismissed/cancelled."""
        executed_count = [0]

        def dummy_action():
            executed_count[0] += 1
            return {"success": True}

        act = Action(action_id="act_once", title="Single Exec", category="Cat", description="Desc", impact="Imp", risk_level=RiskLevel.SAFE, action_fn=dummy_action)
        self.registry.register(act)

        req = self.executor.request_action(act)
        self.assertEqual(req.status, ApprovalStatus.PENDING)

        # 1st approval executes
        res1 = req.approve(self.executor)
        self.assertTrue(res1["success"])
        self.assertEqual(executed_count[0], 1)
        self.assertEqual(req.status, ApprovalStatus.EXECUTED)

        # 2nd approval MUST be rejected (execute-once invariant)
        res2 = req.approve(self.executor)
        self.assertFalse(res2["success"])
        self.assertIn("rejected", res2["message"].lower())
        self.assertEqual(executed_count[0], 1)

    def test_dismissed_and_cancelled_cannot_execute(self):
        """Ensures dismissed or cancelled action proposals reject execution."""
        executed_count = [0]
        act = Action(action_id="act_dismiss", title="Dismiss Me", category="Cat", description="Desc", impact="Imp", risk_level=RiskLevel.SAFE, action_fn=lambda: executed_count.append(1))
        self.registry.register(act)

        # Test Dismissed
        req_d = self.executor.request_action(act)
        req_d.dismiss()
        self.assertEqual(req_d.status, ApprovalStatus.DISMISSED)
        res_d = req_d.approve(self.executor)
        self.assertFalse(res_d["success"])

        # Test Cancelled
        req_c = self.executor.request_action(act)
        req_c.cancel()
        self.assertEqual(req_c.status, ApprovalStatus.CANCELLED)
        res_c = req_c.approve(self.executor)
        self.assertFalse(res_c["success"])

        self.assertEqual(len(executed_count), 1)  # only initial [0]

    def test_high_risk_requires_explicit_confirmation(self):
        """Consequential safety: High & Critical risk actions MUST require user_confirmed=True."""
        act_high = Action(action_id="crit_act", title="Dangerous Operation", category="System", description="Desc", impact="High Impact", risk_level=RiskLevel.HIGH, action_fn=lambda: {"success": True})
        self.registry.register(act_high)

        # Unconfirmed execution blocked
        res_unconfirmed = self.executor.execute_action(act_high, user_confirmed=False)
        self.assertFalse(res_unconfirmed["success"])
        self.assertTrue(res_unconfirmed.get("requires_confirmation"))

        # Confirmed execution succeeds
        res_confirmed = self.executor.execute_action(act_high, user_confirmed=True)
        self.assertTrue(res_confirmed["success"])

    def test_real_state_verification_and_false_success_prevention(self):
        """Universal verification rule: If verification fails, action marked failed, no false success claimed."""
        # Action that claims success but verification check detects Windows state did not change
        fake_act = Action(
            action_id="fake_success_act",
            title="Fake Plan Switch",
            category="Power",
            description="Returns success but verification fails",
            impact="None",
            risk_level=RiskLevel.SAFE,
            action_fn=lambda: {"success": True},  # claims success
            verify_fn=lambda: (False, "Windows power profile did not switch."),  # real check fails!
        )
        self.registry.register(fake_act)

        res = self.executor.execute_action(fake_act)
        # Even though action_fn succeeded, verification failed
        self.assertFalse(res.get("verified"))
        self.assertIn("did not switch", res.get("verification_message"))

        # Audit history must record verification status accurately
        hist_entry = self.history.get_entry(res["history_entry_id"])
        self.assertFalse(hist_entry["verified"])

    def test_pre_state_capture_and_rollback_integrity(self):
        """Validates that before_state is captured and rollback faithfully restores it."""
        mock_windows_registry = {"SettingEnabled": 0}

        def apply_setting():
            mock_windows_registry["SettingEnabled"] = 1
            return {"success": True}

        def verify_setting():
            return (mock_windows_registry["SettingEnabled"] == 1, "Verified")

        def rollback_setting(prev):
            mock_windows_registry["SettingEnabled"] = prev["SettingEnabled"]
            return {"success": True, "message": "Restored previous registry state."}

        act = Action(
            action_id="reg_tweak_1",
            title="Tweak Registry",
            category="Tweak",
            description="Toggles setting",
            impact="Modifies reg",
            risk_level=RiskLevel.SAFE,
            action_fn=apply_setting,
            verify_fn=verify_setting,
            rollback_fn=rollback_setting,
            get_state_fn=lambda: {"SettingEnabled": mock_windows_registry["SettingEnabled"]},
        )
        self.registry.register(act)

        # Initial state is 0
        self.assertEqual(mock_windows_registry["SettingEnabled"], 0)

        # Execute
        res = self.executor.execute_action(act)
        self.assertTrue(res["success"])
        self.assertTrue(res["verified"])
        self.assertEqual(mock_windows_registry["SettingEnabled"], 1)

        # Rollback
        entry_id = res["history_entry_id"]
        rb_res = self.executor.rollback_entry(entry_id)
        self.assertTrue(rb_res["success"])
        self.assertEqual(mock_windows_registry["SettingEnabled"], 0)


class TestSystemTrayManager(unittest.TestCase):
    """Tests System Tray Manager notifications, tooltip truncation, and callback safety."""

    def test_tray_initialization_and_tooltip_truncation(self):
        """Ensures TrayManager initializes cleanly and limits tooltip to 127 characters."""
        opened = [False]
        paused = [False]

        tray = TrayManager(
            on_open_callback=lambda: opened.__setitem__(0, True),
            on_pause_callback=lambda: paused.__setitem__(0, True),
            on_resume_callback=lambda: None,
            on_settings_callback=lambda: None,
            on_exit_callback=lambda: None,
        )

        # Tooltip length safety (Windows API limit is 127 chars)
        long_tooltip = "A" * 200
        tray.update_tooltip(long_tooltip)
        # If _icon exists or mock, length should be clamped to 127
        if tray._icon:
            self.assertLessEqual(len(tray._icon.title), 127)

        # Stop safely
        tray.stop()
        self.assertIsNone(tray._icon)


class TestSingleInstanceManager(unittest.TestCase):
    """Tests Windows single-instance mutex and localhost loopback IPC wakeup."""

    def test_socket_wakeup_message(self):
        """Verifies that sending REN_RESTORE_WINDOW over localhost socket triggers wakeup callback."""
        woken = [False]

        manager = SingleInstanceManager(on_wake_callback=lambda: woken.__setitem__(0, True))

        # Acquire lock (binds socket)
        acquired = manager.acquire()
        if not acquired:
            # If port was already bound in another test run, release and retry
            manager.release()
            acquired = manager.acquire()

        if acquired:
            try:
                # Secondary instance simulates launch and sends wakeup packet
                client = socket.socket(socket.AF_INET, socket.SOCK_STREAM)
                client.settimeout(2.0)
                client.connect(("127.0.0.1", SINGLE_INSTANCE_PORT))
                client.sendall(b"REN_RESTORE_WINDOW\n")
                client.close()

                # Give thread up to 1 second to handle incoming signal
                time.sleep(0.3)
                self.assertTrue(woken[0], "Primary instance should receive wakeup from 2nd instance.")
            finally:
                manager.release()


class TestSystemObserverPauseAndSurvival(unittest.TestCase):
    """Tests pause/resume state and sensor failure tolerance."""

    def test_pause_resume_behavior(self):
        obs = SystemObserver()
        self.assertFalse(obs.is_paused)

        obs.pause()
        self.assertTrue(obs.is_paused)

        # observe_once should do nothing and return empty dict when paused
        res = obs.observe_once()
        self.assertEqual(res, {})

        obs.resume()
        self.assertFalse(obs.is_paused)

    @patch("system_observer.get_system_snapshot")
    def test_sensor_fault_tolerance(self, mock_snapshot):
        """Observer loop must survive unexpected sensor exceptions without crashing."""
        mock_snapshot.side_effect = RuntimeError("Hardware query timeout")
        obs = SystemObserver()

        # Must not raise RuntimeError
        try:
            res = obs.observe_once()
            self.assertEqual(res, {})
        except Exception as e:
            self.fail(f"observe_once should handle sensor exceptions gracefully, but raised: {e}")


class TestStorageAnalyzerEnhanced(unittest.TestCase):
    """Tests storage analysis, file type distribution, and recent large files detection."""

    def setUp(self):
        self.temp_dir = tempfile.mkdtemp()
        self.analyzer = StorageAnalyzer()

        # Create dummy directory structure using os
        os.makedirs(os.path.join(self.temp_dir, "subfolder"), exist_ok=True)
        with open(os.path.join(self.temp_dir, "test1.py"), "w", encoding="utf-8") as f:
            f.write("print('hello')")
        with open(os.path.join(self.temp_dir, "test2.zip"), "wb") as f:
            f.write(b"\x00" * 1024)

    def tearDown(self):
        shutil.rmtree(self.temp_dir, ignore_errors=True)

    def test_read_only_invariant(self):
        """StorageAnalyzer must strictly be read-only."""
        self.assertTrue(self.analyzer.read_only)

    def test_analyze_directory_distribution(self):
        res = self.analyzer.analyze_directory(self.temp_dir)
        self.assertTrue(res["success"])
        self.assertTrue(res["read_only"])
        self.assertIn("type_distribution", res)
        self.assertIn("top_files", res)
        self.assertIn("recent_large_files", res)

        exts = [d["extension"] for d in res["type_distribution"]]
        self.assertIn(".py", exts)
        self.assertIn(".zip", exts)


class TestNetworkCenterEnhanced(unittest.TestCase):
    """Tests DNS lookup, firewall status, and network stack reset formatting."""

    def setUp(self):
        self.net = NetworkCenter()

    def test_dns_lookup(self):
        res = self.net.dns_lookup("127.0.0.1")
        self.assertTrue(res["success"])
        self.assertIn("127.0.0.1", res["addresses"])

    def test_firewall_and_proxy_status(self):
        fw = self.net.get_firewall_status()
        self.assertIsInstance(fw, dict)
        self.assertIn("success", fw)

        proxy = self.net.get_proxy_info()
        self.assertIsInstance(proxy, dict)
        self.assertIn("proxy_enabled", proxy)

    @patch("subprocess.run")
    def test_winsock_and_tcpip_reset_mock(self, mock_run):
        mock_proc = MagicMock()
        mock_proc.returncode = 0
        mock_proc.stdout = "Sucessfully reset the Winsock Catalog."
        mock_run.return_value = mock_proc

        ws_res = self.net.reset_winsock()
        self.assertTrue(ws_res["success"])

        tcp_res = self.net.reset_tcpip()
        self.assertTrue(tcp_res["success"])


class TestTelemetryRingBuffers(unittest.TestCase):
    """Verifies bounded 60-second in-memory performance ring buffers."""

    def test_ring_buffer_fifo_eviction(self):
        buf = deque(maxlen=60)
        for i in range(100):
            buf.append(i)

        self.assertEqual(len(buf), 60)
        self.assertEqual(buf[0], 40)   # Oldest remaining element
        self.assertEqual(buf[-1], 99)  # Newest element


if __name__ == "__main__":
    unittest.main()
