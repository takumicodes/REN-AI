"""
Downloads Folder Organizer for REN Desktop Assistant
Safely organizes clutter in the Windows Downloads directory.
Features:
- Human-driven safety: Dry-run preview, non-destructive collision renaming, recent-download protection.
- Full Undo / Rollback history.
- Zero AI slop: predictable, rule-based file categorization.
"""

import os
import shutil
import time
import json
from pathlib import Path
from typing import Dict, List, Tuple, Any, Optional

CATEGORIES: Dict[str, List[str]] = {
    "Code_and_Dev": [
        ".py", ".js", ".ts", ".jsx", ".tsx", ".html", ".css", ".json", ".sql",
        ".rs", ".go", ".cpp", ".c", ".h", ".cs", ".java", ".sh", ".bat", ".ps1",
        ".ipynb", ".yaml", ".yml", ".toml", ".env", ".xml"
    ],
    "Documents": [
        ".pdf", ".docx", ".doc", ".xlsx", ".xls", ".pptx", ".ppt", ".txt",
        ".csv", ".md", ".epub", ".rtf", ".odt", ".ods", ".odp"
    ],
    "Images": [
        ".png", ".jpg", ".jpeg", ".gif", ".bmp", ".svg", ".webp", ".ico",
        ".psd", ".ai", ".tiff", ".raw"
    ],
    "Media": [
        ".mp4", ".mkv", ".avi", ".mov", ".wmv", ".flv", ".webm",
        ".mp3", ".wav", ".flac", ".aac", ".ogg", ".m4a"
    ],
    "Archives": [
        ".zip", ".rar", ".7z", ".tar", ".gz", ".bz2", ".xz"
    ],
    "Installers": [
        ".exe", ".msi", ".iso", ".dmg", ".pkg"
    ],
}

HISTORY_FILE = Path(__file__).parent / "downloads_history.json"


class DownloadsOrganizer:
    """Manages clean and safe organization of the user's Downloads directory."""

    def __init__(self, downloads_path: Optional[Path] = None):
        if downloads_path:
            self.folder = Path(downloads_path)
        else:
            self.folder = Path.home() / "Downloads"

    def get_category_for_ext(self, ext: str) -> Optional[str]:
        """Maps file extension (e.g. '.pdf') to category folder name."""
        ext = ext.lower()
        for cat, ext_list in CATEGORIES.items():
            if ext in ext_list:
                return cat
        return None

    def scan_unorganized(self, ignore_recent_minutes: int = 15) -> List[Path]:
        """
        Finds loose files in the root of the Downloads folder.
        Skips:
        - Subdirectories
        - Temporary files (.crdownload, .tmp, .part)
        - Files modified within `ignore_recent_minutes` (in-flight or newly saved)
        """
        if not self.folder.exists():
            return []

        unorganized = []
        now = time.time()
        recent_threshold = ignore_recent_minutes * 60

        temp_extensions = {".crdownload", ".tmp", ".part", ".download"}

        try:
            for item in self.folder.iterdir():
                if not item.is_file():
                    continue

                ext = item.suffix.lower()
                if ext in temp_extensions:
                    continue

                # Check if file has a known category
                if not self.get_category_for_ext(ext):
                    continue

                # Protect freshly modified files
                try:
                    mtime = item.stat().st_mtime
                    if (now - mtime) < recent_threshold:
                        continue
                except OSError:
                    continue

                unorganized.append(item)
        except Exception:
            pass

        return unorganized

    def preview_organization(self, ignore_recent_minutes: int = 15) -> Dict[str, Any]:
        """Dry-run preview of planned file movements without making changes."""
        files = self.scan_unorganized(ignore_recent_minutes=ignore_recent_minutes)
        plan: Dict[str, List[Dict[str, str]]] = {cat: [] for cat in CATEGORIES.keys()}
        total_size = 0

        for f in files:
            cat = self.get_category_for_ext(f.suffix)
            if cat:
                size = f.stat().st_size if f.exists() else 0
                total_size += size
                plan[cat].append({
                    "name": f.name,
                    "size_mb": round(size / (1024 * 1024), 2),
                    "source": str(f),
                    "target_dir": str(self.folder / cat),
                })

        return {
            "total_files": len(files),
            "total_size_mb": round(total_size / (1024 * 1024), 2),
            "categories": {k: v for k, v in plan.items() if v},
        }

    def _get_unique_target(self, target_dir: Path, filename: str) -> Path:
        """Finds safe target path, appending counter if collision occurs."""
        target = target_dir / filename
        if not target.exists():
            return target

        stem = target.stem
        suffix = target.suffix
        counter = 1
        while target.exists():
            target = target_dir / f"{stem} ({counter}){suffix}"
            counter += 1
        return target

    def organize(self, dry_run: bool = False, ignore_recent_minutes: int = 15) -> Dict[str, Any]:
        """
        Moves unorganized files into categorized subfolders.
        Records move history for instant rollback capability.
        """
        files = self.scan_unorganized(ignore_recent_minutes=ignore_recent_minutes)
        if dry_run or not files:
            return self.preview_organization(ignore_recent_minutes=ignore_recent_minutes)

        moved_records = []
        errors = []

        for f in files:
            cat = self.get_category_for_ext(f.suffix)
            if not cat:
                continue

            target_dir = self.folder / cat
            try:
                os.makedirs(str(target_dir), exist_ok=True)
                dest = self._get_unique_target(target_dir, f.name)
                src_path_str = str(f)
                dest_path_str = str(dest)

                shutil.move(src_path_str, dest_path_str)
                moved_records.append({
                    "original": src_path_str,
                    "current": dest_path_str,
                    "category": cat,
                    "timestamp": time.time(),
                })
            except Exception as e:
                errors.append({"file": f.name, "error": str(e)})

        # Save to history file for rollback
        if moved_records:
            self._record_history(moved_records)

        return {
            "success": True,
            "moved_count": len(moved_records),
            "errors": errors,
            "moved": moved_records,
        }

    def _record_history(self, records: List[Dict[str, Any]]) -> None:
        """Appends move operation batch to history file."""
        history = []
        if HISTORY_FILE.exists():
            try:
                with open(HISTORY_FILE, "r", encoding="utf-8") as f:
                    history = json.load(f)
            except Exception:
                history = []

        history.append({
            "batch_id": int(time.time()),
            "moves": records,
        })
        # Keep last 10 batches
        history = history[-10:]
        try:
            with open(HISTORY_FILE, "w", encoding="utf-8") as f:
                json.dump(history, f, indent=2)
        except Exception:
            pass

    def undo_last(self) -> Dict[str, Any]:
        """
        Reverses the most recent organization batch, restoring files to original positions.
        """
        if not HISTORY_FILE.exists():
            return {"success": False, "message": "No history available to undo."}

        try:
            with open(HISTORY_FILE, "r", encoding="utf-8") as f:
                history = json.load(f)
        except Exception as e:
            return {"success": False, "message": f"Could not read history: {e}"}

        if not history:
            return {"success": False, "message": "History is empty."}

        last_batch = history.pop()
        restored = 0
        errors = []

        for item in last_batch.get("moves", []):
            curr = Path(item["current"])
            orig = Path(item["original"])
            if curr.exists():
                try:
                    os.makedirs(str(orig.parent), exist_ok=True)
                    shutil.move(str(curr), str(orig))
                    restored += 1
                except Exception as err:
                    errors.append({"file": curr.name, "error": str(err)})

        # Save updated history
        try:
            with open(HISTORY_FILE, "w", encoding="utf-8") as f:
                json.dump(history, f, indent=2)
        except Exception:
            pass

        return {
            "success": True,
            "restored_count": restored,
            "errors": errors,
        }


organizer = DownloadsOrganizer()

if __name__ == "__main__":
    print("=== REN Downloads Organizer Preview ===")
    prev = organizer.preview_organization()
    print(f"Unorganized files found: {prev['total_files']} ({prev['total_size_mb']} MB)")
    for cat, items in prev["categories"].items():
        print(f"  [{cat}]: {len(items)} files")
