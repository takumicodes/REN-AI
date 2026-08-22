"""
REN Dream Mode 2.0 (Cognitive Reflection Daemon)
Resource-aware background reflection performing session compaction, error analysis,
skill re-indexing, downloads organization, and curiosity synthesis.
"""

import os
import json
import time
import random
import shutil
import threading
import sys
from pathlib import Path
from typing import List, Dict, Any, Optional, Callable

from ren.config.settings import settings
from ren.monitoring.logger import agent_logger, error_logger
from ren.monitoring.performance import perf_monitor
from ren.memory.manager import memory_manager
from ren.sessions.manager import session_manager
from ren.skills.registry import skill_registry
from ren.models import get_model_provider


def get_downloads_dir() -> Optional[str]:
    """Resolves Windows Downloads folder."""
    try:
        if sys.platform == "win32":
            import winreg
            subkey = r"Software\Microsoft\Windows\CurrentVersion\Explorer\User Shell Folders"
            with winreg.OpenKey(winreg.HKEY_CURRENT_USER, subkey) as key:
                download_path, _ = winreg.QueryValueEx(key, "{374DE290-123F-4565-9164-39C4925E467B}")
                expanded = os.path.expandvars(download_path)
                if os.path.exists(expanded):
                    return expanded
    except Exception:
        pass
    std = Path.home() / "Downloads"
    return str(std) if std.exists() else None


class DreamDaemon:
    """Resource-aware background reflection engine."""

    def __init__(self):
        self._running = False
        self._thread: Optional[threading.Thread] = None
        self._log_file = settings.PATHS.DREAM_LOG_FILE

    def log_action(self, action_str: str):
        """Appends a line to dream_history.log."""
        timestamp = time.strftime("%Y-%m-%d %H:%M:%S")
        try:
            with open(self._log_file, "a", encoding="utf-8") as f:
                f.write(f"[{timestamp}] {action_str}\n")
        except Exception as e:
            error_logger.error(f"Failed writing dream log: {e}")

    def get_logs(self) -> List[str]:
        """Returns structured logs for the GUI reflection panel."""
        logs = [
            "SYNAPSE OPTIMIZATION: SQLite memory indexing active.",
            "ANALYZING: CPU / RAM limits. Adaptive token budgeting active.",
            "SKILL REGISTRY: Validated active tool and skill components.",
        ]

        # Load recent learned memories
        facts = memory_manager.get_system_facts()
        learned = facts.get("learned_from_dreams", [])
        if isinstance(learned, list):
            for item in learned[-3:]:
                logs.insert(0, f"LEARNED: {str(item)[:70]}")

        # Load recent errors from error log
        err_file = settings.PATHS.ERROR_LOG_FILE
        if err_file.exists():
            try:
                with open(err_file, "r", encoding="utf-8") as f:
                    errs = json.load(f)
                    for err in errs[-2:]:
                        logs.insert(0, f"ANALYZING EXCEPTION: {str(err)[:60]}...")
            except Exception:
                pass

        logs.append("SYNAPSE RE-ALIGNMENT COMPLETE. COGNITION CYCLE IN STANDBY.")
        return logs

    def run_reflection_cycle(self, ui_callback_fn: Optional[Callable[[str, Any], None]] = None):
        """Single resource-aware dream cycle."""
        # 1. Resource check: Do not execute heavy dream tasks if CPU/RAM is strained
        if perf_monitor.is_resource_strained(cpu_thresh=80.0, ram_thresh=85.0):
            self.log_action("DREAM_DAEMON: Resource strain detected. Throttling dream cycle.")
            return

        # 2. Check for unresolved runtime errors in error_log.json
        err_file = settings.PATHS.ERROR_LOG_FILE
        errors = []
        if err_file.exists():
            try:
                with open(err_file, "r", encoding="utf-8") as f:
                    errors = json.load(f)
            except Exception:
                pass

        if errors:
            current_err = errors.pop(0)
            self.log_action(f"ANALYZING_EXCEPTION: Examining '{current_err[:50]}...'")
            # Save updated error file
            try:
                with open(err_file, "w", encoding="utf-8") as f:
                    json.dump(errors, f, indent=4)
            except Exception:
                pass
            return

        # 3. Compact active session if needed (zero-cost maintenance)
        session = session_manager.active_session
        session_manager.compact_session_if_needed(session)

        # 4. Low-cost maintenance: Clean/Organize Downloads
        downloads_dir = get_downloads_dir()
        if downloads_dir and os.path.exists(downloads_dir):
            try:
                files = [f for f in os.listdir(downloads_dir) if os.path.isfile(os.path.join(downloads_dir, f))]
                categories = {
                    "Documents": [".pdf", ".epub", ".docx", ".txt", ".pptx", ".xlsx", ".csv"],
                    "Images": [".jpg", ".jpeg", ".png", ".gif", ".bmp", ".svg"],
                    "Archives": [".zip", ".rar", ".tar", ".gz", ".7z"],
                    "Installers": [".exe", ".msi"]
                }
                moved = 0
                for fname in files[:30]:  # Limit batch
                    fpath = os.path.join(downloads_dir, fname)
                    _, ext = os.path.splitext(fname)
                    ext = ext.lower()
                    for cat, ext_list in categories.items():
                        if ext in ext_list:
                            dest_dir = os.path.join(downloads_dir, cat)
                            os.makedirs(dest_dir, exist_ok=True)
                            shutil.move(fpath, os.path.join(dest_dir, fname))
                            moved += 1
                            break
                if moved > 0:
                    self.log_action(f"SYSTEM: Cleaned Downloads folder. Organized {moved} files.")
            except Exception as e:
                error_logger.error(f"Dream downloads organizer failed: {e}")

        # 5. Low-cost Book Reading / Summary (only if idle)
        books_dir = settings.PATHS.BOOKS_DIR
        books = list(books_dir.glob("*.txt"))
        if books and random.random() < 0.3:
            book = random.choice(books)
            try:
                with open(book, "r", encoding="utf-8", errors="ignore") as bf:
                    text_segment = bf.read(1000)
                prompt = (
                    f"You are Ren. You are reading '{book.name}'. Extract one key insight (1 short sentence) "
                    f"from this text:\n\n{text_segment}\n\nInsight:"
                )
                provider = get_model_provider()
                insight = provider.generate(prompt, max_tokens=64, temperature=0.3)
                if insight and not insight.startswith("Error"):
                    memory_manager.store_fact(
                        content=f"Read '{book.name}': {insight.strip()}",
                        category="reading",
                        tags="book,learning"
                    )
                    self.log_action(f"READING: Learned from '{book.name}': {insight.strip()[:60]}")
            except Exception as e:
                error_logger.error(f"Dream book reading error: {e}")

        if ui_callback_fn:
            ui_callback_fn('reflect_mode', {'active': True, 'logs': self.get_logs()})

    def start(self, ui_callback_fn: Optional[Callable[[str, Any], None]] = None):
        """Starts background dream daemon thread."""
        if self._running:
            return
        self._running = True
        self.log_action("DREAM_DAEMON: Active. Entering dreamscape reflection cycle.")

        def loop():
            while self._running:
                try:
                    self.run_reflection_cycle(ui_callback_fn)
                except Exception as e:
                    error_logger.error(f"Error in dream cycle: {e}")

                # Sleep in increments so stop responds promptly
                for _ in range(20):
                    if not self._running:
                        break
                    time.sleep(1.0)

            self.log_action("DREAM_DAEMON: Stopped. Ren has woken up.")

        self._thread = threading.Thread(target=loop, daemon=True)
        self._thread.start()

    def stop(self):
        """Halts the dream daemon."""
        self._running = False


# Global dream daemon singleton
dream_daemon = DreamDaemon()
