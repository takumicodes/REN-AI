"""
REN-AI Windows Control Center - Complete Graphical User Interface (v1.3.0)
Cyber Dark Styling with 14 Specialized Feature Centers:
- Dashboard: Real-time hardware telemetry (CPU, RAM, Disk, Power), uptime, and human-driven recommendations.
- Process Explorer: Live process table (PID, Name, CPU%, RAM MB, Status) with critical OS shields.
- Power Center: Power plan switcher (Balanced, High Performance, Power Saver, Ultimate), battery reports.
- Storage & Cleaner: Multi-target cache cleaner (temp, shaders, dumps, recycle bin) & storage analyzer.
- Startup Manager: Registry (HKCU/HKLM) and folder startup apps with safe disable and rollback.
- Services Manager: Windows services inspection with core OS shields and startup-type controls.
- Apps Manager: Installed Win32 & UWP programs with search, details, and safe uninstaller launcher.
- Tweaks & Privacy: Modern Windows Explorer & System tweaks + Telemetry & Privacy hardening with rollback.
- Network Center: Adapter telemetry, ping tester, DNS flush with verification, active connections.
- Health & Restore: Drive dirty checks, Event Log error queries, System Restore points & creator.
- Modes & Gaming: 4 Modes (Programmer, Gaming, Balanced, Performance), Dev Tools arsenal & Chris Titus WinUtil.
- Benchmark Center: Deterministic CPU, RAM, and Disk benchmark with composite scoring and history comparison.
- Change History: Audit trail of all actions with verification status and 1-click rollback engine.
- Preferences & Support: Settings, downloads path, YouTube @cyan_code channel, and GitHub support.
"""

import os
import sys
import time
import shutil
import threading
import webbrowser
from pathlib import Path
import tkinter as tk
from tkinter import ttk, messagebox, filedialog

try:
    from .preferences import preferences, DEFAULT_PREFERENCES
    from .system_status import (
        get_system_snapshot,
        set_power_profile,
        get_available_power_schemes,
        get_battery_info,
    )
    from .system_observer import observer
    from .actions import action_queue
    from .downloads_organizer import organizer
    from .debloat import debloat_manager
    from .modes import modes_manager, DEV_TOOLS_CATALOG
    from .history import change_history
    from .action_registry import action_registry, action_executor, Action, RiskLevel
    from .process_manager import process_manager
    from .startup_manager import startup_manager
    from .services_manager import services_manager
    from .storage_cleaner import storage_cleaner
    from .storage_analyzer import storage_analyzer
    from .app_manager import app_manager
    from .tweaks_manager import tweaks_manager
    from .privacy_center import privacy_center
    from .network_center import network_center
    from .health_diagnostics import health_diagnostics
    from .restore_center import restore_center
    from .benchmark import benchmark_center
except ImportError:
    from preferences import preferences, DEFAULT_PREFERENCES
    from system_status import (
        get_system_snapshot,
        set_power_profile,
        get_available_power_schemes,
        get_battery_info,
    )
    from system_observer import observer
    from actions import action_queue
    from downloads_organizer import organizer
    from debloat import debloat_manager
    from modes import modes_manager, DEV_TOOLS_CATALOG
    from history import change_history
    from action_registry import action_registry, action_executor, Action, RiskLevel
    from process_manager import process_manager
    from startup_manager import startup_manager
    from services_manager import services_manager
    from storage_cleaner import storage_cleaner
    from storage_analyzer import storage_analyzer
    from app_manager import app_manager
    from tweaks_manager import tweaks_manager
    from privacy_center import privacy_center
    from network_center import network_center
    from health_diagnostics import health_diagnostics
    from restore_center import restore_center
    from benchmark import benchmark_center


# --- Cyber Dark Theme Constants ---
COLOR_BG = "#0d1117"          # Core dark background
COLOR_PANEL = "#161b22"       # Container card background
COLOR_HEADER = "#21262d"      # Section header background
COLOR_BORDER = "#30363d"      # Subtle boundary lines
COLOR_TEXT = "#f0f6fc"        # Primary sharp white text
COLOR_MUTED = "#8b949e"       # Muted subtitle text
COLOR_CYAN = "#00e5ff"        # Cyber Cyan accent
COLOR_BLUE = "#58a6ff"        # Primary blue
COLOR_GREEN = "#2ea043"       # Success / Applied
COLOR_AMBER = "#d29922"       # Warning / Notice
COLOR_RED = "#da3633"         # Danger / Revert / Critical
COLOR_PURPLE = "#bc8cff"      # Modes / Gaming accent
COLOR_SIDEBAR = "#12171f"     # Sidebar navigation background
COLOR_ACTIVE_NAV = "#1f6feb"  # Active sidebar item


class RenDesktopApp:
    """Main Application Controller for REN-AI Windows Control Center."""

    def __init__(self, root: tk.Tk):
        self.root = root
        self.root.title("🪐 REN-AI Windows Control Center")
        self.root.geometry("1100x760")
        self.root.minsize(980, 680)
        self.root.configure(bg=COLOR_BG)

        # Set Window Logo / Icon
        try:
            base_path = Path(sys._MEIPASS) if getattr(sys, "frozen", False) else Path(__file__).parent
            icon_ico = base_path / "ren_logo.ico"
            icon_png = base_path / "ren_logo.png"
            if icon_ico.exists():
                self.root.iconbitmap(str(icon_ico))
            elif icon_png.exists():
                logo_img = tk.PhotoImage(file=str(icon_png))
                self.root.iconphoto(True, logo_img)
        except Exception:
            pass

        # Intercept close ('X') button to minimize to background
        self.root.protocol("WM_DELETE_WINDOW", self.on_close_window)

        # Start silent observer thread
        observer.start_background()

        # Check for first install / onboarding
        self.container = tk.Frame(self.root, bg=COLOR_BG)
        self.container.pack(fill=tk.BOTH, expand=True)

        if not preferences.get("onboarding_completed", False):
            self.show_onboarding_wizard()
        else:
            self.show_main_control_center()

    # =========================================================================
    # FIRST INSTALL PREFERENCES ONBOARDING WIZARD
    # =========================================================================

    def show_onboarding_wizard(self):
        """Displays the first-time setup wizard for initial user configuration."""
        for w in self.container.winfo_children():
            w.destroy()

        wizard_frame = tk.Frame(self.container, bg=COLOR_BG)
        wizard_frame.pack(fill=tk.BOTH, expand=True, padx=40, pady=30)

        # Title Card
        title_box = tk.Frame(wizard_frame, bg=COLOR_PANEL, bd=1, relief=tk.SOLID)
        title_box.pack(fill=tk.X, pady=(0, 20), ipady=12)

        lbl_title = tk.Label(
            title_box,
            text="🪐 Welcome to REN-AI Windows Control Center",
            font=("Segoe UI", 18, "bold"),
            fg=COLOR_CYAN,
            bg=COLOR_PANEL,
        )
        lbl_title.pack(anchor=tk.W, padx=20, pady=(6, 2))

        lbl_subtitle = tk.Label(
            title_box,
            text="Autonomous Windows Control Center — 100% Human-Driven with Zero AI Slop.\nPlease configure your initial preferences below:",
            font=("Segoe UI", 10),
            fg=COLOR_TEXT,
            bg=COLOR_PANEL,
            justify=tk.LEFT,
        )
        lbl_subtitle.pack(anchor=tk.W, padx=20, pady=(0, 6))

        # Main Form Card
        form_card = tk.Frame(wizard_frame, bg=COLOR_PANEL, bd=1, relief=tk.SOLID)
        form_card.pack(fill=tk.BOTH, expand=True, ipady=10)

        canvas = tk.Canvas(form_card, bg=COLOR_PANEL, highlightthickness=0)
        scrollbar = ttk.Scrollbar(form_card, orient="vertical", command=canvas.yview)
        scroll_content = tk.Frame(canvas, bg=COLOR_PANEL)

        scroll_content.bind(
            "<Configure>",
            lambda e: canvas.configure(scrollregion=canvas.bbox("all")),
        )
        canvas.create_window((0, 0), window=scroll_content, anchor="nw")
        canvas.configure(yscrollcommand=scrollbar.set)

        canvas.pack(side=tk.LEFT, fill=tk.BOTH, expand=True, padx=20, pady=10)
        scrollbar.pack(side=tk.RIGHT, fill=tk.Y, pady=10)

        # 1. Downloads Folder Path
        tk.Label(
            scroll_content,
            text="📁 1. Downloads Folder Path:",
            font=("Segoe UI", 11, "bold"),
            fg=COLOR_CYAN,
            bg=COLOR_PANEL,
        ).pack(anchor=tk.W, pady=(10, 4))

        path_frame = tk.Frame(scroll_content, bg=COLOR_PANEL)
        path_frame.pack(fill=tk.X, pady=(0, 15))

        self.var_downloads = tk.StringVar(value=preferences.get("downloads_folder", str(Path.home() / "Downloads")))
        ent_path = tk.Entry(path_frame, textvariable=self.var_downloads, font=("Segoe UI", 10), bg="#0d1117", fg=COLOR_TEXT, insertbackground=COLOR_TEXT)
        ent_path.pack(side=tk.LEFT, fill=tk.X, expand=True, ipady=4, padx=(0, 10))

        btn_browse = tk.Button(
            path_frame,
            text="Browse...",
            font=("Segoe UI", 9, "bold"),
            bg=COLOR_HEADER,
            fg=COLOR_CYAN,
            command=self._browse_downloads,
            cursor="hand2",
            padx=12,
        )
        btn_browse.pack(side=tk.RIGHT)

        # 2. User Profession
        tk.Label(
            scroll_content,
            text="💼 2. Select Your Profession:",
            font=("Segoe UI", 11, "bold"),
            fg=COLOR_CYAN,
            bg=COLOR_PANEL,
        ).pack(anchor=tk.W, pady=(10, 4))

        self.var_profession = tk.StringVar(value=preferences.get("profession", "Software Engineer"))
        professions = [
            ("Software Engineer / Developer", "Optimizes compile speed, dev tools, and dev cache cleaning"),
            ("Designer / Content Creator", "Optimizes GPU RAM allocation, media downloads, and scratch disks"),
            ("Student / Researcher / Office", "Whisper-quiet operation, documents organization, battery conservation"),
            ("Gamer / Hardware Power User", "Ultimate performance power plan, max clock boosts, latency reduction"),
            ("General / Casual User", "Balanced Windows operation with zero clutter and low overhead"),
        ]

        for prof_title, prof_desc in professions:
            rb_frame = tk.Frame(scroll_content, bg=COLOR_PANEL)
            rb_frame.pack(fill=tk.X, pady=3)
            rb = tk.Radiobutton(
                rb_frame,
                text=prof_title,
                variable=self.var_profession,
                value=prof_title.split(" / ")[0],
                font=("Segoe UI", 10, "bold"),
                fg=COLOR_TEXT,
                bg=COLOR_PANEL,
                selectcolor="#0d1117",
                activebackground=COLOR_PANEL,
                activeforeground=COLOR_CYAN,
            )
            rb.pack(anchor=tk.W)
            tk.Label(
                rb_frame,
                text=f"    {prof_desc}",
                font=("Segoe UI", 8),
                fg=COLOR_MUTED,
                bg=COLOR_PANEL,
            ).pack(anchor=tk.W)

        # 3. Operational Mode Preference
        tk.Label(
            scroll_content,
            text="⚡ 3. Preferred Operational Mode:",
            font=("Segoe UI", 11, "bold"),
            fg=COLOR_CYAN,
            bg=COLOR_PANEL,
        ).pack(anchor=tk.W, pady=(18, 4))

        self.var_mode = tk.StringVar(value=preferences.active_mode)
        modes_info = [
            ("programmer", "Programmer Mode (Recommended)", "Developer tools compatibility (Git, VS Code, wt, Rust), low RAM debloat, compile booster"),
            ("gaming", "Gaming Mode", "Maximum FPS & latency stability, high performance power, visual optimizations"),
            ("balanced", "Balanced Mode", "Unobtrusive daily assistant, standard Windows balance, quiet background monitoring"),
            ("performance", "Performance Mode", "Maximum hardware clock rates, frees standby memory for heavy compute workloads"),
        ]

        for m_key, m_title, m_desc in modes_info:
            m_frame = tk.Frame(scroll_content, bg=COLOR_PANEL)
            m_frame.pack(fill=tk.X, pady=4)
            rb_m = tk.Radiobutton(
                m_frame,
                text=m_title,
                variable=self.var_mode,
                value=m_key,
                font=("Segoe UI", 10, "bold"),
                fg=COLOR_PURPLE if m_key in ("programmer", "gaming") else COLOR_TEXT,
                bg=COLOR_PANEL,
                selectcolor="#0d1117",
                activebackground=COLOR_PANEL,
                activeforeground=COLOR_CYAN,
            )
            rb_m.pack(anchor=tk.W)
            tk.Label(
                m_frame,
                text=f"    {m_desc}",
                font=("Segoe UI", 8),
                fg=COLOR_MUTED,
                bg=COLOR_PANEL,
            ).pack(anchor=tk.W)

        # 4. Background Settings
        tk.Label(
            scroll_content,
            text="🛡️ 4. Background & Control Center Behavior:",
            font=("Segoe UI", 11, "bold"),
            fg=COLOR_CYAN,
            bg=COLOR_PANEL,
        ).pack(anchor=tk.W, pady=(18, 4))

        self.var_close_bg = tk.BooleanVar(value=preferences.get("close_to_background", True))
        cb_bg = tk.Checkbutton(
            scroll_content,
            text="Run silently in background when window is closed (minimize to system tray)",
            variable=self.var_close_bg,
            font=("Segoe UI", 10),
            fg=COLOR_TEXT,
            bg=COLOR_PANEL,
            selectcolor="#0d1117",
            activebackground=COLOR_PANEL,
            activeforeground=COLOR_CYAN,
        )
        cb_bg.pack(anchor=tk.W, pady=2)

        # Bottom Button Bar
        btn_bar = tk.Frame(wizard_frame, bg=COLOR_BG)
        btn_bar.pack(fill=tk.X, pady=(20, 0))

        btn_defaults = tk.Button(
            btn_bar,
            text="⚡ Use Programmer Defaults",
            font=("Segoe UI", 10),
            bg=COLOR_HEADER,
            fg=COLOR_MUTED,
            command=self._apply_wizard_defaults,
            cursor="hand2",
            padx=16,
            pady=6,
        )
        btn_defaults.pack(side=tk.LEFT)

        btn_save = tk.Button(
            btn_bar,
            text="🚀 Enter Control Center",
            font=("Segoe UI", 11, "bold"),
            bg="#1f6feb",
            fg="#ffffff",
            activebackground="#388bfd",
            command=self._save_wizard_preferences,
            cursor="hand2",
            padx=20,
            pady=6,
        )
        btn_save.pack(side=tk.RIGHT)

    def _browse_downloads(self):
        folder = filedialog.askdirectory(initialdir=self.var_downloads.get(), title="Select Downloads Folder")
        if folder:
            self.var_downloads.set(folder)

    def _apply_wizard_defaults(self):
        self.var_downloads.set(str(Path.home() / "Downloads"))
        self.var_profession.set("Software Engineer")
        self.var_mode.set("programmer")
        self.var_close_bg.set(True)
        self._save_wizard_preferences()

    def _save_wizard_preferences(self):
        downloads_path = self.var_downloads.get().strip()
        if not downloads_path or not Path(downloads_path).exists():
            messagebox.showwarning("Invalid Path", "Please provide a valid existing folder path for Downloads.")
            return

        preferences.update(
            downloads_folder=downloads_path,
            profession=self.var_profession.get(),
            active_mode=self.var_mode.get(),
            close_to_background=self.var_close_bg.get(),
            onboarding_completed=True,
        )
        organizer.folder = Path(downloads_path)
        modes_manager.set_mode(self.var_mode.get(), apply_optimizations=True)
        self.show_main_control_center()

    # =========================================================================
    # MAIN CONTROL CENTER INTERFACE & SIDEBAR NAVIGATION
    # =========================================================================

    def show_main_control_center(self):
        """Constructs the full Windows Control Center UI with sidebar navigation."""
        for w in self.container.winfo_children():
            w.destroy()

        # Top Banner / Header
        self.header = tk.Frame(self.container, bg=COLOR_PANEL, bd=1, relief=tk.SOLID)
        self.header.pack(fill=tk.X, padx=12, pady=(10, 6), ipady=6)

        lbl_h_title = tk.Label(
            self.header,
            text="🪐 REN-AI WINDOWS CONTROL CENTER",
            font=("Segoe UI", 13, "bold"),
            fg=COLOR_CYAN,
            bg=COLOR_PANEL,
        )
        lbl_h_title.pack(side=tk.LEFT, padx=(14, 8))

        lbl_ver = tk.Label(
            self.header,
            text="v1.3.0",
            font=("Segoe UI", 9, "bold"),
            fg=COLOR_MUTED,
            bg="#21262d",
            padx=6,
            pady=1,
        )
        lbl_ver.pack(side=tk.LEFT, padx=4)

        self.lbl_mode_badge = tk.Label(
            self.header,
            text=f"[{preferences.active_mode.upper()} MODE]",
            font=("Segoe UI", 9, "bold"),
            fg=COLOR_PURPLE,
            bg="#21262d",
            padx=8,
            pady=2,
        )
        self.lbl_mode_badge.pack(side=tk.LEFT, padx=6)

        # Header Right Controls
        btn_exit = tk.Button(
            self.header,
            text="Exit App",
            font=("Segoe UI", 9),
            bg=COLOR_HEADER,
            fg=COLOR_RED,
            activebackground=COLOR_BORDER,
            command=self.quit_app_completely,
            cursor="hand2",
            padx=10,
        )
        btn_exit.pack(side=tk.RIGHT, padx=(6, 14))

        btn_min = tk.Button(
            self.header,
            text="Minimize to Tray",
            font=("Segoe UI", 9),
            bg=COLOR_HEADER,
            fg=COLOR_MUTED,
            activebackground=COLOR_BORDER,
            command=self.minimize_to_background,
            cursor="hand2",
            padx=10,
        )
        btn_min.pack(side=tk.RIGHT, padx=6)

        self.lbl_header_metrics = tk.Label(
            self.header,
            text="Loading hardware telemetry...",
            font=("Segoe UI", 9),
            fg=COLOR_MUTED,
            bg=COLOR_PANEL,
        )
        self.lbl_header_metrics.pack(side=tk.RIGHT, padx=14)

        # Main Workspace: Left Sidebar + Right Content Area
        workspace = tk.Frame(self.container, bg=COLOR_BG)
        workspace.pack(fill=tk.BOTH, expand=True, padx=12, pady=(0, 10))

        # --- Sidebar ---
        self.sidebar = tk.Frame(workspace, bg=COLOR_SIDEBAR, width=220, bd=1, relief=tk.SOLID)
        self.sidebar.pack(side=tk.LEFT, fill=tk.Y, padx=(0, 8))
        self.sidebar.pack_propagate(False)

        # --- Content Area ---
        self.content_area = tk.Frame(workspace, bg=COLOR_PANEL, bd=1, relief=tk.SOLID)
        self.content_area.pack(side=tk.RIGHT, fill=tk.BOTH, expand=True)

        # Build Sidebar Navigation Buttons
        self.nav_buttons = {}
        self.panels = {}
        self.active_panel_key = None

        nav_items = [
            ("dashboard", "📊 Dashboard"),
            ("processes", "⚡ Process Explorer"),
            ("power", "🔋 Power Center"),
            ("storage", "🧹 Storage & Cleaner"),
            ("startup", "🚀 Startup Manager"),
            ("services", "⚙️ Services Manager"),
            ("apps", "📦 Apps Manager"),
            ("tweaks", "🛠️ Tweaks & Privacy"),
            ("network", "🌐 Network Center"),
            ("health", "🩺 Health & Restore"),
            ("modes", "🎮 Modes & Gaming"),
            ("benchmark", "📈 Benchmark Center"),
            ("history", "📜 Change History"),
            ("settings", "⚙️ Preferences & Support"),
        ]

        for key, label in nav_items:
            btn = tk.Button(
                self.sidebar,
                text=f"  {label}",
                font=("Segoe UI", 9, "bold"),
                anchor=tk.W,
                bg=COLOR_SIDEBAR,
                fg=COLOR_TEXT,
                activebackground=COLOR_HEADER,
                activeforeground=COLOR_CYAN,
                bd=0,
                cursor="hand2",
                command=lambda k=key: self.switch_panel(k),
                padx=12,
                pady=7,
            )
            btn.pack(fill=tk.X, pady=1)
            self.nav_buttons[key] = btn

        # Switch to default panel
        self.switch_panel("dashboard")

        # Start 2-second background metrics loop
        self._refresh_gui_loop()

    def switch_panel(self, panel_key: str):
        """Switches the visible workspace panel and highlights sidebar button."""
        self.active_panel_key = panel_key

        # Highlight sidebar buttons
        for k, btn in self.nav_buttons.items():
            if k == panel_key:
                btn.configure(bg=COLOR_ACTIVE_NAV, fg="#ffffff")
            else:
                btn.configure(bg=COLOR_SIDEBAR, fg=COLOR_TEXT)

        # Clear content area
        for w in self.content_area.winfo_children():
            w.destroy()

        # Render selected panel
        build_methods = {
            "dashboard": self._build_dashboard_panel,
            "processes": self._build_processes_panel,
            "power": self._build_power_panel,
            "storage": self._build_storage_panel,
            "startup": self._build_startup_panel,
            "services": self._build_services_panel,
            "apps": self._build_apps_panel,
            "tweaks": self._build_tweaks_panel,
            "network": self._build_network_panel,
            "health": self._build_health_panel,
            "modes": self._build_modes_panel,
            "benchmark": self._build_benchmark_panel,
            "history": self._build_history_panel,
            "settings": self._build_settings_panel,
        }

        builder = build_methods.get(panel_key)
        if builder:
            builder()

    # =========================================================================
    # 1. DASHBOARD PANEL
    # =========================================================================

    def _build_dashboard_panel(self):
        pane = tk.Frame(self.content_area, bg=COLOR_PANEL)
        pane.pack(fill=tk.BOTH, expand=True, padx=14, pady=12)

        # Hardware Metrics Cards
        metrics_frame = tk.Frame(pane, bg=COLOR_PANEL)
        metrics_frame.pack(fill=tk.X, pady=(0, 12))

        # CPU Card
        c_cpu = tk.Frame(metrics_frame, bg="#0d1117", bd=1, relief=tk.SOLID)
        c_cpu.pack(side=tk.LEFT, fill=tk.BOTH, expand=True, padx=(0, 6), ipady=6)
        tk.Label(c_cpu, text="💻 PROCESSOR", font=("Segoe UI", 9, "bold"), fg=COLOR_CYAN, bg="#0d1117").pack(anchor=tk.W, padx=10, pady=(2, 4))
        self.lbl_dash_cpu = tk.Label(c_cpu, text="CPU: -- %", font=("Segoe UI", 10), fg=COLOR_TEXT, bg="#0d1117")
        self.lbl_dash_cpu.pack(anchor=tk.W, padx=10)
        self.bar_dash_cpu = ttk.Progressbar(c_cpu, length=140, mode="determinate")
        self.bar_dash_cpu.pack(fill=tk.X, padx=10, pady=(2, 6))

        # RAM Card
        c_ram = tk.Frame(metrics_frame, bg="#0d1117", bd=1, relief=tk.SOLID)
        c_ram.pack(side=tk.LEFT, fill=tk.BOTH, expand=True, padx=3, ipady=6)
        tk.Label(c_ram, text="🧠 MEMORY", font=("Segoe UI", 9, "bold"), fg=COLOR_CYAN, bg="#0d1117").pack(anchor=tk.W, padx=10, pady=(2, 4))
        self.lbl_dash_ram = tk.Label(c_ram, text="RAM: -- %", font=("Segoe UI", 10), fg=COLOR_TEXT, bg="#0d1117")
        self.lbl_dash_ram.pack(anchor=tk.W, padx=10)
        self.bar_dash_ram = ttk.Progressbar(c_ram, length=140, mode="determinate")
        self.bar_dash_ram.pack(fill=tk.X, padx=10, pady=(2, 6))

        # Disk Card
        c_disk = tk.Frame(metrics_frame, bg="#0d1117", bd=1, relief=tk.SOLID)
        c_disk.pack(side=tk.LEFT, fill=tk.BOTH, expand=True, padx=(6, 0), ipady=6)
        tk.Label(c_disk, text="💾 PRIMARY STORAGE", font=("Segoe UI", 9, "bold"), fg=COLOR_CYAN, bg="#0d1117").pack(anchor=tk.W, padx=10, pady=(2, 4))
        self.lbl_dash_disk = tk.Label(c_disk, text="Disk: -- %", font=("Segoe UI", 10), fg=COLOR_TEXT, bg="#0d1117")
        self.lbl_dash_disk.pack(anchor=tk.W, padx=10)
        self.bar_dash_disk = ttk.Progressbar(c_disk, length=140, mode="determinate")
        self.bar_dash_disk.pack(fill=tk.X, padx=10, pady=(2, 6))

        # System Context & Quick Stats
        ctx_box = tk.Frame(pane, bg=COLOR_HEADER, bd=1, relief=tk.SOLID)
        ctx_box.pack(fill=tk.X, pady=(0, 12), ipady=4)
        self.lbl_dash_ctx = tk.Label(
            ctx_box,
            text="System Context: General | Active Power Profile: Balanced | Observer: Silent BG Active",
            font=("Segoe UI", 9),
            fg=COLOR_TEXT,
            bg=COLOR_HEADER,
        )
        self.lbl_dash_ctx.pack(side=tk.LEFT, padx=12)

        # Human-Driven Pending Recommendations
        rec_card = tk.Frame(pane, bg="#0d1117", bd=1, relief=tk.SOLID)
        rec_card.pack(fill=tk.BOTH, expand=True)

        rec_head = tk.Frame(rec_card, bg=COLOR_HEADER)
        rec_head.pack(fill=tk.X, ipady=6)
        tk.Label(rec_head, text="⚡ PENDING RECOMMENDATIONS (HUMAN-DRIVEN)", font=("Segoe UI", 10, "bold"), fg=COLOR_CYAN, bg=COLOR_HEADER).pack(side=tk.LEFT, padx=12)

        btn_ref_rec = tk.Button(
            rec_head,
            text="🔄 Refresh",
            font=("Segoe UI", 8, "bold"),
            bg="#30363d",
            fg=COLOR_TEXT,
            command=self._render_dashboard_recs,
            cursor="hand2",
            padx=8,
        )
        btn_ref_rec.pack(side=tk.RIGHT, padx=12)

        self.dash_rec_scroll = tk.Frame(rec_card, bg="#0d1117")
        self.dash_rec_scroll.pack(fill=tk.BOTH, expand=True, padx=10, pady=8)
        self._render_dashboard_recs()

    def _render_dashboard_recs(self):
        if not hasattr(self, "dash_rec_scroll") or not self.dash_rec_scroll.winfo_exists():
            return

        for w in self.dash_rec_scroll.winfo_children():
            w.destroy()

        recs = action_queue.get_pending()
        if not recs:
            lbl_empty = tk.Label(
                self.dash_rec_scroll,
                text="✓ All system metrics optimal. No interventions pending.\nREN is observing silently with zero background disruptions.",
                font=("Segoe UI", 10),
                fg=COLOR_MUTED,
                bg="#0d1117",
                justify=tk.CENTER,
            )
            lbl_empty.pack(expand=True, pady=40)
            return

        for rec in recs:
            item = tk.Frame(self.dash_rec_scroll, bg=COLOR_PANEL, bd=1, relief=tk.SOLID)
            item.pack(fill=tk.X, pady=4, padx=4, ipady=4)

            top_row = tk.Frame(item, bg=COLOR_PANEL)
            top_row.pack(fill=tk.X, padx=8, pady=(4, 2))
            tk.Label(top_row, text=rec.title, font=("Segoe UI", 10, "bold"), fg=COLOR_TEXT, bg=COLOR_PANEL).pack(side=tk.LEFT)
            tk.Label(top_row, text=f"[{rec.category.upper()}]", font=("Segoe UI", 8), fg=COLOR_CYAN, bg=COLOR_PANEL).pack(side=tk.LEFT, padx=6)

            tk.Label(item, text=f"Impact: {rec.impact}", font=("Segoe UI", 9), fg=COLOR_GREEN, bg=COLOR_PANEL).pack(anchor=tk.W, padx=8)
            tk.Label(item, text=f"Rationale: {rec.description}", font=("Segoe UI", 8), fg=COLOR_MUTED, bg=COLOR_PANEL).pack(anchor=tk.W, padx=8)

            btn_row = tk.Frame(item, bg=COLOR_PANEL)
            btn_row.pack(fill=tk.X, padx=8, pady=(4, 4))
            r_id = rec.id
            btn_app = tk.Button(
                btn_row,
                text="✓ Approve & Apply",
                font=("Segoe UI", 8, "bold"),
                bg=COLOR_GREEN,
                fg="#ffffff",
                command=lambda rid=r_id: self._approve_recommendation(rid),
                cursor="hand2",
                padx=8,
            )
            btn_app.pack(side=tk.LEFT, padx=(0, 6))

            btn_dis = tk.Button(
                btn_row,
                text="✗ Dismiss",
                font=("Segoe UI", 8),
                bg=COLOR_HEADER,
                fg=COLOR_MUTED,
                command=lambda rid=r_id: self._dismiss_recommendation(rid),
                cursor="hand2",
                padx=8,
            )
            btn_dis.pack(side=tk.LEFT)

    def _approve_recommendation(self, rec_id: str):
        res = action_queue.approve(rec_id)
        self._render_dashboard_recs()
        messagebox.showinfo("Action Applied", res.get("message", "Approved successfully."))

    def _dismiss_recommendation(self, rec_id: str):
        action_queue.dismiss(rec_id)
        self._render_dashboard_recs()

    # =========================================================================
    # 2. PROCESS EXPLORER PANEL
    # =========================================================================

    def _build_processes_panel(self):
        pane = tk.Frame(self.content_area, bg=COLOR_PANEL)
        pane.pack(fill=tk.BOTH, expand=True, padx=14, pady=12)

        # Toolbar
        tool_bar = tk.Frame(pane, bg=COLOR_PANEL)
        tool_bar.pack(fill=tk.X, pady=(0, 8))

        tk.Label(tool_bar, text="Search Process:", font=("Segoe UI", 9, "bold"), fg=COLOR_TEXT, bg=COLOR_PANEL).pack(side=tk.LEFT, padx=(0, 6))
        self.var_proc_search = tk.StringVar()
        ent_search = tk.Entry(tool_bar, textvariable=self.var_proc_search, font=("Segoe UI", 9), bg="#0d1117", fg=COLOR_TEXT, insertbackground=COLOR_TEXT, width=22)
        ent_search.pack(side=tk.LEFT, padx=(0, 8), ipady=2)
        ent_search.bind("<KeyRelease>", lambda e: self._refresh_processes_table())

        btn_ref = tk.Button(tool_bar, text="🔄 Refresh", font=("Segoe UI", 8, "bold"), bg=COLOR_HEADER, fg=COLOR_CYAN, command=self._refresh_processes_table, cursor="hand2", padx=8)
        btn_ref.pack(side=tk.LEFT, padx=(0, 10))

        btn_term = tk.Button(tool_bar, text="⚠️ Terminate Selected", font=("Segoe UI", 8, "bold"), bg=COLOR_RED, fg="#ffffff", command=self._terminate_selected_process, cursor="hand2", padx=10)
        btn_term.pack(side=tk.RIGHT)

        # Treeview Process Table
        cols = ("pid", "name", "cpu", "mem", "status", "critical")
        self.proc_tree = ttk.Treeview(pane, columns=cols, show="headings", selectmode="browse")
        self.proc_tree.heading("pid", text="PID", command=lambda: self._sort_proc_col("pid"))
        self.proc_tree.heading("name", text="Process Name", command=lambda: self._sort_proc_col("name"))
        self.proc_tree.heading("cpu", text="CPU %", command=lambda: self._sort_proc_col("cpu_percent"))
        self.proc_tree.heading("mem", text="RAM (MB)", command=lambda: self._sort_proc_col("memory_mb"))
        self.proc_tree.heading("status", text="Status")
        self.proc_tree.heading("critical", text="Protection")

        self.proc_tree.column("pid", width=70, anchor=tk.CENTER)
        self.proc_tree.column("name", width=220, anchor=tk.W)
        self.proc_tree.column("cpu", width=80, anchor=tk.E)
        self.proc_tree.column("mem", width=100, anchor=tk.E)
        self.proc_tree.column("status", width=90, anchor=tk.CENTER)
        self.proc_tree.column("critical", width=110, anchor=tk.CENTER)

        tree_scroll = ttk.Scrollbar(pane, orient="vertical", command=self.proc_tree.yview)
        self.proc_tree.configure(yscrollcommand=tree_scroll.set)

        self.proc_tree.pack(side=tk.LEFT, fill=tk.BOTH, expand=True)
        tree_scroll.pack(side=tk.RIGHT, fill=tk.Y)

        self.proc_sort_by = "memory_mb"
        self._refresh_processes_table()

    def _sort_proc_col(self, col_key: str):
        self.proc_sort_by = col_key
        self._refresh_processes_table()

    def _refresh_processes_table(self):
        if not hasattr(self, "proc_tree") or not self.proc_tree.winfo_exists():
            return

        for item in self.proc_tree.get_children():
            self.proc_tree.delete(item)

        query = self.var_proc_search.get().strip()
        procs = process_manager.get_processes(sort_by=self.proc_sort_by, search_query=query, limit=120)

        for p in procs:
            crit_label = "🛡️ CORE SYSTEM" if p.is_critical else "Standard App"
            self.proc_tree.insert(
                "",
                tk.END,
                values=(p.pid, p.name, f"{p.cpu_percent}%", f"{p.memory_mb} MB", p.status, crit_label),
            )

    def _terminate_selected_process(self):
        sel = self.proc_tree.selection()
        if not sel:
            messagebox.showwarning("No Selection", "Please select a process from the table to terminate.")
            return

        vals = self.proc_tree.item(sel[0])["values"]
        pid = int(vals[0])
        name = str(vals[1])
        is_crit = "CORE" in str(vals[5])

        if is_crit:
            messagebox.showerror(
                "Critical Process Shield",
                f"Cannot terminate '{name}' (PID {pid}).\nThis is a critical Windows system component. Terminating it may destabilize the OS or cause a BSOD."
            )
            return

        if messagebox.askyesno("Confirm Termination", f"Are you sure you want to terminate '{name}' (PID {pid})?"):
            res = process_manager.terminate_process(pid)
            if res.get("success"):
                messagebox.showinfo("Terminated", res.get("message"))
                self._refresh_processes_table()
            else:
                messagebox.showwarning("Termination Failed", res.get("message"))

    # =========================================================================
    # 3. POWER CENTER PANEL
    # =========================================================================

    def _build_power_panel(self):
        pane = tk.Frame(self.content_area, bg=COLOR_PANEL)
        pane.pack(fill=tk.BOTH, expand=True, padx=14, pady=12)

        # Section 1: Power Schemes
        card1 = tk.Frame(pane, bg="#0d1117", bd=1, relief=tk.SOLID)
        card1.pack(fill=tk.X, pady=(0, 12), ipady=8)

        tk.Label(card1, text="⚡ ACTIVE WINDOWS POWER SCHEME", font=("Segoe UI", 10, "bold"), fg=COLOR_CYAN, bg="#0d1117").pack(anchor=tk.W, padx=12, pady=(4, 6))

        schemes = get_available_power_schemes()
        self.var_power_plan = tk.StringVar(value=schemes.get("active", "Balanced"))

        p_row = tk.Frame(card1, bg="#0d1117")
        p_row.pack(fill=tk.X, padx=12, pady=4)

        for plan_name in ("Balanced", "High Performance", "Power Saver", "Ultimate Performance"):
            rb = tk.Radiobutton(
                p_row,
                text=plan_name,
                variable=self.var_power_plan,
                value=plan_name,
                font=("Segoe UI", 9, "bold"),
                fg=COLOR_TEXT,
                bg="#0d1117",
                selectcolor=COLOR_PANEL,
                command=self._on_power_plan_selected,
            )
            rb.pack(side=tk.LEFT, padx=(0, 16))

        # Section 2: Battery Telemetry & Reports
        card2 = tk.Frame(pane, bg="#0d1117", bd=1, relief=tk.SOLID)
        card2.pack(fill=tk.X, pady=(0, 12), ipady=8)

        tk.Label(card2, text="🔋 BATTERY HEALTH & DIAGNOSTICS", font=("Segoe UI", 10, "bold"), fg=COLOR_CYAN, bg="#0d1117").pack(anchor=tk.W, padx=12, pady=(4, 4))

        bat = get_battery_info()
        bat_text = f"Battery State: {bat['percent']}% {'(Plugged in / AC)' if bat['is_plugged'] else '(Discharging on Battery)'}" if bat["has_battery"] else "Device is connected directly to AC wall power (No battery installed)."
        tk.Label(card2, text=bat_text, font=("Segoe UI", 9), fg=COLOR_TEXT, bg="#0d1117").pack(anchor=tk.W, padx=12, pady=(0, 6))

        btn_report = tk.Button(
            card2,
            text="📑 Generate Windows Battery Report (HTML)",
            font=("Segoe UI", 9, "bold"),
            bg=COLOR_HEADER,
            fg=COLOR_CYAN,
            command=self._generate_battery_report,
            cursor="hand2",
            padx=12,
            pady=4,
        )
        btn_report.pack(anchor=tk.W, padx=12)

        # Section 3: Power Optimization Tips
        card3 = tk.Frame(pane, bg="#0d1117", bd=1, relief=tk.SOLID)
        card3.pack(fill=tk.BOTH, expand=True, ipady=8)
        tk.Label(card3, text="💡 POWER OPTIMIZATION TIPS", font=("Segoe UI", 10, "bold"), fg=COLOR_PURPLE, bg="#0d1117").pack(anchor=tk.W, padx=12, pady=(4, 4))
        tips = (
            "• Programmer Mode automatically applies Ultimate Performance on AC and Balanced on battery.\n"
            "• Gaming Mode locks high CPU clocks to reduce 1% low frame stutter.\n"
            "• REN provides 1-click verified powercfg rollback whenever you switch profiles."
        )
        tk.Label(card3, text=tips, font=("Segoe UI", 9), fg=COLOR_MUTED, bg="#0d1117", justify=tk.LEFT).pack(anchor=tk.W, padx=12)

    def _on_power_plan_selected(self):
        plan = self.var_power_plan.get()
        res = set_power_profile(plan)
        messagebox.showinfo("Power Profile", f"Power scheme configured to: {plan}")

    def _generate_battery_report(self):
        res = health_diagnostics.generate_battery_report()
        if res.get("success"):
            fp = res.get("file_path")
            if messagebox.askyesno("Battery Report Generated", f"Report saved at:\n{fp}\n\nOpen report in your web browser now?"):
                webbrowser.open(f"file:///{fp}")
        else:
            messagebox.showwarning("Report Failed", res.get("message"))

    # =========================================================================
    # 4. STORAGE & CLEANER PANEL
    # =========================================================================

    def _build_storage_panel(self):
        pane = tk.Frame(self.content_area, bg=COLOR_PANEL)
        pane.pack(fill=tk.BOTH, expand=True, padx=14, pady=12)

        # Top Buttons Bar
        btn_bar = tk.Frame(pane, bg=COLOR_PANEL)
        btn_bar.pack(fill=tk.X, pady=(0, 8))

        btn_scan = tk.Button(
            btn_bar,
            text="🔍 Scan Cleanable Junk",
            font=("Segoe UI", 9, "bold"),
            bg=COLOR_HEADER,
            fg=COLOR_CYAN,
            command=self._scan_storage_items,
            cursor="hand2",
            padx=12,
            pady=4,
        )
        btn_scan.pack(side=tk.LEFT, padx=(0, 8))

        btn_clean_all = tk.Button(
            btn_bar,
            text="🧹 Clean All Selected",
            font=("Segoe UI", 9, "bold"),
            bg=COLOR_GREEN,
            fg="#ffffff",
            command=self._clean_storage_items,
            cursor="hand2",
            padx=14,
            pady=4,
        )
        btn_clean_all.pack(side=tk.LEFT, padx=(0, 8))

        btn_recycle = tk.Button(
            btn_bar,
            text="🗑️ Empty Recycle Bin",
            font=("Segoe UI", 9),
            bg=COLOR_HEADER,
            fg=COLOR_TEXT,
            command=self._empty_recycle_bin,
            cursor="hand2",
            padx=10,
            pady=4,
        )
        btn_recycle.pack(side=tk.LEFT)

        # Storage Cleaner Items Frame
        self.cleaner_list_frame = tk.Frame(pane, bg="#0d1117", bd=1, relief=tk.SOLID)
        self.cleaner_list_frame.pack(fill=tk.BOTH, expand=True, pady=(0, 10))

        # Drives Overview Bar (Bottom)
        drives_card = tk.Frame(pane, bg=COLOR_HEADER, bd=1, relief=tk.SOLID)
        drives_card.pack(fill=tk.X, ipady=4)
        tk.Label(drives_card, text="CONNECTED DRIVES OVERVIEW:", font=("Segoe UI", 9, "bold"), fg=COLOR_CYAN, bg=COLOR_HEADER).pack(side=tk.LEFT, padx=10)

        drives_str_list = []
        for d in storage_analyzer.get_drives():
            drives_str_list.append(f"{d.mountpoint} ({d.free_gb} GB free / {d.total_gb} GB total - {d.percent}%)")
        tk.Label(drives_card, text=" | ".join(drives_str_list), font=("Segoe UI", 9), fg=COLOR_TEXT, bg=COLOR_HEADER).pack(side=tk.LEFT, padx=6)

        self._scan_storage_items()

    def _scan_storage_items(self):
        if not hasattr(self, "cleaner_list_frame") or not self.cleaner_list_frame.winfo_exists():
            return

        for w in self.cleaner_list_frame.winfo_children():
            w.destroy()

        items = storage_cleaner.scan_all()
        total_mb = sum(i.total_mb for i in items.values())

        head_row = tk.Frame(self.cleaner_list_frame, bg=COLOR_HEADER)
        head_row.pack(fill=tk.X, ipady=4)
        tk.Label(head_row, text=f"SCAN RESULTS: Total Reclaimable Space: {round(total_mb, 1)} MB", font=("Segoe UI", 9, "bold"), fg=COLOR_GREEN, bg=COLOR_HEADER).pack(side=tk.LEFT, padx=10)

        for key, item in items.items():
            row = tk.Frame(self.cleaner_list_frame, bg="#0d1117", bd=1, relief=tk.SOLID)
            row.pack(fill=tk.X, padx=8, pady=3, ipady=3)

            tk.Label(row, text=item.title, font=("Segoe UI", 9, "bold"), fg=COLOR_TEXT, bg="#0d1117").pack(side=tk.LEFT, padx=8)
            tk.Label(row, text=f"{item.file_count} files | {item.total_mb} MB", font=("Segoe UI", 9), fg=COLOR_CYAN, bg="#0d1117").pack(side=tk.LEFT, padx=10)
            tk.Label(row, text=item.description, font=("Segoe UI", 8), fg=COLOR_MUTED, bg="#0d1117").pack(side=tk.LEFT, padx=10)

            btn_one = tk.Button(
                row,
                text="Clean",
                font=("Segoe UI", 8, "bold"),
                bg=COLOR_HEADER,
                fg=COLOR_TEXT,
                command=lambda k=key: self._clean_single_target(k),
                cursor="hand2",
                padx=8,
            )
            btn_one.pack(side=tk.RIGHT, padx=8)

    def _clean_single_target(self, target_key: str):
        res = storage_cleaner.clean_target(target_key)
        messagebox.showinfo("Storage Cleaned", res.get("message"))
        self._scan_storage_items()

    def _clean_storage_items(self):
        res = storage_cleaner.clean_all()
        messagebox.showinfo("Storage Cleanup Complete", res.get("message"))
        self._scan_storage_items()

    def _empty_recycle_bin(self):
        if messagebox.askyesno("Empty Recycle Bin", "Permanently empty all files in the Windows Recycle Bin?"):
            res = storage_cleaner.empty_recycle_bin()
            messagebox.showinfo("Recycle Bin", res.get("message"))
            self._scan_storage_items()

    # =========================================================================
    # 5. STARTUP MANAGER PANEL
    # =========================================================================

    def _build_startup_panel(self):
        pane = tk.Frame(self.content_area, bg=COLOR_PANEL)
        pane.pack(fill=tk.BOTH, expand=True, padx=14, pady=12)

        # Toolbar
        bar = tk.Frame(pane, bg=COLOR_PANEL)
        bar.pack(fill=tk.X, pady=(0, 8))

        btn_ref = tk.Button(bar, text="🔄 Refresh List", font=("Segoe UI", 8, "bold"), bg=COLOR_HEADER, fg=COLOR_CYAN, command=self._refresh_startup_table, cursor="hand2", padx=8)
        btn_ref.pack(side=tk.LEFT, padx=(0, 8))

        btn_toggle = tk.Button(bar, text="⚡ Toggle Enabled / Disabled", font=("Segoe UI", 8, "bold"), bg=COLOR_HEADER, fg=COLOR_PURPLE, command=self._toggle_selected_startup, cursor="hand2", padx=10)
        btn_toggle.pack(side=tk.LEFT)

        cols = ("name", "status", "source", "command")
        self.startup_tree = ttk.Treeview(pane, columns=cols, show="headings", selectmode="browse")
        self.startup_tree.heading("name", text="Program Name")
        self.startup_tree.heading("status", text="Status")
        self.startup_tree.heading("source", text="Location")
        self.startup_tree.heading("command", text="Command Path")

        self.startup_tree.column("name", width=180)
        self.startup_tree.column("status", width=90, anchor=tk.CENTER)
        self.startup_tree.column("source", width=140)
        self.startup_tree.column("command", width=360)

        s_scroll = ttk.Scrollbar(pane, orient="vertical", command=self.startup_tree.yview)
        self.startup_tree.configure(yscrollcommand=s_scroll.set)

        self.startup_tree.pack(side=tk.LEFT, fill=tk.BOTH, expand=True)
        s_scroll.pack(side=tk.RIGHT, fill=tk.Y)

        self._refresh_startup_table()

    def _refresh_startup_table(self):
        if not hasattr(self, "startup_tree") or not self.startup_tree.winfo_exists():
            return

        for item in self.startup_tree.get_children():
            self.startup_tree.delete(item)

        items = startup_manager.get_startup_items()
        for i in items:
            st = "✓ Enabled" if i.enabled else "✗ Disabled"
            self.startup_tree.insert("", tk.END, values=(i.name, st, i.source, i.command))

    def _toggle_selected_startup(self):
        sel = self.startup_tree.selection()
        if not sel:
            messagebox.showwarning("No Selection", "Select an item to enable or disable.")
            return

        vals = self.startup_tree.item(sel[0])["values"]
        name = str(vals[0])
        status = str(vals[1])
        source = str(vals[2])

        if "Enabled" in status:
            res = startup_manager.disable_startup_item(name, source)
        else:
            res = startup_manager.enable_startup_item(name)

        messagebox.showinfo("Startup Manager", res.get("message"))
        self._refresh_startup_table()

    # =========================================================================
    # 6. SERVICES MANAGER PANEL
    # =========================================================================

    def _build_services_panel(self):
        pane = tk.Frame(self.content_area, bg=COLOR_PANEL)
        pane.pack(fill=tk.BOTH, expand=True, padx=14, pady=12)

        # Toolbar
        bar = tk.Frame(pane, bg=COLOR_PANEL)
        bar.pack(fill=tk.X, pady=(0, 8))

        tk.Label(bar, text="Filter:", font=("Segoe UI", 9, "bold"), fg=COLOR_TEXT, bg=COLOR_PANEL).pack(side=tk.LEFT, padx=(0, 4))
        self.var_svc_search = tk.StringVar()
        ent = tk.Entry(bar, textvariable=self.var_svc_search, font=("Segoe UI", 9), bg="#0d1117", fg=COLOR_TEXT, insertbackground=COLOR_TEXT, width=18)
        ent.pack(side=tk.LEFT, padx=(0, 8), ipady=2)
        ent.bind("<KeyRelease>", lambda e: self._refresh_services_table())

        btn_ref = tk.Button(bar, text="🔄 Refresh", font=("Segoe UI", 8, "bold"), bg=COLOR_HEADER, fg=COLOR_CYAN, command=self._refresh_services_table, cursor="hand2", padx=8)
        btn_ref.pack(side=tk.LEFT, padx=(0, 8))

        btn_start = tk.Button(bar, text="▶ Start", font=("Segoe UI", 8, "bold"), bg=COLOR_GREEN, fg="#ffffff", command=lambda: self._service_action("start"), cursor="hand2", padx=8)
        btn_start.pack(side=tk.LEFT, padx=(0, 4))

        btn_stop = tk.Button(bar, text="⏹ Stop", font=("Segoe UI", 8, "bold"), bg=COLOR_RED, fg="#ffffff", command=lambda: self._service_action("stop"), cursor="hand2", padx=8)
        btn_stop.pack(side=tk.LEFT, padx=(0, 4))

        btn_restart = tk.Button(bar, text="🔁 Restart", font=("Segoe UI", 8), bg=COLOR_HEADER, fg=COLOR_TEXT, command=lambda: self._service_action("restart"), cursor="hand2", padx=8)
        btn_restart.pack(side=tk.LEFT)

        cols = ("name", "disp", "status", "start_type", "category", "core")
        self.svc_tree = ttk.Treeview(pane, columns=cols, show="headings", selectmode="browse")
        self.svc_tree.heading("name", text="Service Name")
        self.svc_tree.heading("disp", text="Display Name")
        self.svc_tree.heading("status", text="Status")
        self.svc_tree.heading("start_type", text="Startup Type")
        self.svc_tree.heading("category", text="Category")
        self.svc_tree.heading("core", text="Shield")

        self.svc_tree.column("name", width=140)
        self.svc_tree.column("disp", width=220)
        self.svc_tree.column("status", width=80, anchor=tk.CENTER)
        self.svc_tree.column("start_type", width=90, anchor=tk.CENTER)
        self.svc_tree.column("category", width=90, anchor=tk.CENTER)
        self.svc_tree.column("core", width=90, anchor=tk.CENTER)

        s_scroll = ttk.Scrollbar(pane, orient="vertical", command=self.svc_tree.yview)
        self.svc_tree.configure(yscrollcommand=s_scroll.set)

        self.svc_tree.pack(side=tk.LEFT, fill=tk.BOTH, expand=True)
        s_scroll.pack(side=tk.RIGHT, fill=tk.Y)

        self._refresh_services_table()

    def _refresh_services_table(self):
        if not hasattr(self, "svc_tree") or not self.svc_tree.winfo_exists():
            return

        for item in self.svc_tree.get_children():
            self.svc_tree.delete(item)

        query = self.var_svc_search.get().strip()
        services = services_manager.get_services(search_query=query, limit=120)

        for s in services:
            shield_lbl = "🛡️ Core Windows" if s.is_core else "Standard"
            self.svc_tree.insert("", tk.END, values=(s.name, s.display_name, s.status, s.start_type, s.category.upper(), shield_lbl))

    def _service_action(self, action_type: str):
        sel = self.svc_tree.selection()
        if not sel:
            messagebox.showwarning("No Selection", "Select a service from the table.")
            return

        name = str(self.svc_tree.item(sel[0])["values"][0])
        if action_type == "start":
            res = services_manager.start_service(name)
        elif action_type == "stop":
            res = services_manager.stop_service(name)
        else:
            res = services_manager.restart_service(name)

        messagebox.showinfo("Service Action", res.get("message"))
        self._refresh_services_table()

    # =========================================================================
    # 7. APPS MANAGER PANEL
    # =========================================================================

    def _build_apps_panel(self):
        pane = tk.Frame(self.content_area, bg=COLOR_PANEL)
        pane.pack(fill=tk.BOTH, expand=True, padx=14, pady=12)

        bar = tk.Frame(pane, bg=COLOR_PANEL)
        bar.pack(fill=tk.X, pady=(0, 8))

        tk.Label(bar, text="Search Apps:", font=("Segoe UI", 9, "bold"), fg=COLOR_TEXT, bg=COLOR_PANEL).pack(side=tk.LEFT, padx=(0, 4))
        self.var_app_search = tk.StringVar()
        ent = tk.Entry(bar, textvariable=self.var_app_search, font=("Segoe UI", 9), bg="#0d1117", fg=COLOR_TEXT, insertbackground=COLOR_TEXT, width=20)
        ent.pack(side=tk.LEFT, padx=(0, 8), ipady=2)
        ent.bind("<KeyRelease>", lambda e: self._refresh_apps_table())

        btn_ref = tk.Button(bar, text="🔄 Refresh", font=("Segoe UI", 8, "bold"), bg=COLOR_HEADER, fg=COLOR_CYAN, command=self._refresh_apps_table, cursor="hand2", padx=8)
        btn_ref.pack(side=tk.LEFT, padx=(0, 8))

        btn_uninst = tk.Button(bar, text="🗑️ Launch Uninstaller", font=("Segoe UI", 8, "bold"), bg=COLOR_RED, fg="#ffffff", command=self._uninstall_selected_app, cursor="hand2", padx=10)
        btn_uninst.pack(side=tk.RIGHT)

        cols = ("name", "version", "publisher", "size", "date")
        self.apps_tree = ttk.Treeview(pane, columns=cols, show="headings", selectmode="browse")
        self.apps_tree.heading("name", text="Application Name")
        self.apps_tree.heading("version", text="Version")
        self.apps_tree.heading("publisher", text="Publisher")
        self.apps_tree.heading("size", text="Est. Size (MB)")
        self.apps_tree.heading("date", text="Install Date")

        self.apps_tree.column("name", width=260)
        self.apps_tree.column("version", width=100)
        self.apps_tree.column("publisher", width=160)
        self.apps_tree.column("size", width=90, anchor=tk.E)
        self.apps_tree.column("date", width=90, anchor=tk.CENTER)

        s_scroll = ttk.Scrollbar(pane, orient="vertical", command=self.apps_tree.yview)
        self.apps_tree.configure(yscrollcommand=s_scroll.set)

        self.apps_tree.pack(side=tk.LEFT, fill=tk.BOTH, expand=True)
        s_scroll.pack(side=tk.RIGHT, fill=tk.Y)

        self._refresh_apps_table()

    def _refresh_apps_table(self):
        if not hasattr(self, "apps_tree") or not self.apps_tree.winfo_exists():
            return

        for item in self.apps_tree.get_children():
            self.apps_tree.delete(item)

        query = self.var_app_search.get().strip()
        apps = app_manager.get_installed_apps(search_query=query, limit=150)

        for a in apps:
            sz_str = f"{a.estimated_size_mb} MB" if a.estimated_size_mb > 0 else "N/A"
            self.apps_tree.insert("", tk.END, values=(a.name, a.version, a.publisher, sz_str, a.install_date))

    def _uninstall_selected_app(self):
        sel = self.apps_tree.selection()
        if not sel:
            messagebox.showwarning("No Selection", "Select an app to uninstall.")
            return

        app_name = str(self.apps_tree.item(sel[0])["values"][0])
        if messagebox.askyesno("Confirm Uninstallation", f"Are you sure you want to launch the uninstaller for:\n'{app_name}'?"):
            res = app_manager.launch_uninstall(app_name)
            messagebox.showinfo("Uninstaller Launched", res.get("message"))

    # =========================================================================
    # 8. TWEAKS & PRIVACY PANEL
    # =========================================================================

    def _build_tweaks_panel(self):
        pane = tk.Frame(self.content_area, bg=COLOR_PANEL)
        pane.pack(fill=tk.BOTH, expand=True, padx=14, pady=12)

        # Tabs: Explorer & System Tweaks vs Privacy & Telemetry
        notebook = ttk.Notebook(pane)
        notebook.pack(fill=tk.BOTH, expand=True)

        tab_sys = tk.Frame(notebook, bg="#0d1117")
        tab_priv = tk.Frame(notebook, bg="#0d1117")
        notebook.add(tab_sys, text="  🛠️ Explorer & System Tweaks  ")
        notebook.add(tab_priv, text="  🛡️ Privacy & Telemetry Hardening  ")

        # 1. System Tweaks
        tweaks = tweaks_manager.get_all_tweaks()
        for tid, tinfo in tweaks.items():
            card = tk.Frame(tab_sys, bg=COLOR_PANEL, bd=1, relief=tk.SOLID)
            card.pack(fill=tk.X, padx=10, pady=4, ipady=4)

            tk.Label(card, text=tinfo["title"], font=("Segoe UI", 9, "bold"), fg=COLOR_CYAN, bg=COLOR_PANEL).pack(anchor=tk.W, padx=10, pady=(2, 1))
            tk.Label(card, text=f"Impact: {tinfo['impact']}", font=("Segoe UI", 8), fg=COLOR_MUTED, bg=COLOR_PANEL).pack(anchor=tk.W, padx=10)

            btn_box = tk.Frame(card, bg=COLOR_PANEL)
            btn_box.pack(fill=tk.X, padx=10, pady=(4, 2))

            status_txt = "STATUS: APPLIED" if tinfo["is_applied"] else "STATUS: DEFAULT (NOT APPLIED)"
            fg_col = COLOR_GREEN if tinfo["is_applied"] else COLOR_MUTED
            tk.Label(btn_box, text=status_txt, font=("Segoe UI", 8, "bold"), fg=fg_col, bg=COLOR_PANEL).pack(side=tk.LEFT)

            if tinfo["is_applied"]:
                btn_revert = tk.Button(btn_box, text="Revert to Default", font=("Segoe UI", 8), bg=COLOR_HEADER, fg=COLOR_RED, command=lambda t=tid: self._revert_tweak_ui(t), cursor="hand2", padx=8)
                btn_revert.pack(side=tk.RIGHT)
            else:
                btn_apply = tk.Button(btn_box, text="✓ Apply Tweak", font=("Segoe UI", 8, "bold"), bg=COLOR_GREEN, fg="#ffffff", command=lambda t=tid: self._apply_tweak_ui(t), cursor="hand2", padx=8)
                btn_apply.pack(side=tk.RIGHT)

        # 2. Privacy Tweaks
        priv_items = privacy_center.get_privacy_settings()
        for pid, pinfo in priv_items.items():
            card = tk.Frame(tab_priv, bg=COLOR_PANEL, bd=1, relief=tk.SOLID)
            card.pack(fill=tk.X, padx=10, pady=4, ipady=4)

            tk.Label(card, text=pinfo["title"], font=("Segoe UI", 9, "bold"), fg=COLOR_CYAN, bg=COLOR_PANEL).pack(anchor=tk.W, padx=10, pady=(2, 1))
            tk.Label(card, text=f"Benefit: {pinfo['privacy_benefit']}", font=("Segoe UI", 8), fg=COLOR_GREEN, bg=COLOR_PANEL).pack(anchor=tk.W, padx=10)
            tk.Label(card, text=f"Data Collected: {pinfo['data_collected']}", font=("Segoe UI", 8), fg=COLOR_MUTED, bg=COLOR_PANEL).pack(anchor=tk.W, padx=10)

            btn_box = tk.Frame(card, bg=COLOR_PANEL)
            btn_box.pack(fill=tk.X, padx=10, pady=(4, 2))

            status_txt = "STATUS: PROTECTED" if pinfo["is_protected"] else "STATUS: STANDARD TELEMETRY ACTIVE"
            fg_col = COLOR_GREEN if pinfo["is_protected"] else COLOR_AMBER
            tk.Label(btn_box, text=status_txt, font=("Segoe UI", 8, "bold"), fg=fg_col, bg=COLOR_PANEL).pack(side=tk.LEFT)

            if pinfo["is_protected"]:
                btn_revert = tk.Button(btn_box, text="Restore Default", font=("Segoe UI", 8), bg=COLOR_HEADER, fg=COLOR_MUTED, command=lambda p=pid: self._toggle_privacy_ui(p, False), cursor="hand2", padx=8)
                btn_revert.pack(side=tk.RIGHT)
            else:
                btn_protect = tk.Button(btn_box, text="🛡️ Enable Protection", font=("Segoe UI", 8, "bold"), bg=COLOR_GREEN, fg="#ffffff", command=lambda p=pid: self._toggle_privacy_ui(p, True), cursor="hand2", padx=8)
                btn_protect.pack(side=tk.RIGHT)

    def _apply_tweak_ui(self, tweak_id: str):
        res = tweaks_manager.apply_tweak(tweak_id)
        messagebox.showinfo("Tweak Applied", res.get("message"))
        self._build_tweaks_panel()

    def _revert_tweak_ui(self, tweak_id: str):
        res = tweaks_manager.revert_tweak(tweak_id)
        messagebox.showinfo("Tweak Reverted", res.get("message"))
        self._build_tweaks_panel()

    def _toggle_privacy_ui(self, privacy_id: str, enable: bool):
        res = privacy_center.set_protection(privacy_id, enable)
        messagebox.showinfo("Privacy Setting", res.get("message"))
        self._build_tweaks_panel()

    # =========================================================================
    # 9. NETWORK CENTER PANEL
    # =========================================================================

    def _build_network_panel(self):
        pane = tk.Frame(self.content_area, bg=COLOR_PANEL)
        pane.pack(fill=tk.BOTH, expand=True, padx=14, pady=12)

        # Adapter Telemetry Card
        ad_card = tk.Frame(pane, bg="#0d1117", bd=1, relief=tk.SOLID)
        ad_card.pack(fill=tk.X, pady=(0, 10), ipady=6)
        tk.Label(ad_card, text="🌐 NETWORK ADAPTERS", font=("Segoe UI", 9, "bold"), fg=COLOR_CYAN, bg="#0d1117").pack(anchor=tk.W, padx=10, pady=(2, 4))

        adapters = network_center.get_adapter_info()
        for a in adapters:
            st = "CONNECTED" if a["is_up"] else "DISCONNECTED"
            tk.Label(ad_card, text=f"• {a['name']}: IPv4: {a['ipv4']} | MAC: {a['mac']} | Status: {st}", font=("Segoe UI", 9), fg=COLOR_TEXT, bg="#0d1117").pack(anchor=tk.W, padx=12)

        # Ping Latency Tester & DNS Flush
        diag_card = tk.Frame(pane, bg="#0d1117", bd=1, relief=tk.SOLID)
        diag_card.pack(fill=tk.X, pady=(0, 10), ipady=8)
        tk.Label(diag_card, text="⚡ LATENCY TEST & DNS ACTIONS", font=("Segoe UI", 9, "bold"), fg=COLOR_CYAN, bg="#0d1117").pack(anchor=tk.W, padx=10, pady=(2, 6))

        d_row = tk.Frame(diag_card, bg="#0d1117")
        d_row.pack(fill=tk.X, padx=10, pady=2)

        tk.Label(d_row, text="Ping Host:", font=("Segoe UI", 9), fg=COLOR_TEXT, bg="#0d1117").pack(side=tk.LEFT, padx=(0, 4))
        self.var_ping_host = tk.StringVar(value="1.1.1.1")
        ent_host = tk.Entry(d_row, textvariable=self.var_ping_host, font=("Segoe UI", 9), bg=COLOR_PANEL, fg=COLOR_TEXT, width=16)
        ent_host.pack(side=tk.LEFT, padx=(0, 8))

        btn_ping = tk.Button(d_row, text="Run Ping Test", font=("Segoe UI", 8, "bold"), bg=COLOR_HEADER, fg=COLOR_CYAN, command=self._run_ping_test, cursor="hand2", padx=8)
        btn_ping.pack(side=tk.LEFT, padx=(0, 12))

        btn_flush = tk.Button(d_row, text="🧹 Flush DNS Resolver Cache", font=("Segoe UI", 8, "bold"), bg=COLOR_GREEN, fg="#ffffff", command=self._flush_dns_ui, cursor="hand2", padx=10)
        btn_flush.pack(side=tk.LEFT)

        self.lbl_ping_res = tk.Label(diag_card, text="Ping results will appear here.", font=("Segoe UI", 8), fg=COLOR_MUTED, bg="#0d1117")
        self.lbl_ping_res.pack(anchor=tk.W, padx=10, pady=(6, 2))

        # Active Network Connections
        conns_card = tk.Frame(pane, bg="#0d1117", bd=1, relief=tk.SOLID)
        conns_card.pack(fill=tk.BOTH, expand=True)
        tk.Label(conns_card, text="🔌 ACTIVE NETWORK SOCKETS (ESTABLISHED)", font=("Segoe UI", 9, "bold"), fg=COLOR_PURPLE, bg="#0d1117").pack(anchor=tk.W, padx=10, pady=(4, 4))

        cols = ("pid", "local", "remote", "status")
        self.net_tree = ttk.Treeview(conns_card, columns=cols, show="headings", selectmode="browse", height=8)
        self.net_tree.heading("pid", text="PID")
        self.net_tree.heading("local", text="Local Address")
        self.net_tree.heading("remote", text="Remote Address")
        self.net_tree.heading("status", text="Status")

        self.net_tree.column("pid", width=70, anchor=tk.CENTER)
        self.net_tree.column("local", width=220)
        self.net_tree.column("remote", width=220)
        self.net_tree.column("status", width=120, anchor=tk.CENTER)

        self.net_tree.pack(fill=tk.BOTH, expand=True, padx=8, pady=(0, 6))
        self._refresh_net_conns()

    def _run_ping_test(self):
        host = self.var_ping_host.get().strip()
        self.lbl_ping_res.config(text=f"Pinging {host} (4 packets)...", fg=COLOR_CYAN)
        self.root.update_idletasks()

        def do_ping():
            res = network_center.ping_test(host)
            if res.get("success"):
                self.lbl_ping_res.config(text=f"✓ Ping {host}: Avg Latency = {res['avg_latency_ms']} ms | Packet Loss = {res['packet_loss_percent']}%", fg=COLOR_GREEN)
            else:
                self.lbl_ping_res.config(text=f"✗ Ping failed: {res.get('message', 'Host unreachable')}", fg=COLOR_RED)

        threading.Thread(target=do_ping, daemon=True).start()

    def _flush_dns_ui(self):
        res = network_center.flush_dns()
        messagebox.showinfo("Flush DNS", res.get("message"))

    def _refresh_net_conns(self):
        if not hasattr(self, "net_tree") or not self.net_tree.winfo_exists():
            return
        for item in self.net_tree.get_children():
            self.net_tree.delete(item)
        for c in network_center.get_active_connections(limit=30):
            self.net_tree.insert("", tk.END, values=(c["pid"], c["local_addr"], c["remote_addr"], c["status"]))

    # =========================================================================
    # 10. HEALTH & RESTORE PANEL
    # =========================================================================

    def _build_health_panel(self):
        pane = tk.Frame(self.content_area, bg=COLOR_PANEL)
        pane.pack(fill=tk.BOTH, expand=True, padx=14, pady=12)

        # Health & Drive Integrity Card
        card1 = tk.Frame(pane, bg="#0d1117", bd=1, relief=tk.SOLID)
        card1.pack(fill=tk.X, pady=(0, 10), ipady=6)

        tk.Label(card1, text="🩺 SYSTEM INTEGRITY & DIAGNOSTICS", font=("Segoe UI", 9, "bold"), fg=COLOR_CYAN, bg="#0d1117").pack(anchor=tk.W, padx=10, pady=(2, 4))
        dirty = health_diagnostics.check_drive_dirty("C:")
        tk.Label(card1, text=f"• Drive C: Health Status: {dirty['message']}", font=("Segoe UI", 9), fg=COLOR_GREEN if not dirty["is_dirty"] else COLOR_RED, bg="#0d1117").pack(anchor=tk.W, padx=12)

        recs_box = tk.Frame(card1, bg="#0d1117")
        recs_box.pack(fill=tk.X, padx=12, pady=4)
        for r in health_diagnostics.get_integrity_recommendations():
            tk.Label(recs_box, text=f"• {r['title']}: Run '{r['command']}' in Admin Terminal ({r['description']})", font=("Segoe UI", 8), fg=COLOR_MUTED, bg="#0d1117").pack(anchor=tk.W)

        # Windows Event Log Recent Errors
        card2 = tk.Frame(pane, bg="#0d1117", bd=1, relief=tk.SOLID)
        card2.pack(fill=tk.X, pady=(0, 10), ipady=6)
        tk.Label(card2, text="📋 RECENT WINDOWS SYSTEM EVENT LOG ERRORS", font=("Segoe UI", 9, "bold"), fg=COLOR_AMBER, bg="#0d1117").pack(anchor=tk.W, padx=10, pady=(2, 4))

        errs = health_diagnostics.get_recent_event_errors(limit=4)
        if errs:
            for e in errs:
                tk.Label(card2, text=f"[{e['time']}] {e['source']}: {e['message']}", font=("Segoe UI", 8), fg=COLOR_TEXT, bg="#0d1117").pack(anchor=tk.W, padx=12)
        else:
            tk.Label(card2, text="✓ No critical Windows system errors logged in recent event queries.", font=("Segoe UI", 9), fg=COLOR_GREEN, bg="#0d1117").pack(anchor=tk.W, padx=12)

        # System Restore Points Card
        card3 = tk.Frame(pane, bg="#0d1117", bd=1, relief=tk.SOLID)
        card3.pack(fill=tk.BOTH, expand=True, ipady=6)

        head_r = tk.Frame(card3, bg="#0d1117")
        head_r.pack(fill=tk.X, padx=10, pady=(2, 4))
        tk.Label(head_r, text="🛡️ WINDOWS SYSTEM RESTORE CHECKPOINTS", font=("Segoe UI", 9, "bold"), fg=COLOR_PURPLE, bg="#0d1117").pack(side=tk.LEFT)

        btn_create_rp = tk.Button(
            head_r,
            text="➕ Create Restore Point Now",
            font=("Segoe UI", 8, "bold"),
            bg=COLOR_ACTIVE_NAV,
            fg="#ffffff",
            command=self._create_restore_point_ui,
            cursor="hand2",
            padx=10,
        )
        btn_create_rp.pack(side=tk.RIGHT)

        pts = restore_center.get_restore_points()
        if pts:
            for p in pts[:5]:
                tk.Label(card3, text=f"• #{p['seq']}: {p['description']} ({p['creation_time']})", font=("Segoe UI", 9), fg=COLOR_TEXT, bg="#0d1117").pack(anchor=tk.W, padx=12)
        else:
            tk.Label(card3, text="No existing restore points found or System Protection is disabled on drive C:.", font=("Segoe UI", 9), fg=COLOR_MUTED, bg="#0d1117").pack(anchor=tk.W, padx=12)

    def _create_restore_point_ui(self):
        desc = "REN-AI Manual Safety Checkpoint"
        if messagebox.askyesno("Create Restore Point", f"Create a new Windows System Restore checkpoint named:\n'{desc}'?\n(Requires running as Administrator)"):
            res = restore_center.create_restore_point(desc)
            if res.get("success"):
                messagebox.showinfo("Restore Point Created", res.get("message"))
                self._build_health_panel()
            else:
                messagebox.showwarning("Restore Point", res.get("message"))

    # =========================================================================
    # 11. MODES & GAMING PANEL
    # =========================================================================

    def _build_modes_panel(self):
        pane = tk.Frame(self.content_area, bg=COLOR_PANEL)
        pane.pack(fill=tk.BOTH, expand=True, padx=14, pady=12)

        # 4 Operational Modes Selector Card
        card_m = tk.Frame(pane, bg="#0d1117", bd=1, relief=tk.SOLID)
        card_m.pack(fill=tk.X, pady=(0, 10), ipady=8)

        tk.Label(card_m, text="🎮 OPERATIONAL PROFILES", font=("Segoe UI", 10, "bold"), fg=COLOR_CYAN, bg="#0d1117").pack(anchor=tk.W, padx=12, pady=(2, 6))

        m_box = tk.Frame(card_m, bg="#0d1117")
        m_box.pack(fill=tk.X, padx=12, pady=2)

        for mode_key in ("programmer", "gaming", "balanced", "performance"):
            desc = modes_manager.get_mode_description(mode_key)
            is_active = preferences.active_mode == mode_key

            b_frame = tk.Frame(m_box, bg="#161b22" if is_active else "#0d1117", bd=1, relief=tk.SOLID)
            b_frame.pack(side=tk.LEFT, fill=tk.BOTH, expand=True, padx=3, pady=2, ipady=4)

            tk.Label(b_frame, text=desc["name"], font=("Segoe UI", 9, "bold"), fg=COLOR_CYAN if is_active else COLOR_TEXT, bg=b_frame["bg"]).pack(pady=(2, 1))
            status_txt = "ACTIVE" if is_active else "Select"
            btn = tk.Button(
                b_frame,
                text=status_txt,
                font=("Segoe UI", 8, "bold"),
                bg=COLOR_ACTIVE_NAV if is_active else COLOR_HEADER,
                fg="#ffffff" if is_active else COLOR_MUTED,
                command=lambda m=mode_key: self._activate_mode_ui(m),
                cursor="hand2",
                padx=8,
            )
            btn.pack(pady=4)

        # Developer Tools Arsenal
        card_dev = tk.Frame(pane, bg="#0d1117", bd=1, relief=tk.SOLID)
        card_dev.pack(fill=tk.BOTH, expand=True, pady=(0, 10), ipady=6)

        head_d = tk.Frame(card_dev, bg="#0d1117")
        head_d.pack(fill=tk.X, padx=12, pady=(2, 6))
        tk.Label(head_d, text="🛠️ DEVELOPER TOOLS ARSENAL (WINGET)", font=("Segoe UI", 10, "bold"), fg=COLOR_PURPLE, bg="#0d1117").pack(side=tk.LEFT)

        btn_dev_clean = tk.Button(
            head_d,
            text="🧹 Clean Dev Caches (__pycache__)",
            font=("Segoe UI", 8, "bold"),
            bg=COLOR_HEADER,
            fg=COLOR_CYAN,
            command=self._clean_dev_caches_ui,
            cursor="hand2",
            padx=8,
        )
        btn_dev_clean.pack(side=tk.RIGHT)

        dev_status = modes_manager.check_developer_tools()
        tools_grid = tk.Frame(card_dev, bg="#0d1117")
        tools_grid.pack(fill=tk.BOTH, expand=True, padx=12)

        for t in dev_status["installed"]:
            row = tk.Frame(tools_grid, bg="#0d1117")
            row.pack(fill=tk.X, pady=1)
            tk.Label(row, text=f"✓ {t['name']}", font=("Segoe UI", 9), fg=COLOR_GREEN, bg="#0d1117").pack(side=tk.LEFT)
            tk.Label(row, text=t["description"], font=("Segoe UI", 8), fg=COLOR_MUTED, bg="#0d1117").pack(side=tk.LEFT, padx=8)

        for t in dev_status["missing"]:
            row = tk.Frame(tools_grid, bg="#0d1117")
            row.pack(fill=tk.X, pady=1)
            tk.Label(row, text=f"✗ {t['name']}", font=("Segoe UI", 9), fg=COLOR_AMBER, bg="#0d1117").pack(side=tk.LEFT)
            tk.Label(row, text=f"Winget: {t['winget_id']}", font=("Segoe UI", 8), fg=COLOR_MUTED, bg="#0d1117").pack(side=tk.LEFT, padx=8)
            tk.Button(row, text="Install", font=("Segoe UI", 7, "bold"), bg=COLOR_HEADER, fg=COLOR_CYAN, command=lambda k=t["key"]: self._install_dev_tool_ui(k), cursor="hand2", padx=6).pack(side=tk.RIGHT)

        # Chris Titus Tech WinUtil Launcher Card
        card_ctt = tk.Frame(pane, bg=COLOR_HEADER, bd=1, relief=tk.SOLID)
        card_ctt.pack(fill=tk.X, ipady=6)

        tk.Label(card_ctt, text="CHRIS TITUS TECH WINDOWS UTILITY (WINUTIL)", font=("Segoe UI", 9, "bold"), fg=COLOR_CYAN, bg=COLOR_HEADER).pack(anchor=tk.W, padx=12, pady=(2, 1))
        tk.Label(card_ctt, text="Launches the famous open-source WinUtil script in an elevated PowerShell session for deep debloat and tweaks.", font=("Segoe UI", 8), fg=COLOR_TEXT, bg=COLOR_HEADER).pack(anchor=tk.W, padx=12)

        btn_ctt = tk.Button(
            card_ctt,
            text="🚀 Launch Chris Titus WinUtil",
            font=("Segoe UI", 9, "bold"),
            bg="#1f6feb",
            fg="#ffffff",
            command=self._launch_ctt_ui,
            cursor="hand2",
            padx=12,
            pady=3,
        )
        btn_ctt.pack(anchor=tk.W, padx=12, pady=(4, 2))

    def _activate_mode_ui(self, mode_name: str):
        res = modes_manager.set_mode(mode_name, apply_optimizations=True)
        self.lbl_mode_badge.config(text=f"[{mode_name.upper()} MODE]")
        messagebox.showinfo("Mode Activated", res.get("message"))
        self._build_modes_panel()

    def _clean_dev_caches_ui(self):
        res = modes_manager.clean_dev_caches()
        messagebox.showinfo("Dev Caches Purged", res.get("message"))

    def _install_dev_tool_ui(self, tool_key: str):
        tool = DEV_TOOLS_CATALOG.get(tool_key, {})
        name = tool.get("name", tool_key)
        if messagebox.askyesno("Install Developer Tool", f"Run winget to install {name}?"):
            res = modes_manager.install_tool(tool_key)
            messagebox.showinfo("Installation", res.get("message"))
            self._build_modes_panel()

    def _launch_ctt_ui(self):
        msg = (
            "You are about to launch Chris Titus Tech Windows Utility (winutil).\n\n"
            "Command executed: irm https://christitus.com/win | iex\n"
            "This will open an interactive PowerShell window.\n\n"
            "Proceed?"
        )
        if messagebox.askyesno("Launch CTT WinUtil", msg):
            res = debloat_manager.launch_ctt_winutil()
            messagebox.showinfo("CTT Winutil", res.get("message"))

    # =========================================================================
    # 12. BENCHMARK CENTER PANEL
    # =========================================================================

    def _build_benchmark_panel(self):
        pane = tk.Frame(self.content_area, bg=COLOR_PANEL)
        pane.pack(fill=tk.BOTH, expand=True, padx=14, pady=12)

        # Top Action Bar
        bar = tk.Frame(pane, bg="#0d1117", bd=1, relief=tk.SOLID)
        bar.pack(fill=tk.X, pady=(0, 10), ipady=8)

        tk.Label(bar, text="📈 DETERMINISTIC SYSTEM BENCHMARK", font=("Segoe UI", 10, "bold"), fg=COLOR_CYAN, bg="#0d1117").pack(anchor=tk.W, padx=12, pady=(2, 4))
        tk.Label(bar, text="Tests CPU hashing throughput, Memory copy bandwidth, and Disk sequential write/read speeds.", font=("Segoe UI", 8), fg=COLOR_MUTED, bg="#0d1117").pack(anchor=tk.W, padx=12)

        btn_run = tk.Button(
            bar,
            text="🚀 Run Benchmark Now (Takes ~3s)",
            font=("Segoe UI", 10, "bold"),
            bg=COLOR_ACTIVE_NAV,
            fg="#ffffff",
            command=self._run_benchmark_ui,
            cursor="hand2",
            padx=14,
            pady=4,
        )
        btn_run.pack(anchor=tk.W, padx=12, pady=(6, 4))

        self.lbl_bench_status = tk.Label(bar, text="", font=("Segoe UI", 9, "bold"), fg=COLOR_GREEN, bg="#0d1117")
        self.lbl_bench_status.pack(anchor=tk.W, padx=12)

        # Past Benchmark Runs Table
        card_hist = tk.Frame(pane, bg="#0d1117", bd=1, relief=tk.SOLID)
        card_hist.pack(fill=tk.BOTH, expand=True)

        tk.Label(card_hist, text="HISTORICAL BENCHMARK SCORES", font=("Segoe UI", 9, "bold"), fg=COLOR_PURPLE, bg="#0d1117").pack(anchor=tk.W, padx=12, pady=(6, 4))

        cols = ("date", "composite", "cpu", "mem", "disk", "duration")
        self.bench_tree = ttk.Treeview(card_hist, columns=cols, show="headings", selectmode="browse", height=8)
        self.bench_tree.heading("date", text="Date & Time")
        self.bench_tree.heading("composite", text="Composite Score")
        self.bench_tree.heading("cpu", text="CPU Score")
        self.bench_tree.heading("mem", text="Memory (MB/s)")
        self.bench_tree.heading("disk", text="Disk Write (MB/s)")
        self.bench_tree.heading("duration", text="Duration")

        self.bench_tree.column("date", width=160)
        self.bench_tree.column("composite", width=120, anchor=tk.CENTER)
        self.bench_tree.column("cpu", width=100, anchor=tk.CENTER)
        self.bench_tree.column("mem", width=120, anchor=tk.CENTER)
        self.bench_tree.column("disk", width=120, anchor=tk.CENTER)
        self.bench_tree.column("duration", width=80, anchor=tk.CENTER)

        self.bench_tree.pack(fill=tk.BOTH, expand=True, padx=10, pady=(0, 8))
        self._refresh_bench_history()

    def _refresh_bench_history(self):
        if not hasattr(self, "bench_tree") or not self.bench_tree.winfo_exists():
            return
        for item in self.bench_tree.get_children():
            self.bench_tree.delete(item)
        for h in benchmark_center.get_history():
            self.bench_tree.insert(
                "",
                tk.END,
                values=(
                    h.get("datetime", ""),
                    f"🏆 {h.get('composite_score', 0)}",
                    h.get("cpu_score", 0),
                    f"{h.get('memory_speed_mb_s', 0)} MB/s",
                    f"{h.get('disk_write_mb_s', 0)} MB/s",
                    f"{h.get('duration_seconds', 0)}s",
                ),
            )

    def _run_benchmark_ui(self):
        self.lbl_bench_status.config(text="Running benchmark tests across CPU, Memory, and Disk...", fg=COLOR_CYAN)
        self.root.update_idletasks()

        def do_bench():
            res = benchmark_center.run_benchmark()
            self.lbl_bench_status.config(
                text=f"✓ Benchmark Complete! Composite Score: {res['composite_score']} (CPU: {res['cpu_score']}, RAM: {res['memory_speed_mb_s']} MB/s, Disk: {res['disk_write_mb_s']} MB/s)",
                fg=COLOR_GREEN,
            )
            self._refresh_bench_history()

        threading.Thread(target=do_bench, daemon=True).start()

    # =========================================================================
    # 13. CHANGE HISTORY & ROLLBACK PANEL
    # =========================================================================

    def _build_history_panel(self):
        pane = tk.Frame(self.content_area, bg=COLOR_PANEL)
        pane.pack(fill=tk.BOTH, expand=True, padx=14, pady=12)

        bar = tk.Frame(pane, bg=COLOR_PANEL)
        bar.pack(fill=tk.X, pady=(0, 8))

        tk.Label(bar, text="📜 SYSTEM AUDIT TRAIL & VERIFIED ROLLBACK", font=("Segoe UI", 10, "bold"), fg=COLOR_CYAN, bg=COLOR_PANEL).pack(side=tk.LEFT)

        btn_rollback = tk.Button(
            bar,
            text="↩️ Rollback Selected Action",
            font=("Segoe UI", 8, "bold"),
            bg=COLOR_RED,
            fg="#ffffff",
            command=self._rollback_selected_history,
            cursor="hand2",
            padx=12,
        )
        btn_rollback.pack(side=tk.RIGHT)

        btn_ref = tk.Button(bar, text="🔄 Refresh", font=("Segoe UI", 8, "bold"), bg=COLOR_HEADER, fg=COLOR_TEXT, command=self._refresh_history_table, cursor="hand2", padx=8)
        btn_ref.pack(side=tk.RIGHT, padx=8)

        cols = ("eid", "time", "title", "category", "status", "verified")
        self.hist_tree = ttk.Treeview(pane, columns=cols, show="headings", selectmode="browse")
        self.hist_tree.heading("eid", text="Entry ID")
        self.hist_tree.heading("time", text="Date & Time")
        self.hist_tree.heading("title", text="Action Performed")
        self.hist_tree.heading("category", text="Category")
        self.hist_tree.heading("status", text="Status")
        self.hist_tree.heading("verified", text="Verification")

        self.hist_tree.column("eid", width=120)
        self.hist_tree.column("time", width=140)
        self.hist_tree.column("title", width=260)
        self.hist_tree.column("category", width=100, anchor=tk.CENTER)
        self.hist_tree.column("status", width=90, anchor=tk.CENTER)
        self.hist_tree.column("verified", width=110, anchor=tk.CENTER)

        h_scroll = ttk.Scrollbar(pane, orient="vertical", command=self.hist_tree.yview)
        self.hist_tree.configure(yscrollcommand=h_scroll.set)

        self.hist_tree.pack(side=tk.LEFT, fill=tk.BOTH, expand=True)
        h_scroll.pack(side=tk.RIGHT, fill=tk.Y)

        self._refresh_history_table()

    def _refresh_history_table(self):
        if not hasattr(self, "hist_tree") or not self.hist_tree.winfo_exists():
            return
        for item in self.hist_tree.get_children():
            self.hist_tree.delete(item)

        for entry in change_history.get_history(limit=80):
            st = "Rolled Back" if entry.get("rolled_back") else entry.get("status", "executed").capitalize()
            vf = "✓ Verified" if entry.get("verified") else "Unverified"
            self.hist_tree.insert(
                "",
                tk.END,
                values=(entry.get("entry_id"), entry.get("datetime"), entry.get("title"), entry.get("category"), st, vf),
            )

    def _rollback_selected_history(self):
        sel = self.hist_tree.selection()
        if not sel:
            messagebox.showwarning("No Selection", "Select an action from the history table to roll back.")
            return

        eid = str(self.hist_tree.item(sel[0])["values"][0])
        entry = change_history.get_entry(eid)
        if not entry:
            messagebox.showerror("Error", "Selected entry not found.")
            return

        if entry.get("rolled_back"):
            messagebox.showinfo("Already Rolled Back", f"Action '{entry.get('title')}' is already marked as rolled back.")
            return

        title = entry.get("title", "")
        if messagebox.askyesno("Confirm Rollback", f"Are you sure you want to roll back:\n'{title}'?"):
            res = action_executor.rollback_entry(eid)
            if res.get("success"):
                messagebox.showinfo("Rollback Complete", res.get("message"))
                self._refresh_history_table()
            else:
                # Fallback manual reversal attempt if standard registry tweak
                act_id = entry.get("action_id", "")
                if act_id.startswith("tweak_"):
                    twk_key = act_id[6:]
                    rev_res = tweaks_manager.revert_tweak(twk_key)
                    change_history.mark_rolled_back(eid, message=rev_res.get("message", "Reverted"))
                    messagebox.showinfo("Rollback Complete", rev_res.get("message"))
                    self._refresh_history_table()
                elif act_id.startswith("privacy_"):
                    priv_key = act_id[8:]
                    rev_res = privacy_center.set_protection(priv_key, enable=False)
                    change_history.mark_rolled_back(eid, message=rev_res.get("message", "Restored default"))
                    messagebox.showinfo("Rollback Complete", rev_res.get("message"))
                    self._refresh_history_table()
                else:
                    messagebox.showwarning("Rollback Notice", res.get("message"))

    # =========================================================================
    # 14. PREFERENCES & SUPPORT PANEL
    # =========================================================================

    def _build_settings_panel(self):
        pane = tk.Frame(self.content_area, bg=COLOR_PANEL)
        pane.pack(fill=tk.BOTH, expand=True, padx=14, pady=12)

        # Downloads Folder Config Card
        card_dl = tk.Frame(pane, bg="#0d1117", bd=1, relief=tk.SOLID)
        card_dl.pack(fill=tk.X, pady=(0, 10), ipady=8)

        tk.Label(card_dl, text="📁 DOWNLOADS FOLDER CONFIGURATION", font=("Segoe UI", 9, "bold"), fg=COLOR_CYAN, bg="#0d1117").pack(anchor=tk.W, padx=12, pady=(2, 4))
        p_row = tk.Frame(card_dl, bg="#0d1117")
        p_row.pack(fill=tk.X, padx=12, pady=2)

        self.var_set_dl = tk.StringVar(value=preferences.get("downloads_folder", str(Path.home() / "Downloads")))
        ent_dl = tk.Entry(p_row, textvariable=self.var_set_dl, font=("Segoe UI", 9), bg=COLOR_PANEL, fg=COLOR_TEXT, insertbackground=COLOR_TEXT)
        ent_dl.pack(side=tk.LEFT, fill=tk.X, expand=True, ipady=3, padx=(0, 8))

        btn_browse = tk.Button(p_row, text="Browse...", font=("Segoe UI", 8, "bold"), bg=COLOR_HEADER, fg=COLOR_CYAN, command=self._browse_set_dl, cursor="hand2", padx=10)
        btn_browse.pack(side=tk.RIGHT)

        btn_save_dl = tk.Button(card_dl, text="Save Folder Path", font=("Segoe UI", 8, "bold"), bg=COLOR_ACTIVE_NAV, fg="#ffffff", command=self._save_downloads_pref, cursor="hand2", padx=10)
        btn_save_dl.pack(anchor=tk.W, padx=12, pady=(4, 2))

        # Support Page Card: YouTube @cyan_code & GitHub Section
        card_sup = tk.Frame(pane, bg="#0d1117", bd=1, relief=tk.SOLID)
        card_sup.pack(fill=tk.X, pady=(0, 10), ipady=8)

        tk.Label(card_sup, text="❤️ SUPPORT, COMMUNITY & CREATOR", font=("Segoe UI", 10, "bold"), fg=COLOR_PURPLE, bg="#0d1117").pack(anchor=tk.W, padx=12, pady=(2, 4))
        tk.Label(card_sup, text="REN-AI is proudly human-driven, transparent, and created to liberate Windows from bloat and AI slop.", font=("Segoe UI", 8), fg=COLOR_MUTED, bg="#0d1117").pack(anchor=tk.W, padx=12, pady=(0, 6))

        s_btn_row = tk.Frame(card_sup, bg="#0d1117")
        s_btn_row.pack(fill=tk.X, padx=12, pady=2)

        # YouTube Channel Link
        btn_yt = tk.Button(
            s_btn_row,
            text="📺 YouTube Channel @cyan_code",
            font=("Segoe UI", 9, "bold"),
            bg="#cc0000",
            fg="#ffffff",
            activebackground="#ff0000",
            command=lambda: webbrowser.open("https://youtube.com/@cyan_code"),
            cursor="hand2",
            padx=12,
            pady=4,
        )
        btn_yt.pack(side=tk.LEFT, padx=(0, 10))

        # GitHub Repo Link
        btn_gh = tk.Button(
            s_btn_row,
            text="⭐ GitHub Repository",
            font=("Segoe UI", 9, "bold"),
            bg="#238636",
            fg="#ffffff",
            activebackground="#2ea043",
            command=lambda: webbrowser.open("https://github.com/takumicodes/REN-AI"),
            cursor="hand2",
            padx=12,
            pady=4,
        )
        btn_gh.pack(side=tk.LEFT, padx=(0, 10))

        # Issues Link
        btn_issues = tk.Button(
            s_btn_row,
            text="🐛 Report an Issue",
            font=("Segoe UI", 9),
            bg=COLOR_HEADER,
            fg=COLOR_TEXT,
            command=lambda: webbrowser.open("https://github.com/takumicodes/REN-AI/issues"),
            cursor="hand2",
            padx=10,
            pady=4,
        )
        btn_issues.pack(side=tk.LEFT)

        # Philosophy & Safety Invariants Card
        card_phil = tk.Frame(pane, bg=COLOR_HEADER, bd=1, relief=tk.SOLID)
        card_phil.pack(fill=tk.BOTH, expand=True, ipady=6)

        tk.Label(card_phil, text="THE REN-AI PHILOSOPHY (ZERO AI-SLOP)", font=("Segoe UI", 9, "bold"), fg=COLOR_CYAN, bg=COLOR_HEADER).pack(anchor=tk.W, padx=12, pady=(2, 2))
        phil_text = (
            "• Observe -> Understand -> Explain -> Recommend -> Ask User -> Execute -> Verify -> Rollback.\n"
            "• Never mutates your system without explicit human consent.\n"
            "• Preserves full before-state backups so any modification can be reversed in 1 click.\n"
            "• Tailored specifically for developers, power users, and gamers wanting maximum PC performance."
        )
        tk.Label(card_phil, text=phil_text, font=("Segoe UI", 8), fg=COLOR_TEXT, bg=COLOR_HEADER, justify=tk.LEFT).pack(anchor=tk.W, padx=12)

    def _browse_set_dl(self):
        f = filedialog.askdirectory(initialdir=self.var_set_dl.get(), title="Select Downloads Folder")
        if f:
            self.var_set_dl.set(f)

    def _save_downloads_pref(self):
        val = self.var_set_dl.get().strip()
        if val and Path(val).exists():
            preferences.set("downloads_folder", val)
            organizer.folder = Path(val)
            messagebox.showinfo("Saved", f"Downloads folder path updated to:\n{val}")
        else:
            messagebox.showwarning("Invalid Path", "Please select an existing folder path.")

    # =========================================================================
    # REFRESH LOOP & BACKGROUND TRAY HANDLING
    # =========================================================================

    def _refresh_gui_loop(self):
        """Periodically refreshes hardware telemetry safely."""
        try:
            snapshot = get_system_snapshot()
            cpu = snapshot["cpu_percent"]
            ram = snapshot["ram"]
            disk = snapshot["primary_disk_percent"]
            bat = snapshot["battery"]
            plan = snapshot["power_profile"]

            # Header text
            self.lbl_header_metrics.config(
                text=f"CPU: {cpu}% | RAM: {ram['percent_used']}% | Disk: {disk}% | Power: {plan}"
            )

            # Dashboard widgets if dashboard is currently active
            if hasattr(self, "lbl_dash_cpu") and self.lbl_dash_cpu.winfo_exists():
                self.lbl_dash_cpu.config(text=f"CPU Utilization: {cpu}%")
                self.bar_dash_cpu["value"] = min(100, max(0, cpu))

                self.lbl_dash_ram.config(text=f"RAM: {ram['percent_used']}% ({ram['used_gb']} GB used / {ram['total_gb']} GB)")
                self.bar_dash_ram["value"] = min(100, max(0, ram["percent_used"]))

                self.lbl_dash_disk.config(text=f"Storage: {disk}% used")
                self.bar_dash_disk["value"] = min(100, max(0, disk))

                ctx_cat = snapshot.get("context", {}).get("category", "general").upper()
                self.lbl_dash_ctx.config(
                    text=f"Context: {ctx_cat} | Active Power Scheme: {plan} | Silent Observer: ACTIVE"
                )
        except Exception:
            pass

        self.root.after(2000, self._refresh_gui_loop)

    def on_close_window(self):
        """Intercepts window close button to minimize to background."""
        if preferences.get("close_to_background", True):
            self.minimize_to_background()
        else:
            self.quit_app_completely()

    def minimize_to_background(self):
        """Hides the GUI window while keeping the background observer running."""
        self.root.withdraw()
        try:
            self._ensure_restore_controller()
        except Exception:
            pass

    def _ensure_restore_controller(self):
        """Creates a small top-level controller so the user can easily restore."""
        if hasattr(self, "tray_top") and self.tray_top.winfo_exists():
            return

        self.tray_top = tk.Toplevel(self.root)
        self.tray_top.title("REN Running in BG")
        self.tray_top.geometry("310x120+40+40")
        self.tray_top.configure(bg=COLOR_PANEL)
        self.tray_top.resizable(False, False)
        self.tray_top.attributes("-topmost", True)

        tk.Label(
            self.tray_top,
            text="🪐 REN-AI Control Center in BG",
            font=("Segoe UI", 9, "bold"),
            fg=COLOR_CYAN,
            bg=COLOR_PANEL,
        ).pack(pady=(10, 2))

        tk.Label(
            self.tray_top,
            text="Silent observer active. Window minimized.",
            font=("Segoe UI", 8),
            fg=COLOR_MUTED,
            bg=COLOR_PANEL,
        ).pack()

        btn_row = tk.Frame(self.tray_top, bg=COLOR_PANEL)
        btn_row.pack(pady=8)

        btn_restore = tk.Button(
            btn_row,
            text="Open Control Center",
            font=("Segoe UI", 8, "bold"),
            bg="#1f6feb",
            fg="#ffffff",
            command=self.restore_from_background,
            cursor="hand2",
            padx=8,
        )
        btn_restore.pack(side=tk.LEFT, padx=4)

        btn_quit = tk.Button(
            btn_row,
            text="Exit Completely",
            font=("Segoe UI", 8),
            bg=COLOR_HEADER,
            fg=COLOR_RED,
            command=self.quit_app_completely,
            cursor="hand2",
            padx=8,
        )
        btn_quit.pack(side=tk.LEFT, padx=4)

    def restore_from_background(self):
        """Restores the main window from background."""
        if hasattr(self, "tray_top") and self.tray_top.winfo_exists():
            self.tray_top.destroy()
        self.root.deiconify()
        self.root.lift()
        self.root.focus_force()

    def quit_app_completely(self):
        """Completely terminates background observer and destroys GUI."""
        if messagebox.askyesno("Exit REN", "Are you sure you want to completely stop REN-AI Control Center and exit?"):
            observer.stop()
            self.root.destroy()
            sys.exit(0)


def launch_gui():
    """Main function to launch REN-AI Windows Control Center."""
    root = tk.Tk()
    app = RenDesktopApp(root)
    root.mainloop()


if __name__ == "__main__":
    launch_gui()
