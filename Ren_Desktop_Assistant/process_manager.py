"""
Process Explorer & Safety Engine for REN-AI Windows Control Center
Provides:
- Real-time enumeration of running processes with CPU%, RAM (MB), PID, and status.
- Critical system process shielding (prevents terminating core OS processes).
- Human-driven termination with impact warnings.
- Search and filtering capabilities.
"""

import os
import psutil
from typing import List, Dict, Any, Optional

CRITICAL_SYSTEM_PROCESSES = {
    "system",
    "system idle process",
    "registry",
    "smss.exe",
    "csrss.exe",
    "wininit.exe",
    "services.exe",
    "lsass.exe",
    "svchost.exe",
    "winlogon.exe",
    "explorer.exe",
    "dwm.exe",
    "spoolsv.exe",
    "fontdrvhost.exe",
}


class ProcessInfo:
    """Represents a running process with inspection metrics."""

    def __init__(
        self,
        pid: int,
        name: str,
        cpu_percent: float,
        memory_mb: float,
        memory_percent: float,
        status: str,
        username: str = "",
        exe_path: str = "",
        is_critical: bool = False,
    ):
        self.pid = pid
        self.name = name
        self.cpu_percent = round(cpu_percent, 1)
        self.memory_mb = round(memory_mb, 1)
        self.memory_percent = round(memory_percent, 1)
        self.status = status
        self.username = username
        self.exe_path = exe_path
        self.is_critical = is_critical

    def to_dict(self) -> Dict[str, Any]:
        return {
            "pid": self.pid,
            "name": self.name,
            "cpu_percent": self.cpu_percent,
            "memory_mb": self.memory_mb,
            "memory_percent": self.memory_percent,
            "status": self.status,
            "username": self.username,
            "exe_path": self.exe_path,
            "is_critical": self.is_critical,
        }


class ProcessManager:
    """Manages process inspection, search, and safe termination."""

    @staticmethod
    def is_critical_process(name: str) -> bool:
        """Determines whether a process is essential to Windows operation."""
        return name.lower() in CRITICAL_SYSTEM_PROCESSES

    def get_processes(
        self,
        sort_by: str = "memory_mb",
        ascending: bool = False,
        search_query: str = "",
        limit: int = 150,
    ) -> List[ProcessInfo]:
        """
        Retrieves a snapshot of currently running processes.
        """
        results: List[ProcessInfo] = []
        search_lower = search_query.lower().strip() if search_query else ""

        for proc in psutil.process_iter(["pid", "name", "memory_info", "cpu_percent", "status"]):
            try:
                p_info = proc.info
                pid = p_info["pid"]
                name = p_info["name"] or f"Process-{pid}"

                if search_lower and (search_lower not in name.lower() and search_lower not in str(pid)):
                    continue

                mem_info = p_info.get("memory_info")
                mem_bytes = mem_info.rss if mem_info else 0
                mem_mb = mem_bytes / (1024 * 1024)

                cpu_pct = p_info.get("cpu_percent") or 0.0
                status = p_info.get("status") or "running"
                is_crit = self.is_critical_process(name)

                results.append(
                    ProcessInfo(
                        pid=pid,
                        name=name,
                        cpu_percent=cpu_pct,
                        memory_mb=mem_mb,
                        memory_percent=0.0,
                        status=status,
                        is_critical=is_crit,
                    )
                )
            except (psutil.NoSuchProcess, psutil.AccessDenied, psutil.ZombieProcess):
                continue

        # Sort results
        if sort_by in ("memory_mb", "cpu_percent", "pid", "name"):
            results.sort(key=lambda x: getattr(x, sort_by), reverse=not ascending)

        return results[:limit]

    def terminate_process(self, pid: int, force: bool = False) -> Dict[str, Any]:
        """
        Terminates a process safely with critical system guard.
        """
        try:
            p = psutil.Process(pid)
            name = p.name()

            if self.is_critical_process(name) and not force:
                return {
                    "success": False,
                    "is_critical": True,
                    "message": f"Refused: '{name}' (PID {pid}) is a protected Windows core process. Terminating it may cause a Blue Screen (BSOD).",
                }

            if force:
                p.kill()
            else:
                p.terminate()

            return {
                "success": True,
                "pid": pid,
                "name": name,
                "message": f"Process '{name}' (PID {pid}) terminated successfully.",
            }
        except psutil.NoSuchProcess:
            return {"success": False, "message": f"Process {pid} no longer exists."}
        except psutil.AccessDenied:
            return {"success": False, "message": f"Access denied terminating PID {pid}. Run as Administrator."}
        except Exception as e:
            return {"success": False, "message": f"Error terminating PID {pid}: {e}"}


process_manager = ProcessManager()
