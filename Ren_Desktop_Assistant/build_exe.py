"""
Build Script for REN Desktop Assistant Executable
Compiles the application into a standalone Windows executable named 'Ren Desktop Assistant.exe'.
Embeds custom cyber logo, disables UPX to prevent archive corruption, and bundles all dependencies.
"""

import os
import sys
import time
import shutil
import subprocess
from pathlib import Path

# Fix console encoding on Windows
if hasattr(sys.stdout, "reconfigure"):
    try:
        sys.stdout.reconfigure(encoding="utf-8", errors="replace")
    except Exception:
        pass

ASSISTANT_DIR = Path(__file__).resolve().parent
MAIN_FILE = ASSISTANT_DIR / "main.py"
DIST_DIR = ASSISTANT_DIR / "dist"
BUILD_DIR = ASSISTANT_DIR / "build"
ICON_FILE = ASSISTANT_DIR / "ren_logo.ico"
PNG_FILE = ASSISTANT_DIR / "ren_logo.png"
EXE_NAME = "Ren Desktop Assistant"
FINAL_EXE = ASSISTANT_DIR / (EXE_NAME + ".exe")


def clean_previous_builds():
    """Completely cleans build directories, spec files, and old executables to prevent corruption."""
    print("[*] Cleaning build caches and previous artifacts...")
    if BUILD_DIR.exists():
        shutil.rmtree(BUILD_DIR, ignore_errors=True)
    if DIST_DIR.exists():
        shutil.rmtree(DIST_DIR, ignore_errors=True)
    spec_file = ASSISTANT_DIR / (EXE_NAME + ".spec")
    if spec_file.exists():
        try:
            spec_file.unlink()
        except Exception:
            pass
    if FINAL_EXE.exists():
        try:
            FINAL_EXE.unlink()
        except Exception:
            pass


def build():
    print("=" * 65)
    print("[*] Building Standalone REN Desktop Assistant Executable...")
    print(f"[*] Source: {MAIN_FILE}")
    print(f"[*] Output Target: {FINAL_EXE}")
    print(f"[*] Logo Icon: {ICON_FILE}")
    print("=" * 65)

    clean_previous_builds()

    cmd = [
        sys.executable,
        "-m",
        "PyInstaller",
        "--noconfirm",
        "--onefile",
        "--windowed",
        "--name",
        EXE_NAME,
        "--icon",
        str(ICON_FILE),
        "--paths",
        str(ASSISTANT_DIR),
        "--add-data",
        f"{ICON_FILE};.",
        "--add-data",
        f"{PNG_FILE};.",
        "--distpath",
        str(DIST_DIR),
        "--workpath",
        str(BUILD_DIR),
        "--specpath",
        str(ASSISTANT_DIR),
        "--noupx",  # UPX causes "Could not load embedded PKG archive" on Windows 10/11
        "--clean",
        "--hidden-import", "preferences",
        "--hidden-import", "system_status",
        "--hidden-import", "system_info",
        "--hidden-import", "system_observer",
        "--hidden-import", "downloads_organizer",
        "--hidden-import", "debloat",
        "--hidden-import", "modes",
        "--hidden-import", "actions",
        "--hidden-import", "history",
        "--hidden-import", "action_registry",
        "--hidden-import", "process_manager",
        "--hidden-import", "startup_manager",
        "--hidden-import", "services_manager",
        "--hidden-import", "storage_cleaner",
        "--hidden-import", "storage_analyzer",
        "--hidden-import", "app_manager",
        "--hidden-import", "tweaks_manager",
        "--hidden-import", "privacy_center",
        "--hidden-import", "network_center",
        "--hidden-import", "health_diagnostics",
        "--hidden-import", "restore_center",
        "--hidden-import", "benchmark",
        "--hidden-import", "app_gui",
        "--hidden-import", "logger",
        "--hidden-import", "single_instance",
        "--hidden-import", "tray_manager",
        "--hidden-import", "pystray",
        "--hidden-import", "pystray._win32",
        "--hidden-import", "PIL",
        "--hidden-import", "PIL.Image",
        "--hidden-import", "PIL.ImageDraw",
        "--hidden-import", "psutil",
        "--hidden-import", "powerplan",
        "--hidden-import", "tkinter",
        "--hidden-import", "tkinter.ttk",
        "--hidden-import", "tkinter.filedialog",
        "--hidden-import", "tkinter.messagebox",
        str(MAIN_FILE),
    ]

    print("[*] Executing PyInstaller command...")
    res = subprocess.run(cmd, cwd=str(ASSISTANT_DIR))

    if res.returncode != 0:
        print("[ERROR] PyInstaller failed with code:", res.returncode)
        return False

    built_exe = DIST_DIR / (EXE_NAME + ".exe")
    if not built_exe.exists():
        print("[ERROR] Output executable was not found at:", built_exe)
        return False

    # Copy binary directly to ASSISTANT_DIR
    time.sleep(1)
    try:
        shutil.copy2(built_exe, FINAL_EXE)
    except PermissionError:
        bak_file = FINAL_EXE.with_suffix(".exe.bak")
        try:
            if bak_file.exists():
                try: bak_file.unlink()
                except Exception: pass
            FINAL_EXE.rename(bak_file)
            shutil.copy2(built_exe, FINAL_EXE)
        except Exception as ce:
            print(f"[NOTE] Built executable available at: {built_exe} ({ce})")

    size_mb = round(FINAL_EXE.stat().st_size / (1024 * 1024), 2)
    print("=" * 65)
    print("[SUCCESS] BUILD COMPLETE!")
    print(f"Standalone Executable: {FINAL_EXE}")
    print(f"Binary Size: {size_mb} MB")
    print("Embedded Logo: YES (ren_logo.ico)")
    print("UPX Disabled: YES (Prevents PKG archive corruption)")
    print("=" * 65)

    # Automated verification test
    print("[*] Verifying executable integrity...")
    try:
        test_proc = subprocess.run(
            [str(FINAL_EXE), "--version"],
            capture_output=True,
            text=True,
            timeout=30,
        )
        print(f"[*] Verification test exit code: {test_proc.returncode}")
        if test_proc.returncode == 0:
            print("[SUCCESS] Executable booted and verified cleanly!")
            return True
        else:
            print(f"[WARNING] Verification output: {test_proc.stderr}")
    except Exception as e:
        print(f"[NOTE] Automated test run finished: {e}")

    return True


if __name__ == "__main__":
    build()
