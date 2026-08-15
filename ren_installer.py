# Ren AI Installer
# Installs all required components for Ren AI and launches Ren.
#
# Requirements:
# - Windows 10/11
# - Internet connection
#
# Components:
# Git
# Python 3.10
# Ollama
# Qwen2.5-Coder 3B
# REN-AI repository
# Python dependencies

import os
import shutil
import subprocess
import sys
import time
import urllib.request
from tkinter import Tk, filedialog


# ============================================================
# CONFIGURATION
# ============================================================

REPO_URL = "https://github.com/takumicodes/REN-AI.git"

PYTHON_310_URL = (
    "https://www.python.org/ftp/python/3.10.11/"
    "python-3.10.11-amd64.exe"
)

OLLAMA_API_TAGS = "http://127.0.0.1:11434/api/tags"

OLLAMA_MODEL = "qwen2.5-coder:3b"

target_project_path = None


# ============================================================
# UTILITY FUNCTIONS
# ============================================================

def refresh_environment():
    """
    Refresh the current Python process PATH from Windows'
    machine + user environment variables.
    """

    if sys.platform != "win32":
        return

    try:
        import winreg

        machine_path = ""
        user_path = ""

        try:
            with winreg.OpenKey(
                winreg.HKEY_LOCAL_MACHINE,
                r"SYSTEM\CurrentControlSet\Control\Session Manager\Environment"
            ) as key:
                machine_path, _ = winreg.QueryValueEx(key, "Path")
        except Exception:
            pass

        try:
            with winreg.OpenKey(
                winreg.HKEY_CURRENT_USER,
                r"Environment"
            ) as key:
                user_path, _ = winreg.QueryValueEx(key, "Path")
        except Exception:
            pass

        os.environ["PATH"] = (
            machine_path
            + os.pathsep
            + user_path
        )

    except Exception:
        pass


def run_live_command(command, error_message):
    """
    Run a command while displaying its output live.
    Returns True when the command exits successfully.
    """

    try:
        print(f" -> Running: {' '.join(command) if isinstance(command, list) else command}")

        process = subprocess.Popen(
            command,
            stdout=subprocess.PIPE,
            stderr=subprocess.STDOUT,
            text=True,
            encoding="utf-8",
            errors="ignore",
            shell=False
        )

        if process.stdout:
            for line in process.stdout:
                line = line.strip()

                if line:
                    print(f"    {line}", flush=True)

        return_code = process.wait()

        if return_code == 0:
            return True

        print(
            f" -> ❌ Command failed with exit code {return_code}",
            file=sys.stderr
        )
        return False

    except Exception as e:
        print(f" -> {error_message}: {e}", file=sys.stderr)
        return False


def command_exists(command):
    """Check whether a command exists in PATH."""

    refresh_environment()
    return shutil.which(command) is not None


# ============================================================
# WINDOWS CHECK
# ============================================================

def check_windows():
    print("\n[1/11] Checking Windows compatibility...")

    if sys.platform != "win32":
        print(" -> ❌ Ren Installer only supports Windows.")
        sys.exit(1)

    if not command_exists("winget"):
        print(
            " -> ❌ winget was not found.\n"
            " -> Please install/update App Installer from Microsoft."
        )
        sys.exit(1)

    print(" -> ✅ Windows and winget detected.")


# ============================================================
# GIT
# ============================================================

def install_git():
    print("\n[2/11] Checking Git...")

    if command_exists("git"):
        print(" -> ✅ Git is already installed.")
        return

    print(" -> Git not found.")
    print(" -> Installing Git through winget...")

    command = [
        "winget",
        "install",
        "--id",
        "Git.Git",
        "--exact",
        "--silent",
        "--accept-source-agreements",
        "--accept-package-agreements"
    ]

    if not run_live_command(
        command,
        "❌ Git installation failed"
    ):
        sys.exit(1)

    refresh_environment()

    if not command_exists("git"):
        print(" -> ❌ Git installation completed but Git was not found.")
        sys.exit(1)

    print(" -> ✅ Git installed successfully.")


# ============================================================
# PYTHON 3.10
# ============================================================

def python_310_exists():
    """Check whether Python 3.10 is available through the launcher."""

    try:
        result = subprocess.run(
            ["py", "-3.10", "--version"],
            capture_output=True,
            text=True
        )

        version = result.stdout.strip() or result.stderr.strip()

        return (
            result.returncode == 0
            and version.startswith("Python 3.10")
        )

    except Exception:
        return False


def install_python_310():
    print("\n[3/11] Checking Python 3.10...")

    if python_310_exists():
        result = subprocess.run(
            ["py", "-3.10", "--version"],
            capture_output=True,
            text=True
        )

        print(f" -> ✅ {result.stdout.strip()}")
        return

    print(" -> Python 3.10 not found.")
    print(" -> Downloading official Python 3.10.11 installer...")

    temp_dir = os.environ.get("TEMP", os.environ.get("TMP", "."))
    installer_path = os.path.join(
        temp_dir,
        "python-3.10.11-amd64.exe"
    )

    try:
        download_python(installer_path)

        print("\n -> Installing Python 3.10...")
        print(" -> This may take a moment.")

        command = [
            installer_path,
            "/quiet",
            "InstallAllUsers=1",
            "PrependPath=1",
            "Include_pip=1"
        ]

        result = subprocess.run(
            command,
            check=False
        )

        if result.returncode != 0:
            print(
                f" -> ❌ Python installer returned "
                f"exit code {result.returncode}"
            )
            sys.exit(1)

        refresh_environment()

        if not python_310_exists():
            print(
                " -> ❌ Python installation finished, "
                "but Python 3.10 could not be detected."
            )
            sys.exit(1)

        print(" -> ✅ Python 3.10 installed successfully.")

    except Exception as e:
        print(
            f" -> ❌ Python installation failed: {e}",
            file=sys.stderr
        )
        sys.exit(1)


def download_python(destination):
    """Download Python with a simple progress display."""

    try:
        with urllib.request.urlopen(
            PYTHON_310_URL,
            timeout=30
        ) as response:

            total_size = response.headers.get("Content-Length")

            if total_size:
                total_size = int(total_size)

            downloaded = 0
            block_size = 256 * 1024

            with open(destination, "wb") as output:

                while True:
                    data = response.read(block_size)

                    if not data:
                        break

                    output.write(data)
                    downloaded += len(data)

                    if total_size:
                        percent = int(
                            downloaded * 100 / total_size
                        )

                        mb_done = downloaded / (1024 * 1024)
                        mb_total = total_size / (1024 * 1024)

                        sys.stdout.write(
                            f"\r    Downloading Python: "
                            f"{percent}% "
                            f"({mb_done:.1f}/{mb_total:.1f} MB)"
                        )

                        sys.stdout.flush()

        print()

    except Exception:
        if os.path.exists(destination):
            os.remove(destination)

        raise


# ============================================================
# OLLAMA
# ============================================================

def install_ollama():
    print("\n[4/11] Checking Ollama...")

    if command_exists("ollama"):
        print(" -> ✅ Ollama is already installed.")
        return

    print(" -> Ollama not found.")
    print(" -> Installing Ollama through winget...")

    command = [
        "winget",
        "install",
        "--id",
        "Ollama.Ollama",
        "--exact",
        "--silent",
        "--accept-source-agreements",
        "--accept-package-agreements"
    ]

    if not run_live_command(
        command,
        "❌ Ollama installation failed"
    ):
        sys.exit(1)

    refresh_environment()

    if not command_exists("ollama"):
        print(
            " -> ❌ Ollama installation completed "
            "but executable was not found."
        )
        sys.exit(1)

    print(" -> ✅ Ollama installed successfully.")


# ============================================================
# OLLAMA SERVER
# ============================================================

def ollama_api_ready():
    """Check whether Ollama's local API is responding."""

    try:
        with urllib.request.urlopen(
            OLLAMA_API_TAGS,
            timeout=2
        ) as response:

            return response.status == 200

    except Exception:
        return False


def wait_for_ollama(timeout=45):
    print("\n[5/11] Starting Ollama service...")

    if ollama_api_ready():
        print(" -> ✅ Ollama API is already running.")
        return True

    print(" -> Ollama API is not running.")
    print(" -> Starting Ollama...")

    try:
        subprocess.Popen(
            ["ollama", "serve"],
            stdout=subprocess.DEVNULL,
            stderr=subprocess.DEVNULL,
            creationflags=subprocess.CREATE_NO_WINDOW
        )
    except Exception as e:
        print(f" -> ❌ Could not start Ollama: {e}")
        return False

    start_time = time.time()

    while time.time() - start_time < timeout:

        if ollama_api_ready():
            print("\n -> ✅ Ollama API is online.")
            return True

        sys.stdout.write(".")
        sys.stdout.flush()

        time.sleep(1)

    print()
    print(
        " -> ❌ Ollama did not respond within "
        f"{timeout} seconds."
    )

    return False


# ============================================================
# QWEN MODEL
# ============================================================

def install_qwen():
    print(
        "\n[6/11] Installing "
        "Qwen2.5-Coder 3B..."
    )

    if not command_exists("ollama"):
        print(" -> ❌ Ollama command not found.")
        sys.exit(1)

    command = [
        "ollama",
        "pull",
        OLLAMA_MODEL
    ]

    if not run_live_command(
        command,
        "❌ Qwen model installation failed"
    ):
        sys.exit(1)

    # Verify model through API
    try:
        with urllib.request.urlopen(
            OLLAMA_API_TAGS,
            timeout=5
        ) as response:

            data = response.read().decode(
                "utf-8",
                errors="ignore"
            )

        if OLLAMA_MODEL in data:
            print(
                f" -> ✅ {OLLAMA_MODEL} verified."
            )
        else:
            print(
                " -> ❌ Model pull finished, "
                "but the model was not found."
            )
            sys.exit(1)

    except Exception as e:
        print(
            f" -> ❌ Could not verify model: {e}"
        )
        sys.exit(1)


# ============================================================
# CLONE REN
# ============================================================

def choose_install_directory():
    print("\n[7/11] Selecting Ren installation directory...")

    root = Tk()
    root.withdraw()
    root.attributes("-topmost", True)

    destination = filedialog.askdirectory(
        title="Select folder for Ren AI"
    )

    root.destroy()

    if destination:
        return destination

    # Automatic fallback
    user_profile = os.environ.get(
        "USERPROFILE",
        os.path.expanduser("~")
    )

    fallback = os.path.join(
        user_profile,
        "RenAI"
    )

    os.makedirs(
        fallback,
        exist_ok=True
    )

    print(
        f" -> No folder selected.\n"
        f" -> Using: {fallback}"
    )

    return fallback


def clone_ren():
    global target_project_path

    destination_dir = choose_install_directory()

    target_project_path = os.path.join(
        destination_dir,
        "REN-AI"
    )

    if os.path.exists(target_project_path):
        print(
            f" -> Ren directory already exists:\n"
            f"    {target_project_path}"
        )
        return

    print()
    print(" -> Downloading Ren AI from GitHub...")

    command = [
        "git",
        "clone",
        REPO_URL,
        target_project_path
    ]

    if not run_live_command(
        command,
        "❌ Ren repository download failed"
    ):
        sys.exit(1)

    print(" -> ✅ Ren repository downloaded.")


# ============================================================
# PYTHON DEPENDENCIES
# ============================================================

def install_dependencies():
    print("\n[8/11] Installing Ren Python dependencies...")

    requirements = os.path.join(
        target_project_path,
        "requirements.txt"
    )

    if not os.path.isfile(requirements):
        print(
            " -> ⚠️ requirements.txt was not found."
        )
        return

    print(" -> Upgrading pip...")

    run_live_command(
        [
            "py",
            "-3.10",
            "-m",
            "pip",
            "install",
            "--upgrade",
            "pip"
        ],
        "⚠️ pip upgrade failed"
    )

    print(" -> Installing requirements...")

    command = [
        "py",
        "-3.10",
        "-m",
        "pip",
        "install",
        "-r",
        requirements
    ]

    if not run_live_command(
        command,
        "❌ Dependency installation failed"
    ):
        sys.exit(1)

    print(" -> ✅ Ren dependencies installed.")


# ============================================================
# REN CONFIGURATION
# ============================================================

def configure_ren():
    print("\n[9/11] Configuring Ren → Ollama...")

    env_file = os.path.join(
        target_project_path,
        ".env"
    )

    try:
        with open(
            env_file,
            "w",
            encoding="utf-8"
        ) as file:

            file.write(
                "OLLAMA_API_BASE="
                "http://127.0.0.1:11434\n"
            )

            file.write(
                f"MODEL_NAME={OLLAMA_MODEL}\n"
            )

        print(" -> ✅ Ren configuration created.")

    except Exception as e:
        print(
            f" -> ❌ Could not create .env: {e}"
        )
        sys.exit(1)


# ============================================================
# FINAL VERIFICATION
# ============================================================

def verify_installation():
    print("\n[10/11] Verifying installation...")

    problems = []

    refresh_environment()

    if not command_exists("git"):
        problems.append("Git")

    if not python_310_exists():
        problems.append("Python 3.10")

    if not command_exists("ollama"):
        problems.append("Ollama")

    if not ollama_api_ready():
        problems.append("Ollama API")

    requirements = os.path.join(
        target_project_path,
        "requirements.txt"
    )

    if not os.path.isfile(requirements):
        problems.append("requirements.txt")

    gui_file = os.path.join(
        target_project_path,
        "gui.py"
    )

    if not os.path.isfile(gui_file):
        problems.append("gui.py")

    if problems:
        print()
        print(" -> ❌ Verification failed.")

        for problem in problems:
            print(f"    - {problem}")

        sys.exit(1)

    print(" -> ✅ All major components verified.")


# ============================================================
# LAUNCH REN
# ============================================================

def launch_ren():
    print("\n[11/11] Launching Ren AI...")

    gui_path = os.path.join(
        target_project_path,
        "gui.py"
    )

    if not os.path.isfile(gui_path):
        print(
            " -> ❌ gui.py was not found."
        )
        sys.exit(1)

    try:
        subprocess.Popen(
            [
                "py",
                "-3.10",
                gui_path
            ],
            cwd=target_project_path
        )

        print()
        print("==============================================")
        print("          🚀 REN AI IS STARTING              ")
        print("==============================================")

    except Exception as e:
        print(
            f" -> ❌ Could not launch Ren: {e}",
            file=sys.stderr
        )
        sys.exit(1)


# ============================================================
# MAIN
# ============================================================

def main():

    print()
    print("==============================================")
    print("        WELCOME TO THE REN AI INSTALLER       ")
    print("==============================================")
    print()
    print("This installer will configure:")
    print("  • Git")
    print("  • Python 3.10")
    print("  • Ollama")
    print("  • Qwen2.5-Coder 3B")
    print("  • Ren AI")
    print()

    time.sleep(1)

    check_windows()

    install_git()

    install_python_310()

    install_ollama()

    if not wait_for_ollama():
        sys.exit(1)

    install_qwen()

    clone_ren()

    install_dependencies()

    configure_ren()

    verify_installation()

    launch_ren()

    print()
    print("==============================================")
    print("       REN AI INSTALLATION COMPLETE 🚀       ")
    print("==============================================")


if __name__ == "__main__":
    main()