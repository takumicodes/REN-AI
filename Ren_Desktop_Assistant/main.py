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

# Add current directory to path
CURRENT_DIR = Path(__file__).resolve().parent
if str(CURRENT_DIR) not in sys.path:
    sys.path.insert(0, str(CURRENT_DIR))

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
        print(f"REN Desktop Assistant v{preferences.get('version', '2.0')}")
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
        from app_gui import launch_gui
        launch_gui()


if __name__ == "__main__":
    main()
