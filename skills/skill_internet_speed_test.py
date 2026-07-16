import subprocess
from pynotifier import Notification

def run_internet_speed_test():
    try:
        # Run the command to check internet speed
        result = subprocess.run(['speedtest-cli'], capture_output=True, text=True)
        
        # Display the results
        sadiq.speak(result.stdout)
        
    except Exception as e:
        sadiq.speak(f"Error checking internet speed: {e}")
    
    finally:
        speak("[DONE]")

run_internet_speed_test()