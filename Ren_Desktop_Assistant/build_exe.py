"""
Build Script for REN Desktop Assistant Executable
Compiles the application into a standalone Windows executable named 'Ren Desktop Assistant.exe'.
"""

import os
import sys
import shutil
import subprocess
from pathlib import Path

# Fix Windows console encoding if needed
if hasattr(sys.stdout, "reconfigure"):
    try:
        sys.stdout.reconfigure(encoding="utf-8", errors="replace")
    except Exception:
        pass

ASSISTANT_DIR = Path(__file__).resolve().parent
MAIN_FILE = ASSISTANT_DIR / "main.py"
DIST_DIR = ASSISTANT_DIR / "dist"
BUILD_DIR = ASSISTANT_DIR / "build"
EXE_NAME = "Ren Desktop Assistant"


def build():
    print("=" * 60)
    print("[*] Building REN Desktop Assistant Executable...")
    print(f"[*] Source: {MAIN_FILE}")
    print(f"[*] Output: {DIST_DIR / (EXE_NAME + '.exe')}")
    print("=" * 60)

    cmd = [
        sys.executable,
        "-m",
        "PyInstaller",
        "--noconfirm",
        "--onefile",
        "--windowed",
        "--name",
        EXE_NAME,
        "--distpath",
        str(DIST_DIR),
        "--workpath",
        str(BUILD_DIR),
        "--specpath",
        str(ASSISTANT_DIR),
        "--hidden-import",
        "psutil",
        "--hidden-import",
        "powerplan",
        "--hidden-import",
        "tkinter",
        "--hidden-import",
        "tkinter.ttk",
        "--hidden-import",
        "tkinter.filedialog",
        "--hidden-import",
        "tkinter.messagebox",
        "--clean",
        str(MAIN_FILE),
    ]

    print("[*] Running PyInstaller command...")
    res = subprocess.run(cmd, cwd=str(ASSISTANT_DIR))

    if res.returncode == 0:
        built_exe = DIST_DIR / (EXE_NAME + ".exe")
        target_root_exe = ASSISTANT_DIR / (EXE_NAME + ".exe")
        if built_exe.exists():
            shutil.copy2(built_exe, target_root_exe)
            print("=" * 60)
            print("[SUCCESS] BUILD COMPLETE!")
            print("Standalone Executable created at:")
            print(f"  1) {built_exe}")
            print(f"  2) {target_root_exe}")
            size_mb = round(target_root_exe.stat().st_size / (1024 * 1024), 2)
            print(f"Binary Size: {size_mb} MB")
            print("=" * 60)
            return True
    else:
        print("[ERROR] Build failed with exit code:", res.returncode)
        return False


if __name__ == "__main__":
    build()
