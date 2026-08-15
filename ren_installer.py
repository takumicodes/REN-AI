# ============================================================
# REN AI INSTALLER
# Automatically installs:
#   1. Git
#   2. Python 3.10
#   3. Ollama
#   4. Qwen2.5-Coder 3B
#   5. REN-AI
#   6. Python dependencies
#   7. Ren configuration
#   8. Launches Ren
# ============================================================

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
# ENVIRONMENT / PATH
# ============================================================

def refresh_environment():
    """
    Refresh PATH from Windows registry and add common
    Windows executable locations.
    """

    if sys.platform != "win32":
        return

    try:
        import winreg

        machine_path = ""
        user_path = ""

        # Machine PATH
        try:
            with winreg.OpenKey(
                winreg.HKEY_LOCAL_MACHINE,
                r"SYSTEM\CurrentControlSet\Control\Session Manager\Environment"
            ) as key:
                machine_path, _ = winreg.QueryValueEx(
                    key,
                    "Path"
                )
        except Exception:
            pass

        # User PATH
        try:
            with winreg.OpenKey(
                winreg.HKEY_CURRENT_USER,
                r"Environment"
            ) as key:
                user_path, _ = winreg.QueryValueEx(
                    key,
                    "Path"
                )
        except Exception:
            pass

        combined_path = (
            machine_path
            + os.pathsep
            + user_path
        )

        os.environ["PATH"] = combined_path

        # WindowsApps contains winget.exe
        local_app_data = os.environ.get(
            "LOCALAPPDATA",
            ""
        )

        windows_apps = os.path.join(
            local_app_data,
            "Microsoft",
            "WindowsApps"
        )

        if os.path.isdir(windows_apps):
            if windows_apps not in os.environ["PATH"]:
                os.environ["PATH"] += (
                    os.pathsep + windows_apps
                )

        # Common Git location
        git_cmd = r"C:\Program Files\Git\cmd"

        if os.path.isdir(git_cmd):
            if git_cmd not in os.environ["PATH"]:
                os.environ["PATH"] += (
                    os.pathsep + git_cmd
                )

        # Common Ollama location
        ollama_path = os.path.join(
            local_app_data,
            "Programs",
            "Ollama"
        )

        if os.path.isdir(ollama_path):
            if ollama_path not in os.environ["PATH"]:
                os.environ["PATH"] += (
                    os.pathsep + ollama_path
                )

    except Exception:
        pass


# ============================================================
# COMMAND DETECTION
# ============================================================

def find_command(command):
    """
    Find an executable after refreshing PATH.
    """

    refresh_environment()

    result = shutil.which(command)

    if result:
        return result

    # Explicit winget fallback
    if command.lower() == "winget":
        possible_paths = [
            os.path.join(
                os.environ.get("LOCALAPPDATA", ""),
                "Microsoft",
                "WindowsApps",
                "winget.exe"
            ),
            r"C:\Windows\System32\winget.exe"
        ]

        for path in possible_paths:
            if os.path.isfile(path):
                return path

    return None


def command_exists(command):
    return find_command(command) is not None


# ============================================================
# LIVE COMMAND EXECUTION
# ============================================================

def run_live_command(command, error_message):
    """
    Runs a command and prints output live.
    """

    try:
        refresh_environment()

        print()

        if isinstance(command, list):
            printable = " ".join(
                f'"{x}"' if " " in str(x) else str(x)
                for x in command
            )
        else:
            printable = command

        print(f" -> Running: {printable}")

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
                line = line.rstrip()

                if line:
                    print(
                        f"    {line}",
                        flush=True
                    )

        return_code = process.wait()

        if return_code == 0:
            return True

        print(
            f" -> ❌ Command failed with "
            f"exit code {return_code}",
            file=sys.stderr
        )

        return False

    except Exception as e:

        print(
            f" -> {error_message}: {e}",
            file=sys.stderr
        )

        return False


# ============================================================
# WINDOWS / WINGET
# ============================================================

def check_windows():
    print("\n[1/11] Checking Windows compatibility...")

    if sys.platform != "win32":

        print(
            " -> ❌ This installer only supports Windows."
        )

        sys.exit(1)

    refresh_environment()

    winget_path = find_command("winget")

    if not winget_path:

        print()
        print(
            " -> ❌ winget was not found."
        )
        print()
        print(
            " -> Windows App Installer / winget "
            "is required for Git and Ollama installation."
        )
        print()

        sys.exit(1)

    print(
        f" -> ✅ winget detected:"
        f"\n    {winget_path}"
    )

    try:

        result = subprocess.run(
            [winget_path, "--version"],
            capture_output=True,
            text=True
        )

        version = (
            result.stdout.strip()
            or result.stderr.strip()
        )

        print(
            f" -> ✅ winget version: {version}"
        )

    except Exception as e:

        print(
            f" -> ❌ Could not execute winget: {e}"
        )

        sys.exit(1)


# ============================================================
# GIT
# ============================================================

def install_git():

    print("\n[2/11] Checking Git...")

    if command_exists("git"):

        git_path = find_command("git")

        print(
            " -> ✅ Git is already installed."
        )
        print(
            f"    {git_path}"
        )

        return

    print(
        " -> Git not found."
    )

    print(
        " -> Installing Git through winget..."
    )

    winget = find_command("winget")

    command = [
        winget,
        "install",
        "--id",
        "Git.Git",
        "--exact",
        "--silent",
        "--accept-source-agreements",
        "--accept-package-agreements"
    ]

    success = run_live_command(
        command,
        "❌ Git installation failed"
    )

    if not success:
        sys.exit(1)

    refresh_environment()

    if not command_exists("git"):

        print(
            " -> ❌ Git installer finished, "
            "but Git could not be detected."
        )

        sys.exit(1)

    print(
        " -> ✅ Git installed successfully."
    )


# ============================================================
# PYTHON 3.10
# ============================================================

def python_310_exists():

    try:

        result = subprocess.run(
            [
                "py",
                "-3.10",
                "--version"
            ],
            capture_output=True,
            text=True
        )

        version = (
            result.stdout.strip()
            or result.stderr.strip()
        )

        return (
            result.returncode == 0
            and version.startswith("Python 3.10")
        )

    except Exception:
        return False


def download_python(destination):

    print(
        " -> Downloading Python 3.10.11..."
    )

    try:

        with urllib.request.urlopen(
            PYTHON_310_URL,
            timeout=30
        ) as response:

            total_size = response.headers.get(
                "Content-Length"
            )

            if total_size:
                total_size = int(total_size)

            downloaded = 0

            block_size = 256 * 1024

            with open(
                destination,
                "wb"
            ) as output:

                while True:

                    data = response.read(
                        block_size
                    )

                    if not data:
                        break

                    output.write(data)

                    downloaded += len(data)

                    if total_size:

                        percent = int(
                            downloaded
                            * 100
                            / total_size
                        )

                        mb_done = (
                            downloaded
                            / 1024
                            / 1024
                        )

                        mb_total = (
                            total_size
                            / 1024
                            / 1024
                        )

                        sys.stdout.write(
                            "\r    Python download: "
                            f"{percent}% "
                            f"({mb_done:.1f}/"
                            f"{mb_total:.1f} MB)"
                        )

                        sys.stdout.flush()

        print()

    except Exception:

        if os.path.exists(destination):
            os.remove(destination)

        raise


def install_python_310():

    print(
        "\n[3/11] Checking Python 3.10..."
    )

    if python_310_exists():

        result = subprocess.run(
            [
                "py",
                "-3.10",
                "--version"
            ],
            capture_output=True,
            text=True
        )

        version = (
            result.stdout.strip()
            or result.stderr.strip()
        )

        print(
            f" -> ✅ {version}"
        )

        return

    print(
        " -> Python 3.10 was not found."
    )

    temp_dir = os.environ.get(
        "TEMP",
        "."
    )

    installer_path = os.path.join(
        temp_dir,
        "python-3.10.11-amd64.exe"
    )

    try:

        download_python(
            installer_path
        )

        print(
            " -> Installing Python silently..."
        )

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
                " -> ❌ Python installer "
                f"returned {result.returncode}"
            )

            sys.exit(1)

        refresh_environment()

        if not python_310_exists():

            print(
                " -> ❌ Python installation "
                "could not be verified."
            )

            sys.exit(1)

        print(
            " -> ✅ Python 3.10 installed."
        )

    except Exception as e:

        print(
            f" -> ❌ Python installation failed: {e}"
        )

        sys.exit(1)


# ============================================================
# OLLAMA INSTALLATION
# ============================================================

def install_ollama():

    print(
        "\n[4/11] Checking Ollama..."
    )

    if command_exists("ollama"):

        print(
            " -> ✅ Ollama is already installed."
        )

        return

    print(
        " -> Ollama not found."
    )

    print(
        " -> Installing Ollama through winget..."
    )

    winget = find_command("winget")

    command = [
        winget,
        "install",
        "--id",
        "Ollama.Ollama",
        "--exact",
        "--silent",
        "--accept-source-agreements",
        "--accept-package-agreements"
    ]

    success = run_live_command(
        command,
        "❌ Ollama installation failed"
    )

    if not success:
        sys.exit(1)

    refresh_environment()

    if not command_exists("ollama"):

        print(
            " -> ❌ Ollama installer finished, "
            "but Ollama could not be detected."
        )

        sys.exit(1)

    print(
        " -> ✅ Ollama installed successfully."
    )


# ============================================================
# OLLAMA API
# ============================================================

def ollama_api_ready():

    try:

        with urllib.request.urlopen(
            OLLAMA_API_TAGS,
            timeout=2
        ) as response:

            return response.status == 200

    except Exception:
        return False


def wait_for_ollama(timeout=45):

    print(
        "\n[5/11] Starting Ollama service..."
    )

    if ollama_api_ready():

        print(
            " -> ✅ Ollama API is already running."
        )

        return True

    print(
        " -> Ollama API is offline."
    )

    print(
        " -> Starting Ollama server..."
    )

    ollama = find_command("ollama")

    if not ollama:

        print(
            " -> ❌ Ollama executable not found."
        )

        return False

    try:

        subprocess.Popen(
            [
                ollama,
                "serve"
            ],
            stdout=subprocess.DEVNULL,
            stderr=subprocess.DEVNULL,
            creationflags=subprocess.CREATE_NO_WINDOW
        )

    except Exception as e:

        print(
            f" -> ❌ Failed to start Ollama: {e}"
        )

        return False

    start_time = time.time()

    while (
        time.time() - start_time
        < timeout
    ):

        if ollama_api_ready():

            print(
                "\n -> ✅ Ollama API is online."
            )

            return True

        sys.stdout.write(".")
        sys.stdout.flush()

        time.sleep(1)

    print()

    print(
        " -> ❌ Ollama did not respond "
        f"within {timeout} seconds."
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

    ollama = find_command("ollama")

    if not ollama:

        print(
            " -> ❌ Ollama executable "
            "was not found."
        )

        sys.exit(1)

    command = [
        ollama,
        "pull",
        OLLAMA_MODEL
    ]

    success = run_live_command(
        command,
        "❌ Qwen model installation failed"
    )

    if not success:
        sys.exit(1)

    # Verify through API

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
                " -> ❌ Model was not found "
                "after download."
            )

            sys.exit(1)

    except Exception as e:

        print(
            f" -> ❌ Model verification failed: {e}"
        )

        sys.exit(1)


# ============================================================
# SELECT REN DIRECTORY
# ============================================================

def choose_install_directory():

    print(
        "\n[7/11] Selecting Ren AI location..."
    )

    root = Tk()

    root.withdraw()

    root.attributes(
        "-topmost",
        True
    )

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
        " -> No folder selected."
    )

    print(
        f" -> Using: {fallback}"
    )

    return fallback


# ============================================================
# CLONE REN
# ============================================================

def clone_ren():

    global target_project_path

    destination_dir = (
        choose_install_directory()
    )

    target_project_path = os.path.join(
        destination_dir,
        "REN-AI"
    )

    if os.path.exists(
        target_project_path
    ):

        print(
            " -> REN-AI directory already exists."
        )

        return

    git = find_command("git")

    if not git:

        print(
            " -> ❌ Git executable "
            "was not found."
        )

        sys.exit(1)

    print(
        " -> Downloading Ren AI repository..."
    )

    command = [
        git,
        "clone",
        REPO_URL,
        target_project_path
    ]

    success = run_live_command(
        command,
        "❌ Ren repository download failed"
    )

    if not success:
        sys.exit(1)

    print(
        " -> ✅ Ren repository downloaded."
    )


# ============================================================
# PYTHON DEPENDENCIES
# ============================================================

def install_dependencies():

    print(
        "\n[8/11] Installing Ren dependencies..."
    )

    requirements = os.path.join(
        target_project_path,
        "requirements.txt"
    )

    if not os.path.isfile(
        requirements
    ):

        print(
            " -> ⚠️ requirements.txt "
            "was not found."
        )

        return

    print(
        " -> Upgrading pip..."
    )

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

    print(
        " -> Installing requirements..."
    )

    success = run_live_command(
        [
            "py",
            "-3.10",
            "-m",
            "pip",
            "install",
            "-r",
            requirements
        ],
        "❌ Dependency installation failed"
    )

    if not success:
        sys.exit(1)

    print(
        " -> ✅ Ren dependencies installed."
    )


# ============================================================
# REN CONFIGURATION
# ============================================================

def configure_ren():

    print(
        "\n[9/11] Configuring Ren → Ollama..."
    )

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

        print(
            " -> ✅ .env configuration created."
        )

    except Exception as e:

        print(
            f" -> ❌ Could not create .env: {e}"
        )

        sys.exit(1)


# ============================================================
# FINAL VERIFICATION
# ============================================================

def verify_installation():

    print(
        "\n[10/11] Verifying installation..."
    )

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

    if not target_project_path:
        problems.append("Ren directory")

    else:

        gui_file = os.path.join(
            target_project_path,
            "gui.py"
        )

        if not os.path.isfile(gui_file):
            problems.append("gui.py")

    if problems:

        print()
        print(
            " -> ❌ Installation verification failed:"
        )

        for problem in problems:

            print(
                f"    • {problem}"
            )

        sys.exit(1)

    print(
        " -> ✅ All major components verified."
    )


# ============================================================
# LAUNCH REN
# ============================================================

def launch_ren():

    print(
        "\n[11/11] Launching Ren AI..."
    )

    gui_path = os.path.join(
        target_project_path,
        "gui.py"
    )

    if not os.path.isfile(
        gui_path
    ):

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
        print(
            "=============================================="
        )
        print(
            "          🚀 REN AI IS STARTING              "
        )
        print(
            "=============================================="
        )

    except Exception as e:

        print(
            f" -> ❌ Could not launch Ren: {e}"
        )

        sys.exit(1)


# ============================================================
# MAIN
# ============================================================

def main():

    print()

    print(
        "=============================================="
    )
    print(
        "        WELCOME TO THE REN AI INSTALLER       "
    )
    print(
        "=============================================="
    )

    print()

    print(
        "This installer will configure:"
    )

    print(
        "  • Git"
    )
    print(
        "  • Python 3.10"
    )
    print(
        "  • Ollama"
    )
    print(
        "  • Qwen2.5-Coder 3B"
    )
    print(
        "  • Ren AI"
    )

    print()

    time.sleep(1)

    # 1
    check_windows()

    # 2
    install_git()

    # 3
    install_python_310()

    # 4
    install_ollama()

    # 5
    if not wait_for_ollama():
        sys.exit(1)

    # 6
    install_qwen()

    # 7
    clone_ren()

    # 8
    install_dependencies()

    # 9
    configure_ren()

    # 10
    verify_installation()

    # 11
    launch_ren()

    print()

    print(
        "=============================================="
    )
    print(
        "       🚀 REN AI INSTALLATION COMPLETE       "
    )
    print(
        "=============================================="
    )


# ============================================================
# ENTRY POINT
# ============================================================

if __name__ == "__main__":
    main()
