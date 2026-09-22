"""
Advanced Storage Analyzer Engine for REN-AI Windows Control Center
Provides:
- Detailed breakdown of all connected local drives (Total, Free, Used, % Used).
- Hierarchical folder and subdirectory size analysis.
- File type distribution (Archives, Media, Code, Installers, Documents).
- Top largest files and recently modified large files detector.
- Guaranteed 100% read-only: never deletes files without explicit user action through the Action system.
"""

import os
import time
import psutil
from pathlib import Path
from typing import List, Dict, Any, Optional

try:
    from .logger import logger
except ImportError:
    try:
        from logger import logger
    except ImportError:
        import logging
        logger = logging.getLogger("RenAssistant")


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
    """Read-only inspector for disk drives, directory hierarchies, and file distributions."""

    def __init__(self):
        self.read_only = True  # Strict safety guarantee

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
            except Exception as e:
                logger.debug(f"Could not read partition {part.mountpoint}: {e}")
                continue
        return results

    def analyze_directory(self, target_dir: str, top_n: int = 15) -> Dict[str, Any]:
        """
        Scans target_dir and produces:
        - Top largest folders
        - Top largest files
        - File type distribution (extensions and sizes)
        - Recently modified large files (>10MB modified in last 30 days)
        """
        target = Path(target_dir)
        if not target.exists() or not target.is_dir():
            return {"success": False, "message": f"Path '{target_dir}' does not exist or is not a directory."}

        folders = []
        files = []
        ext_distribution: Dict[str, Dict[str, Any]] = {}
        recent_large_files = []
        now = time.time()
        thirty_days_ago = now - (30 * 86400)

        total_scanned_bytes = 0

        try:
            with os.scandir(str(target)) as it:
                for entry in it:
                    try:
                        if entry.is_file(follow_symlinks=False):
                            stat = entry.stat()
                            sz = stat.st_size
                            mtime = stat.st_mtime
                            ext = Path(entry.name).suffix.lower() or "no_ext"

                            total_scanned_bytes += sz

                            # Track extensions
                            if ext not in ext_distribution:
                                ext_distribution[ext] = {"count": 0, "size_bytes": 0}
                            ext_distribution[ext]["count"] += 1
                            ext_distribution[ext]["size_bytes"] += sz

                            file_info = {
                                "name": entry.name,
                                "path": entry.path,
                                "size_bytes": sz,
                                "size_mb": round(sz / (1024 * 1024), 2),
                                "modified": time.strftime("%Y-%m-%d %H:%M", time.localtime(mtime)),
                            }
                            files.append(file_info)

                            # Recent large files check (>10MB, last 30 days)
                            if sz > (10 * 1024 * 1024) and mtime > thirty_days_ago:
                                recent_large_files.append(file_info)

                        elif entry.is_dir(follow_symlinks=False):
                            folder_size = 0
                            file_count = 0
                            try:
                                for root, _, filenames in os.walk(entry.path):
                                    for f in filenames:
                                        try:
                                            fp = os.path.join(root, f)
                                            s = os.path.getsize(fp)
                                            folder_size += s
                                            file_count += 1
                                        except (PermissionError, OSError):
                                            pass
                            except (PermissionError, OSError):
                                pass

                            total_scanned_bytes += folder_size

                            folders.append({
                                "name": entry.name,
                                "path": entry.path,
                                "size_bytes": folder_size,
                                "size_mb": round(folder_size / (1024 * 1024), 2),
                                "file_count": file_count,
                            })
                    except (PermissionError, OSError):
                        continue
        except Exception as e:
            logger.warning(f"Error scanning directory {target_dir}: {e}")
            return {"success": False, "message": str(e)}

        folders.sort(key=lambda x: x["size_bytes"], reverse=True)
        files.sort(key=lambda x: x["size_bytes"], reverse=True)
        recent_large_files.sort(key=lambda x: x["size_bytes"], reverse=True)

        # Format extension distribution
        ext_list = [
            {
                "extension": ext,
                "count": data["count"],
                "size_mb": round(data["size_bytes"] / (1024 * 1024), 2),
            }
            for ext, data in ext_distribution.items()
        ]
        ext_list.sort(key=lambda x: x["size_mb"], reverse=True)

        return {
            "success": True,
            "target_dir": target_dir,
            "total_scanned_mb": round(total_scanned_bytes / (1024 * 1024), 2),
            "top_folders": folders[:top_n],
            "top_files": files[:top_n],
            "type_distribution": ext_list[:10],
            "recent_large_files": recent_large_files[:top_n],
            "read_only": True,
        }


storage_analyzer = StorageAnalyzer()
