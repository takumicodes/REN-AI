"""
REN Desktop Assistant - System Observer Core
Continuously and silently observes Windows system state in the background.
Adheres strictly to the REN Philosophy:
- 100% Human-Driven: Never takes destructive or disruptive actions without user approval.
- Zero AI Slop: No unprompted chatbot babble, no annoying popups, no blocking background loops.
- Intelligent Mode Awareness: Programmer Mode, Balanced Mode, Performance Mode.
- Safe Background Execution with rich CLI and programmatic APIs.
"""

import os
import sys
import time
import threading
from typing import Dict, Any, Optional, Tuple, List
from pathlib import Path

try:
    from .system_info import current_system, get_system_snapshot, format_system_summary
    from .system_status import (
        set_power_profile,
        get_power_profile,
        get_battery_info,
        get_ram_details,
        current_ram_usage,
        disk_usage,
        get_cpu_info,
    )
    from .preferences import preferences
    from .downloads_organizer import organizer
    from .debloat import debloat_manager
    from .modes import modes_manager
    from .actions import action_queue, Recommendation
except ImportError:
    from system_info import current_system, get_system_snapshot, format_system_summary
    from system_status import (
        set_power_profile,
        get_power_profile,
        get_battery_info,
        get_ram_details,
        current_ram_usage,
        disk_usage,
        get_cpu_info,
    )
    from preferences import preferences
    from downloads_organizer import organizer
    from debloat import debloat_manager
    from modes import modes_manager
    from actions import action_queue, Recommendation


try:
    from .logger import logger
except ImportError:
    try:
        from logger import logger
    except ImportError:
        import logging
        logger = logging.getLogger("RenAssistant")


class SystemObserver:
    """
    Continuous background daemon. Inspects hardware metrics, battery status, power schemes,
    and user environment dynamically without disturbing the user.
    """

    def __init__(self, check_interval: int = 10):
        self.interval = check_interval
        self._running = False
        self._is_paused = False
        self._thread: Optional[threading.Thread] = None
        self._lock = threading.Lock()

        # State tracking
        self.previous_snapshot: Optional[Dict[str, Any]] = None
        self.previous_battery_config: Any = None
        self.previous_power_state: Any = None
        self.previous_power_plan: Optional[str] = None
        self.observation_count = 0

    def pause(self) -> None:
        """Pauses polling and recommendation generation while keeping thread alive."""
        with self._lock:
            self._is_paused = True
            logger.info("SystemObserver paused.")

    def resume(self) -> None:
        """Resumes active polling and evaluation passes."""
        with self._lock:
            self._is_paused = False
            logger.info("SystemObserver resumed.")

    @property
    def is_paused(self) -> bool:
        return self._is_paused

    def start_background(self) -> None:
        """Starts the observer daemon in a silent background thread."""
        with self._lock:
            if self._running:
                return
            self._running = True
            self._thread = threading.Thread(target=self._run_loop, name="RenSystemObserver", daemon=True)
            self._thread.start()

    def stop(self) -> None:
        """Stops the background observer."""
        with self._lock:
            self._running = False
        if self._thread and self._thread.is_alive():
            self._thread.join(timeout=2.0)

    @property
    def is_running(self) -> bool:
        return self._running

    def observe_once(self) -> Dict[str, Any]:
        """Performs a single evaluation pass across all system metrics."""
        if self._is_paused:
            return {}

        try:
            snapshot = get_system_snapshot()
        except Exception as e:
            logger.warning(f"Error reading system snapshot in observer: {e}")
            return {}

        self.observation_count += 1

        # Check battery & power transitions
        self._evaluate_power_transitions(snapshot)

        # Check RAM utilization
        self._evaluate_ram_usage(snapshot)

        # Check Disk capacity & clutter
        self._evaluate_disk_and_downloads(snapshot)

        # Check Mode-specific developer optimizations
        self._evaluate_mode_requirements(snapshot)

        # Update previous state
        self.previous_snapshot = snapshot
        if "battery" in snapshot and isinstance(snapshot["battery"], dict):
            self.previous_battery_config = snapshot["battery"].get("percent")
            self.previous_power_state = snapshot["battery"].get("is_plugged")
        self.previous_power_plan = snapshot.get("power_profile")

        return snapshot

    def _run_loop(self) -> None:
        """Internal background polling loop."""
        while self._running:
            try:
                self.observe_once()
            except Exception as e:
                logger.error(f"Error in SystemObserver loop: {e}", exc_info=False)
            time.sleep(self.interval)

    # --- Dynamic Evaluation Routines ---

    def _evaluate_power_transitions(self, snapshot: Dict[str, Any]) -> None:
        """Detects plugged/unplugged changes and power scheme drift."""
        bat = snapshot["battery"]
        current_plugged = bat["is_plugged"]
        current_plan = snapshot["power_profile"]
        active_mode = preferences.active_mode

        if self.previous_power_state is not None:
            # AC Plugged In Event
            if current_plugged and not self.previous_power_state:
                if active_mode in ("programmer", "performance") and "ultimate" not in current_plan.lower() and "high" not in current_plan.lower():
                    action_queue.propose(
                        Recommendation(
                            rec_id="opt_plugged_performance",
                            title="Boost Compiler & System Performance",
                            description="Laptop plugged into AC power. Switch to high-performance power plan for faster compile times.",
                            category="power",
                            impact="Increases CPU clock boost headroom for development builds.",
                            action_fn=lambda: set_power_profile("Ultimate Performance"),
                            command_preview="powercfg /setactive Ultimate Performance",
                        )
                    )

            # Unplugged / On Battery Event
            elif not current_plugged and self.previous_power_state:
                if "high" in current_plan.lower() or "ultimate" in current_plan.lower():
                    action_queue.propose(
                        Recommendation(
                            rec_id="opt_unplugged_battery_save",
                            title="Conserve Battery Power",
                            description="Laptop running on battery with high-performance power plan active.",
                            category="power",
                            impact="Prevents rapid battery drain while coding on the go.",
                            action_fn=lambda: set_power_profile("Balanced"),
                            command_preview="powercfg /setactive Balanced",
                        )
                    )

        # Low battery alert
        if bat["has_battery"] and not current_plugged:
            percent = bat["percent"]
            if percent <= preferences.get("low_battery_threshold", 20.0):
                action_queue.propose(
                    Recommendation(
                        rec_id="opt_low_battery",
                        title=f"Low Battery Warning ({percent}%)",
                        description="Battery level is low. Switch to power-saver and save ongoing work.",
                        category="power",
                        impact="Extends remaining battery life by throttling background tasks.",
                        action_fn=lambda: set_power_profile("Power Saver"),
                        command_preview="powercfg /setactive Power Saver",
                    )
                )

    def _evaluate_ram_usage(self, snapshot: Dict[str, Any]) -> None:
        """Detects high RAM usage and proposes clean memory freeing."""
        ram_percent = snapshot["ram"]["percent_used"]
        threshold = preferences.get("high_ram_threshold", 80.0)

        if ram_percent >= threshold:
            action_queue.propose(
                Recommendation(
                    rec_id="opt_high_ram",
                    title=f"High RAM Usage Detected ({ram_percent}%)",
                    description="Memory consumption is elevated. Purge temporary caches to liberate memory.",
                    category="ram",
                    impact="Cleans temporary files and trims working set memory.",
                    action_fn=lambda: debloat_manager.clean_temp_caches(),
                    command_preview="Clean %TEMP% and purge standby caches",
                )
            )

    def _evaluate_disk_and_downloads(self, snapshot: Dict[str, Any]) -> None:
        """Monitors downloads directory clutter and primary disk space."""
        # Only check downloads periodically (every 6th cycle)
        if self.observation_count % 6 == 0:
            unorganized = organizer.scan_unorganized(
                ignore_recent_minutes=preferences.get("downloads_ignore_recent_minutes", 15)
            )
            clutter_thresh = preferences.get("downloads_clutter_threshold", 15)
            if len(unorganized) >= clutter_thresh:
                action_queue.propose(
                    Recommendation(
                        rec_id="opt_downloads_clutter",
                        title=f"Downloads Folder Clutter ({len(unorganized)} loose files)",
                        description="Unorganized files detected in Downloads folder. Ready to categorize safely.",
                        category="downloads",
                        impact=f"Organizes {len(unorganized)} files into Code, Docs, Media, and Archives folders.",
                        action_fn=lambda: organizer.organize(dry_run=False),
                        command_preview="DownloadsOrganizer.organize()",
                    )
                )

        # Primary disk space warning
        if snapshot["primary_disk_percent"] >= 90.0:
            action_queue.propose(
                Recommendation(
                    rec_id="opt_disk_full",
                    title=f"Storage Drive Low ({snapshot['primary_disk_percent']}% used)",
                    description="Primary Windows drive is running low on free storage.",
                    category="disk",
                    impact="Frees temporary storage and caches.",
                    action_fn=lambda: debloat_manager.clean_temp_caches(),
                    command_preview="Clean temp directories",
                )
            )

    def _evaluate_mode_requirements(self, snapshot: Dict[str, Any]) -> None:
        """Evaluates developer tool requirements in Programmer Mode."""
        if preferences.active_mode == "programmer" and self.observation_count % 12 == 1:
            dev_status = modes_manager.check_developer_tools()
            if dev_status["missing_count"] > 0:
                missing_names = ", ".join([t["name"] for t in dev_status["missing"][:2]])
                action_queue.propose(
                    Recommendation(
                        rec_id="opt_missing_dev_tools",
                        title=f"Developer Tools Available ({dev_status['missing_count']} recommended)",
                        description=f"Programmer Mode detected missing tools: {missing_names}. Install via winget.",
                        category="tools",
                        impact="Sets up developer environment with official packages.",
                        action_fn=None,  # Handled via explicit user selection in CLI/UI
                        command_preview=modes_manager.generate_winget_install_command(),
                    )
                )


# Global singleton observer instance
observer = SystemObserver()


# =====================================================================
# Backward Compatibility Layer
# Preserves legacy function names from original system_observer.py
# without crashing on type errors or blocking background threads!
# =====================================================================

system = current_system()
previous_battery_config = system[4]
previous_power_state = system[6]
previous_power_plan = system[5]


def battery_change(prev_battery):
    """Legacy helper: checks battery percentage changes."""
    curr = current_system()[4]
    if curr != prev_battery:
        print(f"[REN Observer] Battery changed: {prev_battery} -> {curr}")


def plugged_state(prev_power_state):
    """Legacy helper: checks AC plugged changes."""
    curr = current_system()[6]
    if curr != prev_power_state:
        state_str = "Plugged in" if curr is True else ("Unplugged" if curr is False else str(curr))
        print(f"[REN Observer] Power status changed: {state_str}")


def power_plan_change(prev_power_plan):
    """Legacy helper: checks power plan changes."""
    curr = current_system()[5]
    if curr != prev_power_plan:
        print(f"[REN Observer] Power plan changed: {prev_power_plan} -> {curr}")


def battery_logic():
    """Legacy helper: safe evaluation of battery charge without TypeError."""
    bat_info = get_battery_info()
    if bat_info["has_battery"]:
        if bat_info["percent"] > 70:
            return "Excellent battery charge"
        elif bat_info["percent"] < 20:
            return "Low battery charge"
        return "Normal battery charge"
    return "Desktop AC power"


def ram_logic():
    """Legacy helper: RAM usage threshold."""
    ram = current_ram_usage()
    return "High RAM usage" if ram > 80 else "Low RAM usage"


def power_logic():
    """Legacy helper: evaluates power plan and plugs status safely."""
    curr = current_system()
    plan = curr[5]
    plugged = curr[6]
    if "ultimate" in plan.lower() or "high" in plan.lower():
        return "Performance-oriented power configuration"
    return "Balanced power configuration"


# =====================================================================
# Interactive Neon Cyber CLI Dashboard
# =====================================================================

def run_cyber_dashboard():
    """Displays an interactive neon cyber terminal dashboard for REN Desktop Assistant."""
    observer.start_background()

    while True:
        snapshot = get_system_snapshot()
        cpu = snapshot["cpu_percent"]
        ram = snapshot["ram"]
        disk = snapshot["primary_disk_percent"]
        bat = snapshot["battery"]
        power = snapshot["power_profile"]
        mode = preferences.active_mode.upper()
        context = snapshot["context"]["category"].upper()
        recs = action_queue.get_pending()

        bat_str = f"{bat['percent']}% [{'PLUGGED (AC)' if bat['is_plugged'] else 'DISCHARGING'}]" if bat["has_battery"] else "AC DESKTOP POWER"

        print("\n" + "=" * 65)
        print(f"🪐 REN-AI DESKTOP ASSISTANT | MODE: [{mode}] | CONTEXT: [{context}]")
        print("=" * 65)
        print(f" CPU Usage:    [{cpu:>5.1f}%]  |  RAM Usage: [{ram['percent_used']:>5.1f}%] ({ram['available_gb']} GB Free)")
        print(f" Primary Disk: [{disk:>5.1f}%]  |  Battery:   [{bat_str}]")
        print(f" Power Scheme: [{power}]")
        print("-" * 65)

        if recs:
            print(f"⚡ PENDING RECOMMENDATIONS ({len(recs)}):")
            for i, r in enumerate(recs, 1):
                print(f"  [{i}] {r.title}")
                print(f"      Impact: {r.impact}")
        else:
            print("⚡ System status optimal. Zero distractions active.")

        print("-" * 65)
        print("ACTIONS:")
        print("  [1] Review & Approve Recommendations")
        print("  [2] Switch Mode (Programmer / Balanced / Performance)")
        print("  [3] Organize Downloads Folder (Preview / Run / Undo)")
        print("  [4] Debloat Windows & Clean Temp Caches (Low RAM)")
        print("  [5] Check & Install Developer Tools (winget)")
        print("  [6] Clean Developer & Workspace Caches")
        print("  [7] Refresh Metrics")
        print("  [8] Exit Dashboard (Keep running in background)")
        print("=" * 65)

        try:
            choice = input("Enter choice [1-8]: ").strip()
        except (KeyboardInterrupt, EOFError):
            break

        if choice == "1":
            _handle_recommendations_menu()
        elif choice == "2":
            _handle_modes_menu()
        elif choice == "3":
            _handle_downloads_menu()
        elif choice == "4":
            _handle_debloat_menu()
        elif choice == "5":
            _handle_devtools_menu()
        elif choice == "6":
            res = modes_manager.clean_dev_caches()
            print(f"\n>> {res['message']}")
            time.sleep(2)
        elif choice == "7":
            continue
        elif choice == "8":
            print("\nExiting dashboard. REN continues running silently in the background.")
            break


def _handle_recommendations_menu():
    recs = action_queue.get_pending()
    if not recs:
        print("\nNo pending recommendations.")
        time.sleep(1.5)
        return

    print("\n--- PENDING RECOMMENDATIONS ---")
    for i, r in enumerate(recs, 1):
        print(f"[{i}] {r.title}")
        print(f"    Rationale: {r.description}")
        print(f"    Impact:    {r.impact}")
        if r.command_preview:
            print(f"    Command:   {r.command_preview}")

    idx = input("\nEnter number to approve, 'd<number>' to dismiss, or 'b' for back: ").strip().lower()
    if idx == "b":
        return
    if idx.startswith("d"):
        try:
            num = int(idx[1:]) - 1
            if 0 <= num < len(recs):
                action_queue.dismiss(recs[num].id)
                print(">> Recommendation dismissed.")
        except Exception:
            pass
    else:
        try:
            num = int(idx) - 1
            if 0 <= num < len(recs):
                res = action_queue.approve(recs[num].id)
                print(f">> Result: {res.get('message', 'Completed')}")
        except Exception:
            pass
    time.sleep(2)


def _handle_modes_menu():
    print("\n--- SWITCH MODE ---")
    print("[1] Programmer Mode  -- Developer tools compatibility, low RAM, compile boost & battery saver")
    print("[2] Balanced Mode    -- Unobtrusive daily assistant, quiet monitoring, standard balance")
    print("[3] Performance Mode -- Maximum CPU performance, high power plan, frees RAM")
    m_choice = input("Select mode [1-3] or 'b' for back: ").strip()
    mapping = {"1": "programmer", "2": "balanced", "3": "performance"}
    if m_choice in mapping:
        res = modes_manager.set_mode(mapping[m_choice])
        print(f">> {res['message']}")
        for act in res.get("actions_taken", []):
            print(f"   * {act}")
        time.sleep(2)


def _handle_downloads_menu():
    print("\n--- DOWNLOADS ORGANIZER ---")
    print("[1] Preview planned organization (Dry Run)")
    print("[2] Execute organization now")
    print("[3] Undo last organization batch (Rollback)")
    d_choice = input("Select option [1-3] or 'b' for back: ").strip()
    if d_choice == "1":
        prev = organizer.preview_organization()
        print(f"\nUnorganized loose files found: {prev['total_files']} ({prev['total_size_mb']} MB)")
        for cat, items in prev["categories"].items():
            print(f"  [{cat}]: {len(items)} files")
        input("\nPress Enter to continue...")
    elif d_choice == "2":
        res = organizer.organize(dry_run=False)
        print(f"\n>> Organized {res.get('moved_count', 0)} files into categorized folders.")
        time.sleep(2)
    elif d_choice == "3":
        res = organizer.undo_last()
        print(f"\n>> Undo result: {res}")
        time.sleep(2)


def _handle_debloat_menu():
    print("\n--- WINDOWS DEBLOATER & LOW RAM TUNING ---")
    tweaks = debloat_manager.get_tweak_definitions()
    tweak_keys = list(tweaks.keys())
    for i, k in enumerate(tweak_keys, 1):
        tw = tweaks[k]
        status = "[APPLIED]" if tw["is_applied"] else "[READY]"
        print(f"[{i}] {status} {tw['title']}")
        print(f"    {tw['impact']}")
    print("[A] Apply all safe Programmer Mode debloat tweaks")
    choice = input("\nSelect tweak number to toggle, 'A' for all, or 'b' for back: ").strip()
    if choice.upper() == "A":
        res = debloat_manager.apply_programmer_mode_debloat()
        print(f"\n>> {res['summary']}")
        time.sleep(2)
    elif choice.isdigit():
        num = int(choice) - 1
        if 0 <= num < len(tweak_keys):
            key = tweak_keys[num]
            if tweaks[key]["is_applied"]:
                fn = getattr(debloat_manager, f"rollback_{key}", None)
            else:
                fn = getattr(debloat_manager, key, None)
            if fn:
                r = fn()
                print(f"\n>> {r.get('message')}")
            time.sleep(2)


def _handle_devtools_menu():
    print("\n--- DEVELOPER TOOLS (WINGET) ---")
    tools = modes_manager.check_developer_tools()
    print(f"Status: {tools['installed_count']}/{tools['total_tools']} tools installed.")
    print("\nInstalled:")
    for t in tools["installed"]:
        print(f"  ✓ {t['name']}")
    if tools["missing"]:
        print("\nMissing (Ready to install):")
        for i, t in enumerate(tools["missing"], 1):
            print(f"  [{i}] {t['name']} (ID: {t['winget_id']})")
        print("  [A] Generate command to install all missing tools")
        choice = input("\nEnter number to install tool, 'A' for full command, or 'b': ").strip()
        if choice.upper() == "A":
            cmd = modes_manager.generate_winget_install_command()
            print(f"\nWinget Command:\n{cmd}\n")
            input("Press Enter to continue...")
        elif choice.isdigit():
            idx = int(choice) - 1
            if 0 <= idx < len(tools["missing"]):
                selected = tools["missing"][idx]
                print(f"Installing {selected['name']} via winget...")
                r = modes_manager.install_tool(selected["key"])
                print(f">> {r.get('message')}")
                time.sleep(2)
    else:
        print("\nAll recommended developer tools are installed!")
        input("\nPress Enter to continue...")


if __name__ == "__main__":
    run_cyber_dashboard()