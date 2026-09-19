"""
REN Desktop Assistant Package
Provides silent Windows background system monitoring, human-driven optimizations,
downloads folder organization, debloating, and 3 intelligent operational modes (Programmer, Balanced, Performance).
"""

from .system_status import (
    get_cpu_info,
    current_ram_usage,
    percentage_ram_left,
    get_ram_details,
    disk_usage,
    get_all_disks,
    current_battery,
    get_battery_info,
    get_power_status,
    get_power_profile,
    get_available_power_schemes,
    set_power_profile,
    get_foreground_context,
    get_system_snapshot,
)

from .system_info import (
    current_system,
    format_system_summary,
)

from .preferences import (
    UserPreferences,
    preferences,
)

from .downloads_organizer import (
    DownloadsOrganizer,
    organizer,
)

from .debloat import (
    DebloatManager,
    debloat_manager,
)

from .modes import (
    ModesManager,
    modes_manager,
    DEV_TOOLS_CATALOG,
)

from .actions import (
    Recommendation,
    ActionQueue,
    action_queue,
)

from .system_observer import (
    SystemObserver,
    observer,
    battery_logic,
    ram_logic,
    power_logic,
    battery_change,
    plugged_state,
    power_plan_change,
)

__all__ = [
    "get_cpu_info",
    "current_ram_usage",
    "percentage_ram_left",
    "get_ram_details",
    "disk_usage",
    "get_all_disks",
    "current_battery",
    "get_battery_info",
    "get_power_status",
    "get_power_profile",
    "get_available_power_schemes",
    "set_power_profile",
    "get_foreground_context",
    "get_system_snapshot",
    "current_system",
    "format_system_summary",
    "UserPreferences",
    "preferences",
    "DownloadsOrganizer",
    "organizer",
    "DebloatManager",
    "debloat_manager",
    "ModesManager",
    "modes_manager",
    "DEV_TOOLS_CATALOG",
    "Recommendation",
    "ActionQueue",
    "action_queue",
    "SystemObserver",
    "observer",
    "battery_logic",
    "ram_logic",
    "power_logic",
    "battery_change",
    "plugged_state",
    "power_plan_change",
]
