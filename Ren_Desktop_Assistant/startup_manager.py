"""
Windows Startup Apps Manager for REN-AI Windows Control Center
Features:
- Enumerate startup applications from Registry (HKCU / HKLM / Wow6432Node) and Startup folders.
- Enable/Disable toggles with safe disabled state preservation.
- Full 1-click rollback support via change history.
"""

import os
import sys
import winreg
from pathlib import Path
from typing import List, Dict, Any, Optional

try:
    from .history import change_history
except ImportError:
    from history import change_history


class StartupItem:
    """Represents a program scheduled to launch on Windows login."""

    def __init__(
        self,
        name: str,
        command: str,
        source: str,
        enabled: bool = True,
        registry_key: Optional[str] = None,
        registry_root: Optional[int] = None,
        file_path: Optional[str] = None,
    ):
        self.name = name
        self.command = command
        self.source = source              # e.g., 'HKCU Run', 'HKLM Run', 'Startup Folder'
        self.enabled = enabled
        self.registry_key = registry_key
        self.registry_root = registry_root
        self.file_path = file_path

    def to_dict(self) -> Dict[str, Any]:
        return {
            "name": self.name,
            "command": self.command,
            "source": self.source,
            "enabled": self.enabled,
            "file_path": self.file_path,
        }


class StartupManager:
    """Manages reading, disabling, and enabling Windows startup programs."""

    REG_RUN_LOCATIONS = [
        (winreg.HKEY_CURRENT_USER, r"Software\Microsoft\Windows\CurrentVersion\Run", "HKCU Run"),
        (winreg.HKEY_LOCAL_MACHINE, r"Software\Microsoft\Windows\CurrentVersion\Run", "HKLM Run"),
        (winreg.HKEY_LOCAL_MACHINE, r"Software\WOW6432Node\Microsoft\Windows\CurrentVersion\Run", "HKLM Wow6432 Run"),
    ]

    DISABLED_KEY = r"Software\RenDesktopAssistant\DisabledStartup"

    def get_startup_items(self) -> List[StartupItem]:
        """Scans all registry keys and startup folders for startup items."""
        items: List[StartupItem] = []

        # 1. Registry Run keys (Enabled)
        for hkey_root, subkey, label in self.REG_RUN_LOCATIONS:
            try:
                with winreg.OpenKey(hkey_root, subkey, 0, winreg.KEY_READ) as key:
                    index = 0
                    while True:
                        try:
                            val_name, val_data, _ = winreg.EnumValue(key, index)
                            items.append(
                                StartupItem(
                                    name=val_name,
                                    command=str(val_data),
                                    source=label,
                                    enabled=True,
                                    registry_key=subkey,
                                    registry_root=hkey_root,
                                )
                            )
                            index += 1
                        except OSError:
                            break
            except Exception:
                pass

        # 2. REN Disabled Registry subkey
        try:
            with winreg.OpenKey(winreg.HKEY_CURRENT_USER, self.DISABLED_KEY, 0, winreg.KEY_READ) as d_key:
                index = 0
                while True:
                    try:
                        val_name, val_data, _ = winreg.EnumValue(d_key, index)
                        # Format stored: "original_source||command"
                        parts = str(val_data).split("||", 1)
                        orig_src = parts[0] if len(parts) > 1 else "Registry"
                        cmd = parts[1] if len(parts) > 1 else str(val_data)
                        items.append(
                            StartupItem(
                                name=val_name,
                                command=cmd,
                                source=f"{orig_src} (Disabled)",
                                enabled=False,
                                registry_key=self.DISABLED_KEY,
                                registry_root=winreg.HKEY_CURRENT_USER,
                            )
                        )
                        index += 1
                    except OSError:
                        break
        except Exception:
            pass

        # 3. User Startup Folder
        appdata = os.environ.get("APPDATA")
        if appdata:
            startup_dir = Path(appdata) / "Microsoft" / "Windows" / "Start Menu" / "Programs" / "Startup"
            if startup_dir.exists():
                for f in startup_dir.iterdir():
                    if f.name.lower() != "desktop.ini":
                        items.append(
                            StartupItem(
                                name=f.stem,
                                command=str(f),
                                source="User Startup Folder",
                                enabled=True,
                                file_path=str(f),
                            )
                        )

        return items

    def disable_startup_item(self, name: str, source: str) -> Dict[str, Any]:
        """
        Disables a startup item by safely relocating it to the REN Disabled registry area.
        """
        items = self.get_startup_items()
        target = next((i for i in items if i.name == name and i.source == source and i.enabled), None)
        if not target:
            return {"success": False, "message": f"Active startup item '{name}' not found."}

        if target.file_path:
            # For folder items, rename to .disabled extension
            p = Path(target.file_path)
            try:
                new_p = p.with_name(p.name + ".rendisabled")
                p.rename(new_p)
                return {"success": True, "message": f"Disabled startup shortcut '{name}'."}
            except Exception as e:
                return {"success": False, "message": f"Failed to disable shortcut: {e}"}

        if target.registry_root and target.registry_key:
            try:
                # Save into Disabled key
                with winreg.CreateKey(winreg.HKEY_CURRENT_USER, self.DISABLED_KEY) as d_key:
                    winreg.SetValueEx(d_key, name, 0, winreg.REG_SZ, f"{target.source}||{target.command}")

                # Delete from original run key
                with winreg.OpenKey(target.registry_root, target.registry_key, 0, winreg.KEY_SET_VALUE) as orig_key:
                    winreg.DeleteValue(orig_key, name)

                return {"success": True, "message": f"Disabled '{name}' from startup."}
            except Exception as e:
                return {"success": False, "message": f"Failed to modify registry: {e}"}

        return {"success": False, "message": "Unknown startup source type."}

    def enable_startup_item(self, name: str) -> Dict[str, Any]:
        """
        Re-enables a previously disabled startup item.
        """
        try:
            with winreg.OpenKey(winreg.HKEY_CURRENT_USER, self.DISABLED_KEY, 0, winreg.KEY_ALL_ACCESS) as d_key:
                val_data, _ = winreg.QueryValueEx(d_key, name)
                parts = str(val_data).split("||", 1)
                orig_src = parts[0] if len(parts) > 1 else "HKCU Run"
                cmd = parts[1] if len(parts) > 1 else str(val_data)

                # Restore to HKCU Run
                run_key_path = r"Software\Microsoft\Windows\CurrentVersion\Run"
                with winreg.CreateKey(winreg.HKEY_CURRENT_USER, run_key_path) as run_key:
                    winreg.SetValueEx(run_key, name, 0, winreg.REG_SZ, cmd)

                # Delete from disabled
                winreg.DeleteValue(d_key, name)
                return {"success": True, "message": f"Re-enabled '{name}' in startup."}
        except FileNotFoundError:
            pass
        except Exception as e:
            return {"success": False, "message": f"Failed to restore startup item: {e}"}

        # Check for folder disabled item
        appdata = os.environ.get("APPDATA")
        if appdata:
            startup_dir = Path(appdata) / "Microsoft" / "Windows" / "Start Menu" / "Programs" / "Startup"
            if startup_dir.exists():
                for f in startup_dir.glob("*.rendisabled"):
                    if f.name.startswith(name):
                        orig_name = f.name[:-12]
                        f.rename(f.with_name(orig_name))
                        return {"success": True, "message": f"Re-enabled '{name}' in startup folder."}

        return {"success": False, "message": f"Disabled item '{name}' not found."}


startup_manager = StartupManager()
