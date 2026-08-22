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
  * **Self-Education:** Summarizes book passages and technical topics relevant to Sadiq's skills and youtube channel, saving the knowledge to `memory.json`.
  * **System Organizer:** Scans the Windows `Downloads/` directory and categorizes files (Documents, Images, Archives, Installers) into tidy subfolders.
* **📝 Detailed Action Logging:** Keeps a persistent, timestamped chronicle of all background dream accomplishments in [dream_history.log](file:///D:/Coding%20projects/REN-AI-main/dream_history.log).

---

## 🗺️ System Architecture

```mermaid
graph TD
    User([Sadiq / User]) -->|Keyboard / Voice| HUD[HUD Frontend - pywebview]
    HUD -->|Prompt / Events| Backend[Python Core - back_end.py]
    
    subgraph Offline Mechanics
        Backend -->|Check Socket| NetTest{Internet Connected?}
        NetTest -->|Yes| Online[Edge TTS + SpeechRecognition]
        NetTest -->|No| Offline[pyttsx3 SAPI5 + Keyboard Input Mode]
    end

    subgraph Cognitive Engine
        Backend -->|Ollama Query| LLM[Local Qwen / Ollama]
        Backend -->|Execute Script| Sandbox[exec Namespace Sandbox]
        Sandbox -->|Writes skill_*.py| SkillsDir[skills/ folder]
        Sandbox -->|Saves variables| Memory[memory.json]
    end

    subgraph Dream Daemon (Sleep Mode)
        Backend -->|Idle 1m / 'sleep'| DreamLoop[Dream Reflection Loop]
        DreamLoop -->|Parse tracebacks| Resolver[Self-Mutation Exception Patching]
        DreamLoop -->|Download text books| Gutenberg[Project Gutenberg Reader]
        DreamLoop -->|Scan user system| Clean[Downloads Folder Organizer]
        DreamLoop -->|Write history| LogFile[(dream_history.log)]
    end
```

---

## 📦 Installation & Setup

### Prerequisites
1. **Ollama:** Install [Ollama for Windows](https://ollama.com/) and run the target local LLM (e.g. Qwen / Llama):
   ```bash
   ollama run qwen
   ```
2. **Python:** Python 3.8+ is recommended.

### Dependency Installation
Clone the repository and install the required libraries inside a virtual environment:
```bash
python -m venv .venv
.venv\Scripts\activate
pip install -r requirements.txt
```

---

## 🎮 Usage Guide

### Booting Desktop HUD
Launch the desktop assistant by running:
```bash
python gui.py
```
Click **INITIALIZE CORE** on the startup screen to launch the reactor and activate the HUD panels.

### 📱 Booting Mobile Web Client

#### 1. Local Wi-Fi Access (Same Network)
```bash
python server.py
```
* **Local PC Access:** `http://localhost:8000`
* **Phone on Same Wi-Fi:** `http://<YOUR_PC_IP>:8000`

#### 2. 🌍 Global Remote Access (Any Country, 4G/5G, Zero-Config HTTPS)
Access REN from anywhere in the world without port forwarding:
```bash
python server.py --public
```
* **Zero-Config Cloudflare HTTPS Tunnel:** Instant global `https://*.trycloudflare.com` URL with SSL encryption.
* **🔒 Passkey Protection:** Auto-generates a 6-character access passkey (or set custom with `--key YOUR_PASSKEY`).
* **📷 Instant QR Code:** Scans directly with your phone camera to open REN with one tap.
* **📱 PWA Standalone Mode:** Tap *"Add to Home Screen"* on Safari/Chrome to install REN as a full-screen native mobile app.
* **🎙 Mobile Microphone Support:** Full Web Speech API voice input unlocked via trusted HTTPS.
* **⚡ Real-time Token Streaming:** Live typewriter responses via Server-Sent Events (SSE).
* **⏹ Instant Cancellation:** Real stop button halts Ollama generation and speech immediately.

### Interacting
* **Voice / Chat Commands:** Ask Ren questions or give commands.
* **Creating Skills:** Tell Ren: *"Give yourself a skill to calculate mortgage rates"* or *"Give yourself a skill named internet speed test"*. The system will code, test, save, and install the script automatically.
* **Triggering Sleep:** Type or speak `"sleep"` to put Ren into Dream Mode. Alternatively, leave your computer idle for 1 minute.
* **Waking Up:** Move your mouse, press any key, or say `"wake up"` or `"hello"` to restore the full desktop HUD.
