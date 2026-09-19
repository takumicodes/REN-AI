# 🪐 REN-AI Desktop Assistant

The **REN Desktop Assistant** is an intelligent, lightweight Windows desktop application and background system observer. It dynamically monitors hardware health, optimizes system resources, organizes downloads, debloats Windows, and tunes power profiles—all while remaining **100% human-driven** with **zero AI slop**.

---

## 🧭 Core Philosophy: Human-Driven vs. AI Slop

Unlike tools like Microsoft Copilot that interrupt with unwanted popups, run heavy background telemetry, consume high RAM, and make destructive assumptions, REN Desktop Assistant adheres to strict developer-first principles:

* **Human Agency First:** REN never applies system-altering changes (like switching power plans, installing software, debloating Windows, or moving files) without explicit user review and confirmation.
* **Zero Interruptions & Anti-Spam:** Background loops never block on user input. Proactive recommendations are non-intrusive, deduplicated, and rate-limited with cooldowns and quiet hours support.
* **Full Transparency & Rollback:** Every recommendation explains its exact rationale, measurable impact, and command preview. File operations include a dry-run preview and instant undo rollback. Debloat tweaks can be reverted to Windows defaults with 1 click.
* **Low Footprint:** Consumes minimal CPU cycles and runs silently in the background. When closed via the 'X' button, it continues observing in the background without hogging resources.

---

## 📦 Executable & Installation

The entire application is compiled into a standalone Windows executable:
```
Ren_Desktop_Assistant/Ren Desktop Assistant.exe
```
* **Pure Windows Native GUI:** Runs without opening a console window.
* **Portable:** Requires no installation; double-click `Ren Desktop Assistant.exe` to run.
* **High-DPI Aware:** Crisp rendering on 1080p, 2K, and 4K displays.

---

## 🖥️ Graphical Interface & Special Tabs

### 🌟 First-Install Preferences Wizard
Upon first launch (or when re-run from Preferences), REN displays an initial setup wizard:
1. **Downloads Folder Path:** Entry with a native `[📁 Browse]` folder picker.
2. **User Profession:** Tailors resource optimization and developer tools:
   * 💻 *Software Engineer / Developer* (Compile speed, low RAM, dev tool management)
   * 🎨 *Designer / Content Creator* (GPU RAM allocation, media downloads, scratch disks)
   * 📊 *Student / Researcher / Office* (Whisper-quiet operation, documents organization, battery conservation)
   * 🎮 *Gamer / Hardware Power User* (Ultimate performance power plan, max clock boosts, standby RAM purging)
   * ⚙️ *General User* (Balanced Windows operation with zero clutter)
3. **Preferred Operational Mode:** Programmer Mode (Default), Balanced Mode, or Performance Mode.
4. **Silent Background Toggle:** Runs in background on close.

---

### 📑 Special Tabs

#### 1. 📊 Dashboard & System Status Tab
* **Live Hardware Metrics:** Real-time gauges for CPU utilization, RAM usage (used/available GB), primary drive storage, battery percentage (AC plugged vs discharging), and active power plan.
* **Process Context Sensor:** Detects current user activity (`PROGRAMMING`, `BROWSING`, `GAMING`, `MEDIA`, `GENERAL`).
* **⚡ Pending Human-Driven Recommendations:**
  * Displays proposals from the non-intrusive `ActionQueue`.
  * Shows Title, Rationale, Impact, and Command Preview.
  * Interactive `[✓ Approve & Apply]` and `[✗ Dismiss]` buttons.

#### 2. ⚡ Operational Modes & Developer Arsenal Tab
* **3 Operational Modes:**
  * **🛠️ Programmer Mode (Default):** Developer tools compatibility, low-RAM debloat, compile power boost on AC, battery optimization when mobile.
  * **⚖️ Balanced Mode:** Unobtrusive everyday assistant with standard Windows balance.
  * **🚀 Performance Mode:** Maximum sustained hardware clock boost, high power plan, frees standby memory.
* **Developer Tools Arsenal (Winget Integration):**
  * Live status for essential developer tools: Git, Visual Studio Code, Python 3, Windows Terminal, Node.js LTS, 7-Zip.
  * Badges: `✓ INSTALLED` (green) or `⚠ MISSING` (amber).
  * Single-click `[Install (winget)]` for missing tools.
  * `[Install All Missing Tools via Winget]` button.
  * `[🧹 Purge Dev Caches]` button (cleans `__pycache__`, `.pytest_cache`, `.mypy_cache`).

#### 3. 📁 Downloads Organizer Tab
* Displays active Downloads path with `[Change Path...]` button.
* Unorganized files counter and total size.
* Category breakdown preview:
  * `Code_and_Dev` (`.py`, `.js`, `.ts`, `.html`, `.css`, `.json`, `.sql`, `.rs`, `.go`, `.cpp`, `.ipynb`, etc.)
  * `Documents` (`.pdf`, `.docx`, `.xlsx`, `.pptx`, `.txt`, `.csv`, `.md`, etc.)
  * `Images` (`.png`, `.jpg`, `.svg`, `.webp`, `.ico`, etc.)
  * `Media` (`.mp4`, `.mkv`, `.avi`, `.mov`, `.mp3`, `.wav`, etc.)
  * `Archives` (`.zip`, `.rar`, `.7z`, `.tar`, etc.)
  * `Installers` (`.exe`, `.msi`, `.iso`, etc.)
* **Interactive Buttons:**
  * `[👁️ Dry-Run Preview]` - Inspect planned file moves before touching files.
  * `[⚡ Organize Downloads Now]` - Categorizes loose files safely.
  * **`[⏪ Rollback / Undo Last Batch]` Button** - Reverses the last organization batch, restoring all moved files to their original loose locations!

#### 4. 🛡️ Windows Debloater & Chris Titus Tech Utility Tab
* **🔥 Chris Titus Tech (CTT) Windows Utility (winutil) Integration:**
  * Prominent feature card with launch button:
  * `[🚀 Launch CTT Winutil (PowerShell)]`
  * Executes `irm https://christitus.com/win | iex` in an elevated PowerShell session for deep Windows debloating, package installs, and system tweaks.
* **Safe Built-in Debloat Tweaks:**
  * **Disable Bing in Start Search** (`[Apply]` / `[Rollback]`) - Restores instant local search without telemetry.
  * **Turn Off Copilot Background Integration** (`[Apply]` / `[Rollback]`) - Stops Copilot from consuming background RAM.
  * **Optimize Visual Effects for Low RAM** (`[Apply]` / `[Rollback]`) - Disables drop shadows and animations for instant window responsiveness.
  * **Clean Temp & Crash Caches** (`[Purge Temp Now]`) - Purges temporary files.
  * **`[⏪ Rollback All Tweaks]` Button** - Restores Windows defaults!

#### 5. ⚙️ Preferences & Configuration Tab
* Update Profession, Active Mode, and Downloads clutter threshold.
* Toggle minimize-to-background behavior.
* `[🔄 Relaunch Initial Setup Wizard]` button.
* `[💾 Save Preferences]` button.

#### 6. ❤️ Support, Community & Contribute Tab
* **📺 YouTube Channel Section:**
  * Channel: `@cyan_code`
  * Link: [https://www.youtube.com/@cyan_code](https://www.youtube.com/@cyan_code)
  * Button: `[🔴 Open @cyan_code on YouTube]`
* **⭐ GitHub Support & Contribute Section:**
  * Repository: `takumicodes/REN-AI`
  * Link: [https://github.com/takumicodes/REN-AI](https://github.com/takumicodes/REN-AI)
  * Buttons: `[⭐ Star on GitHub]`, `[🐛 Report an Issue]`, `[🤝 Submit Pull Request]`
* **The REN Vision:**
  * Built for developers by developers. Zero AI slop, 100% human-driven.

---

## 🔄 Silent Background Operation & Tray Behavior

* When the window is closed using the `X` button, REN does **not** exit.
* It hides to the background (`root.withdraw()`) and continues monitoring system health silently.
* A floating quick-access controller allows you to restore the GUI with one click (`[Open GUI]`) or exit completely (`[Exit Completely]`).
* In the GUI header, you can also use `[Minimize to Tray]` or `[Exit App]`.

---

## 🚀 How to Run

### 1. Run Pre-Compiled Executable
Double-click:
```
Ren_Desktop_Assistant/Ren Desktop Assistant.exe
```

### 2. Run from Python Source
```bash
# Launch GUI
python Ren_Desktop_Assistant/main.py

# Launch interactive terminal cyber dashboard
python Ren_Desktop_Assistant/main.py --cli

# Launch silent headless background daemon
python Ren_Desktop_Assistant/main.py --bg
```

### 3. Rebuilding the Executable
To recompile the standalone `.exe` using PyInstaller:
```bash
python Ren_Desktop_Assistant/build_exe.py
```

### 4. Running Unit Tests
A complete 21-test verification suite tests all modules, safety checks, and rollback operations:
```bash
python -m unittest Ren_Desktop_Assistant/tests/test_desktop_assistant.py
```