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
    description = "Get detailed diagnostic information on OS, CPU, RAM, and disk utilization for target device (PC or Phone)."
    required_permissions = [PermissionCategory.FILESYSTEM_READ]
    parameters_schema = {
        "type": "object",
        "properties": {
            "device": {"type": "string", "description": "Target device ('pc' or 'phone'). Defaults to context target."}
        }
    }

    def run(self, device: Optional[str] = None, device_context: Optional[Any] = None, **kwargs) -> ToolResult:
        start_t = time.perf_counter()
        target_is_phone = False
        if device and "phone" in device.lower():
            target_is_phone = True
        elif device_context and not device_context.is_target_host:
            target_is_phone = True

        if target_is_phone:
            from ren.core.device_context import device_manager
            target_id = device_context.target_device_id if device_context else "phone_default"
            dev = device_manager.get_device(target_id)
            if dev:
                bat_str = f"{dev.battery_info.get('level', 'N/A')}%" if dev.battery_info else "N/A"
                storage_str = f"{dev.storage_info.get('free_gb', 'N/A')} GB free" if dev.storage_info else "N/A"
                report = (
                    f"Device: {dev.name} ({dev.platform.value} {dev.device_type.value})\n"
                    f"Status: {dev.connection_state.value}\n"
                    f"Battery: {bat_str}\n"
                    f"Storage: {storage_str}\n"
                    f"Capabilities: {', '.join(dev.capabilities) if dev.capabilities else 'standard'}"
                )
            else:
                report = "Target device: Phone (Connected via companion client). No active background sensors."

            return ToolResult(success=True, output=report, duration=time.perf_counter() - start_t)

        try:
            cpu = psutil.cpu_percent(interval=0.5)
            ram = psutil.virtual_memory()
            disk = psutil.disk_usage('/')

            report = (
                f"Device: PC Host\n"
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
    description = "Inspect battery percentage and power charging status for target device (PC or Phone)."
    required_permissions = [PermissionCategory.FILESYSTEM_READ]
    parameters_schema = {
        "type": "object",
        "properties": {
            "device": {"type": "string", "description": "Target device ('pc' or 'phone'). Defaults to current device."}
        }
    }

    def run(self, device: Optional[str] = None, device_context: Optional[Any] = None, **kwargs) -> ToolResult:
        start_t = time.perf_counter()
        target_is_phone = False
        if device and "phone" in device.lower():
            target_is_phone = True
        elif device_context and not device_context.is_target_host:
            target_is_phone = True

        if target_is_phone:
            from ren.core.device_context import device_manager
            target_id = device_context.target_device_id if device_context else "phone_default"
            dev = device_manager.get_device(target_id)
            if dev and dev.battery_info:
                b = dev.battery_info
                plugged = "Charging" if b.get("charging") else "Discharging"
                return ToolResult(
                    success=True,
                    output=f"Phone Battery ({dev.name}): {b.get('level', 100)}% ({plugged})",
                    duration=time.perf_counter() - start_t
                )
            return ToolResult(
                success=True,
                output="Phone connected. Real-time battery telemetry is synchronized via companion client.",
                duration=time.perf_counter() - start_t
            )

        try:
            battery = psutil.sensors_battery()
            if not battery:
                return ToolResult(
                    success=True,
                    output="PC Battery: No battery detected on this hardware (Desktop or VM).",
                    duration=time.perf_counter() - start_t
                )

            plugged = "Plugged in (Charging)" if battery.power_plugged else "Discharging"
            output = f"PC Battery: {battery.percent}% ({plugged})"
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
