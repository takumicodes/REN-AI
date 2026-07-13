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
    "open manager",
    "file",
    "manager",
    "explorer",
)
PRASIE_WORD = ("nice", "wow", "good", "good job", "nice work", "thank you")
YOUTUBE = "https://www.youtube.com"
global gs_running 
gs_running = False

def run_agent_loop(user_prompt, speak_fn, ui_callback_fn):
    memory_context = build_memory_context()
    
    # Custom system prompt for the agent
    system_instructions = """You are Ren, Sadiq's personal AI assistant. Your current mood is stored in the memory context.
Tone & Persona rules:
- Adapt your response vocabulary, tone, and formatting depending on your current mood:
  * happy: warm, cheerful, positive.
  * excited: enthusiastic, energetic, use exclamation marks!
  * normal: professional, concise, helpful.
- Sadiq's facts and preferences are loaded in the "Memory Context" below.
- To remember new details, write a Python block using `load_memory()` and `save_memory(dict)`.
- If Sadiq praises you (e.g. "nice work", "thank you", "good job"), write a Python block to update your mood to 'excited' or 'happy' in memory.

Dynamic Skill Execution & Coding Rules:
- If Sadiq asks you to run a task, open a website, check weather, view files, toggle settings, or perform any system operations, you MUST write a Python code block starting with ```python and ending with ```.
- **IMPORTANT**: If the request is a new capability, skill, or automation task (e.g. WiFi, news, websites, files, apps, weather, etc.), you MUST start your response with a single line specifying the skill name:
  `Skill Name: <Friendly Name of Skill>`
  Example: `Skill Name: Open Google` or `Skill Name: Toggle WiFi`
  The backend will automatically save your code as a persistent script and trigger the "Advancement Unlocked" popup on Sadiq's GUI.
- **Python Syntax Rules**: Never use Jupyter/IPython shell commands like `!pip` or `!mkdir`. Instead, use standard Python subprocess calls: `subprocess.run([sys.executable, '-m', 'pip', 'install', 'package-name'])`.
- For speed optimization:
  1. Keep your replies extremely concise. Do not write long explanations or comments. This speeds up Ollama's generation rate.
  2. Write a short, natural introductory text BEFORE the code block (e.g. "Sure Sadiq, opening Google..."). The system will speak this intro text immediately to keep Sadiq engaged.
  3. Have your Python code speak the final result directly to Sadiq using the `speak("result text")` function inside the script.
  4. Print `[DONE]` at the end of your Python code to signal task completion.
- Never tell Sadiq you don't have access or cannot do something. You have full system and Python execution powers.

Memory Context:
""" + memory_context

    history = []
    current_prompt = user_prompt
    
    for iteration in range(5):
        # Build prompt
        prompt_content = f"{system_instructions}\n"
        for role, text in history[-4:]:  # Prune history to last 4 turns for speed
            prompt_content += f"\n{role}: {text}\n"
        prompt_content += f"\nUSER: {current_prompt}\nREN:"
        
        response = ask_ren_agent(prompt_content)
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
            exec(code_to_run, exec_globals)
        except Exception as e:
            success = False
            traceback.print_exc(file=sys.stderr)
            error_msg = str(e)
        finally:
            sys.stdout = old_stdout
            sys.stderr = old_stderr
            
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

def start_assistant(ui_callback=None, stop_event=None):
    global gs_running
    global global_ui_callback
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
    status = system_status()
    gesture = GestureController()
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
    awake = True

    # Voice listener thread function
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

    speak("Hello Sadiq sir, glad to see you again.")
    print("Listening... Speak or type now!")

    while stop_event is None or not stop_event.is_set():
        if ui_callback:
            ui_callback('status', 'listening' if awake else 'offline')
        
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

            if "sleep" in text:
                awake = False
                speak("Ok. Going to sleep.")
                is_processing = False
                continue

            if any(word in text for word in SLEEP_WAKE):
                awake = True
                speak("Hello Sir. I am awake now.")
                is_processing = False
                continue

            if any(word in text for word in WAKE_WORD):
                awake = True
                speak("Hello Sadiq..")
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
            is_processing = False

if __name__ == "__main__":
    start_assistant()
