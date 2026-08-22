"""
Skill: Defensive Wi-Fi Security & Encryption Profile Analyzer
Provides educational and defensive cybersecurity analysis of Wi-Fi encryption protocols (WPA2/WPA3).
Does NOT perform or provide unauthorized credential cracking.
"""

import subprocess
import sys

def analyze_wifi_security():
    summary = (
        "Wi-Fi Security Analysis:\n"
        "- WPA3-SAE (Simultaneous Authentication of Equals): Recommended. Resistant to offline dictionary attacks.\n"
        "- WPA2-Personal (AES-CCMP): Standard. Secure with long, complex passphrases (>16 characters).\n"
        "- WEP / WPA-TKIP: Deprecated & Insecure. Vulnerable to legacy protocol flaws.\n"
    )
    
    try:
        if sys.platform == "win32":
            result = subprocess.run(["netsh", "wlan", "show", "interfaces"], capture_output=True, text=True, timeout=5)
            if result.returncode == 0:
                summary += f"\nLocal Interface State:\n{result.stdout[:500]}"
    except Exception:
        pass

    return summary

if __name__ == "__main__":
    print(analyze_wifi_security())