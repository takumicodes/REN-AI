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

from .history import (
    ChangeHistory,
    change_history,
)

from .action_registry import (
    Action,
    RiskLevel,
    ActionRegistry,
    ActionExecutor,
    action_registry,
    action_executor,
)

from .process_manager import (
    ProcessInfo,
    ProcessManager,
    process_manager,
)

from .startup_manager import (
    StartupItem,
    StartupManager,
    startup_manager,
)

from .services_manager import (
    ServiceInfo,
    ServicesManager,
    services_manager,
)

from .storage_cleaner import (
    CleanupItem,
    StorageCleaner,
    storage_cleaner,
)

from .storage_analyzer import (
    DriveSummary,
    StorageAnalyzer,
    storage_analyzer,
)

from .app_manager import (
    InstalledApp,
    AppManager,
    app_manager,
)

from .tweaks_manager import (
    TweaksManager,
    tweaks_manager,
)

from .privacy_center import (
    PrivacyCenter,
    privacy_center,
)

from .network_center import (
    NetworkCenter,
    network_center,
)

from .health_diagnostics import (
    HealthDiagnostics,
    health_diagnostics,
)

from .restore_center import (
    RestoreCenter,
    restore_center,
)

from .benchmark import (
    BenchmarkCenter,
    benchmark_center,
)

__all__ = [
    # v1.2.0 Core Exports (Strict Preservation)
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
    # v1.3.0 Control Center Exports
    "ChangeHistory",
    "change_history",
    "Action",
    "RiskLevel",
    "ActionRegistry",
    "ActionExecutor",
    "action_registry",
    "action_executor",
    "ProcessInfo",
    "ProcessManager",
    "process_manager",
    "StartupItem",
    "StartupManager",
    "startup_manager",
    "ServiceInfo",
    "ServicesManager",
    "services_manager",
    "CleanupItem",
    "StorageCleaner",
    "storage_cleaner",
    "DriveSummary",
    "StorageAnalyzer",
    "storage_analyzer",
    "InstalledApp",
    "AppManager",
    "app_manager",
    "TweaksManager",
    "tweaks_manager",
    "PrivacyCenter",
    "privacy_center",
    "NetworkCenter",
    "network_center",
    "HealthDiagnostics",
    "health_diagnostics",
    "RestoreCenter",
    "restore_center",
    "BenchmarkCenter",
    "benchmark_center",
]
