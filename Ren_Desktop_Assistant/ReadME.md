# 🪐 REN-AI Windows Control Center (v1.3.0)

**REN-AI Windows Control Center** is a modern, lightweight, autonomous Windows management and optimization platform. Combining the power of modern Windows utilities (like Wintoys and PowerToys) with REN's cyber aesthetic and zero-slop architecture, it gives developers, power users, and gamers granular, transparent control over their entire Windows operating system.

---

## 🧭 The Core Philosophy: 100% Human-Driven vs. AI Slop

Unlike tools like Microsoft Copilot that force disruptive popups, consume excess background RAM, and make destructive assumptions, REN adheres to strict developer-first invariants:

```
Observe ──> Understand ──> Explain ──> Recommend ──> Ask User ──> Execute ──> Verify ──> Rollback
```

* **Human Agency First:** REN never alters system settings, terminates processes, or cleans files without explicit human confirmation.
* **Explainable Transparency:** Every single action explains what it does, why it is recommended, measurable impact, and exact command preview before execution.
* **Post-Execution Verification:** Confirms that registry keys, services, or reclaimed disk bytes actually took effect.
* **1-Click Audit & Rollback:** Every modification captures pre-state and post-state snapshots, stored in a persistent local audit history (`change_history.json`). Any action can be reversed in 1 click.
* **Whisper-Quiet Background Daemon:** Runs silently in the system tray, consuming virtually zero CPU cycles.

---

## 📦 Standalone Executable & Distribution

Compiled into a standalone, portable Windows 64-bit executable with embedded cyber logo and zero dependencies:
```
Ren_Desktop_Assistant/Ren Desktop Assistant.exe
```

* **Zero External Dependencies:** Self-contained executable with embedded Python runtime and native Windows API bindings.
* **Portable & High-DPI Aware:** Runs from any folder or USB drive with crisp rendering on 1080p, 2K, and 4K displays.
* **Single-Instance Enforcement:** Protected by a native Windows Mutex; launching a second instance automatically activates and brings the existing window to the front.
* **System Tray Behavior:** Closing the window (`X`) minimizes to the system tray while the background observer monitors health silently.

---

## 🖥️ The 14 Control Center Modules

### 1. 📊 Dashboard
* **Hardware Telemetry Gauges:** Real-time meters for CPU utilization, RAM usage (used / available GB), primary drive space, and battery status.
* **System Context Sensor:** Automatically detects active workload (`PROGRAMMING`, `GAMING`, `BROWSING`, `MEDIA`, `GENERAL`).
* **Human-Driven Recommendations Queue:** Anti-spam, rate-limited optimization proposals with interactive `[✓ Approve & Apply]` and `[✗ Dismiss]` buttons.

### 2. ⚡ Process Explorer
* Real-time process table displaying PID, Process Name, CPU%, RAM (MB), and Status.
* Sort by memory, CPU, or name with instantaneous live search filtering.
* **🛡️ Critical OS Process Shield:** Identifies and prevents terminating core Windows processes (`csrss.exe`, `lsass.exe`, `services.exe`, `explorer.exe`, etc.) to protect against system crashes or BSODs.

### 3. 🔋 Power Center
* 1-click power scheme switcher (`Balanced`, `High Performance`, `Power Saver`, `Ultimate Performance`).
* Real-time battery status and AC wall-power detection.
* **📑 Battery Health Report:** Generates an official Windows battery diagnostics HTML report via `powercfg /batteryreport` and opens it in your default browser.

### 4. 🧹 Storage & Cleaner Center
* **Itemized Scan & Preview:** Calculates exact file count and megabytes across:
  * User Temporary Files (`%TEMP%`)
  * Windows System Temp (`C:\Windows\Temp`)
  * Delivery Optimization Cache
  * Windows Error Reporting & Crash Dumps
  * DirectX, Nvidia, and AMD GPU Shader Caches
  * Windows Explorer Thumbnail Cache
  * Windows Recycle Bin
* **Zero-Destruction Cleaning:** Gracefully handles active file locks without crashing.
* **Post-Clean Verification:** Confirms actual megabytes reclaimed.
* **Storage Analyzer:** Overview of all connected drives and top space consumers.

### 5. 🚀 Startup Apps Manager
* Scans all Windows startup locations: `HKCU\Software\...\Run`, `HKLM\Software\...\Run`, and User Startup folders.
* Safe enable and disable toggles: disabled items are preserved in a dedicated backup subkey for 100% reversible restoration.

### 6. ⚙️ Services Manager
* Comprehensive enumeration of Windows Services with fallback to `HKLM\SYSTEM\CurrentControlSet\Services` for un-elevated execution.
* Classifies services into **Core Windows**, **Telemetry**, **Third-Party**, and **General**.
* Core Windows Shield prevents stopping or disabling essential system components.
* Controls: `Start`, `Stop`, `Restart`, and `Startup Type` (`Automatic`, `Manual`, `Disabled`).

### 7. 📦 Apps Manager
* Deep scan of installed Win32 programs and UWP packages across 32-bit and 64-bit registry uninstall keys.
* Displays publisher, version, install date, and estimated disk footprint.
* Launches uninstallers with confirmation and command preview.

### 8. 🛠️ Tweaks & Privacy Center
* **Explorer & System Tweaks:**
  * Show known file extensions (`HideFileExt` = 0)
  * Show hidden files and folders (`Hidden` = 1)
  * Enable Compact View in Windows 11 Explorer
  * Enable "End Task" on Taskbar right-click
  * Eliminate Windows startup application launch delay
  * Disable lock screen tips and Spotlight ads
* **Privacy & Telemetry Hardening:**
  * Disable Windows Advertising ID tracking
  * Disable Tailored Experiences with diagnostic data
  * Disable Activity Feed cloud synchronization
  * Set Feedback prompt frequency to Never
* All tweaks backed by registry read/write with 1-click instant rollback.

### 9. 🌐 Network Center
* Network adapter telemetry: active interface name, IPv4 address, MAC address, connection status, and link speed.
* **Ping Latency Tester:** Tests latency and packet loss against any target host (default `1.1.1.1`).
* **Flush DNS Resolver Cache:** Runs `ipconfig /flushdns` with execution confirmation.
* Active Network Sockets monitor inspecting `ESTABLISHED` connections.

### 10. 🩺 Health & System Restore Center
* **Drive Health:** Queries volume dirty bit status via `fsutil dirty query`.
* **System Event Log Monitor:** Retrieves recent Critical and Error entries from the Windows System Event Log.
* **Windows File Integrity:** Ready-to-run recommendations for `sfc /scannow` and `DISM /Online /Cleanup-image /Restorehealth`.
* **System Restore Manager:** Lists existing Windows Restore Points and provides a 1-click `[➕ Create Restore Point Now]` button.

### 11. 🎮 Modes & Gaming Center
* **4 Tailored Operational Profiles:**
  * 🛠️ **Programmer Mode:** Ultimate Performance on AC, Balanced on battery, low-RAM visual tuning, dev caches cleaning.
  * 🎮 **Gaming Mode:** Low desktop latency, highest CPU/GPU power plan, temp files purged, background telemetry silenced.
  * ⚖️ **Balanced Mode:** Quiet, unnoticeable background maintenance.
  * 🚀 **Performance Mode:** Full hardware clock boosts and standby RAM liberation.
* **Developer Tools Arsenal:**
  * Inspects status of Git, VS Code, Python 3, Windows Terminal, Node.js, 7-Zip, Rust toolchain, and Docker Desktop.
  * 1-click Winget installer command generator.
  * 🧹 Dev Caches cleaner (`__pycache__`, `.pytest_cache`, `.mypy_cache`).
* **Chris Titus Tech WinUtil Integration:**
  * Directly launches the popular CTT WinUtil in an elevated PowerShell session (`irm https://christitus.com/win | iex`) with `-NoExit` so the window stays open.

### 12. 📈 Benchmark Center
* Deterministic, offline, reproducible hardware test:
  * **CPU Benchmark:** SHA-256 cryptographic hashing rounds.
  * **Memory Benchmark:** Buffer allocation and memory copy bandwidth.
  * **Disk Benchmark:** Sequential 16MB temporary write/read speed.
* Generates a normalized Composite Score.
* Historical scores table to compare PC performance before and after optimizations.

### 13. 📜 Change History & Rollback Center
* Complete audit trail of all changes performed by REN-AI.
* Records entry ID, timestamp, action title, category, execution status, and verification status.
* **`[↩️ Rollback Selected Action]` Button:** Automatically reverses the change using captured before-state snapshots.

### 14. ⚙️ Preferences & Community Support
* Custom Downloads folder picker with intelligent categorization (`Code_and_Dev`, `Documents`, `Images`, `Media`, `Archives`, `Installers`).
* 1-click Downloads undo rollback engine.
* **Creator Support:**
  * 📺 YouTube Channel: [@cyan_code](https://youtube.com/@cyan_code)
  * ⭐ GitHub Repository: [takumicodes/REN-AI](https://github.com/takumicodes/REN-AI)
  * 🐛 Issue reporting and Pull Request submission links.

---

## 🛠️ CLI & Headless Daemon Modes

While REN-AI provides a full GUI, it can also be run entirely from the terminal or as a headless background Windows service:

```bash
# Launch Modern Cyber GUI Control Center (Default)
python Ren_Desktop_Assistant/main.py

# Launch Interactive Cyber Terminal Dashboard
python Ren_Desktop_Assistant/main.py --cli

# Run Headless Background Observer Service
python Ren_Desktop_Assistant/main.py --bg

# Display Version
python Ren_Desktop_Assistant/main.py --version
```

---

## 🧪 Comprehensive Test Suite

All modules are accompanied by unit tests verifying safety invariants, fallback behavior, critical shields, and rollback mechanics:

```bash
python -m unittest Ren_Desktop_Assistant/tests/test_desktop_assistant.py
```

* 36 unit tests covering all hardware monitors, actions, verification, change history, and control center modules.