import subprocess

def open_folder(folder_path):
    try:
        subprocess.run(['explorer', folder_path], check=True)
        speak("Folder opened successfully!")
    except Exception as e:
        speak(f"Failed to open folder. Error: {e}")

open_folder("/path/to/your/folder")