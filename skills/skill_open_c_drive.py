import subprocess
from os import system

try:
    subprocess.run(['explorer', '/select,', 'C:\\'], check=True)
except Exception as e:
    speak(f"An error occurred while opening C Drive: {e}")
speak("C Drive opened successfully.")
print("[DONE]")