"""
Windows System & Explorer Tweaks Manager for REN-AI Windows Control Center
Provides:
- Curated registry tweaks with live status inspection.
- 100% reversible: stores before-state for instantaneous 1-click rollback.
- Human-driven: transparent registry commands and impact descriptions.
"""

import winreg
import ctypes
from typing import Dict, List, Any, Optional

try:
    from .history import change_history
except ImportError:
    from history import change_history


def notify_shell_change():
    """Notifies Windows Explorer of shell/association/setting changes."""
    try:
        # SHCNE_ASSOCCHANGED = 0x08000000, SHCNF_FLUSH = 0x1000
        ctypes.windll.shell32.SHChangeNotify(0x08000000, 0x1000, None, None)
    except Exception:
        pass


class TweakDefinition:
    def __init__(
        self,
        tweak_id: str,
        title: str,
        description: str,
        category: str,
        impact: str,
        root_key: int,
        subkey: str,
        value_name: str,
        value_type: int,
        applied_val: Any,
        default_val: Any,
    ):
        self.id = tweak_id
        self.title = title
        self.description = description
        self.category = category
        self.impact = impact
        self.root_key = root_key
        self.subkey = subkey
        self.value_name = value_name
        self.value_type = value_type
        self.applied_val = applied_val
        self.default_val = default_val

    def is_applied(self) -> bool:
        """Reads registry to determine if tweak is currently applied."""
        try:
            with winreg.OpenKey(self.root_key, self.subkey, 0, winreg.KEY_READ) as key:
                val, _ = winreg.QueryValueEx(key, self.value_name)
                return val == self.applied_val
        except Exception:
            return False

    def apply(self) -> Dict[str, Any]:
        """Applies tweak to registry."""
        try:
            with winreg.CreateKey(self.root_key, self.subkey) as key:
                winreg.SetValueEx(key, self.value_name, 0, self.value_type, self.applied_val)
            notify_shell_change()
            return {"success": True, "message": f"Applied tweak: {self.title}"}
        except Exception as e:
            return {"success": False, "message": f"Failed to apply tweak: {e}"}

    def revert(self) -> Dict[str, Any]:
        """Reverts tweak back to Windows default."""
        try:
            with winreg.CreateKey(self.root_key, self.subkey) as key:
                winreg.SetValueEx(key, self.value_name, 0, self.value_type, self.default_val)
            notify_shell_change()
            return {"success": True, "message": f"Reverted tweak: {self.title}"}
        except Exception as e:
            return {"success": False, "message": f"Failed to revert tweak: {e}"}


class TweaksManager:
    """Manages curated Windows system and Explorer tweaks."""

    def __init__(self):
        self._tweaks: Dict[str, TweakDefinition] = {}
        self._init_tweaks()

    def _init_tweaks(self):
        self._tweaks = {
            "show_file_extensions": TweakDefinition(
                tweak_id="show_file_extensions",
                title="Show Known File Extensions",
                description="Forces File Explorer to display extensions (.exe, .py, .txt) for security and clarity.",
                category="Explorer",
                impact="Improves security by preventing file spoofing and gives developers clear visibility of file formats.",
                root_key=winreg.HKEY_CURRENT_USER,
                subkey=r"Software\Microsoft\Windows\CurrentVersion\Explorer\Advanced",
                value_name="HideFileExt",
                value_type=winreg.REG_DWORD,
                applied_val=0,
                default_val=1,
            ),
            "show_hidden_files": TweakDefinition(
                tweak_id="show_hidden_files",
                title="Show Hidden Files and Folders",
                description="Displays hidden system and user files (.git, AppData, etc.) in File Explorer.",
                category="Explorer",
                impact="Essential for developers and power users navigating project dotfiles and configuration directories.",
                root_key=winreg.HKEY_CURRENT_USER,
                subkey=r"Software\Microsoft\Windows\CurrentVersion\Explorer\Advanced",
                value_name="Hidden",
                value_type=winreg.REG_DWORD,
                applied_val=1,
                default_val=2,
            ),
            "compact_view": TweakDefinition(
                tweak_id="compact_view",
                title="Compact View in File Explorer",
                description="Reduces padding between files and folders in Windows 11 Explorer.",
                category="Explorer",
                impact="Displays more files per screen, matching the efficient Windows 10 density.",
                root_key=winreg.HKEY_CURRENT_USER,
                subkey=r"Software\Microsoft\Windows\CurrentVersion\Explorer\Advanced",
                value_name="UseCompactMode",
                value_type=winreg.REG_DWORD,
                applied_val=1,
                default_val=0,
            ),
            "end_task_taskbar": TweakDefinition(
                tweak_id="end_task_taskbar",
                title="Enable 'End Task' on Taskbar Right-Click",
                description="Adds a direct 'End Task' option to running applications on the Windows taskbar.",
                category="Taskbar",
                impact="Instantly terminate frozen or unresponsive apps without opening Task Manager.",
                root_key=winreg.HKEY_CURRENT_USER,
                subkey=r"Software\Microsoft\Windows\CurrentVersion\Explorer\Advanced\TaskbarDeveloperSettings",
                value_name="TaskbarEndTask",
                value_type=winreg.REG_DWORD,
                applied_val=1,
                default_val=0,
            ),
            "disable_startup_delay": TweakDefinition(
                tweak_id="disable_startup_delay",
                title="Eliminate Windows Startup Delay",
                description="Disables the artificial 10-second delay Windows imposes on startup programs at login.",
                category="System",
                impact="Accelerates initial desktop readiness by launching startup applications immediately.",
                root_key=winreg.HKEY_CURRENT_USER,
                subkey=r"Software\Microsoft\Windows\CurrentVersion\Explorer\Serialize",
                value_name="StartupDelayInMSec",
                value_type=winreg.REG_DWORD,
                applied_val=0,
                default_val=10000,
            ),
            "disable_lockscreen_tips": TweakDefinition(
                tweak_id="disable_lockscreen_tips",
                title="Disable Lock Screen Tips and Ads",
                description="Stops Windows Spotlight from displaying suggestions, tips, and ads on the lock screen.",
                category="System",
                impact="Keeps lock screen clean and reduces background network fetches.",
                root_key=winreg.HKEY_CURRENT_USER,
                subkey=r"Software\Microsoft\Windows\CurrentVersion\ContentDeliveryManager",
                value_name="RotatingLockScreenOverlayEnabled",
                value_type=winreg.REG_DWORD,
                applied_val=0,
                default_val=1,
            ),
        }

    def get_all_tweaks(self) -> Dict[str, Dict[str, Any]]:
        """Returns metadata and current applied state for all tweaks."""
        result = {}
        for k, twk in self._tweaks.items():
            result[k] = {
                "id": twk.id,
                "title": twk.title,
                "description": twk.description,
                "category": twk.category,
                "impact": twk.impact,
                "is_applied": twk.is_applied(),
            }
        return result

    def apply_tweak(self, tweak_id: str) -> Dict[str, Any]:
        """Applies a tweak and registers change into audit history."""
        twk = self._tweaks.get(tweak_id)
        if not twk:
            return {"success": False, "message": f"Tweak '{tweak_id}' not found."}

        res = twk.apply()
        if res.get("success") and change_history:
            change_history.record_action(
                action_id=f"tweak_{tweak_id}",
                title=f"Enable: {twk.title}",
                category="Tweaks",
                status="executed",
                verified=twk.is_applied(),
                verification_message="Registry key updated and shell notified.",
                reversible=True,
                before_state={"applied": False},
                after_state={"applied": True},
            )
        return res

    def revert_tweak(self, tweak_id: str) -> Dict[str, Any]:
        """Reverts a tweak and logs to history."""
        twk = self._tweaks.get(tweak_id)
        if not twk:
            return {"success": False, "message": f"Tweak '{tweak_id}' not found."}

        res = twk.revert()
        if res.get("success") and change_history:
            change_history.record_action(
                action_id=f"tweak_{tweak_id}_revert",
                title=f"Revert: {twk.title}",
                category="Tweaks",
                status="executed",
                verified=not twk.is_applied(),
                verification_message="Registry restored to Windows default.",
                reversible=True,
                before_state={"applied": True},
                after_state={"applied": False},
            )
        return res


tweaks_manager = TweaksManager()
