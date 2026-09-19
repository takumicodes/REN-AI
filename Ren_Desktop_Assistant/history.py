"""
Audit & Change History System for REN Desktop Assistant
Persists all system actions, optimizations, and configuration changes with:
- Timestamp & action identifiers
- Pre-change state snapshot and post-change state snapshot
- Execution status and verification results
- 1-click rollback tracking
"""

import os
import json
import time
from datetime import datetime
from pathlib import Path
from typing import Dict, List, Any, Optional


import sys

def get_history_file_path() -> Path:
    """Returns the persistent path for REN change history."""
    if getattr(sys, "frozen", False):
        exe_dir = Path(sys.executable).parent
        portable_flag = exe_dir / "change_history.json"
        if portable_flag.exists():
            return portable_flag
        appdata = os.environ.get("LOCALAPPDATA")
        base = Path(appdata) / "RenDesktopAssistant" if appdata else Path.home() / ".ren_desktop_assistant"
    else:
        base = Path(__file__).parent

    try:
        os.makedirs(str(base), exist_ok=True)
    except Exception:
        pass
    return base / "change_history.json"


class ChangeHistory:
    """Manages persistent change tracking, verification logs, and rollback state."""

    def __init__(self, file_path: Optional[Path] = None):
        self.file_path = file_path or get_history_file_path()
        self._entries: List[Dict[str, Any]] = []
        self._load()

    def _load(self):
        """Loads history entries from JSON file."""
        if self.file_path.exists():
            try:
                with open(self.file_path, "r", encoding="utf-8") as f:
                    data = json.load(f)
                    if isinstance(data, list):
                        self._entries = data
            except Exception:
                self._entries = []
        else:
            self._entries = []

    def _save(self):
        """Saves history entries to disk atomically."""
        try:
            temp_file = self.file_path.with_suffix(".tmp")
            with open(temp_file, "w", encoding="utf-8") as f:
                json.dump(self._entries, f, indent=2)
            temp_file.replace(self.file_path)
        except Exception:
            pass

    def record_action(
        self,
        action_id: str,
        title: str,
        category: str,
        status: str = "executed",
        verified: bool = True,
        verification_message: str = "",
        reversible: bool = True,
        before_state: Any = None,
        after_state: Any = None,
        details: Optional[Dict[str, Any]] = None,
    ) -> Dict[str, Any]:
        """
        Records an executed action into the audit trail.
        """
        now = time.time()
        dt_str = datetime.fromtimestamp(now).strftime("%Y-%m-%d %H:%M:%S")
        entry_id = f"hist_{int(now * 1000)}"

        entry = {
            "entry_id": entry_id,
            "timestamp": now,
            "datetime": dt_str,
            "action_id": action_id,
            "title": title,
            "category": category,
            "status": status,
            "verified": verified,
            "verification_message": verification_message,
            "reversible": reversible,
            "before_state": before_state,
            "after_state": after_state,
            "details": details or {},
            "rolled_back": False,
            "rolled_back_at": None,
        }

        self._entries.insert(0, entry)
        # Cap history at 500 entries
        if len(self._entries) > 500:
            self._entries = self._entries[:500]
        self._save()
        return entry

    def mark_rolled_back(self, entry_id: str, message: str = "") -> bool:
        """Marks an entry as successfully rolled back."""
        for entry in self._entries:
            if entry.get("entry_id") == entry_id:
                entry["rolled_back"] = True
                entry["status"] = "rolled_back"
                entry["rolled_back_at"] = datetime.now().strftime("%Y-%m-%d %H:%M:%S")
                if message:
                    entry["details"]["rollback_message"] = message
                self._save()
                return True
        return False

    def get_history(self, limit: int = 100, category: Optional[str] = None) -> List[Dict[str, Any]]:
        """Returns recent change history entries."""
        if category:
            filtered = [e for e in self._entries if e.get("category") == category]
            return filtered[:limit]
        return self._entries[:limit]

    def get_entry(self, entry_id: str) -> Optional[Dict[str, Any]]:
        """Finds entry by entry_id."""
        for entry in self._entries:
            if entry.get("entry_id") == entry_id:
                return entry
        return None

    def clear_history(self):
        """Clears all history entries."""
        self._entries = []
        self._save()


change_history = ChangeHistory()
