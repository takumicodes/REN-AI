import os
from ctypes import windll

def get_battery_status():
    battery_info = windll.Win32OLE.CreateObject('WbemScripting.SWbemLocator').ConnectServer('.', 'root\cimv2').ExecQuery("SELECT * FROM Win32_Battery")[0]
    
    percentage = int(battery_info.EstimatedChargeRemaining)
    plugged_in = "Plugged in" if battery_info.PowerState == 1 else "Not plugged in"
    
    speak(f"Current battery percentage: {percentage}% {plugged_in}")
    
    print("[DONE]")

get_battery_status()