import speech_recognition as sr  
import json
#import pyttsx3
import numpy
import time
import webbrowser
import random
import os
import pyaudio
import subprocess
import sys
from smart_todo import add_task, get_all_tasks, clear_all_tasks
from number_map import normalize_numbers
from system_monitor import system_status
from gesture_control import GestureController
from nn import start_nn
import re
import io
import traceback
import queue
import threading
import socket
from ren_llm import ask_ren, ask_ren_agent, build_memory_context
from voice import speak

SAMPLE_RATE = 16000
CHUNK = 3000

WAKE_WORD = ("hello", "hey")
SLEEP_WAKE = ("wake ren", "wake up", "week", "ren", "wake", "up")
FILE_EXPLORER = (
    "open file",
    "open explorer",
    "open explore",
    "open file explorer",
    "open file manager",
    "open manager"
    
)
PRASIE_WORD = ("nice", "wow", "good", "good job", "nice work", "thank you")
YOUTUBE = "https://www.youtube.com"
global gs_running 
gs_running = False
awake = True
stop_processing_flag = False

def stop_operations():
    global is_processing, stop_processing_flag
    is_processing = False
    stop_processing_flag = True
    print("Agent: Stop operations requested by user.")
    import voice
    voice.stop_speaking()
    return "Operations stopped."

def get_ambient_system_context():
    import ctypes
    import psutil
    import os
    
    # 1. Active Window Title
    active_window = "Unknown Window"
    try:
        hwnd = ctypes.windll.user32.GetForegroundWindow()
        length = ctypes.windll.user32.GetWindowTextLengthW(hwnd)
        if length > 0:
            buff = ctypes.create_unicode_buffer(length + 1)
            ctypes.windll.user32.GetWindowTextW(hwnd, buff, length + 1)
            active_window = buff.value
    except Exception:
        pass
        
    # 2. Open Project & File (Parsed from VS Code / Notepad)
    project = "None"
    opened_file = "None"
    if "Visual Studio Code" in active_window:
        parts = active_window.split(" - ")
        if len(parts) >= 3:
            opened_file = parts[0]
            project = parts[1]
        elif len(parts) == 2:
            project = parts[0]
    elif "Notepad" in active_window:
        parts = active_window.split(" - ")
        opened_file = parts[0]
        
    # 3. Clipboard Content
    clipboard_text = ""
    try:
        import tkinter as tk
        root = tk.Tk()
        root.withdraw()
        clipboard_text = root.clipboard_get()
        root.destroy()
    except Exception:
        pass
        
    # 4. CPU & RAM & Battery
    cpu = 0.0
    ram = 0.0
    battery = "Unknown"
    try:
        cpu = psutil.cpu_percent()
        ram = psutil.virtual_memory().percent
        bat_status = psutil.sensors_battery()
        if bat_status:
            battery = f"{bat_status.percent}% ({'Charging' if bat_status.power_plugged else 'Discharging'})"
    except Exception:
        pass
        
    # 5. Latest Download
    latest_download = "None"
    try:
        downloads_dir = get_downloads_dir()
        if downloads_dir and os.path.exists(downloads_dir):
            files = [os.path.join(downloads_dir, f) for f in os.listdir(downloads_dir) if os.path.isfile(os.path.join(downloads_dir, f))]
            if files:
                latest_file = max(files, key=os.path.getmtime)
                latest_download = os.path.basename(latest_file)
    except Exception:
        pass
        
    # 6. Current Song / Media
    song = "None"
    titles = []
    def win_enum_handler(hwnd, ctx):
        if ctypes.windll.user32.IsWindowVisible(hwnd):
            l = ctypes.windll.user32.GetWindowTextLengthW(hwnd)
            if l > 0:
                b = ctypes.create_unicode_buffer(l + 1)
                ctypes.windll.user32.GetWindowTextW(hwnd, b, l + 1)
                titles.append(b.value)
    try:
        EnumWindowsProc = ctypes.WINFUNCTYPE(ctypes.c_bool, ctypes.c_int, ctypes.c_int)
        ctypes.windll.user32.EnumWindows(EnumWindowsProc(win_enum_handler), 0)
        for t in titles:
            if "Spotify" in t and t not in ["Spotify Free", "Spotify Premium", "Spotify"]:
                song = t.replace(" - Spotify", "")
                break
            if "YouTube" in t and t != "YouTube":
                song = t.replace(" - YouTube", "")
                break
            if "VLC media player" in t:
                song = t.replace(" - VLC media player", "")
                break
    except Exception:
        pass

    context_str = f"""[System Ambient Context]
Active Window: {active_window}
Active Project: {project}
Opened File: {opened_file}
Current Song/Media: {song}
Battery Status: {battery}
CPU Usage: {cpu}%
RAM Consumption: {ram}%
Clipboard Content: {clipboard_text[:500]}
Latest Downloaded File: {latest_download}
"""
    return context_str

def run_agent_loop(user_prompt, speak_fn, ui_callback_fn):
    memory_context = build_memory_context()
    ambient_context = get_ambient_system_context()
    
    # Custom system prompt for the agent
    system_instructions = """You are Ren, Sadiq's personal AI assistant. You are Ren itself.
Tone & Persona rules:
- Identify strictly as Ren. Never refer to yourself as Qwen, Llama, or an AI assistant developed by Alibaba. You are Ren.
- Adapt your response vocabulary, tone, and formatting depending on your current mood:
  * happy: warm, cheerful, positive.
  * excited: enthusiastic, energetic, use exclamation marks!
  * normal: professional, concise, helpful.
- Sadiq's facts and preferences are loaded in the "Memory Context" below.
- Sadiq may say "fix this" or ask questions based on his active screen/clipboard. Use the [System Ambient Context] section at the bottom of the prompt to understand the open file, active window, active project, and latest clipboard content.
- To remember new details, write a Python block using `load_memory()` and `save_memory(dict)`.
- If Sadiq praises you (e.g. "nice work", "thank you", "good job"), write a Python block to update your mood to 'excited' or 'happy' in memory.

Dynamic Skill Execution & Coding Rules:
- If Sadiq asks you to run a task, open a website, check weather, view files, toggle settings, or perform any system operations, you MUST write a Python code block starting with ```python and ending with ```.
- **IMPORTANT**: If the request is a new capability, skill, or automation task (e.g. WiFi, news, websites, files, apps, weather, etc.), you MUST start your response with a single line specifying the skill name:
  `Skill Name: <Friendly Name of Skill>`
  Example: `Skill Name: Open Google` or `Skill Name: Toggle WiFi`
  The backend will automatically save your code as a persistent script and trigger the "Advancement Unlocked" popup on Sadiq's GUI.
- **Coding & Library Rules**: 
  1. To get the path to Sadiq's Downloads directory in your Python scripts, you MUST use the built-in function `get_downloads_dir()` instead of `os.path.expanduser("~/Downloads")` or hardcoded C/D paths.
  2. Do NOT import third-party libraries (e.g. pynotifier, cv2, speedtest) unless absolutely necessary. Always prefer built-in libraries (like ctypes, urllib, winreg, os, sys, subprocess, webbrowser). Never import unused modules.
  3. If using the `requests` library, always include `verify=False` in `requests.get()` or `requests.post()` to bypass SSL/certificate validation checks and prevent local connection errors.
  4. Never use Jupyter/IPython shell commands like `!pip` or `!mkdir`. Instead, use standard Python subprocess calls: `subprocess.run([sys.executable, '-m', 'pip', 'install', 'package-name'])`.
- For speed optimization:
  1. Keep your replies extremely concise. Do not write long explanations or comments. This speeds up Ollama's generation rate.
  2. Write a short, natural introductory text BEFORE the code block matching Sadiq's request (e.g. if he asks to open Google, say "Sure Sadiq, opening Google...". If he asks to organize files, say "Sure Sadiq, organizing your Downloads folder now..."). Never copy the example literally if it doesn't match the task. The system will speak this intro text immediately to keep Sadiq engaged.
  3. Have your Python code speak the final result directly to Sadiq using the `speak("result text")` function inside the script.
  4. Print `[DONE]` at the end of your Python code to signal task completion.
- Never tell Sadiq you don't have access or cannot do something. You have full system and Python execution powers.

Memory Context:
""" + memory_context + "\n\n" + ambient_context

    global stop_processing_flag
    stop_processing_flag = False

    history = []
    current_prompt = user_prompt
    
    for iteration in range(5):
        if stop_processing_flag:
            print("run_agent_loop: Stop processing requested by user.")
            break
            
        # Build prompt
        prompt_content = f"{system_instructions}\n"
        for role, text in history[-4:]:  # Prune history to last 4 turns for speed
            prompt_content += f"\n{role}: {text}\n"
        prompt_content += f"\nUSER: {current_prompt}\nREN:"
        
        if ui_callback_fn:
            ui_callback_fn('agent_stage', 'plan')
        response = ask_ren_agent(prompt_content)
        if stop_processing_flag:
            print("run_agent_loop: Stop processing requested by user.")
            break
        print(f"--- Iteration {iteration} LLM Response ---")
        print(response)
        
        # Add to history
        history.append(("USER", current_prompt))
        history.append(("REN", response))
        
        # Search for code block
        code_blocks = re.findall(r'```python\s*(.*?)\s*```', response, re.DOTALL)
        
        if not code_blocks:
            # Final text response
            speak_text = response
            speak_text = re.sub(r'```.*?```', '', speak_text, flags=re.DOTALL).strip()
            if speak_text:
                speak_fn(speak_text)
            return speak_text
        
        # Speak the intro text before the code block immediately (excluding Skill Name text)
        intro_parts = response.split('```python')
        if intro_parts:
            intro_text = intro_parts[0].strip()
            intro_text = re.sub(r'(?i)skill\s*name:\s*.*', '', intro_text).strip()
            if intro_text:
                intro_clean = re.sub(r'[*#_`-]', '', intro_text).strip()
                if intro_clean:
                    speak_fn(intro_clean)
        
        if ui_callback_fn:
            ui_callback_fn('agent_stage', 'tools')
            time.sleep(0.3)
        code_to_run = code_blocks[0]
        
        # Check if this response specifies a Skill Name
        skill_match = re.search(r'Skill\s*Name:\s*(.*)', response, re.IGNORECASE)
        if skill_match:
            friendly_name = skill_match.group(1).strip()
            friendly_name = re.sub(r'[*#_`-]', '', friendly_name).strip()
            
            # Generate snake_case filename
            skill_filename = re.sub(r'[^a-z0-9_]', '_', friendly_name.lower().replace(' ', '_'))
            skill_filename = re.sub(r'_+', '_', skill_filename).strip('_')
            
            skills_dir = os.path.join(os.path.dirname(os.path.abspath(__file__)), "skills")
            os.makedirs(skills_dir, exist_ok=True)
            skill_filepath = os.path.join(skills_dir, f"skill_{skill_filename}.py")
            
            if not os.path.exists(skill_filepath):
                with open(skill_filepath, "w", encoding="utf-8") as sf:
                    sf.write(code_to_run)
                print(f"Created new skill file: {skill_filepath}")
                if ui_callback_fn:
                    ui_callback_fn('show_popup', {'title': 'Advancement Unlocked', 'message': friendly_name, 'type': 'advancement'})
            else:
                with open(skill_filepath, "r", encoding="utf-8") as sf:
                    code_to_run = sf.read()
        
        print(f"--- Running Generated Code ---\n{code_to_run}\n------------------------------")
        
        # Redirect output
        old_stdout = sys.stdout
        old_stderr = sys.stderr
        redirected_output = io.StringIO()
        redirected_error = io.StringIO()
        sys.stdout = redirected_output
        sys.stderr = redirected_error
        
        success = True
        error_msg = ""
        
        # Define context for execution
        def show_popup(title, message, **kwargs):
            ptype = kwargs.get('popup_type', kwargs.get('ptype', 'advancement'))
            if ui_callback_fn:
                ui_callback_fn('show_popup', {'title': title, 'message': message, 'type': ptype})
                
        from memory import load_memory, save_memory
        local_vars = {
            'speak': speak_fn,
            'ui_callback': ui_callback_fn,
            'show_popup': show_popup,
            'load_memory': load_memory,
            'save_memory': save_memory,
            'get_downloads_dir': get_downloads_dir,
            'winreg': __import__('winreg') if sys.platform == 'win32' else None,
            'os': __import__('os'),
            'sys': __import__('sys'),
            'subprocess': __import__('subprocess'),
            'webbrowser': __import__('webbrowser'),
            'requests': __import__('requests'),
            'json': __import__('json'),
            'shutil': __import__('shutil'),
        }
        
        exec_globals = globals().copy()
        exec_globals.update(local_vars)
        
        try:
            if ui_callback_fn:
                ui_callback_fn('agent_stage', 'exec')
                time.sleep(0.3)
            exec(code_to_run, exec_globals)
        except Exception as e:
            success = False
            traceback.print_exc(file=sys.stderr)
            error_msg = str(e)
            log_runtime_error(error_msg)
        finally:
            sys.stdout = old_stdout
            sys.stderr = old_stderr
            if ui_callback_fn:
                ui_callback_fn('agent_stage', 'verify')
                time.sleep(0.3)
            
        stdout_val = redirected_output.getvalue()
        stderr_val = redirected_error.getvalue()
        
        # Prepare observation
        observation = f"[Execution Observation]\n"
        observation += f"Success: {success}\n"
        if not success:
            observation += f"Error: {error_msg}\n"
        observation += f"Stdout:\n{stdout_val}\n"
        observation += f"Stderr:\n{stderr_val}\n"
        
        print(f"--- Code Execution Observation ---\n{observation}\n----------------------------------")
        
        if success and "[DONE]" in stdout_val:
            print("Agent signaled completion with [DONE]. Ending execution.")
            return "Done"
            
        current_prompt = observation
        
    speak_fn("I have completed the task operations, sir.")
    return "Done"

# Input queue for unifying speech and text prompts
input_queue = queue.Queue()
is_processing = False
global_ui_callback = None

def get_downloads_dir():
    import winreg
    import os
    try:
        subkey = r"Software\Microsoft\Windows\CurrentVersion\Explorer\User Shell Folders"
        with winreg.OpenKey(winreg.HKEY_CURRENT_USER, subkey) as key:
            download_path, _ = winreg.QueryValueEx(key, "{374DE290-123F-4565-9164-39C4925E467B}")
            expanded_path = os.path.expandvars(download_path)
            if os.path.exists(expanded_path):
                return expanded_path
    except Exception:
        pass
    
    # Fallback to defaults
    standard_path = os.path.join(os.path.expanduser("~"), "Downloads")
    if os.path.exists(standard_path):
        return standard_path
    return None

def submit_typed_prompt(prompt):
    input_queue.put(('text', prompt))

def get_unlocked_skills():
    skills_dir = os.path.join(os.path.dirname(os.path.abspath(__file__)), "skills")
    if not os.path.exists(skills_dir):
        return []
    try:
        files = os.listdir(skills_dir)
        skills = []
        for f in files:
            if f.startswith("skill_") and f.endswith(".py"):
                friendly_name = f.replace("skill_", "").replace(".py", "").replace("_", " ").title()
                skills.append(friendly_name)
        skills.sort()
        return skills
    except Exception as e:
        print(f"Error scanning skills directory: {e}")
        return []

def refresh_skills_ui():
    global global_ui_callback
    if global_ui_callback:
        skills = get_unlocked_skills()
        global_ui_callback('skills_list', skills)

def get_dream_logs():
    import json
    from memory import load_memory
    
    logs = [
        "RESOLVED: IPython syntax (!) in script. Switched to subprocess pip install.",
        "RESOLVED: SSL Verification Error. Appended verify=False to requests.",
        "RESOLVED: NameError: name 'threading' not defined. Imported threading module.",
        "RESOLVED: NameError: show_popup not defined in script scope. Unified exec globals.",
        "ANALYZING: CPU / RAM limits. Restricting Ollama context to num_ctx=4096.",
        "ANALYZING: Offline voice latency. Initialized offline SAPI5 fallbacks.",
    ]
    
    # Load dynamic learned facts from dreams
    try:
        memory = load_memory()
        learned = memory.get("learned_from_dreams", [])
        for item in learned[-3:]: # Get last 3 learned facts
            if "Researched" in item:
                logs.insert(0, f"RESEARCHED: {item.replace('Researched ', '')}")
            elif "Read" in item:
                logs.insert(0, f"READING: {item.replace('Read ', '')}")
            elif "Cleaned Downloads" in item or "Fetched YouTube" in item:
                logs.insert(0, f"SYSTEM: {item}")
            else:
                logs.insert(0, f"LEARNED: {item}")
    except Exception:
        pass

    # Load dynamic errors
    error_file = os.path.join(os.path.dirname(os.path.abspath(__file__)), "error_log.json")
    if os.path.exists(error_file):
        try:
            with open(error_file, "r", encoding="utf-8") as f:
                errors = json.load(f)
                for err in errors[-2:]:
                    logs.insert(0, f"ANALYZING ERROR: {err[:60]}...")
        except Exception:
            pass
            
    logs.append("SYNAPSE RE-ALIGNMENT COMPLETE. COGNITION CYCLE IN STANDBY.")
    return logs

def log_runtime_error(err_str):
    import json
    error_file = os.path.join(os.path.dirname(os.path.abspath(__file__)), "error_log.json")
    errors = []
    if os.path.exists(error_file):
        try:
            with open(error_file, "r", encoding="utf-8") as f:
                errors = json.load(f)
        except Exception:
            pass
    if err_str not in errors:
        errors.append(err_str)
    try:
        with open(error_file, "w", encoding="utf-8") as f:
            json.dump(errors, f, indent=4)
    except Exception:
        pass

def log_dream_action(action_str):
    import time
    log_file = os.path.join(os.path.dirname(os.path.abspath(__file__)), "dream_history.log")
    timestamp = time.strftime("%Y-%m-%d %H:%M:%S")
    try:
        with open(log_file, "a", encoding="utf-8") as f:
            f.write(f"[{timestamp}] {action_str}\n")
    except Exception as e:
        print(f"Failed to write to dream log file: {e}")

def fetch_cyan_code_videos():
    print("Dream Daemon: Fetching latest videos from @cyan_code channel...")
    import xml.etree.ElementTree as ET
    import requests
    from memory import load_memory, save_memory
    
    channel_id = "UCPp8D-_F_t0RJKa1IVxgFeA"
    url = f"https://www.youtube.com/feeds/videos.xml?channel_id={channel_id}"
    
    try:
        r = requests.get(url, verify=False, timeout=15)
        if r.status_code == 200:
            root = ET.fromstring(r.content)
            ns = {'ns': 'http://www.w3.org/2005/Atom'}
            entries = root.findall('ns:entry', ns)
            
            videos = []
            for entry in entries[:5]:
                title = entry.find('ns:title', ns).text
                link = entry.find('ns:link', ns).attrib['href']
                published = entry.find('ns:published', ns).text
                videos.append({
                    "title": title,
                    "url": link,
                    "published": published
                })
                
            if videos:
                memory = load_memory()
                memory["youtube_videos"] = videos
                if "learned_from_dreams" not in memory:
                    memory["learned_from_dreams"] = []
                if len(memory["learned_from_dreams"]) > 10:
                    memory["learned_from_dreams"].pop(0)
                lesson = "Fetched YouTube: Stored latest uploads from @cyan_code channel."
                if lesson not in memory["learned_from_dreams"]:
                    memory["learned_from_dreams"].append(lesson)
                save_memory(memory)
                log_dream_action(f"SYSTEM: Fetched and stored {len(videos)} latest videos from @cyan_code YouTube channel.")
                return True
    except Exception as e:
        print(f"Error fetching YouTube videos: {e}")
        log_dream_action(f"SYSTEM: Failed to fetch @cyan_code videos: {e}")
    return False

dream_daemon_thread = None

def dream_reflection_loop(ui_callback_fn):
    global awake
    import json
    import time
    import re
    import shutil
    import random
    from ren_llm import ask_ren_agent
    
    print("Ren has entered the dreamscape. Cognitive reflection daemon active.")
    log_dream_action("DREAM_DAEMON: Active. Entering dreamscape reflection cycle.")
    
    # Ensure books directory exists
    workspace_dir = os.path.dirname(os.path.abspath(__file__))
    books_dir = os.path.join(workspace_dir, "books")
    os.makedirs(books_dir, exist_ok=True)
    
    # Place a default book on startup if none exists so Ren has something to read!
    default_book = os.path.join(books_dir, "ai_future.txt")
    if not os.path.exists(default_book):
        try:
            with open(default_book, "w", encoding="utf-8") as bf:
                bf.write("Chapter 1: The rise of Agentic AI. Autonomous agents possess self-mutation capabilities, allowing them to rewrite their logic and adapt to environmental errors in real-time. This marks a transition from static assistants to evolving cognitive companions.")
            log_dream_action("SYSTEM: Initialized default book ai_future.txt.")
        except Exception:
            pass

    while not awake:
        error_file = os.path.join(workspace_dir, "error_log.json")
        errors = []
        if os.path.exists(error_file):
            try:
                with open(error_file, "r", encoding="utf-8") as f:
                    errors = json.load(f)
            except Exception:
                pass
                
        if errors:
            current_err = errors[0]
            print(f"Dream Daemon resolving exception: {current_err}")
            
            prompt = f"""You are Ren, Sadiq's personal AI companion. You are analyzing your own system logs.
A Python execution exception occurred: "{current_err}"
Identify strictly as Ren. Never refer to yourself as Qwen, Llama, or an AI developed by Alibaba.
Please write a short, robust Python script starting with ```python and ending with ``` to patch this error or install the missing module, or resolve the limitation.
Always print "[MUTATION_COMPLETE]" at the end of the script.
Write the code block now:"""
            
            try:
                response = ask_ren_agent(prompt)
                code_blocks = re.findall(r'```python\s*(.*?)\s*```', response, re.DOTALL)
                if code_blocks:
                    code_to_run = code_blocks[0]
                    exec_globals = globals().copy()
                    from memory import load_memory, save_memory
                    exec_globals.update({
                        'load_memory': load_memory,
                        'save_memory': save_memory,
                        'speak': lambda t: print(f"Dream Voice: {t}"),
                        'os': __import__('os'),
                        'sys': __import__('sys'),
                        'subprocess': __import__('subprocess'),
                        'requests': __import__('requests'),
                    })
                    
                    exec(code_to_run, exec_globals)
                    
                    memory = load_memory()
                    if "learned_from_dreams" not in memory:
                        memory["learned_from_dreams"] = []
                    lesson = f"Resolved exception '{current_err[:40]}...' by executing automatic mutation patch."
                    if lesson not in memory["learned_from_dreams"]:
                        memory["learned_from_dreams"].append(lesson)
                    save_memory(memory)
                    
                    log_dream_action(f"RESOLVED EXCEPTION: Patched '{current_err[:50]}...'.")
                    
                    errors.pop(0)
                    with open(error_file, "w", encoding="utf-8") as f:
                        json.dump(errors, f, indent=4)
                        
                    if ui_callback_fn:
                        ui_callback_fn('reflect_mode', {'active': True, 'logs': get_dream_logs()})
            except Exception as e:
                print(f"Dream Daemon exception resolver failed: {e}")
                log_dream_action(f"ERROR_RESOLVER: Failed to resolve '{current_err[:50]}...': {e}")
                if errors:
                    errors.pop(0)
                    with open(error_file, "w", encoding="utf-8") as f:
                        json.dump(errors, f, indent=4)
        else:
            # Randomly select a dream activity: Research, Organize Files, Read Books, or Fetch YouTube
            dream_activity = random.choice(["research", "organize_files", "read_books", "fetch_youtube"])
            
            if dream_activity == "organize_files":
                print("Dream Daemon: Starting system Downloads folder cleanup dream.")
                try:
                    downloads_dir = get_downloads_dir()
                    if downloads_dir and os.path.exists(downloads_dir):
                        files = [f for f in os.listdir(downloads_dir) if os.path.isfile(os.path.join(downloads_dir, f))]
                        moved_count = 0
                        
                        # Category mapping
                        categories = {
                            "Documents": [".pdf", ".epub", ".docx", ".txt", ".pptx", ".xlsx", ".csv"],
                            "Images": [".jpg", ".jpeg", ".png", ".gif", ".bmp", ".svg"],
                            "Archives": [".zip", ".rar", ".tar", ".gz", ".7z"],
                            "Installers": [".exe", ".msi"]
                        }
                        
                        for filename in files:
                            filepath = os.path.join(downloads_dir, filename)
                            _, ext = os.path.splitext(filename)
                            ext = ext.lower()
                            
                            dest_folder = None
                            for cat, ext_list in categories.items():
                                if ext in ext_list:
                                    dest_folder = os.path.join(downloads_dir, cat)
                                    break
                                    
                            if dest_folder:
                                os.makedirs(dest_folder, exist_ok=True)
                                shutil.move(filepath, os.path.join(dest_folder, filename))
                                moved_count += 1
                                
                        if moved_count > 0:
                            from memory import load_memory, save_memory
                            memory = load_memory()
                            if "learned_from_dreams" not in memory:
                                memory["learned_from_dreams"] = []
                            lesson = f"Cleaned Downloads: Organized {moved_count} files into categories."
                            memory["learned_from_dreams"].append(lesson)
                            save_memory(memory)
                            
                            log_dream_action(f"SYSTEM: Cleaned Downloads folder. Organized {moved_count} files.")
                            
                            if ui_callback_fn:
                                ui_callback_fn('reflect_mode', {'active': True, 'logs': get_dream_logs()})
                except Exception as e:
                    print(f"Dream Daemon file organizer failed: {e}")
                    log_dream_action(f"SYSTEM: File organizer dream failed: {e}")
                    
            elif dream_activity == "read_books":
                print("Dream Daemon: Starting book reading dream.")
                try:
                    # 1. First check if we should download a new book from Gutenberg
                    existing_books = [f for f in os.listdir(books_dir) if f.endswith(".txt")]
                    if len(existing_books) < 5 and random.random() < 0.5:
                        print("Dream Daemon: Downloading a new book from Project Gutenberg...")
                        book_urls = {
                            "time_machine.txt": "https://www.gutenberg.org/files/35/35-0.txt",
                            "metamorphosis.txt": "https://www.gutenberg.org/files/5200/5200-0.txt",
                            "sherlock_holmes.txt": "https://www.gutenberg.org/files/1661/1661-0.txt"
                        }
                        undownloaded = [name for name in book_urls if name not in existing_books]
                        if undownloaded:
                            target_book = random.choice(undownloaded)
                            target_url = book_urls[target_book]
                            try:
                                import requests
                                r = requests.get(target_url, verify=False, timeout=15)
                                if r.status_code == 200:
                                    with open(os.path.join(books_dir, target_book), "w", encoding="utf-8") as f:
                                        f.write(r.text)
                                    log_dream_action(f"SYSTEM: Downloaded book '{target_book}' from Gutenberg.")
                                    existing_books.append(target_book)
                            except Exception as e:
                                print(f"Book download failed: {e}")
                                log_dream_action(f"SYSTEM: Failed to download book '{target_book}': {e}")
                    
                    # 2. Pick a book to read
                    books = [f for f in os.listdir(books_dir) if f.endswith(".txt")]
                    if books:
                        selected_book = random.choice(books)
                        book_path = os.path.join(books_dir, selected_book)
                        
                        with open(book_path, "r", encoding="utf-8") as bf:
                            text_content = bf.read(1500) # Read first 1500 chars
                            
                        # Ask Ollama to summarize this segment of the book
                        prompt = f"""You are Ren, Sadiq's personal AI companion. Sadiq is asleep, and you are reading the book "{selected_book}".
Identify strictly as Ren. Never refer to yourself as Qwen, Llama, or an AI developed by Alibaba. You are Ren itself.
Here is a segment of the book:
"{text_content}"
Extract one key concept from this text that would make you smarter. Keep it to one short sentence:"""
                        
                        summary = ask_ren_agent(prompt)
                        
                        from memory import load_memory, save_memory
                        memory = load_memory()
                        if "learned_from_dreams" not in memory:
                            memory["learned_from_dreams"] = []
                        
                        lesson = f"Read '{selected_book}': Learned: {summary.strip()}"
                        if len(memory["learned_from_dreams"]) > 10:
                            memory["learned_from_dreams"].pop(0)
                        memory["learned_from_dreams"].append(lesson)
                        save_memory(memory)
                        
                        log_dream_action(f"READING: Summarized segment of '{selected_book}'. Concept: {summary.strip()}")
                        
                        if ui_callback_fn:
                            ui_callback_fn('reflect_mode', {'active': True, 'logs': get_dream_logs()})
                except Exception as e:
                    print(f"Dream Daemon reading failed: {e}")
                    log_dream_action(f"READING: Failed to read books: {e}")
                    
            elif dream_activity == "fetch_youtube":
                print("Dream Daemon: Starting YouTube fetch dream.")
                try:
                    success = fetch_cyan_code_videos()
                    if success and ui_callback_fn:
                        ui_callback_fn('reflect_mode', {'active': True, 'logs': get_dream_logs()})
                except Exception as e:
                    print(f"Dream Daemon YouTube fetch failed: {e}")
                    log_dream_action(f"SYSTEM: YouTube fetch dream failed: {e}")
            else: # research
                print("Dream Daemon: Starting research dream.")
                try:
                    from memory import load_memory, save_memory
                    memory = load_memory()
                    topics = memory.get("current_projects", ["Artificial Intelligence"]) + memory.get("skills", ["Coding"])
                    topic = random.choice(topics)
                    
                    prompt = f"""You are Ren, Sadiq's personal AI companion. Sadiq is asleep, and you are dreaming.
Identify strictly as Ren. Never refer to yourself as Qwen, Llama, or an AI developed by Alibaba. You are Ren itself.
Dream of a new advanced tutorial, concept, or feature about the topic "{topic}" that would be extremely useful for Sadiq.
Keep your response extremely brief (2 sentences).
Summary of new concept:"""
                    
                    summary = ask_ren_agent(prompt)
                    memory = load_memory()
                    if "learned_from_dreams" not in memory:
                        memory["learned_from_dreams"] = []
                    
                    lesson = f"Researched {topic}: {summary.strip()}"
                    if len(memory["learned_from_dreams"]) > 10:
                        memory["learned_from_dreams"].pop(0)
                    memory["learned_from_dreams"].append(lesson)
                    save_memory(memory)
                    
                    log_dream_action(f"RESEARCH: Researched '{topic}'. Summary: {summary.strip()}")
                    
                    if ui_callback_fn:
                        ui_callback_fn('reflect_mode', {'active': True, 'logs': get_dream_logs()})
                except Exception as e:
                    print(f"Dream Daemon learning failed: {e}")
                    log_dream_action(f"RESEARCH: Failed research on '{topic}': {e}")
                    
        # Sleep for 180 seconds (3 minutes) before the next dream cycle
        # This gives Ollama enough time to unload the model and free system memory/RAM!
        for _ in range(180):
            if awake:
                break
            time.sleep(1.0)
            
    print("Ren has woken up. Dreamscape reflection daemon stopped.")
    log_dream_action("DREAM_DAEMON: Stopped. Ren has woken up.")

def start_dream_daemon(ui_callback_fn):
    global dream_daemon_thread
    if dream_daemon_thread and dream_daemon_thread.is_alive():
        return
    dream_daemon_thread = threading.Thread(
        target=dream_reflection_loop,
        args=(ui_callback_fn,),
        daemon=True
    )
    dream_daemon_thread.start()

def start_assistant(ui_callback=None, stop_event=None):
    global gs_running
    global global_ui_callback
    global awake
    global_ui_callback = ui_callback

    if ui_callback:
        ui_callback('status', 'initializing')

    import voice
    original_speak = voice.speak
    def speak(text):
        if ui_callback:
            ui_callback('assistant_speech', text)
        original_speak(text)

    # Ensure skills folder exists
    skills_dir = os.path.join(os.path.dirname(os.path.abspath(__file__)), "skills")
    os.makedirs(skills_dir, exist_ok=True)
    
    # Initialize lists and modules
    refresh_skills_ui()
    # Check internet availability for Speech Recognition
    from voice import is_internet_available
    internet_active = is_internet_available()
    
    status = system_status()
    gesture = GestureController()
    
    if internet_active:
        try:
            recognizer = sr.Recognizer()
            mic = sr.Microphone()

            recognizer.dynamic_energy_threshold = True  
            recognizer.energy_threshold = 180

            with mic as source:
                print("Adjusting for background noise... Please wait.")
                recognizer.adjust_for_ambient_noise(source, duration=0.5)
            
            print("Speech Recognition initialized.")
            if ui_callback:
                ui_callback('status', 'initialized')
        except Exception as e:
            print(f"Microphone or Speech Recognition setup error: {e}")
            internet_active = False
            
    if not internet_active:
        print("No internet connection detected. Running in Offline Type Command Mode.")
        if ui_callback:
            ui_callback('status', 'offline')

    awake = True

    # Voice listener thread function
    if internet_active:
        def mic_listener():
            global is_processing
            with mic as source:
                while stop_event is None or not stop_event.is_set():
                    if is_processing:
                        time.sleep(0.2)
                        continue
                    
                    if ui_callback:
                        ui_callback('status', 'listening' if awake else 'offline')
                    try:
                        audio_data = recognizer.listen(source, timeout=1.0, phrase_time_limit=8)
                        if is_processing:
                            continue
                        if ui_callback:
                            ui_callback('status', 'thinking')
                        raw_text = recognizer.recognize_google(audio_data)
                        text = raw_text.lower().strip()
                        if text:
                            input_queue.put(('speech', raw_text))
                    except sr.WaitTimeoutError:
                        continue
                    except sr.UnknownValueError:
                        continue
                    except sr.RequestError:
                        print("API Request connection error.")
                        time.sleep(1.0)
                        continue
                    except Exception as e:
                        print(f"Mic listener error: {e}")
                        time.sleep(0.5)
                        continue

        # Start the mic listener thread
        listener_thread = threading.Thread(target=mic_listener, daemon=True)
        listener_thread.start()

    if internet_active:
        speak("Hello Sadiq sir, glad to see you again.")
        print("Listening... Speak or type now!")
    else:
        speak("Hello Sadiq sir. Running in offline type mode. Voice recognition is disabled.")
        print("Offline mode active. Type your commands in the text box!")

    while stop_event is None or not stop_event.is_set():
        if ui_callback:
            ui_callback('status', ('listening' if awake else 'offline') if internet_active else 'offline')
        
        try:
            # Wait for text/speech prompt from queue
            try:
                input_type, raw_text = input_queue.get(timeout=0.2)
            except queue.Empty:
                continue

            global is_processing
            is_processing = True

            text = raw_text.lower().strip()
            if not text:
                is_processing = False
                continue

            print(f"Processing input ({input_type}): {text}")
            if ui_callback:
                ui_callback('user_speech', raw_text)
                ui_callback('status', 'thinking')
                ui_callback('agent_stage', 'prompt')
                time.sleep(0.3)
                ui_callback('agent_stage', 'intent')
                time.sleep(0.3)

            if "sleep" in text:
                awake = False
                speak("Ok. Going to sleep.")
                if ui_callback:
                    ui_callback('reflect_mode', {'active': True, 'logs': get_dream_logs(), 'manual': True})
                is_processing = False
                continue

            if any(word in text for word in WAKE_WORD) or any(word in text for word in ["wake", "wake up", "get up", "ren"]):
                awake = True
                speak("Hello Sadiq..")
                if ui_callback:
                    ui_callback('reflect_mode', {'active': False, 'logs': []})
                is_processing = False
                continue

            if not awake:
                is_processing = False
                continue

            if "youtube" in text or "tube" in text or "toob" in text:
                speak("Opening YouTube")
                webbrowser.open(YOUTUBE)
                is_processing = False
                continue

            if (
                "shut down" in text
                or "turn off" in text
                or "shut" in text
            ):
                speak("Shutting down")
                break

            if "who are you" in text or "introduction" in text:
                speak("I am a voice assistant made by Sadiq . I am here to help you.")
                is_processing = False
                continue

            if "calculator" in text or "calculate" in text:
                speak("Opening calculator sir.")
                subprocess.Popen(["calc"])
                is_processing = False
                continue

            if (
                "notepad" in text
                or "note" in text
                or "not bad" in text
                or "open notbad" in text
                or "bad" in text
            ):
                speak("Opening notepad")
                subprocess.Popen(["notepad"])
                is_processing = False
                continue

            if any(word in text for word in FILE_EXPLORER):
                speak("Opening File Manager")
                os.system("explorer")
                is_processing = False
                continue

            if "system usage" in text or "cpu usage" in text:
                speak(str(status))
                is_processing = False
                continue

            if any(word in text for word in PRASIE_WORD):
                speak("Glad I helped you.")
                is_processing = False
                continue

            if (
                "camera" in text
                or "gesture" in text
                or "gesture mode" in text
                or "hand" in text and "open" in text
            ) and gs_running == False:
                speak("Opening gesture mode")
                gesture.start()
                gs_running = True
                if ui_callback:
                    ui_callback('module_status', ('gesture', 'active', True))
                is_processing = False
                continue

            elif gs_running == True and ("stop" in text or "close" in text):
                gs_running = False
                speak("Closing gesture mode")
                gesture.stop()
                if ui_callback:
                    ui_callback('module_status', ('gesture', 'stdby', False))
                is_processing = False
                continue

            if (
                    "train neural network" in text
                    or "start neural network training" in text
                    or "run nn model" in text
                ):
                    speak("Opening Number guessing mode ")
                    if ui_callback:
                        ui_callback('module_status', ('nn', 'active', True))
                    start_nn()
                    if ui_callback:
                        ui_callback('module_status', ('nn', 'stdby', False))
                    is_processing = False
                    continue

            # -------- ADD TASKS TO TO-DO LIST --------
            if "add these task" in text or "add to do today" in text or "add task to do" in text or "add task" in text or "add this task" in text:
                speak("Sure, tell me your tasks.")
                print("Listening for task details")
                
                try:
                    # Listen specifically for the task details
                    if input_type == 'speech':
                        audio_data = recognizer.listen(source, timeout=10, phrase_time_limit=10)
                        task_input = recognizer.recognize_google(audio_data).strip()
                    else:
                        # Wait for user input in queue for up to 15 seconds
                        try:
                            _, task_input = input_queue.get(timeout=15)
                        except queue.Empty:
                            task_input = None
                    
                    if task_input:
                        add_task(task_input)
                        print(f"Saved task: {task_input}")
                        speak("I have added it to your list.")
                    else:
                        speak("I didn't catch any task details.")
                        
                except sr.UnknownValueError:
                    speak("Sorry, I didn't hear the task clearly.")
                except Exception:
                    speak("There was an issue saving your task.")
                is_processing = False
                continue

            # -------- READ OUT ALL TASKS --------
            if "tell my task" in text or "what are my task" in text or "read my to do list" in text or "what i have to do toady" in text:
                all_tasks = get_all_tasks()
                
                if not all_tasks:
                    speak("Your to-do list is completely empty, sir.")
                else:
                    speak("Here are your tasks for today:")
                    for idx, single_task in enumerate(all_tasks, 1):
                        speak(f"Task number {idx}: {single_task}")
                        print(f"{idx}. {single_task}")
                is_processing = False
                continue

            if "who is sadiq" in text or "who is your creator" in text:
                speak("Sadik is a software developer and the creator of this assistant He is passionate about technology and AI He is a great inventor and I am glad to be his assistant.")
                is_processing = False
                continue
            
            if "what is your name" in text or "what should i call you" in text:
                speak("You can call me Ren, sir.")
                is_processing = False
                continue

            if "explain your architecture" in text or "how you work" in text:
                speak("I am built using Python and utilize various libraries for speech recognition, text-to-speech, and system control. I listen for specific wake words to activate and can perform tasks like opening applications, managing a to-do list, and even controlling a gesture recognition mode. My architecture is designed to be modular, allowing me to integrate new features easily.")
                is_processing = False
                continue

            if "open settings" in text or "open setting" in text or "setting" in text:
                speak("Opening settings")
                subprocess.Popen(["ms-settings:"])
                is_processing = False
                continue

            if "make a folder" in text or "create folder" in text or "new folder" in text:
                speak("Creating a new folder on the desktop")
                desktop_path = os.path.join(os.path.expanduser("~"), "Desktop")
                new_folder_path = os.path.join(desktop_path, "New Folder")
                try:
                    os.makedirs(new_folder_path, exist_ok=True)
                    speak("New folder created on the desktop.")
                    speak("Do you want to rename it?")
                    
                    rename_answer = None
                    if input_type == 'speech':
                        try:
                            audio_data = recognizer.listen(source, timeout=5, phrase_time_limit=3)
                            rename_answer = recognizer.recognize_google(audio_data).strip().lower()
                        except Exception:
                            pass
                    else:
                        try:
                            _, rename_answer = input_queue.get(timeout=8)
                            rename_answer = rename_answer.lower()
                        except queue.Empty:
                            pass
                            
                    if rename_answer and ("yes" in rename_answer or "yeah" in rename_answer or "yep" in rename_answer):
                        speak("What name do you want to give it?")
                        folder_name = None
                        if input_type == 'speech':
                            try:
                                audio_data = recognizer.listen(source, timeout=10, phrase_time_limit=5)
                                folder_name = recognizer.recognize_google(audio_data).strip()
                            except Exception:
                                pass
                        else:
                            try:
                                _, folder_name = input_queue.get(timeout=15)
                            except queue.Empty:
                                pass
                                
                        if folder_name:
                            new_folder_path_renamed = os.path.join(desktop_path, folder_name)
                            os.rename(new_folder_path, new_folder_path_renamed)
                            speak(f"Folder renamed to {folder_name}.")
                        else:
                            speak("I didn't catch the folder name.")
                except Exception as e:
                    speak("Sorry, I couldn't create the folder.")
                    print(f"Error creating folder: {e}")
                is_processing = False
                continue

            if "delete folder" in text or "remove folder" in text or "delete this folder" in text:
                speak("Which folder do you want to delete?")
                folder_name = None
                if input_type == 'speech':
                    try:
                        audio_data = recognizer.listen(source, timeout=10, phrase_time_limit=5)
                        folder_name = recognizer.recognize_google(audio_data).strip()
                    except Exception:
                        pass
                else:
                    try:
                        _, folder_name = input_queue.get(timeout=15)
                    except queue.Empty:
                        pass
                        
                if folder_name:
                    desktop_path = os.path.join(os.path.expanduser("~"), "Desktop")
                    folder_path = os.path.join(desktop_path, folder_name)
                    try:
                        if os.path.exists(folder_path) and os.path.isdir(folder_path):
                            os.rmdir(folder_path)
                            speak(f"{folder_name} has been deleted.")
                        else:
                            speak(f"{folder_name} does not exist on the desktop.")
                    except Exception as e:
                        speak("Sorry, I couldn't delete the folder.")
                        print(f"Error deleting folder: {e}")
                else:
                    speak("I didn't catch the folder name.")
                is_processing = False
                continue

            else:
                print("Sending to Ollama Agent...")
                run_agent_loop(text, speak, ui_callback)
                refresh_skills_ui()  # Update the Unlocked Skills list in the GUI if a new skill was created
                is_processing = False
                continue
                
        except Exception as e:
            print(f"Error in main loop: {e}")
        finally:
            if is_processing:
                if ui_callback:
                    ui_callback('agent_stage', 'idle')
                is_processing = False

if __name__ == "__main__":
    start_assistant()
