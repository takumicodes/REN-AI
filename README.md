# 🪐 REN-AI: Autonomous Cognitive Assistant & Desktop System

**REN-AI** is a next-generation, local-first autonomous cognitive assistant and Windows desktop system designed to adapt, learn, monitor, and optimize your machine. Built on a modular Python core with high-performance neon cyber HUDs, REN-AI doesn't just respond to prompts—it autonomously writes its own code skills, patches its own errors, educates itself by reading books during sleep cycles, and silently observes Windows system health with **100% human-driven control and zero AI slop**.

---

## 🚀 Key Features

### 1. 🖥️ REN Desktop Assistant (`Ren_Desktop_Assistant/`)
* **Pure Windows Native GUI & Standalone EXE:** Launch `Ren Desktop Assistant.exe` for an instant, high-DPI cyber HUD without command-line dependencies.
* **First-Install Preferences Wizard:** Set your downloads folder path, select your profession (Software Engineer, Designer, Student, Gamer, General), pick your preferred mode, and configure background behavior.
* **100% Human-Driven Agency:** Never mutates your system or takes destructive actions without explicit user review. No unsolicited chatbot hallucinations or annoying popups like Copilot.
* **Silent Background Observation:** Non-blocking background daemon tracking CPU, RAM, multi-partition storage health, battery drain, AC power status, and foreground context (`PROGRAMMING`, `BROWSING`, `GAMING`, `MEDIA`).
* **3 Intelligent Operational Modes:**
  * 🛠️ **Programmer Mode (Default):** Developer tools inspector & winget installer (Git, VS Code, Python 3, Windows Terminal, Node.js LTS, 7-Zip), low-RAM Windows debloat, compile power boost on AC, and battery saver when mobile.
  * ⚖️ **Balanced Mode:** Whisper-quiet everyday assistant maintaining standard Windows balance.
  * 🚀 **Performance Mode:** Maximum sustained hardware clock boost, high power plan, and standby RAM purging for heavy workloads.
* **Safe Downloads Organizer with Rollback:** Categorizes loose files into Code, Documents, Images, Media, Archives, and Installers. Features dry-run preview, 15-minute protection for active downloads, and **1-click Undo / Rollback** to restore files to their exact original locations.
* **Windows Debloater & Chris Titus Tech Utility (winutil):** Safe toggles to disable Bing Start search, turn off Copilot background processes, tune visual animations for low RAM, clean `%TEMP%` caches, and launch the famous **Chris Titus Tech Windows Utility** (`irm https://christitus.com/win | iex`) in an elevated PowerShell session.
* **Close-to-Background Tray Operation:** When the window is closed, it minimizes to the background and continues observing silently.

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
