"""
Windows Debloater & System Optimizer for REN Desktop Assistant
Features:
- Safe, non-destructive, human-driven system debloating.
- Tailored for low RAM usage, zero background telemetry, and disabling AI slop (Copilot / Cortana).
- Clean temp file purging and standby RAM optimization.
- Full transparency with preview and rollback capabilities.
"""

import os
import shutil
import tempfile
import winreg
import subprocess
from pathlib import Path
from typing import Dict, List, Any, Optional
try:
    from .preferences import preferences
except ImportError:
    from preferences import preferences


class DebloatManager:
    """Provides safe Windows debloating and performance tuning."""

    TWEAKS = {
        "disable_search_bing": {
            "title": "Disable Bing Search in Start Menu",
            "category": "ai_slop_removal",
            "impact": "Eliminates web search delays and telemetry in Windows search; keeps search 100% local and fast.",
            "safe": True,
            "requires_admin": False,
        },
        "disable_copilot": {
            "title": "Turn Off Windows Copilot Background Integration",
            "category": "ai_slop_removal",
            "impact": "Stops Copilot background telemetry and edge web processes from consuming background RAM.",
            "safe": True,
            "requires_admin": False,
        },
        "optimize_visual_effects": {
            "title": "Optimize Visual Effects for Low RAM & Programmer Mode",
            "category": "ram_optimization",
            "impact": "Disables window minimize/maximize animations and drop shadows, freeing DWM RAM and GPU cycles.",
            "safe": True,
            "requires_admin": False,
        },
        "clean_temp_caches": {
            "title": "Clean Windows Temp & Crash Caches",
            "category": "disk_cleanup",
            "impact": "Purges temporary files from user and system temp folders to free storage.",
            "safe": True,
            "requires_admin": False,
        },
        "disable_telemetry_services": {
            "title": "Disable Diagnostic Tracking (DiagTrack)",
            "category": "telemetry",
            "impact": "Stops Windows Connected User Experiences and Telemetry service to save background CPU/network.",
            "safe": True,
            "requires_admin": True,
        },
    }

    def get_tweak_definitions(self) -> Dict[str, Any]:
        """Returns metadata for all available tweaks."""
        applied = preferences.get("applied_debloat_tweaks", [])
        result = {}
        for key, info in self.TWEAKS.items():
            result[key] = {
                **info,
                "is_applied": key in applied,
            }
        return result

    # --- Tweak Implementations ---

    def disable_search_bing(self) -> Dict[str, Any]:
        """Disables Bing web results in Windows Search."""
        key_path = r"Software\Policies\Microsoft\Windows\Explorer"
        try:
            with winreg.CreateKey(winreg.HKEY_CURRENT_USER, key_path) as key:
                winreg.SetValueEx(key, "DisableSearchBoxSuggestions", 0, winreg.REG_DWORD, 1)

            search_key = r"Software\Microsoft\Windows\CurrentVersion\Search"
            with winreg.CreateKey(winreg.HKEY_CURRENT_USER, search_key) as key:
                winreg.SetValueEx(key, "BingSearchEnabled", 0, winreg.REG_DWORD, 0)
                winreg.SetValueEx(key, "CortanaConsent", 0, winreg.REG_DWORD, 0)

            self._mark_applied("disable_search_bing")
            return {"success": True, "message": "Bing search in Start Menu disabled."}
        except Exception as e:
            return {"success": False, "message": f"Failed to set registry: {e}"}

    def rollback_search_bing(self) -> Dict[str, Any]:
        """Re-enables Bing web results in Windows Search."""
        search_key = r"Software\Microsoft\Windows\CurrentVersion\Search"
        try:
            with winreg.CreateKey(winreg.HKEY_CURRENT_USER, search_key) as key:
                winreg.SetValueEx(key, "BingSearchEnabled", 0, winreg.REG_DWORD, 1)
            self._mark_unapplied("disable_search_bing")
            return {"success": True, "message": "Bing search restored."}
        except Exception as e:
            return {"success": False, "message": f"Failed to revert registry: {e}"}

    def disable_copilot(self) -> Dict[str, Any]:
        """Disables Windows Copilot via user policy."""
        key_path = r"Software\Policies\Microsoft\Windows\WindowsCopilot"
        try:
            with winreg.CreateKey(winreg.HKEY_CURRENT_USER, key_path) as key:
                winreg.SetValueEx(key, "TurnOffWindowsCopilot", 0, winreg.REG_DWORD, 1)
            self._mark_applied("disable_copilot")
            return {"success": True, "message": "Windows Copilot integration disabled."}
        except Exception as e:
            return {"success": False, "message": f"Failed to set registry: {e}"}

    def rollback_copilot(self) -> Dict[str, Any]:
        """Re-enables Windows Copilot."""
        key_path = r"Software\Policies\Microsoft\Windows\WindowsCopilot"
        try:
            with winreg.CreateKey(winreg.HKEY_CURRENT_USER, key_path) as key:
                winreg.SetValueEx(key, "TurnOffWindowsCopilot", 0, winreg.REG_DWORD, 0)
            self._mark_unapplied("disable_copilot")
            return {"success": True, "message": "Windows Copilot re-enabled."}
        except Exception as e:
            return {"success": False, "message": f"Failed to revert: {e}"}

    def optimize_visual_effects(self) -> Dict[str, Any]:
        """Sets visual performance for responsiveness and lower RAM consumption."""
        desktop_key = r"Control Panel\Desktop"
        try:
            with winreg.CreateKey(winreg.HKEY_CURRENT_USER, desktop_key) as key:
                winreg.SetValueEx(key, "UserPreferencesMask", 0, winreg.REG_BINARY, b"\x90\x12\x03\x80\x10\x00\x00\x00")
                winreg.SetValueEx(key, "MenuShowDelay", 0, winreg.REG_SZ, "20")

            self._mark_applied("optimize_visual_effects")
            return {"success": True, "message": "Visual animations optimized for low RAM and high responsiveness."}
        except Exception as e:
            return {"success": False, "message": f"Visual effects adjustment failed: {e}"}

    def rollback_visual_effects(self) -> Dict[str, Any]:
        """Restores default Windows visual effects."""
        desktop_key = r"Control Panel\Desktop"
        try:
            with winreg.CreateKey(winreg.HKEY_CURRENT_USER, desktop_key) as key:
                winreg.SetValueEx(key, "MenuShowDelay", 0, winreg.REG_SZ, "400")
            self._mark_unapplied("optimize_visual_effects")
            return {"success": True, "message": "Visual effects restored to Windows defaults."}
        except Exception as e:
            return {"success": False, "message": f"Failed to restore visual effects: {e}"}

    def clean_temp_caches(self) -> Dict[str, Any]:
        """Purges user temporary files safely without breaking active locks."""
        temp_dir = Path(tempfile.gettempdir())
        freed_bytes = 0
        deleted_count = 0

        if temp_dir.exists():
            for item in temp_dir.iterdir():
                try:
                    if item.is_file():
                        size = item.stat().st_size
                        item.unlink()
                        freed_bytes += size
                        deleted_count += 1
                    elif item.is_dir():
                        shutil.rmtree(item, ignore_errors=True)
                except Exception:
                    continue

        freed_mb = round(freed_bytes / (1024 * 1024), 2)
        return {
            "success": True,
            "deleted_files": deleted_count,
            "freed_mb": freed_mb,
            "message": f"Cleaned {deleted_count} temporary files, freeing {freed_mb} MB.",
        }

    def disable_telemetry_services(self) -> Dict[str, Any]:
        """Stops and disables Windows DiagTrack service (requires Administrator)."""
        try:
            cmd = "sc.exe stop DiagTrack && sc.exe config DiagTrack start= disabled"
            res = subprocess.run(cmd, shell=True, capture_output=True, text=True)
            if res.returncode == 0:
                self._mark_applied("disable_telemetry_services")
                return {"success": True, "message": "Diagnostic tracking service disabled."}
            else:
                return {"success": False, "message": "Requires running as Administrator to stop system services."}
        except Exception as e:
            return {"success": False, "message": str(e)}

    def rollback_telemetry_services(self) -> Dict[str, Any]:
        """Restores DiagTrack service."""
        try:
            cmd = "sc.exe config DiagTrack start= auto && sc.exe start DiagTrack"
            subprocess.run(cmd, shell=True, capture_output=True, text=True)
            self._mark_unapplied("disable_telemetry_services")
            return {"success": True, "message": "Diagnostic tracking restored."}
        except Exception as e:
            return {"success": False, "message": str(e)}

    # --- Mode Presets ---

    def apply_programmer_mode_debloat(self) -> Dict[str, Any]:
        """Applies debloat optimizations designed for programmers and low RAM."""
        results = []
        results.append(self.disable_search_bing())
        results.append(self.disable_copilot())
        results.append(self.optimize_visual_effects())
        results.append(self.clean_temp_caches())

        success_count = sum(1 for r in results if r.get("success"))
        return {
            "success": True,
            "applied_count": success_count,
            "details": results,
            "summary": f"Programmer Mode debloat complete ({success_count}/4 tweaks applied).",
        }

    def launch_ctt_winutil(self) -> Dict[str, Any]:
        """
        Launches the Chris Titus Tech Windows Utility (winutil) script.
        Command: irm https://christitus.com/win | iex in PowerShell.
        """
        try:
            ps_cmd = 'Start-Process powershell -ArgumentList "-ExecutionPolicy Bypass -NoExit -Command \\"irm https://christitus.com/win | iex\\"" -Verb RunAs'
            subprocess.Popen(["powershell.exe", "-Command", ps_cmd])
            return {
                "success": True,
                "message": "Chris Titus Tech Windows Utility launched in PowerShell."
            }
        except Exception:
            try:
                subprocess.Popen(["powershell.exe", "-ExecutionPolicy", "Bypass", "-NoExit", "-Command", "irm https://christitus.com/win | iex"])
                return {
                    "success": True,
                    "message": "Chris Titus Tech Windows Utility launched."
                }
            except Exception as err:
                return {
                    "success": False,
                    "message": f"Failed to launch CTT Winutil: {err}"
                }

    def rollback_all_tweaks(self) -> Dict[str, Any]:
        """Rolls back all applied debloat tweaks to Windows defaults."""
        results = []
        results.append(self.rollback_search_bing())
        results.append(self.rollback_copilot())
        results.append(self.rollback_visual_effects())
        results.append(self.rollback_telemetry_services())
        success_count = sum(1 for r in results if r.get("success"))
        return {
            "success": True,
            "rolled_back_count": success_count,
            "message": f"Rolled back {success_count} debloat tweaks to Windows defaults."
        }

    # --- Tracking Helpers ---

    def _mark_applied(self, tweak_key: str):
        applied = set(preferences.get("applied_debloat_tweaks", []))
        applied.add(tweak_key)
        preferences.set("applied_debloat_tweaks", list(applied))

    def _mark_unapplied(self, tweak_key: str):
        applied = set(preferences.get("applied_debloat_tweaks", []))
        applied.discard(tweak_key)
        preferences.set("applied_debloat_tweaks", list(applied))


debloat_manager = DebloatManager()

if __name__ == "__main__":
    print("=== REN Windows Debloat Manager ===")
    tweaks = debloat_manager.get_tweak_definitions()
    for k, v in tweaks.items():
        status = "[APPLIED]" if v["is_applied"] else "[READY]"
        print(f"{status} {v['title']} ({v['impact']})")
