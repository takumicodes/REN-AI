"""
Modes Manager for REN Desktop Assistant
Implements the 3 Modes defined in REN specifications:
1. Programmer Mode: Developer tool compatibility & winget installer, low RAM debloat, battery & compile optimization.
2. Balanced Mode: Silent, unobtrusive daily operation with standard Windows balance.
3. Performance Mode: Maximum clock boost, high-performance power plan, and resource liberation.

Human-driven: Never forces installs or changes without user consent.
"""

import os
import shutil
import subprocess
from pathlib import Path
from typing import Dict, List, Any, Optional

try:
    from .preferences import preferences
    from .system_status import set_power_profile, get_power_profile, get_battery_info
    from .debloat import debloat_manager
except ImportError:
    from preferences import preferences
    from system_status import set_power_profile, get_power_profile, get_battery_info
    from debloat import debloat_manager


DEV_TOOLS_CATALOG: Dict[str, Dict[str, str]] = {
    "git": {
        "name": "Git (Version Control)",
        "winget_id": "Git.Git",
        "command_check": "git",
        "description": "Essential source code version control tool.",
    },
    "vscode": {
        "name": "Visual Studio Code",
        "winget_id": "Microsoft.VisualStudioCode",
        "command_check": "code",
        "description": "Modern lightweight code editor for developers.",
    },
    "python": {
        "name": "Python 3",
        "winget_id": "Python.Python.3.11",
        "command_check": "python",
        "description": "Python programming language runtime.",
    },
    "terminal": {
        "name": "Windows Terminal",
        "winget_id": "Microsoft.WindowsTerminal",
        "command_check": "wt",
        "description": "Multi-tab modern terminal for PowerShell, CMD, and WSL.",
    },
    "nodejs": {
        "name": "Node.js (LTS)",
        "winget_id": "OpenJS.NodeJS.LTS",
        "command_check": "node",
        "description": "JavaScript runtime for full-stack and web development.",
    },
    "7zip": {
        "name": "7-Zip Archive Manager",
        "winget_id": "7zip.7zip",
        "command_check": "7z",
        "description": "Fast archive utility for compressed developer packages.",
    },
}


class ModesManager:
    """Manages switching and enforcing features across the 3 modes."""

    def __init__(self):
        self.modes = ("programmer", "balanced", "performance")

    @property
    def current_mode(self) -> str:
        return preferences.active_mode

    def get_mode_description(self, mode: str) -> Dict[str, Any]:
        """Returns structured information regarding a mode's configuration."""
        descriptions = {
            "programmer": {
                "name": "Programmer Mode",
                "tagline": "Best compatibility for developers, developer tools installer, low RAM usage, battery & compile optimizer.",
                "power_plan_ac": "Ultimate Performance",
                "power_plan_battery": "Balanced",
                "debloat_profile": "Programmer (Removes Bing Start Search, Copilot background tasks, trims visual lag)",
                "ram_target": "Ultra-low background usage to maximize IDE/compiler headroom",
            },
            "balanced": {
                "name": "Balanced Mode",
                "tagline": "Unobtrusive daily assistant. Preserves system defaults, organizes downloads, ensures quiet background health.",
                "power_plan_ac": "Balanced",
                "power_plan_battery": "Balanced",
                "debloat_profile": "Standard (Safe maintenance only)",
                "ram_target": "Standard Windows balance",
            },
            "performance": {
                "name": "Performance Mode",
                "tagline": "Maximum system horsepower. Unlocks full CPU frequency, high power plan, frees standby memory.",
                "power_plan_ac": "Ultimate Performance",
                "power_plan_battery": "High Performance",
                "debloat_profile": "High Performance (Temp files cleaned, standby RAM purged)",
                "ram_target": "Freed RAM prioritized for active foreground workload",
            },
        }
        return descriptions.get(mode, descriptions["balanced"])

    def set_mode(self, mode_name: str, apply_optimizations: bool = True) -> Dict[str, Any]:
        """
        Switches the active mode and applies its corresponding settings.
        Human-driven: confirms all changes clearly.
        """
        mode_name = mode_name.lower().strip()
        if mode_name not in self.modes:
            return {"success": False, "message": f"Unknown mode '{mode_name}'. Choose from: {', '.join(self.modes)}"}

        preferences.active_mode = mode_name
        actions_taken = []

        if apply_optimizations:
            bat = get_battery_info()
            is_plugged = bat["is_plugged"]

            if mode_name == "programmer":
                # Power plan optimization
                target_plan = "Ultimate Performance" if is_plugged else "Balanced"
                set_power_profile(target_plan)
                actions_taken.append(f"Power plan tuned to '{target_plan}' ({'AC' if is_plugged else 'Battery'} profile)")

                # Low RAM debloat
                debloat_res = debloat_manager.apply_programmer_mode_debloat()
                actions_taken.append(f"Debloated Windows for low RAM: {debloat_res['summary']}")

            elif mode_name == "balanced":
                set_power_profile("Balanced")
                actions_taken.append("Power plan set to 'Balanced'")

            elif mode_name == "performance":
                set_power_profile("Ultimate Performance")
                debloat_manager.clean_temp_caches()
                actions_taken.append("Power plan set to 'Ultimate Performance' and caches cleared")

        return {
            "success": True,
            "mode": mode_name,
            "actions_taken": actions_taken,
            "message": f"Successfully activated {mode_name.capitalize()} Mode.",
        }

    # --- Programmer Mode Developer Tools Inspector ---

    def check_developer_tools(self) -> Dict[str, Any]:
        """
        Scans system for developer tools listed in DEV_TOOLS_CATALOG.
        Returns installed and missing tools with winget install IDs.
        """
        installed = []
        missing = []

        for key, tool in DEV_TOOLS_CATALOG.items():
            cmd = tool["command_check"]
            found = shutil.which(cmd) is not None
            info = {
                "key": key,
                "name": tool["name"],
                "winget_id": tool["winget_id"],
                "description": tool["description"],
                "is_installed": found,
            }
            if found:
                installed.append(info)
            else:
                missing.append(info)

        return {
            "total_tools": len(DEV_TOOLS_CATALOG),
            "installed_count": len(installed),
            "missing_count": len(missing),
            "installed": installed,
            "missing": missing,
        }

    def generate_winget_install_command(self, tool_keys: Optional[List[str]] = None) -> str:
        """
        Generates a human-inspectable winget command to install missing developer tools.
        Zero AI slop: transparent command string ready for user execution.
        """
        tools_status = self.check_developer_tools()
        missing = tools_status["missing"]

        if tool_keys:
            selected_ids = [t["winget_id"] for t in missing if t["key"] in tool_keys]
        else:
            selected_ids = [t["winget_id"] for t in missing]

        if not selected_ids:
            return ""

        commands = [f"winget install --id {wid} -e --accept-source-agreements --accept-package-agreements" for wid in selected_ids]
        return " && ".join(commands)

    def install_tool(self, tool_key: str) -> Dict[str, Any]:
        """
        Executes winget installation for a specific developer tool upon user approval.
        """
        tool = DEV_TOOLS_CATALOG.get(tool_key)
        if not tool:
            return {"success": False, "message": f"Unknown tool key '{tool_key}'."}

        winget_path = shutil.which("winget")
        if not winget_path:
            return {"success": False, "message": "winget package manager is not available on this system."}

        cmd = [winget_path, "install", "--id", tool["winget_id"], "-e", "--accept-source-agreements", "--accept-package-agreements"]
        try:
            res = subprocess.run(cmd, capture_output=True, text=True, timeout=180)
            if res.returncode == 0:
                return {"success": True, "message": f"Successfully installed {tool['name']}."}
            else:
                return {"success": False, "message": f"Installation failed with code {res.returncode}: {res.stderr[:200]}"}
        except Exception as e:
            return {"success": False, "message": f"Error running winget: {str(e)}"}

    def is_system_python_installed(self) -> bool:
        """Checks if Python is installed on host system PATH."""
        for bin_name in ("python", "python3", "py"):
            if shutil.which(bin_name):
                return True
        return False

    def install_system_python(self) -> Dict[str, Any]:
        """
        Installs Python 3 on the host system if not already installed.
        Uses winget first, falling back to official python.org installer.
        """
        if self.is_system_python_installed():
            return {"success": True, "message": "Python 3 is already installed on this machine."}

        winget_path = shutil.which("winget")
        if winget_path:
            try:
                cmd = [winget_path, "install", "--id", "Python.Python.3.11", "-e", "--accept-source-agreements", "--accept-package-agreements"]
                res = subprocess.run(cmd, capture_output=True, text=True, timeout=300)
                if res.returncode == 0:
                    return {"success": True, "message": "Python 3.11 installed successfully via winget."}
            except Exception:
                pass

        try:
            ps_cmd = (
                "$url = 'https://www.python.org/ftp/python/3.11.9/python-3.11.9-amd64.exe'; "
                "$installer = [System.IO.Path]::Combine($env:TEMP, 'python_installer.exe'); "
                "Invoke-WebRequest -Uri $url -OutFile $installer; "
                "Start-Process -FilePath $installer -ArgumentList '/quiet InstallAllUsers=1 PrependPath=1' -Wait; "
                "Remove-Item $installer -Force"
            )
            res = subprocess.run(["powershell.exe", "-ExecutionPolicy", "Bypass", "-Command", ps_cmd], capture_output=True, text=True, timeout=360)
            if res.returncode == 0:
                return {"success": True, "message": "Python 3.11 downloaded and installed successfully."}
        except Exception as e:
            return {"success": False, "message": f"Python install failed: {e}"}

        return {"success": False, "message": "Could not install Python automatically. Please download from https://python.org"}

    # --- Programmer Cache Cleaner ---

    def clean_dev_caches(self, root_dir: Optional[Path] = None) -> Dict[str, Any]:
        """
        Cleans developer caches (__pycache__, .pytest_cache, .mypy_cache) in workspace.
        """
        root = root_dir or Path(__file__).parent.parent
        cleaned_dirs = 0
        cleaned_files = 0
        freed_bytes = 0

        target_dir_names = {"__pycache__", ".pytest_cache", ".mypy_cache", ".ruff_cache"}

        for dirpath, dirnames, filenames in os.walk(str(root)):
            p = Path(dirpath)
            if p.name in target_dir_names:
                for f in p.glob("*"):
                    try:
                        if f.is_file():
                            freed_bytes += f.stat().st_size
                            cleaned_files += 1
                    except Exception:
                        pass
                try:
                    shutil.rmtree(p, ignore_errors=True)
                    cleaned_dirs += 1
                except Exception:
                    pass

        freed_mb = round(freed_bytes / (1024 * 1024), 2)
        return {
            "success": True,
            "cleaned_dirs": cleaned_dirs,
            "cleaned_files": cleaned_files,
            "freed_mb": freed_mb,
            "message": f"Purged {cleaned_dirs} developer cache directories ({cleaned_files} files, {freed_mb} MB).",
        }


modes_manager = ModesManager()

if __name__ == "__main__":
    print("=== REN Modes Manager ===")
    print(f"Current Mode: {modes_manager.current_mode.upper()}")
    tools = modes_manager.check_developer_tools()
    print(f"Developer Tools: {tools['installed_count']}/{tools['total_tools']} installed.")
    for t in tools["installed"]:
        print(f"  [INSTALLED] {t['name']}")
    for t in tools["missing"]:
        print(f"  [MISSING]   {t['name']} (winget ID: {t['winget_id']})")
