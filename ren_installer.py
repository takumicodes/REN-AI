# This file installs all necessary components for Ren AI. Enjoy it
import os
import subprocess
import sys
import threading
import time
from tkinter import Tk, filedialog

def refresh_environment():
    """Forces Python to refresh its Environment PATH variable in case winget just installed Git or Ollama."""
    if sys.platform == "win32":
        import winreg
        try:
            with winreg.OpenKey(winreg.HKEY_LOCAL_MACHINE, r"SYSTEM\CurrentControlSet\Control\Session Manager\Environment") as key:
                path, _ = winreg.QueryValueEx(key, "Path")
                os.environ["PATH"] = path
        except Exception:
            pass

def render_progress_bar(stop_event, message, mock_duration=30):
    """
    Renders a standard, high-visibility developer text progress bar [████░░░░]
    Increments steadily towards 95% over the mock_duration, then waits for the finish flag.
    """
    bar_width = 30
    start_time = time.time()
    
    while not stop_event.is_set():
        elapsed = time.time() - start_time
        # Progress scales slowly up to 95% to maintain continuous visual movement
        percent = min(95, int((elapsed / mock_duration) * 95))
        
        filled_amount = int((percent / 100) * bar_width)
        empty_amount = bar_width - filled_amount
        bar = "█" * filled_amount + "░" * empty_amount
        
        # Overwrite the current terminal line dynamically (\r)
        sys.stdout.write(f"\r    {message}: [{bar}] {percent}% ({int(elapsed)}s)")
        sys.stdout.flush()
        time.sleep(0.2)
        
    # Jump to 100% instantly when the background task signals it's finished
    total_elapsed = int(time.time() - start_time)
    full_bar = "█" * bar_width
    sys.stdout.write(f"\r    {message}: [{full_bar}] 100% Complete! ({total_elapsed}s)\n")
    sys.stdout.flush()

def install_git_if_missing():
    print("\n[1/4] Checking Git Dependency...")
    try:
        subprocess.run("git --version", shell=True, check=True, capture_output=True)
        print(" -> Git is already installed.")
    except (subprocess.CalledProcessError, FileNotFoundError):
        print(" -> Git not found. Deploying installation pipeline...")
        
        command = "winget install --id Git.Git --accept-source-agreements --accept-package-agreements"
        stop_flag = threading.Event()
        
        # Git setup visual baseline tracking thread
        progress_thread = threading.Thread(target=render_progress_bar, args=(stop_flag, "Downloading Git Engine", 15))
        progress_thread.start()
        
        try:
            subprocess.run(command, shell=True, capture_output=True, text=True, check=True)
            stop_flag.set()  
            progress_thread.join()
            refresh_environment()
        except subprocess.CalledProcessError as e:
            stop_flag.set()
            progress_thread.join()
            print(f" -> ❌ Git automated installation failed with exit code {e.returncode}", file=sys.stderr)

def install_ollama_winget():
    print("\n[2/4] Checking Ollama Dependency...")
    try:
        subprocess.run("ollama --version", shell=True, check=True, capture_output=True)
        print(" -> Ollama is already installed.")
    except (subprocess.CalledProcessError, FileNotFoundError):
        print(" -> Ollama not found. Deploying installation pipeline...")
        
        command = "winget install --id Ollama.Ollama --accept-source-agreements --accept-package-agreements"
        stop_flag = threading.Event()
        
        # Ollama configuration visual baseline tracking thread
        progress_thread = threading.Thread(target=render_progress_bar, args=(stop_flag, "Downloading Ollama Base", 220))
        progress_thread.start()
        
        try:
            subprocess.run(command, shell=True, capture_output=True, text=True, check=True)
            stop_flag.set()
            progress_thread.join()
            refresh_environment()
            
            # Post-install buffer window to allow engine architecture setup sequences
            print(" -> Waiting for Ollama background engine service to wake up...")
            time.sleep(15)
        except subprocess.CalledProcessError as e:
            stop_flag.set()
            progress_thread.join()
            print(f" -> ❌ Ollama installation failed with exit code {e.returncode}", file=sys.stderr)

def download_qwen_coder():
    print("\n[3/4] Pulling Local LLM Weights (Qwen Coder 3B)...")
    command = "ollama pull qwen2.5-coder:3b"
    try:
        # Added encoding="utf-8" and errors="ignore" to prevent translation crashes
        process = subprocess.Popen(
            command, 
            shell=True, 
            stdout=subprocess.PIPE, 
            stderr=subprocess.STDOUT, 
            text=True,
            encoding="utf-8",
            errors="ignore"
        )
        # Directly pipe live streaming engine download metrics
        while True:
            output = process.stdout.readline()
            if output == '' and process.poll() is not None:
                break
            if output:
                print(f"    {output.strip()}", flush=True)
        
        if process.poll() == 0:
            print(" -> 🎉 Qwen Coder 3B successfully installed!")
        else:
            print(f" -> ❌ Model download exited with code: {process.poll()}")
    except FileNotFoundError:
        print(" -> ⚠️ Could not call Ollama. Restart your terminal context.", file=sys.stderr)


def clone_repo_and_install_deps():
    print("\n[4/4] Setting up Project Repository...")
    root = Tk()
    root.withdraw()
    root.attributes('-topmost', True)
    
    destination_dir = filedialog.askdirectory(title="Select Folder to Clone Ren AI Into")
    if not destination_dir:
        print(" -> Operation cancelled: No destination folder selected.")
        return

    repo_url = "https://github.com/takumicodes/REN-AI.git"
    repo_name = "REN-AI"
    target_project_path = os.path.join(destination_dir, repo_name)

    print(f" -> Cloning {repo_url} into {destination_dir}...")
    try:
        subprocess.run(
            f'git clone {repo_url}', shell=True, cwd=destination_dir, capture_output=True, text=True, check=True
        )
        print(" -> 🎉 Repository successfully cloned!")
    except subprocess.CalledProcessError as e:
        print(f" -> ❌ Git clone failed:\n{e.stderr}", file=sys.stderr)
        return

    requirements_path = os.path.join(target_project_path, "requirements.txt")
    if os.path.exists(requirements_path):
        print(" -> Found 'requirements.txt'. Installing dependencies...")
        pip_command = f'"{sys.executable}" -m pip install -r requirements.txt'
        try:
            subprocess.run(pip_command, shell=True, cwd=target_project_path, check=True)
            print(" -> ✅ All dependencies installed successfully!")
        except subprocess.CalledProcessError:
            print(f" -> ❌ Failed to install dependencies.", file=sys.stderr)
    else:
        print(" -> ⚠️ Warning: No 'requirements.txt' file found inside the repository.")

def main():
    print("==============================================")
    print("        WELCOME TO THE REN AI INSTALLER       ")
    print("==============================================")
    print("This setup manager will configure your environment and fetch core components.")
    time.sleep(1.5)

    install_git_if_missing()
    install_ollama_winget()
    download_qwen_coder()
    clone_repo_and_install_deps()

    print("\n==============================================")
    print("        SETUP PROCESS COMPLETE! Enjoy REN AI  ")
    print("==============================================")

if __name__ == "__main__":
    main()
