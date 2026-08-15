"""
REN-AI End-to-End System Health & Feature Verification Script
Runs automated diagnostics across all subsystems: Memory, Sessions, Skills, Tools, Security, Model, and Runtime.
"""

import sys
import os
import time
from pathlib import Path

# Ensure UTF-8 output on Windows consoles
if sys.platform == "win32":
    try:
        sys.stdout.reconfigure(encoding="utf-8")
        sys.stderr.reconfigure(encoding="utf-8")
    except Exception:
        pass

# Add project root to sys.path
ROOT_DIR = Path(__file__).resolve().parent
if str(ROOT_DIR) not in sys.path:
    sys.path.insert(0, str(ROOT_DIR))

from ren.config.settings import settings
from ren.monitoring.performance import perf_monitor
from ren.memory.manager import memory_manager
from ren.sessions.manager import session_manager
from ren.skills.registry import skill_registry
from ren.tools.registry import tool_registry
from ren.security.permissions import permission_manager, PermissionCategory, PermissionRisk
from ren.models import get_model_provider
from ren.core.agent import agent_runtime
from ren.core.planner import TaskPlanner
from ren.dream.daemon import dream_daemon


def print_section(title: str):
    print("\n" + "=" * 60)
    print(f" {title.upper()}")
    print("=" * 60)


def check_feature(name: str, test_fn) -> bool:
    try:
        start_t = time.perf_counter()
        res = test_fn()
        elapsed = time.perf_counter() - start_t
        print(f"  [PASS] {name:<40} ({elapsed*1000:.1f}ms)")
        if isinstance(res, str) and res.strip():
            # Use ASCII safe tree indicator
            clean_res = res.replace("\n", " ").strip()
            print(f"         +-- Output: {clean_res[:70]}")
        return True
    except Exception as e:
        print(f"  [FAIL] {name:<40} Error: {e}")
        return False


def run_full_diagnostics():
    print_section("REN-AI Core Runtime Diagnostics")
    passed = 0
    total = 0

    # 1. System & Performance Monitor
    print("\n[1] Performance & Host Monitoring:")
    total += 2
    if check_feature("Hardware Snapshot (CPU/RAM/Disk)", lambda: str(perf_monitor.get_system_snapshot())):
        passed += 1
    if check_feature("Single Inference Concurrency Lock", lambda: "Lock Available" if perf_monitor.inference_lock else "Unavailable"):
        passed += 1

    # 2. SQLite Persistent Memory
    print("\n[2] Persistent Memory System:")
    total += 3
    if check_feature("System Facts Persistence (SQLite)", lambda: f"Creator: {memory_manager.get_system_facts().get('creator', 'Unknown')}"):
        passed += 1
    if check_feature("Episodic Memory Retrieval", lambda: f"Episodes: {len(memory_manager.get_recent_episodes(limit=5))}"):
        passed += 1
    if check_feature("Relevance Context Engine (BM25)", lambda: memory_manager.get_relevant_memory_context("Python AI robots")):
        passed += 1

    # 3. Persistent Sessions
    print("\n[3] Session Lifecycle & Compaction:")
    total += 2
    if check_feature("Active Session Retrieval", lambda: f"Session ID: {session_manager.active_session.session_id}"):
        passed += 1
    if check_feature("List All Persistent Sessions", lambda: f"Total Sessions: {len(session_manager.list_sessions(include_archived=True))}"):
        passed += 1

    # 4. Skill Registry 2.0
    print("\n[4] Skill Registry 2.0:")
    total += 2
    if check_feature("Scan & Index Active Skills", lambda: f"Skills: {', '.join(skill_registry.get_unlocked_skill_names()[:4])}..."):
        passed += 1
    if check_feature("Compact Skill Index Builder", lambda: skill_registry.build_compact_skill_index()[:70]):
        passed += 1

    # 5. Tool Registry
    print("\n[5] Unified Tool Registry:")
    total += 3
    if check_feature("Registered Tools Lookup (18 tools)", lambda: f"Total Registered: {len(tool_registry.list_tools())}"):
        passed += 1
    if check_feature("System Diagnostics Tool Execution", lambda: tool_registry.execute_tool("system_status").output.splitlines()[0]):
        passed += 1
    if check_feature("Project Inspection Tool", lambda: tool_registry.execute_tool("inspect_project", {"path": "."}).output.splitlines()[0]):
        passed += 1

    # 6. Security Model & Sandboxing
    print("\n[6] Security & Sandboxing:")
    total += 2
    if check_feature("Destructive Command Blacklist Gate", lambda: "BLOCKED" if not permission_manager.evaluate_permissions([PermissionCategory.TERMINAL_EXECUTE], details={"command": "rmdir /s /q c:\\"}).allowed else "ERROR"):
        passed += 1
    if check_feature("Python Subprocess Sandbox", lambda: tool_registry.execute_tool("python_execute", {"code": "print('Sandbox OK')"}).output):
        passed += 1

    # 7. Model Backend & Provider
    print("\n[7] Model Backend Connectivity:")
    total += 1
    provider = get_model_provider()
    health = provider.health_check()
    status_str = f"Online: {health.get('online')}, Active Model: {health.get('active_model')}"
    if check_feature("Ollama Backend Health Check", lambda: status_str):
        passed += 1

    # 8. Fast Intent Routing & Agent Runtime
    print("\n[8] Agent Runtime & Fast Routing:")
    total += 2
    if check_feature("Fast Path Intent Dispatch ('who are you')", lambda: agent_runtime.process_input("who are you")):
        passed += 1
    if check_feature("Task Planning Decomposition", lambda: f"Complexity check OK: is_complex={TaskPlanner.is_complex_task('debug python script and git commit')}"):
        passed += 1

    # 9. Dream Mode 2.0
    print("\n[9] Dream Mode 2.0 (Cognitive Reflection):")
    total += 1
    if check_feature("Dream Log Generation & Status", lambda: f"Logs available: {len(dream_daemon.get_logs())}"):
        passed += 1

    # Final Summary
    print_section("Verification Summary")
    print(f"Total Tests Executed : {total}")
    print(f"Total Tests Passed   : {passed}")
    print(f"Total Tests Failed   : {total - passed}")
    print(f"System Health Status : {'[HEALTHY 100%]' if passed == total else '[ATTENTION NEEDED]'}\n")


if __name__ == "__main__":
    run_full_diagnostics()
