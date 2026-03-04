from vosk import Model, KaldiRecognizer
import json
import pyttsx3
import numpy
import audioop 
import pyaudio
import time
import webbrowser
import random
import os
import subprocess
import sys
from number_map import normalize_numbers
from system_monitor import system_status
from gesture_control import GestureController
from face_lock import run_face_lock
from nn import start_nn
print("Python", sys.executable)
print("Numpy", numpy.__file__)


# ---------- CONFIG ----------
MODEL_PATH = "vosk-model-small-en-us-0.15"
SAMPLE_RATE = 16000
CHUNK = 3000

WAKE_WORD = ("hello", "hey")
SLEEP_WAKE = ("wake ren", "wake up", "week", "ren", "wake", "up")
FILE_EXPLORER = ("open file", "open explorer", "open explore", 
                 "open file explorer", "open file manager", "open manager", "file","manager","explorer")
PRASIE_WORD = ("nice", "wow", "good", "good job", "nice work", "thank you")

YOUTUBE = "https://www.youtube.com"



# ---------- MAIN ----------
def start_assistant():

    # ---------------- FACE LOCK FIRST ----------------
    print(sys.executable)
    print("Starting Face Lock...")
    if not run_face_lock():
        print("Face verification failed.")
        return

    print("Access granted.")

    # ---------------- INIT SYSTEM ----------------
    status = system_status()
    gesture = GestureController()

    # Load Vosk
    model = Model(MODEL_PATH)
    recogniser = KaldiRecognizer(model, SAMPLE_RATE)
    print("Model loaded")

    # Microphone
    p = pyaudio.PyAudio()
    stream = p.open(
        format=pyaudio.paInt16,
        channels=1,
        rate=SAMPLE_RATE,
        input=True,
        frames_per_buffer=CHUNK
    )
    stream.start_stream()
    print("Listening...")

    awake = True

    # ---------- SPEAK FUNCTION ----------
    def speak(text):
        stream.stop_stream()
        engine = pyttsx3.init()
        engine.setProperty("rate", 130)
        engine.say(text)
        engine.runAndWait()
        stream.start_stream()

    # ---------- NUMBER EXTRACTOR ----------
    def extract_numbers(text):
        nums = []
        for word in text.split():
            try:
                nums.append(float(word))
            except ValueError:
                pass
        return nums

    speak("Welcome to your desktop sir.")

    # ---------------- MAIN LOOP ----------------
    while True:

        data = stream.read(CHUNK, exception_on_overflow=False)

        if recogniser.AcceptWaveform(data):
            result = json.loads(recogniser.Result())
            text = result.get("text", "").lower()
            text = text.split()

            if not text:
                continue

            print("Input:", text)
            
            #-------------------------- ADD FUNCTIONS FROM HERE -------------------------------

            # -------- SLEEP --------
            if "sleep" in text:
                awake = False
                speak("Ok. Going to sleep.")
                continue

            # -------- WAKE --------
            if any(word in text for word in WAKE_WORD + SLEEP_WAKE):
                awake = True
                speak("Hello Sir. How can I help you?")
                continue

            if not awake:
                continue

            # -------- OPEN YOUTUBE --------
            if "youtube" in text or "tube" in text or "toob" in text:
                speak("Opening YouTube")
                webbrowser.open(YOUTUBE)
                continue

            # -------- SHUTDOWN --------
            if "shut down" in text or "turn off" in text or "shut" in text or "down" in text:
                speak("Shutting down")
                break

            # -------- INTRO --------
            if "who are you" in text or "introduction" in text:
                speak("I am a voice assistant made by NAME :) . I am here to help you.")
                continue

            # -------- CALCULATOR --------
            if "calculator" in text or "calculate" in text:
                speak("Opening calculator sir.")
                subprocess.Popen(['calc'])
                continue

            # -------- ADDITION --------
            if "add" in text or "sum" in text or "plus" in text:
                text_norm = normalize_numbers(text)
                numbers = extract_numbers(text_norm)

                if len(numbers) >= 2:
                    result = sum(numbers)
                    speak(f"The sum is {result}")
                else:
                    speak("I need at least two numbers.")
                continue

            # -------- NOTEPAD --------
            if "notepad" in text or "note" in text or "not bad" in text or "open notbad" in text or "not" in text or "bad" in text:
                speak("Opening notepad")
                subprocess.Popen(['notepad'])
                continue

            # -------- FILE EXPLORER --------
            if any(word in text for word in FILE_EXPLORER):
                speak("Opening File Manager")
                os.system('explorer')
                continue

            # -------- SYSTEM STATUS --------
            if "system" in text or "usage" in text:
                speak(str(status))
                continue

            # -------- PRAISE --------
            if any(word in text for word in PRASIE_WORD):
                speak("Glad I helped you.")
                continue

            # -------- GESTURE MODE --------
            if "camera" in text or "gesture" in text or "gesture mode" in text or "hand" in text:
                speak("Opening gesture mode")
                gesture.start()
                continue
            
            #----------NUMBER GUESSING MODE (NEURAL NETWORK)------------------#
            if "neural network" in text or "cnn"in text or "nn" in text or "number" in text or "number recognition" in text or "mnist dataset" in text or "number" in text or "neural" in text:
                speak("Opening Number guessing mode ")
                start_nn()
                continue
                


if __name__ == "__main__":
    start_assistant()
            
            
