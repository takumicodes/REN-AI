"""
User Preferences & Dynamic Learning Manager for REN Desktop Assistant
Persists user configuration and dynamically learns user habits over time.
Ensures the assistant remains 100% human-driven with zero AI slop.
"""

import os
import json
import time
from pathlib import Path
from typing import Dict, Any, List, Optional

PREFERENCES_FILE = Path(__file__).parent / "user_preferences.json"

DEFAULT_PREFERENCES: Dict[str, Any] = {
    "version": "2.0",
    "onboarding_completed": False,        # Shows first-install preferences wizard if False
    "profession": "Software Engineer",    # User's profession (Software Engineer, Designer, Student, Gamer, Other)
    "active_mode": "programmer",          # Options: 'programmer', 'balanced', 'performance'
    "human_driven_mode": True,            # Explicit confirmation for all system-altering actions
    "close_to_background": True,          # Close button hides to background system tray instead of exiting
    
    # Downloads Organizer Settings
    "downloads_folder": str(Path.home() / "Downloads"),
    "auto_organize_downloads": False,     # Human-driven default: prompt/preview before organizing
    "downloads_clutter_threshold": 15,    # Suggest organization if unorganized files exceed this
    "downloads_ignore_recent_minutes": 15,# Protect freshly downloaded files
    
    # Power & Hardware Optimization
    "auto_power_switch": False,           # Human-driven default: suggest instead of auto-switching
    "preferred_ac_power_plan": "Ultimate Performance",
    "preferred_battery_power_plan": "Balanced",
    "high_ram_threshold": 80.0,
    "high_cpu_threshold": 85.0,
    "low_battery_threshold": 20.0,
    
    # Quiet Hours & Notifications
    "quiet_hours_enabled": False,
    "quiet_hours_start": 23,              # 11 PM
    "quiet_hours_end": 7,                 # 7 AM
    "notification_cooldown_seconds": 300, # 5 minutes cooldown between similar suggestions
    
    # Applied Debloat Tweaks tracking
    "applied_debloat_tweaks": [],
    
    # Dynamic Learned Preferences
    "learned_patterns": {
        "preferred_dev_tools": ["git", "vscode", "python", "terminal"],
        "power_switch_approvals": 0,
        "power_switch_rejections": 0,
        "downloads_clean_approvals": 0,
        "last_observed_timestamp": 0,
    },
}


class UserPreferences:
    """Manages reading, writing, and dynamic learning of user preferences."""

    def __init__(self, filepath: Optional[Path] = None):
        self.filepath = filepath or PREFERENCES_FILE
        self._data: Dict[str, Any] = {}
        self.load()

    def load(self) -> Dict[str, Any]:
        """Loads preferences from disk, filling in default values for missing keys."""
        if self.filepath.exists():
            try:
                with open(self.filepath, "r", encoding="utf-8") as f:
                    loaded = json.load(f)
                    self._data = {**DEFAULT_PREFERENCES, **loaded}
                    # Merge nested dicts
                    self._data["learned_patterns"] = {
                        **DEFAULT_PREFERENCES["learned_patterns"],
                        **loaded.get("learned_patterns", {}),
                    }
                    return self._data
            except Exception:
                pass

        self._data = dict(DEFAULT_PREFERENCES)
        self.save()
        return self._data

    def save(self) -> bool:
        """Persists current preferences to JSON."""
        try:
            os.makedirs(str(self.filepath.parent), exist_ok=True)
            with open(self.filepath, "w", encoding="utf-8") as f:
                json.dump(self._data, f, indent=4)
            return True
        except Exception:
            return False

    def get(self, key: str, default: Any = None) -> Any:
        """Gets preference value."""
        return self._data.get(key, default)

    def set(self, key: str, value: Any) -> None:
        """Sets preference value and saves immediately."""
        self._data[key] = value
        self.save()

    def update(self, **kwargs) -> None:
        """Updates multiple preferences."""
        self._data.update(kwargs)
        self.save()

    @property
    def active_mode(self) -> str:
        return self._data.get("active_mode", "programmer")

    @active_mode.setter
    def active_mode(self, mode: str) -> None:
        if mode in ("programmer", "balanced", "performance"):
            self._data["active_mode"] = mode
            self.save()

    @property
    def human_driven(self) -> bool:
        return self._data.get("human_driven_mode", True)

    def is_quiet_hours(self) -> bool:
        """Checks if current system time falls within quiet hours."""
        if not self.get("quiet_hours_enabled", False):
            return False
        current_hour = time.localtime().tm_hour
        start = self.get("quiet_hours_start", 23)
        end = self.get("quiet_hours_end", 7)
        if start > end:
            return current_hour >= start or current_hour < end
        return start <= current_hour < end

    def record_decision(self, action_type: str, approved: bool) -> None:
        """
        Dynamically learns from user decisions:
        If the user repeatedly approves an action (e.g. power plan switch),
        Ren notes this habit. If the user rejects, Ren respects boundaries.
        """
        patterns = self._data.setdefault("learned_patterns", {})
        if action_type == "power_switch":
            key = "power_switch_approvals" if approved else "power_switch_rejections"
            patterns[key] = patterns.get(key, 0) + 1
        elif action_type == "downloads_clean":
            key = "downloads_clean_approvals" if approved else "downloads_clean_rejections"
            patterns[key] = patterns.get(key, 0) + 1

        patterns["last_observed_timestamp"] = time.time()
        self.save()


preferences = UserPreferences()
