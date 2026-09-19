"""
System Information Provider for REN Desktop Assistant
Supplies clean hardware metrics and status summaries.
Maintains 100% backward compatibility with original current_system() signature.
"""

from typing import Tuple, Any, Dict
try:
    from .system_status import (
        get_cpu_info,
        current_battery,
        current_ram_usage,
        disk_usage,
        percentage_ram_left,
        get_power_status,
        get_power_profile,
        get_system_snapshot as _get_snapshot,
        get_battery_info,
        get_ram_details,
    )
except ImportError:
    from system_status import (
        get_cpu_info,
        current_battery,
        current_ram_usage,
        disk_usage,
        percentage_ram_left,
        get_power_status,
        get_power_profile,
        get_system_snapshot as _get_snapshot,
        get_battery_info,
        get_ram_details,
    )


def current_system() -> Tuple[float, float, float, float, Any, str, Any]:
    """
    Returns original 7-tuple:
    (cpu, ram_usage, ram_left, disk_use, battery, power_profile, power_status)
    Maintains 100% compatibility with legacy Ren AI callers.
    """
    cpu = get_cpu_info()
    ram_usage = current_ram_usage()
    ram_left = percentage_ram_left()
    disk_use = disk_usage()
    battery = current_battery()
    power_profile = get_power_profile()
    power_status = get_power_status()

    return cpu, ram_usage, ram_left, disk_use, battery, power_profile, power_status


def get_system_snapshot() -> Dict[str, Any]:
    """Returns the comprehensive structured system snapshot dictionary."""
    return _get_snapshot()


def format_system_summary() -> str:
    """Returns a clean, human-readable summary of the current system state."""
    snapshot = _get_snapshot()
    cpu = snapshot["cpu_percent"]
    ram = snapshot["ram"]
    disk = snapshot["primary_disk_percent"]
    battery = snapshot["battery"]
    power = snapshot["power_profile"]
    context = snapshot["context"]

    bat_str = f"{battery['percent']}% ({'AC Plugged' if battery['is_plugged'] else 'Discharging'})" if battery["has_battery"] else "AC Wall Power (Desktop)"
    
    return (
        f"CPU: {cpu}% | RAM: {ram['percent_used']}% ({ram['available_gb']} GB free) | "
        f"Disk: {disk}% | Power: {power} | Battery: {bat_str} | Context: {context['category'].upper()}"
    )


if __name__ == "__main__":
    print("=== REN System Info ===")
    print(format_system_summary())