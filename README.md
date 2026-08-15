# 🪐 REN-AI: Autonomous Cognitive Assistant

REN-AI is a next-generation, local AI assistant designed to adapt, learn, and maintain itself. Built on a modular Python core and styled with a gorgeous, high-performance neon cyber HUD, REN-AI doesn't just respond to prompts—it autonomously writes its own code skills, patches its own errors, educates itself by reading books during sleep cycles, and organizes your system's download files.

---

## 🚀 Key Features

* **🖥️ Neon Cyber HUD:** A beautiful, responsive frontend built with Vanilla HTML/CSS/JS via Pywebview, featuring sliding control panels, status LEDs, dynamic diagnostics indicators, and a center-stage particle dynosphere.
* **🌐 Dynamic Connectivity Fallbacks:**
  * **Online Mode:** Uses speech recognition and high-quality cloud voice synthesis (Edge TTS).
  * **Offline Mode:** Seamlessly falls back to silent keyboard input (Type Command Mode) and local SAPI5 speech synthesis (`pyttsx3`) when no internet is detected, ensuring 100% startup reliability.
* **🔧 Self-Mutation & Skill Generation:** Ren writes its own Python skills on command, saves them to the `skills/` directory, updates the sidebar menu, and displays a gold *Advancement Unlocked* popup card in the UI.
* **💤 Cognitive Dream / Reflect Mode:**
  * Triggered automatically after 1 minute of user inactivity (idle tracking) or manually by typing/saying `sleep`.
  * The main interface fades, the skills panel collapses, and a central scrolling terminal displays live cognitive log updates.
  * Instantly wakes up upon registering mouse/keyboard movements or wake words.
* **🧬 Autonomous Dream Daemon (Self-Learning):**
  * **Self-Healing Code:** Automatically intercepts Python exceptions, queries the local LLM for code patches, and runs the mutation scripts to fix itself.
  * **Web Book Downloader:** Periodically connects to Project Gutenberg to download and catalog text books.
  * **Self-Education:** Summarizes book passages and technical topics relevant to User skills and youtube channel, saving the knowledge to `memory.json`.
  * **System Organizer:** Scans the Windows `Downloads/` directory and categorizes files (Documents, Images, Archives, Installers) into tidy subfolders.
* 

---


---

## 📦 Installation & Setup
Install Ren_AI_Installer.exe from releases and run it has administrator.

---

## 🎮 Usage Guide

### Booting the System
Launch the assistant by running the main interface script:
```bash
python gui.py
```
Click **INITIALIZE CORE** on the startup screen to launch the reactor and activate the HUD panels.

### Interacting
* **Voice / Chat Commands:** Ask Ren questions or give commands.
* **Creating Skills:** Tell Ren: *"Give yourself a skill to calculate mortgage rates"* or *"Give yourself a skill named internet speed test"*. The system will code, test, save, and install the script automatically.
* **Triggering Sleep:** Type or speak `"sleep"` to put Ren into Dream Mode. Alternatively, leave your computer idle for 1 minute.
* **Waking Up:** Move your mouse, press any key, or say `"wake up"` or `"hello"` to restore the full desktop HUD.
