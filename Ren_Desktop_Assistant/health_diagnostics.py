"""
Health & Diagnostics Engine for REN-AI Windows Control Center
Provides:
- Windows integrity scan commands (SFC /scannow, DISM ScanHealth).
- Drive dirty bit status checks (fsutil).
- Event Log recent error queries.
- Battery health report generator.
"""

import os
import subprocess
from pathlib import Path
from typing import Dict, List, Any, Optional


class HealthDiagnostics:
    """Provides system health checks, file integrity verification, and diagnostic reports."""

    def check_drive_dirty(self, drive_letter: str = "C:") -> Dict[str, Any]:
        """Checks if a drive has the dirty bit set (corrupted volume flag)."""
        try:
            cmd = ["fsutil", "dirty", "query", drive_letter]
            res = subprocess.run(cmd, capture_output=True, text=True, timeout=10)
            is_dirty = "is dirty" in res.stdout.lower()
            return {
                "success": True,
                "drive": drive_letter,
                "is_dirty": is_dirty,
                "message": f"Drive {drive_letter} is clean and healthy." if not is_dirty else f"Warning: Drive {drive_letter} is marked dirty. A disk check is recommended.",
            }
        except Exception as e:
            return {"success": False, "message": str(e)}

    def get_recent_event_errors(self, limit: int = 5) -> List[Dict[str, Any]]:
        """Queries recent Critical and Error entries from the Windows System Event Log."""
        results = []
        try:
            ps_cmd = (
                f"Get-WinEvent -FilterHashtable @{{LogName='System'; Level=1,2}} -MaxEvents {limit} -ErrorAction SilentlyContinue | "
                "Select-Object TimeCreated, ProviderName, Message | ConvertTo-Json"
            )
            res = subprocess.run(["powershell.exe", "-Command", ps_cmd], capture_output=True, text=True, timeout=15)
            if res.returncode == 0 and res.stdout.strip():
                import json
                data = json.loads(res.stdout)
                if isinstance(data, dict):
                    data = [data]
                for item in data:
                    results.append({
                        "time": str(item.get("TimeCreated", ""))[:19],
                        "source": str(item.get("ProviderName", "")),
                        "message": str(item.get("Message", "")).strip().replace("\r\n", " ")[:160],
                    })
        except Exception:
            pass
        return results

    def generate_battery_report(self) -> Dict[str, Any]:
        """Generates an official Windows battery report HTML in user's temp folder."""
        try:
            output_path = Path(os.environ.get("TEMP", ".")) / "battery_report.html"
            cmd = f'powercfg /batteryreport /output "{output_path}"'
            res = subprocess.run(cmd, shell=True, capture_output=True, text=True, timeout=20)
            if res.returncode == 0 and output_path.exists():
                return {
                    "success": True,
                    "file_path": str(output_path),
                    "message": f"Battery report generated successfully at {output_path.name}",
                }
            return {"success": False, "message": "No battery detected or powercfg failed."}
        except Exception as e:
            return {"success": False, "message": f"Failed to generate battery report: {e}"}

    def get_integrity_recommendations(self) -> List[Dict[str, Any]]:
        """Returns standard recommendations for Windows file system integrity."""
        return [
            {
                "title": "System File Checker (SFC)",
                "command": "sfc /scannow",
                "description": "Scans all protected system files and replaces corrupted files with a cached copy.",
                "requires_admin": True,
            },
            {
                "title": "DISM Component Store Repair",
                "command": "DISM.exe /Online /Cleanup-image /Restorehealth",
                "description": "Repairs Windows Component Store corruption using Windows Update as the repair source.",
                "requires_admin": True,
            },
        ]


health_diagnostics = HealthDiagnostics()
