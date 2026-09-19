"""
Storage Analyzer Engine for REN-AI Windows Control Center
Provides:
- Detailed breakdown of all connected drives (Total, Free, Used, File System).
- Fast, non-blocking scan of largest directories and files.
- Visual breakdown data for charts and tables.
"""

import os
import psutil
from pathlib import Path
from typing import List, Dict, Any, Optional


class DriveSummary:
    def __init__(self, mountpoint: str, fstype: str, total_gb: float, used_gb: float, free_gb: float, percent: float):
        self.mountpoint = mountpoint
        self.fstype = fstype
        self.total_gb = round(total_gb, 1)
        self.used_gb = round(used_gb, 1)
        self.free_gb = round(free_gb, 1)
        self.percent = round(percent, 1)

    def to_dict(self) -> Dict[str, Any]:
        return {
            "mountpoint": self.mountpoint,
            "fstype": self.fstype,
            "total_gb": self.total_gb,
            "used_gb": self.used_gb,
            "free_gb": self.free_gb,
            "percent": self.percent,
        }


class StorageAnalyzer:
    """Inspects disk drives and analyzes folder size distributions."""

    def get_drives(self) -> List[DriveSummary]:
        """Returns statistics for all available local disk drives."""
        results = []
        for part in psutil.disk_partitions(all=False):
            try:
                usage = psutil.disk_usage(part.mountpoint)
                total_gb = usage.total / (1024**3)
                used_gb = usage.used / (1024**3)
                free_gb = usage.free / (1024**3)
                results.append(
                    DriveSummary(
                        mountpoint=part.mountpoint,
                        fstype=part.fstype,
                        total_gb=total_gb,
                        used_gb=used_gb,
                        free_gb=free_gb,
                        percent=usage.percent,
                    )
                )
            except Exception:
                continue
        return results

    def analyze_largest_items(self, target_dir: str, top_n: int = 15) -> Dict[str, Any]:
        """
        Scans top-level folders and files in target_dir to find space consumers.
        """
        target = Path(target_dir)
        if not target.exists() or not target.is_dir():
            return {"success": False, "message": f"Path '{target_dir}' does not exist or is not a directory."}

        folders = []
        files = []

        try:
            with os.scandir(str(target)) as it:
                for entry in it:
                    try:
                        if entry.is_file(follow_symlinks=False):
                            sz = entry.stat().st_size
                            files.append({
                                "name": entry.name,
                                "path": entry.path,
                                "size_bytes": sz,
                                "size_mb": round(sz / (1024 * 1024), 2),
                            })
                        elif entry.is_dir(follow_symlinks=False):
                            # Calculate top-level subfolder size (capped recursion for speed)
                            folder_size = 0
                            try:
                                for root, _, filenames in os.walk(entry.path):
                                    for f in filenames:
                                        try:
                                            fp = os.path.join(root, f)
                                            folder_size += os.path.getsize(fp)
                                        except Exception:
                                            pass
                            except Exception:
                                pass

                            folders.append({
                                "name": entry.name,
                                "path": entry.path,
                                "size_bytes": folder_size,
                                "size_mb": round(folder_size / (1024 * 1024), 2),
                            })
                    except Exception:
                        continue
        except Exception as e:
            return {"success": False, "message": str(e)}

        folders.sort(key=lambda x: x["size_bytes"], reverse=True)
        files.sort(key=lambda x: x["size_bytes"], reverse=True)

        return {
            "success": True,
            "target_dir": target_dir,
            "top_folders": folders[:top_n],
            "top_files": files[:top_n],
        }


storage_analyzer = StorageAnalyzer()
