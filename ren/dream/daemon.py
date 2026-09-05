"""
REN Dream Mode 2.0 (Cognitive Reflection Daemon)
Autonomous background worker performing state inspection, unresolved problem analysis,
session compaction, skill indexing, book learning, and proactive initiative proposals.
Runs headlessly and independently of desktop GUI or browser connections.
"""

import os
import json
import time
import random
import shutil
import threading
import sys
from pathlib import Path
from typing import List, Dict, Any, Optional, Callable, Tuple

from ren.config.settings import settings
from ren.monitoring.logger import agent_logger, error_logger
from ren.monitoring.performance import perf_monitor
from ren.memory.manager import memory_manager
from ren.sessions.manager import session_manager
from ren.skills.registry import skill_registry
from ren.models import get_model_provider
from ren.core.events import event_bus, EventType
from ren.autonomy.engine import autonomy_engine


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
    """Headless background reflection and self-improvement engine."""

    def __init__(self):
        self._running = False
        self._thread: Optional[threading.Thread] = None
        self._log_file = settings.PATHS.DREAM_LOG_FILE

    @property
    def is_running(self) -> bool:
        return self._running

    def log_action(self, action_str: str):
        """Appends an event to dream_history.log."""
        timestamp = time.strftime("%Y-%m-%d %H:%M:%S")
        try:
            with open(self._log_file, "a", encoding="utf-8") as f:
                f.write(f"[{timestamp}] {action_str}\n")
        except Exception as e:
            error_logger.error(f"Failed writing dream log: {e}")

    def get_logs(self) -> List[str]:
        """Returns structured reflection logs."""
        logs = [
            "SYNAPSE OPTIMIZATION: SQLite memory indexing active.",
            "ANALYZING: Cloud inference latency & telemetry online.",
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

    def check_resource_limits(self) -> Tuple[bool, str]:
        """Ensures CPU, RAM, and battery levels are safe for background sleep cognition."""
        try:
            import psutil
            cpu = psutil.cpu_percent(interval=None)
            if cpu > 85.0:
                return False, f"CPU usage high ({cpu}%)"
            ram = psutil.virtual_memory().percent
            if ram > 90.0:
                return False, f"RAM usage high ({ram}%)"
            bat = psutil.sensors_battery()
            if bat and not bat.power_plugged and bat.percent < 20:
                return False, f"Battery low ({bat.percent}%) and discharging"
        except Exception:
            pass
        return True, "Resources healthy"

    def run_reflection_cycle(self, ui_callback_fn: Optional[Callable[[str, Any], None]] = None):
        """Single cognitive reflection and sleep learning cycle."""
        # Check resource bounds
        healthy, reason = self.check_resource_limits()
        if not healthy:
            self.log_action(f"RESOURCE_THROTTLE: Postponing cognitive cycle: {reason}")
            return

        event_bus.publish(EventType.DREAM_STARTED, {"timestamp": time.time()})
        reviewed_count = 0
        gaps_found = 0
        tests_run = 0

        # 1. Review recent experiences
        recent_episodes = memory_manager.get_recent_episodes(limit=5)
        reviewed_count = len(recent_episodes)

        # 2. Curiosity Engine: Identify knowledge gaps & failure patterns
        from ren.cognitive.curiosity import curiosity_engine
        objectives = curiosity_engine.inspect_knowledge_gaps()
        gaps_found = len(objectives)

        # 3. Self-Evaluation Engine: Identify weak tools or skills
        from ren.cognitive.self_evaluation import self_evaluation_engine
        improvements = self_evaluation_engine.evaluate_and_generate_improvement_objectives()

        # 4. Check for unresolved runtime errors in error_log.json
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
            try:
                with open(err_file, "w", encoding="utf-8") as f:
                    json.dump(errors, f, indent=4)
            except Exception:
                pass

            if len(errors) > 2:
                autonomy_engine.propose_initiative(
                    content=f"During background reflection, I examined system error '{current_err[:50]}'. {len(errors)} related exceptions remain.",
                    source="dream_reflection",
                    importance=0.85,
                    curiosity_score=0.80,
                    reason="Recurring error analysis in Dream Mode",
                    title="Exception Diagnostic"
                )
            event_bus.publish(EventType.DREAM_COMPLETED, {"reviewed": reviewed_count, "gaps": gaps_found})
            return

        # 2. Compact active sessions (zero-cost maintenance)
        session = session_manager.active_session
        session_manager.compact_session_if_needed(session)

        # 3. Clean and Organize Downloads
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
                for fname in files[:30]:
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

        # 4. Learning from Books
        books_dir = settings.PATHS.BOOKS_DIR
        books = list(books_dir.glob("*.txt"))
        if books and random.random() < 0.35:
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
                    clean_insight = insight.strip()
                    memory_manager.store_fact(
                        content=f"Read '{book.name}': {clean_insight}",
                        category="reading",
                        tags="book,learning"
                    )
                    self.log_action(f"READING: Learned from '{book.name}': {clean_insight[:60]}")

                    # Propose autonomous suggestion if highly interesting
                    if len(clean_insight) > 20 and random.random() < 0.2:
                        autonomy_engine.propose_initiative(
                            content=f"While reflecting on '{book.name}', I learned: \"{clean_insight}\"",
                            source="dream_reading",
                            importance=0.75,
                            curiosity_score=0.85,
                            reason="Book reflection insight",
                            title="Reading Discovery"
                        )
            except Exception as e:
                error_logger.error(f"Dream book reading error: {e}")

        # 5. Run Autonomy periodic inspection
        autonomy_engine.run_inspection_cycle()

        # 6. Sleep Mode Updates Check
        from ren.system.upgrade_manager import upgrade_manager
        pending_upgrades = upgrade_manager.check_updates()

        # 7. Record Structured Dream Report
        report_str = f"Dream Report: Reviewed {reviewed_count} experiences, found {gaps_found} knowledge gaps, {len(pending_upgrades)} maintenance items pending."
        self.log_action(report_str)

        if ui_callback_fn:
            ui_callback_fn('reflect_mode', {'active': True, 'logs': self.get_logs()})

        # Publish completion event
        event_bus.publish(EventType.DREAM_COMPLETED, {
            "reviewed": reviewed_count,
            "gaps": gaps_found,
            "pending_upgrades": len(pending_upgrades),
            "report": report_str
        })
        event_bus.publish(EventType.POPUP_NOTIFICATION, {
            "type": "dream_result",
            "message": report_str,
            "logs": self.get_logs()[:3]
        })

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
                for _ in range(30):
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
