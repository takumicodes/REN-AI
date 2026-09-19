"""
System Restore Management Engine for REN-AI Windows Control Center
Provides:
- Enumeration of existing Windows System Restore Points.
- On-demand System Restore point creation before deep modifications.
- System Protection status inspection.
"""

import subprocess
import json
from typing import List, Dict, Any


class RestoreCenter:
    """Manages Windows System Restore points and safety checkpoints."""

    def get_restore_points(self) -> List[Dict[str, Any]]:
        """Queries Windows for existing System Restore points."""
        results = []
        try:
            ps_cmd = (
                "Get-ComputerRestorePoint -ErrorAction SilentlyContinue | "
                "Select-Object SequenceNumber, Description, CreationTime, RestorePointType | "
                "ConvertTo-Json"
            )
            res = subprocess.run(["powershell.exe", "-Command", ps_cmd], capture_output=True, text=True, timeout=15)
            if res.returncode == 0 and res.stdout.strip():
                data = json.loads(res.stdout)
                if isinstance(data, dict):
                    data = [data]
                for item in data:
                    results.append({
                        "seq": item.get("SequenceNumber"),
                        "description": item.get("Description"),
                        "creation_time": str(item.get("CreationTime", "")),
                    })
        except Exception:
            pass
        return results

    def create_restore_point(self, description: str = "REN-AI System Checkpoint") -> Dict[str, Any]:
        """
        Creates a new Windows System Restore point. Requires Administrator privileges.
        """
        try:
            ps_cmd = f'Checkpoint-Computer -Description "{description}" -RestorePointType "MODIFY_SETTINGS"'
            res = subprocess.run(
                ["powershell.exe", "-Command", ps_cmd],
                capture_output=True,
                text=True,
                timeout=45,
            )
            if res.returncode == 0:
                return {
                    "success": True,
                    "message": f"Successfully created System Restore point: '{description}'.",
                }
            return {
                "success": False,
                "message": res.stderr.strip() or "Failed to create restore point. Ensure System Protection is enabled and run as Administrator.",
            }
        except Exception as e:
            return {"success": False, "message": f"Restore point error: {e}"}


restore_center = RestoreCenter()
