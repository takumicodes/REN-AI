"""
System Status Monitor for REN Desktop Assistant
Safely queries CPU, RAM, Disk, Battery, Power schemes, and Foreground activity on Windows.
Runs silently on import, with zero unsolicited side-effects.
"""

import os
import re
import sys
import psutil
import subprocess
from typing import Dict, Any, Optional, Tuple

# Initialize CPU measurement seed
_ = psutil.cpu_percent(interval=None)


def get_cpu_info() -> float:
    """Returns current CPU utilization percentage (0.0 - 100.0)."""
    try:
        val = psutil.cpu_percent(interval=None)
        if val == 0.0:
            val = psutil.cpu_percent(interval=0.1)
        return round(val, 1)
    except Exception:
        return 0.0


def current_ram_usage() -> float:
    """Returns current RAM usage percentage."""
    try:
        return round(psutil.virtual_memory().percent, 1)
    except Exception:
        return 0.0


def percentage_ram_left() -> float:
    """Returns percentage of RAM remaining available."""
    try:
        mem = psutil.virtual_memory()
        return round(mem.available * 100.0 / mem.total, 1)
    except Exception:
        return 0.0


def get_ram_details() -> Dict[str, Any]:
    """Returns detailed RAM statistics in MB and GB."""
    try:
        mem = psutil.virtual_memory()
        return {
            "percent_used": round(mem.percent, 1),
            "percent_free": round(mem.available * 100.0 / mem.total, 1),
            "used_gb": round((mem.total - mem.available) / (1024 ** 3), 2),
            "available_gb": round(mem.available / (1024 ** 3), 2),
            "total_gb": round(mem.total / (1024 ** 3), 2),
        }
    except Exception:
        return {"percent_used": 0.0, "percent_free": 100.0, "used_gb": 0.0, "available_gb": 0.0, "total_gb": 0.0}


def disk_usage(path: Optional[str] = None) -> float:
    """
    Returns percentage disk usage for the primary or specified drive.
    Defaults to SystemDrive (e.g. C:) on Windows.
    """
    try:
        if not path:
            path = os.environ.get("SystemDrive", "C:") + "\\"
        return round(psutil.disk_usage(path).percent, 1)
    except Exception:
        try:
            return round(psutil.disk_usage("/").percent, 1)
        except Exception:
            return 0.0


def get_all_disks() -> Dict[str, Dict[str, Any]]:
    """Returns usage breakdown for all accessible fixed disk partitions."""
    disks = {}
    try:
        for part in psutil.disk_partitions(all=False):
            if "fixed" in part.opts or os.name == "nt":
                try:
                    usage = psutil.disk_usage(part.mountpoint)
                    disks[part.mountpoint] = {
                        "total_gb": round(usage.total / (1024 ** 3), 2),
                        "used_gb": round(usage.used / (1024 ** 3), 2),
                        "free_gb": round(usage.free / (1024 ** 3), 2),
                        "percent": round(usage.percent, 1),
                    }
                except (PermissionError, OSError):
                    continue
    except Exception:
        pass
    return disks


def current_battery() -> Any:
    """
    Returns battery percentage as int/float, or 'No battery detected'.
    Maintains 100% backward compatibility with original Ren signature.
    """
    try:
        battery = psutil.sensors_battery()
        if battery is not None:
            return battery.percent
        return "No battery detected"
    except Exception:
        return "No battery detected"


def get_battery_info() -> Dict[str, Any]:
    """Returns structured battery information with safe typing."""
    try:
        battery = psutil.sensors_battery()
        if battery is not None:
            return {
                "has_battery": True,
                "percent": round(battery.percent, 1),
                "is_plugged": bool(battery.power_plugged),
                "seconds_left": battery.secsleft if battery.secsleft != psutil.POWER_TIME_UNLIMITED else None,
            }
        return {
            "has_battery": False,
            "percent": 100.0,
            "is_plugged": True,  # Desktop PCs are AC powered
            "seconds_left": None,
        }
    except Exception:
        return {
            "has_battery": False,
            "percent": 100.0,
            "is_plugged": True,
            "seconds_left": None,
        }


def get_power_status() -> Any:
    """
    Returns True if plugged in, False if on battery, or 'No battery detected'.
    Maintains 100% backward compatibility with original Ren signature.
    """
    try:
        battery = psutil.sensors_battery()
        if battery is not None:
            return battery.power_plugged
        return "No battery detected"
    except Exception:
        return "No battery detected"


def get_power_profile() -> str:
    """Returns active Windows power scheme name (e.g. 'Balanced', 'High Performance', 'Ultimate Performance')."""
    try:
        result = subprocess.check_output("powercfg /getactivescheme", shell=True, text=True, stderr=subprocess.DEVNULL)
        match = re.search(r"\(([^)]+)\)", result)
        if match:
            return match.group(1).strip()
    except Exception:
        pass

    try:
        import powerplan
        name = powerplan.get_current_scheme_name()
        if name:
            return str(name).strip()
    except Exception:
        pass

    return "Balanced"


def get_available_power_schemes() -> Dict[str, str]:
    """Returns mapping of power scheme names to their GUIDs."""
    schemes = {}
    try:
        output = subprocess.check_output("powercfg /list", shell=True, text=True, stderr=subprocess.DEVNULL)
        for line in output.splitlines():
            m = re.search(r"GUID:\s*([a-fA-F0-9-]+)\s+\(([^)]+)\)", line)
            if m:
                guid, name = m.group(1), m.group(2)
                schemes[name.strip()] = guid.strip()
    except Exception:
        pass
    return schemes


def set_power_profile(scheme_name: str) -> bool:
    """Safely switches Windows active power scheme by name (case-insensitive)."""
    schemes = get_available_power_schemes()
    target_guid = None

    for name, guid in schemes.items():
        if scheme_name.lower() in name.lower() or name.lower() in scheme_name.lower():
            target_guid = guid
            break

    if target_guid:
        try:
            subprocess.check_call(f"powercfg /setactive {target_guid}", shell=True, stdout=subprocess.DEVNULL, stderr=subprocess.DEVNULL)
            return True
        except Exception:
            pass

    # Fallback via powerplan library
    try:
        import powerplan
        lower_name = scheme_name.lower()
        if "high" in lower_name or "ultimate" in lower_name:
            powerplan.change_current_scheme_to_high()
            return True
        elif "saver" in lower_name:
            powerplan.change_current_scheme_to_powersaver()
            return True
        elif "balance" in lower_name:
            powerplan.change_current_scheme_to_balanced()
            return True
    except Exception:
        pass

    return False


def get_foreground_context() -> Dict[str, Any]:
    """
    Inspects running processes to determine user activity category
    (e.g., 'programming', 'browsing', 'gaming', 'media', 'general').
    Zero AI slop: uses deterministic, fast process signature matching.
    """
    dev_procs = {"code.exe", "pycharm64.exe", "idea64.exe", "devenv.exe", "windowsterminal.exe", "cmd.exe", "powershell.exe", "git.exe", "node.exe", "python.exe"}
    browser_procs = {"chrome.exe", "msedge.exe", "firefox.exe", "brave.exe", "opera.exe"}
    media_procs = {"vlc.exe", "spotify.exe", "mpv.exe", "wmplayer.exe"}
    game_procs = {"steam.exe", "epicgameslauncher.exe", "javaw.exe", "minecraft.exe"}

    detected_category = "general"
    active_dev_tools = []

    try:
        running_names = {p.info["name"].lower() for p in psutil.process_iter(["name"]) if p.info.get("name")}
        
        dev_matches = running_names.intersection(dev_procs)
        if dev_matches:
            detected_category = "programming"
            active_dev_tools = sorted(list(dev_matches))
        elif running_names.intersection(game_procs):
            detected_category = "gaming"
        elif running_names.intersection(media_procs):
            detected_category = "media"
        elif running_names.intersection(browser_procs):
            detected_category = "browsing"
    except Exception:
        pass

    return {
        "category": detected_category,
        "is_programming": detected_category == "programming",
        "active_dev_tools": active_dev_tools,
    }


def get_system_snapshot() -> Dict[str, Any]:
    """Returns a full, structured system snapshot."""
    cpu = get_cpu_info()
    ram = get_ram_details()
    disk = disk_usage()
    battery = get_battery_info()
    power_plan = get_power_profile()
    context = get_foreground_context()

    return {
        "cpu_percent": cpu,
        "ram": ram,
        "primary_disk_percent": disk,
        "all_disks": get_all_disks(),
        "battery": battery,
        "power_profile": power_plan,
        "context": context,
    }


if __name__ == "__main__":
    # Runs ONLY when directly executed for debugging, never on import
    print("=== REN System Status Debug ===")
    print("Current RAM usage:", current_ram_usage(), "%")
    print("Current RAM left: ", percentage_ram_left(), "%")
    print("Current Disk usage:", disk_usage(), "%")
    print("Current Battery:   ", current_battery())
    print("Current Power State:", get_power_status())
    print("Current Power profile:", get_power_profile())
    print("Current CPU utilisation:", get_cpu_info(), "%")
    print("Context:", get_foreground_context())