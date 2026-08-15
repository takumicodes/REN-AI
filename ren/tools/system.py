"""
System Diagnostic and Process Inspection Tools
"""

import time
import platform
import psutil
from typing import Dict, Any, Optional

from ren.tools.base import BaseTool, ToolResult
from ren.security.permissions import PermissionCategory


class SystemStatusTool(BaseTool):
    name = "system_status"
    description = "Get detailed diagnostic information on OS, CPU, RAM, and disk utilization."
    required_permissions = [PermissionCategory.FILESYSTEM_READ]
    parameters_schema = {"type": "object", "properties": {}}

    def run(self, **kwargs) -> ToolResult:
        start_t = time.perf_counter()
        try:
            cpu = psutil.cpu_percent(interval=0.5)
            ram = psutil.virtual_memory()
            disk = psutil.disk_usage('/')

            report = (
                f"Operating System: {platform.system()} {platform.release()} ({platform.machine()})\n"
                f"Python Version: {platform.python_version()}\n"
                f"CPU Usage: {cpu}%\n"
                f"RAM Usage: {ram.percent}% (Used: {ram.used // (1024*1024)} MB, Total: {ram.total // (1024*1024)} MB)\n"
                f"Disk Usage: {disk.percent}% (Free: {disk.free // (1024*1024*1024)} GB)"
            )

            return ToolResult(
                success=True,
                output=report,
                duration=time.perf_counter() - start_t
            )
        except Exception as e:
            return ToolResult(
                success=False,
                error=f"Error inspecting system status: {e}",
                exit_code=1,
                duration=time.perf_counter() - start_t
            )


class BatteryStatusTool(BaseTool):
    name = "battery_status"
    description = "Inspect laptop battery percentage and power plugged status."
    required_permissions = [PermissionCategory.FILESYSTEM_READ]
    parameters_schema = {"type": "object", "properties": {}}

    def run(self, **kwargs) -> ToolResult:
        start_t = time.perf_counter()
        try:
            battery = psutil.sensors_battery()
            if not battery:
                return ToolResult(
                    success=True,
                    output="No battery detected on this hardware (Desktop or VM).",
                    duration=time.perf_counter() - start_t
                )

            plugged = "Plugged in (Charging)" if battery.power_plugged else "Discharging"
            output = f"Battery: {battery.percent}% ({plugged})"
            return ToolResult(
                success=True,
                output=output,
                duration=time.perf_counter() - start_t
            )
        except Exception as e:
            return ToolResult(
                success=False,
                error=f"Error reading battery status: {e}",
                exit_code=1,
                duration=time.perf_counter() - start_t
            )


class ProcessListTool(BaseTool):
    name = "list_processes"
    description = "List top running processes sorted by CPU and memory usage."
    required_permissions = [PermissionCategory.FILESYSTEM_READ]
    parameters_schema = {
        "type": "object",
        "properties": {
            "limit": {"type": "integer", "description": "Number of top processes to return (default: 10)."}
        }
    }

    def run(self, limit: int = 10, **kwargs) -> ToolResult:
        start_t = time.perf_counter()
        try:
            procs = []
            for p in psutil.process_iter(['pid', 'name', 'cpu_percent', 'memory_percent']):
                try:
                    info = p.info
                    procs.append(info)
                except (psutil.NoSuchProcess, psutil.AccessDenied):
                    continue

            procs.sort(key=lambda x: (x.get('memory_percent') or 0.0), reverse=True)
            top_procs = procs[:limit]

            lines = ["PID    NAME                          RAM%   CPU%"]
            lines.append("-" * 48)
            for p in top_procs:
                name = (p.get('name') or 'Unknown')[:28]
                pid = p.get('pid', 0)
                ram_p = p.get('memory_percent') or 0.0
                cpu_p = p.get('cpu_percent') or 0.0
                lines.append(f"{pid:<6} {name:<28} {ram_p:>5.1f}% {cpu_p:>5.1f}%")

            return ToolResult(
                success=True,
                output="\n".join(lines),
                duration=time.perf_counter() - start_t
            )
        except Exception as e:
            return ToolResult(
                success=False,
                error=f"Failed to list processes: {e}",
                exit_code=1,
                duration=time.perf_counter() - start_t
            )
