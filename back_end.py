"""
REN-AI Backend Integration Core
Connects the local agent runtime with PyWebView GUI, microphone listeners, TTS, gesture controls, and dream mode.
"""

import os
import sys
import time
import json
import queue
import threading
import subprocess
import webbrowser
from typing import Optional, Callable, Any

# Speech & Audio
import speech_recognition as sr
from voice import speak, is_internet_available
import voice

# System & Modules
from system_monitor import system_status
from gesture_control import GestureController
from nn import start_nn
from smart_todo import add_task, get_all_tasks, clear_all_tasks

# New REN Agent Runtime
from ren.core.agent import agent_runtime
from ren.skills.registry import skill_registry
from ren.dream.daemon import dream_daemon
from ren.memory.manager import memory_manager
from ren.monitoring.logger import agent_logger, error_logger

# State flags
is_processing = False
awake = True
gs_running = False
input_queue = queue.Queue()
global_ui_callback: Optional[Callable[[str, Any], None]] = None

WAKE_WORDS = ("hello", "hey", "wake ren", "wake up", "ren", "wake")
PRAISE_WORDS = ("nice", "wow", "good", "good job", "nice work", "thank you")


def stop_operations() -> str:
    """Stops current running agent operations and speaking."""
    global is_processing
    is_processing = False
    agent_logger.info("Stop operations requested.")
    voice.stop_speaking()
    return agent_runtime.stop_operations()


def submit_typed_prompt(prompt: str):
    """Pushes typed input from GUI text box to the execution queue."""
    input_queue.put(('text', prompt))


def get_unlocked_skills() -> list:
    """Returns list of unlocked skill names from SkillRegistry 2.0."""
    return skill_registry.get_unlocked_skill_names()


def refresh_skills_ui():
    """Notifies GUI with current unlocked skill names."""
    global global_ui_callback
    if global_ui_callback:
        skills = get_unlocked_skills()
        global_ui_callback('skills_list', skills)


def get_dream_logs() -> list:
    """Retrieves logs from Dream Mode 2.0 for the GUI reflection panel."""
    return dream_daemon.get_logs()


def start_dream_daemon(ui_callback_fn: Optional[Callable[[str, Any], None]] = None):
    """Starts background dream daemon."""
    dream_daemon.start(ui_callback_fn)


def run_agent_loop(user_prompt: str, speak_fn: Callable[[str], None], ui_callback_fn: Optional[Callable[[str, Any], None]]) -> str:
    """Executes prompt via the new AgentRuntime."""
    return agent_runtime.process_input(user_prompt, speak_fn=speak_fn, ui_callback=ui_callback_fn)


def start_assistant(ui_callback: Optional[Callable[[str, Any], None]] = None, stop_event: Optional[threading.Event] = None):
    """Main assistant background thread running input polling, speech listener, and command handling."""
    global gs_running, global_ui_callback, awake, is_processing
    global_ui_callback = ui_callback

    if ui_callback:
        ui_callback('status', 'initializing')

    def agent_speak(text: str):
        if ui_callback:
            ui_callback('assistant_speech', text)
        speak(text)

    # Refresh skills list on startup
    refresh_skills_ui()

    # Check network connectivity
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
                print("Adjusting microphone for ambient noise...")
                recognizer.adjust_for_ambient_noise(source, duration=0.5)

            if ui_callback:
                ui_callback('status', 'initialized')
        except Exception as e:
            agent_logger.warning(f"Microphone setup unavailable: {e}")
            internet_active = False

    if not internet_active:
        agent_logger.info("Running in Offline / Text Input Mode.")
        if ui_callback:
            ui_callback('status', 'offline')

    awake = True

    # Voice listener thread
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
                        time.sleep(1.0)
                        continue
                    except Exception as e:
                        time.sleep(0.5)
                        continue

        listener_thread = threading.Thread(target=mic_listener, daemon=True)
        listener_thread.start()

    if internet_active:
        agent_speak("Hello sir, glad to see you again.")
    else:
        agent_speak("Hello sir. Running in offline type mode.")

    # Main Command Polling Loop
    while stop_event is None or not stop_event.is_set():
        if ui_callback:
            ui_callback('status', ('listening' if awake else 'offline') if internet_active else 'offline')

        try:
            try:
                input_type, raw_text = input_queue.get(timeout=0.2)
            except queue.Empty:
                continue

            is_processing = True
            text = raw_text.lower().strip()
            if not text:
                is_processing = False
                continue

            agent_logger.info(f"Processing input ({input_type}): {text}")
            if ui_callback:
                ui_callback('user_speech', raw_text)
                ui_callback('status', 'thinking')

            # Sleep / Wake commands
            if "sleep" in text:
                awake = False
                agent_speak("Going to sleep, Sir.")
                if ui_callback:
                    ui_callback('reflect_mode', {'active': True, 'logs': get_dream_logs(), 'manual': True})
                start_dream_daemon(ui_callback)
                is_processing = False
                continue

            if any(w in text for w in WAKE_WORDS):
                awake = True
                dream_daemon.stop()
                agent_speak("Hello sir.")
                if ui_callback:
                    ui_callback('reflect_mode', {'active': False, 'logs': []})
                is_processing = False
                continue

            if not awake:
                is_processing = False
                continue

            # Praise recognition
            if any(w in text for w in PRAISE_WORDS):
                memory_manager.set_system_fact("mood", "excited")
                agent_speak("Glad I could help, Sir.")
                is_processing = False
                continue

            # Gesture Control Commands
            if ("camera" in text or "gesture" in text or ("hand" in text and "open" in text)) and not gs_running:
                agent_speak("Opening gesture recognition mode.")
                gesture.start()
                gs_running = True
                if ui_callback:
                    ui_callback('module_status', ('gesture', 'active', True))
                is_processing = False
                continue

            elif gs_running and ("stop" in text or "close" in text):
                gs_running = False
                agent_speak("Closing gesture mode.")
                gesture.stop()
                if ui_callback:
                    ui_callback('module_status', ('gesture', 'stdby', False))
                is_processing = False
                continue

            # Neural Network Mode
            if "train neural network" in text or "start neural network training" in text or "run nn model" in text:
                agent_speak("Opening neural network mode.")
                if ui_callback:
                    ui_callback('module_status', ('nn', 'active', True))
                start_nn()
                if ui_callback:
                    ui_callback('module_status', ('nn', 'stdby', False))
                is_processing = False
                continue

            # Task & Todo Commands
            if "add task" in text or "add to do" in text or "add this task" in text:
                task_content = text.replace("add task", "").replace("add to do", "").replace("add this task", "").strip()
                if not task_content:
                    agent_speak("Sure, tell me what task to add.")
                    try:
                        _, task_content = input_queue.get(timeout=10)
                    except queue.Empty:
                        task_content = ""

                if task_content:
                    add_task(task_content)
                    agent_speak("Task added to your to-do list.")
                else:
                    agent_speak("No task details received.")
                is_processing = False
                continue

            # Default: Dispatch to Autonomous Agent Runtime
            agent_runtime.process_input(raw_text, speak_fn=agent_speak, ui_callback=ui_callback)
            refresh_skills_ui()

        except Exception as e:
            error_logger.error(f"Error in backend assistant loop: {e}", exc_info=True)
        finally:
            if is_processing:
                if ui_callback:
                    ui_callback('agent_stage', 'idle')
                is_processing = False


if __name__ == "__main__":
    start_assistant()
