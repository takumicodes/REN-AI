"""
REN Desktop Assistant - Main Application Entry Point
Supports:
- Default: Launches Modern Cyber GUI Application.
- CLI Mode (--cli): Launches Interactive Terminal Cyber Dashboard.
- Daemon Mode (--bg): Runs Headless Background Observer Service.
"""

import sys
import argparse
from pathlib import Path

# Safe stdout/stderr initialization for Windows windowed mode
class DummyStream:
    def write(self, *a, **k): pass
    def flush(self, *a, **k): pass

if sys.platform == "win32":
    try:
        import ctypes
        # Attach to parent process console if available (e.g. CLI run from cmd/powershell)
        if ctypes.windll.kernel32.AttachConsole(-1):
            import io
            try:
                sys.stdout = io.TextIOWrapper(open("CONOUT$", "wb"), encoding="utf-8", errors="replace")
                sys.stderr = io.TextIOWrapper(open("CONOUT$", "wb"), encoding="utf-8", errors="replace")
            except Exception:
                pass
    except Exception:
        pass

if sys.stdout is None:
    sys.stdout = DummyStream()
if sys.stderr is None:
    sys.stderr = DummyStream()

# Add current directory to path
CURRENT_DIR = Path(__file__).resolve().parent
if str(CURRENT_DIR) not in sys.path:
    sys.path.insert(0, str(CURRENT_DIR))

# Core module imports for PyInstaller bundling
import preferences
import system_status
import system_info
import system_observer
import downloads_organizer
import debloat
import modes
import actions
import history
import action_registry
import process_manager
import startup_manager
import services_manager
import storage_cleaner
import storage_analyzer
import app_manager
import tweaks_manager
import privacy_center
import network_center
import health_diagnostics
import restore_center
import logger
import single_instance
import tray_manager
import app_gui

from single_instance import SingleInstanceManager
from logger import logger

# Enable Windows High-DPI Awareness for razor-sharp rendering
if sys.platform == "win32":
    try:
        import ctypes
        ctypes.windll.shcore.SetProcessDpiAwareness(1)
    except Exception:
        try:
            ctypes.windll.user32.SetProcessDPIAware()
        except Exception:
            pass


def main():
    parser = argparse.ArgumentParser(description="REN Desktop Assistant - Autonomous Cognitive System")
    parser.add_argument("--cli", action="store_true", help="Launch interactive terminal cyber dashboard")
    parser.add_argument("--bg", "--daemon", action="store_true", help="Run headless background observer daemon")
    parser.add_argument("--version", action="store_true", help="Display assistant version")
    args = parser.parse_args()

    if args.version:
        from preferences import preferences
        print(f"REN Desktop Assistant v{preferences.get('version', '1.3.0')}")
        return

    if args.cli:
        from system_observer import run_cyber_dashboard
        run_cyber_dashboard()
    elif args.bg:
        import time
        from system_observer import observer
        print("🪐 REN Desktop Assistant running in silent headless background daemon mode.")
        print("Press Ctrl+C to stop.")
        observer.start_background()
        try:
            while True:
                time.sleep(1)
        except KeyboardInterrupt:
            observer.stop()
            print("REN Assistant stopped.")
    else:
        single_inst = SingleInstanceManager()
        if not single_inst.acquire():
            print("🪐 REN-AI Control Center is already running. Existing window activated.")
            sys.exit(0)
        from app_gui import launch_gui
        launch_gui(single_instance=single_inst)


if __name__ == "__main__":
    main()
