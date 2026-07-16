import subprocess

def get_wifi_password_from_handshake(handshake_file):
    try:
        result = subprocess.run(['aircrack-ng', '-w', 'rockyou.txt', handshake_file], capture_output=True, text=True)
        if "KEY FOUND!" in result.stdout:
            return result.stdout.split(":")[2].strip()
        else:
            return None
    except Exception as e:
        speak(f"An error occurred: {e}")
        return None

handshake_file = input("Enter the path to your handshake file (e.g., handshake.cap): ")
password = get_wifi_password_from_handshake(handshake_file)

if password:
    speak(f"The WiFi password is: {password}")
else:
    speak("Failed to retrieve the password. Please check if the handshake file is correct and try again.")

speak("[DONE]")