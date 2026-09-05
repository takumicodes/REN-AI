import psutil

def main():
    """
    Checks the current battery percentage and power status of the laptop.
    Returns a formatted string with the details.
    """
    try:
        battery = psutil.sensors_battery()
        if battery is None:
            return "Error: No battery detected. This system might be a desktop or the battery driver is missing."

        percent = battery.percent
        power_plugged = battery.power_plugged
        
        status = "Plugged In" if power_plugged else "Discharging"
        
        return f"Battery Status: {percent}% | Power State: {status}"
    except Exception as e:
        return f"An error occurred while checking battery status: {str(e)}"

if __name__ == "__main__":
    print(main())