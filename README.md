# 🪐 REN-AI: Autonomous Cognitive Assistant & Desktop System

**REN-AI** is a next-generation, local-first autonomous cognitive assistant and Windows desktop system designed to adapt, learn, monitor, and optimize your machine. Built on a modular Python core with high-performance neon cyber HUDs, REN-AI doesn't just respond to prompts—it autonomously writes its own code skills, patches its own errors, educates itself by reading books during sleep cycles, and silently observes Windows system health with **100% human-driven control and zero AI slop**.

---

## 🚀 Key Features

### 1. 🖥️ REN-AI Windows Control Center (`Ren_Desktop_Assistant/`) [v1.3.0]
* **Pure Windows Native GUI & Standalone EXE:** Launch `Ren Desktop Assistant.exe` for an instant, high-DPI cyber Control Center without command-line dependencies or external runtimes.
* **14 Specialized Control Centers:**
  * 📊 **Dashboard:** Real-time hardware telemetry (CPU, RAM, Disk, Power), active context detection, and pending human-driven recommendations.
  * ⚡ **Process Explorer:** Interactive process viewer with CPU/RAM sorting, search, and core Windows system shields preventing accidental OS termination.
  * 🔋 **Power Center:** 1-click power scheme switcher (Balanced, High Performance, Power Saver, Ultimate) and official HTML battery report generator.
  * 🧹 **Storage & Cleaner:** Multi-target scan (User temp, Windows temp, shader caches, crash dumps, Delivery Optimization, thumbnail cache) + 1-click Recycle Bin purge and storage analyzer.
  * 🚀 **Startup Manager:** Registry (HKCU/HKLM) and folder startup apps inspector with safe disable/enable toggles and rollback preservation.
  * ⚙️ **Services Manager:** Enumerate services with standard user registry fallback, core service protection, and startup type management.
  * 📦 **Apps Manager:** Installed Win32 & UWP programs inspector with publisher, version, size, and uninstaller launcher.
  * 🛠️ **Tweaks & Privacy:** Explorer tweaks (extensions, hidden files, compact view, taskbar end task) + Privacy hardening (Ad ID, telemetry, activity history) with 1-click rollback.
  * 🌐 **Network Center:** Adapter telemetry, ping latency test, DNS resolver cache flush with verification, and active socket connections monitor.
  * 🩺 **Health & Restore:** Drive dirty queries, Windows System Event Log error queries, file integrity guides (SFC/DISM), and System Restore points manager & creator.
  * 🎮 **Modes & Gaming:** 4 operational profiles (Programmer, Gaming, Balanced, Performance), Developer Arsenal (winget installer, dev caches cleaner), and Chris Titus WinUtil integration.
  * 📈 **Benchmark Center:** Deterministic, offline 3-part benchmark (CPU SHA-256 rounds, RAM copy bandwidth, Disk sequential write/read) with composite scores and history tracking.
  * 📜 **Change History & Rollback:** Persistent audit log of all system changes with pre/post-state capture and 1-click rollback execution.
  * ⚙️ **Preferences & Support:** Downloads folder settings with category organization and undo, YouTube @cyan_code channel link, and GitHub community links.
* **100% Human-Driven Agency:** `Observe -> Understand -> Explain -> Recommend -> Ask User -> Execute -> Verify -> Rollback`. Zero unsolicited chatbot slop.
* **Single-Instance Enforcement & System Tray:** Named Windows Mutex prevents multiple copies; closing to tray continues whisper-quiet background monitoring.

### 2. 🌌 Autonomous Core HUD & Cognitive Systems
* **Neon Cyber HUD:** High-performance frontend built with Vanilla HTML/CSS/JS via Pywebview, featuring sliding control panels, status LEDs, dynamic diagnostics indicators, and a center-stage particle dynosphere.
* **Dynamic Connectivity Fallbacks:**
  * **Online Mode:** Speech recognition and high-quality cloud voice synthesis (Edge TTS).
  * **Offline Mode:** Seamless fallback to silent keyboard input (Type Command Mode) and local SAPI5 speech synthesis (`pyttsx3`) when no internet is detected.
* **Self-Mutation & Skill Generation:** Ren writes its own Python skills on command, saves them to `skills/`, updates sidebar menus, and displays advancement unlocked popups.
* **Cognitive Dream / Reflect Mode:**
  * Triggered automatically after 1 minute of user inactivity or manually by typing/saying `sleep`.
  * Reflects on past sessions, identifies knowledge gaps, and summarizes book passages from Project Gutenberg to memory.
* **System Downloads Maintenance:** Cleans and organizes Windows Downloads periodically during reflection cycles.

### 3. 📱 Mobile Web Client & Remote Access
* **Local Wi-Fi Access:** Access Ren from your phone or tablet on the same Wi-Fi network at `http://<YOUR_PC_IP>:8000`.
* **Zero-Config HTTPS Tunnel:** Instant global `https://*.trycloudflare.com` URL with SSL encryption, 6-character passkey security, and camera QR code login.
* **PWA Standalone App:** Install Ren as a full-screen native mobile application with Web Speech API voice input and real-time Server-Sent Events (SSE) token streaming.

---

## 📦 Installation & Setup

### Quick Start: Desktop Assistant
Run the standalone executable:
```bash
Ren_Desktop_Assistant/Ren Desktop Assistant.exe
```

Or run from source:
```bash
python Ren_Desktop_Assistant/main.py
```

### Quick Start: Core REN-AI HUD
```bash
python gui.py
```
Click **INITIALIZE CORE** on the startup screen to launch the reactor and activate the neon HUD panels.

### Quick Start: Mobile Web Server
```bash
# Local Wi-Fi
python server.py

# Global Remote Access (Cloudflare HTTPS Tunnel)
python server.py --public
```

---

## 🎮 Desktop Assistant CLI & Script Usage

```bash
# Launch GUI
python Ren_Desktop_Assistant/main.py

# Launch interactive terminal cyber dashboard
python Ren_Desktop_Assistant/main.py --cli

# Launch silent headless background daemon
python Ren_Desktop_Assistant/main.py --bg

# Recompile standalone executable (PyInstaller)
python Ren_Desktop_Assistant/build_exe.py

# Run complete 21-test verification suite
python -m unittest Ren_Desktop_Assistant/tests/test_desktop_assistant.py
```

---

## ❤️ Community, Support & Contributing

### 📺 YouTube Channel
Follow **[@cyan_code](https://www.youtube.com/@cyan_code)** on YouTube for AI development devlogs, architecture walkthroughs, tutorials, and project showcases:
* **YouTube:** [https://www.youtube.com/@cyan_code](https://www.youtube.com/@cyan_code)

### ⭐ GitHub Support & Contribution
* **Repository:** [https://github.com/takumicodes/REN-AI](https://github.com/takumicodes/REN-AI)
* **Issues:** [https://github.com/takumicodes/REN-AI/issues](https://github.com/takumicodes/REN-AI/issues)
* **Pull Requests:** [https://github.com/takumicodes/REN-AI/pulls](https://github.com/takumicodes/REN-AI/pulls)

We welcome community contributions! Please star the repository, report bugs, suggest skills, and submit pull requests.

---

## 📜 License
Released under the [MIT License](LICENSE).
Built for developers by developers.
Zero AI slop. 100% Human-driven.
