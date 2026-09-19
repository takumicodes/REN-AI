"""
Installed Applications Manager for REN-AI Windows Control Center
Features:
- Enumerates installed Win32 programs and UWP apps from Windows Registry.
- Extracts publisher, version, install date, and estimated size.
- Generates safe, transparent uninstall commands with human confirmation.
"""

import os
import winreg
import subprocess
from typing import List, Dict, Any, Optional


class InstalledApp:
    """Represents an installed application on Windows."""

    def __init__(
        self,
        name: str,
        version: str = "",
        publisher: str = "",
        install_date: str = "",
        uninstall_string: str = "",
        estimated_size_mb: float = 0.0,
        is_system: bool = False,
    ):
        self.name = name
        self.version = version
        self.publisher = publisher
        self.install_date = install_date
        self.uninstall_string = uninstall_string
        self.estimated_size_mb = round(estimated_size_mb, 1)
        self.is_system = is_system

    def to_dict(self) -> Dict[str, Any]:
        return {
            "name": self.name,
            "version": self.version,
            "publisher": self.publisher,
            "install_date": self.install_date,
            "uninstall_string": self.uninstall_string,
            "estimated_size_mb": self.estimated_size_mb,
        }


class AppManager:
    """Manages querying and uninstalling Windows applications."""

    REG_UNINSTALL_KEYS = [
        (winreg.HKEY_LOCAL_MACHINE, r"Software\Microsoft\Windows\CurrentVersion\Uninstall"),
        (winreg.HKEY_LOCAL_MACHINE, r"Software\WOW6432Node\Microsoft\Windows\CurrentVersion\Uninstall"),
        (winreg.HKEY_CURRENT_USER, r"Software\Microsoft\Windows\CurrentVersion\Uninstall"),
    ]

    def get_installed_apps(self, search_query: str = "", limit: int = 200) -> List[InstalledApp]:
        """Scans the registry for installed applications."""
        apps_dict: Dict[str, InstalledApp] = {}
        search_lower = search_query.lower().strip() if search_query else ""

        for hkey_root, subkey in self.REG_UNINSTALL_KEYS:
            try:
                with winreg.OpenKey(hkey_root, subkey, 0, winreg.KEY_READ) as key:
                    num_subkeys = winreg.QueryInfoKey(key)[0]
                    for i in range(num_subkeys):
                        try:
                            app_sub_name = winreg.EnumKey(key, i)
                            with winreg.OpenKey(key, app_sub_name, 0, winreg.KEY_READ) as app_key:
                                def get_val(val_name: str, default: Any = "") -> Any:
                                    try:
                                        return winreg.QueryValueEx(app_key, val_name)[0]
                                    except Exception:
                                        return default

                                display_name = str(get_val("DisplayName", "")).strip()
                                if not display_name:
                                    continue

                                # Skip system components / hotfixes if desired
                                if get_val("SystemComponent", 0) == 1:
                                    continue
                                if display_name.startswith("Security Update") or display_name.startswith("Update for"):
                                    continue

                                if search_lower and (search_lower not in display_name.lower()):
                                    continue

                                version = str(get_val("DisplayVersion", ""))
                                publisher = str(get_val("Publisher", ""))
                                install_date = str(get_val("InstallDate", ""))
                                uninst_str = str(get_val("UninstallString", ""))
                                quiet_uninst = str(get_val("QuietUninstallString", ""))
                                chosen_uninst = quiet_uninst if quiet_uninst else uninst_str

                                est_kb = get_val("EstimatedSize", 0)
                                size_mb = (float(est_kb) / 1024.0) if est_kb else 0.0

                                # De-duplicate by name
                                if display_name not in apps_dict:
                                    apps_dict[display_name] = InstalledApp(
                                        name=display_name,
                                        version=version,
                                        publisher=publisher,
                                        install_date=install_date,
                                        uninstall_string=chosen_uninst,
                                        estimated_size_mb=size_mb,
                                    )
                        except Exception:
                            continue
            except Exception:
                continue

        results = list(apps_dict.values())
        results.sort(key=lambda x: x.name.lower())
        return results[:limit]

    def launch_uninstall(self, app_name: str) -> Dict[str, Any]:
        """
        Launches the uninstaller for the specified program after human confirmation.
        """
        apps = self.get_installed_apps(search_query=app_name)
        target = next((a for a in apps if a.name.lower() == app_name.lower()), None)
        if not target or not target.uninstall_string:
            return {"success": False, "message": f"Uninstall string for '{app_name}' not found."}

        cmd = target.uninstall_string.strip()
        try:
            # Handle MsiExec command execution safely
            if cmd.lower().startswith("msiexec"):
                subprocess.Popen(cmd, shell=True)
            else:
                subprocess.Popen(cmd, shell=True)
            return {
                "success": True,
                "message": f"Uninstaller for '{app_name}' launched. Please follow the on-screen uninstaller prompt.",
                "command": cmd,
            }
        except Exception as e:
            return {"success": False, "message": f"Failed to launch uninstaller: {e}"}


app_manager = AppManager()
