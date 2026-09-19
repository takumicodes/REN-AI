"""
REN Desktop Assistant - Full Graphical User Interface (GUI)
Built with Python Tkinter & ttk with Cyber Dark Styling.
Features:
- First-install preferences onboarding page (profession, mode, downloads path).
- Live real-time dashboard for CPU, RAM, Disk, Battery, Power Plan, and context.
- Non-intrusive action queue with Approve/Dismiss buttons.
- Operational Modes tab with Developer Arsenal (winget installer, dev caches cleaner).
- Safe Downloads Organizer with dry-run preview, execution, and 1-click Undo Rollback.
- Safe Windows Debloat & Chris Titus Tech Utility (winutil) launcher.
- Preferences & Settings configuration.
- Support Page: @cyan_code YouTube channel & GitHub Support & Contribute section.
- Silent background daemon execution with close-to-background tray behavior.
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
    )
    from .system_observer import observer
    from .actions import action_queue
    from .downloads_organizer import organizer
    from .debloat import debloat_manager
    from .modes import modes_manager, DEV_TOOLS_CATALOG
except ImportError:
    from preferences import preferences, DEFAULT_PREFERENCES
    from system_status import (
        get_system_snapshot,
        set_power_profile,
        get_available_power_schemes,
    )
    from system_observer import observer
    from actions import action_queue
    from downloads_organizer import organizer
    from debloat import debloat_manager
    from modes import modes_manager, DEV_TOOLS_CATALOG


# --- Styling Constants ---
COLOR_BG = "#0d1117"          # Dark background
COLOR_PANEL = "#161b22"       # Card / container background
COLOR_HEADER = "#21262d"      # Tab / header background
COLOR_BORDER = "#30363d"      # Border lines
COLOR_TEXT = "#f0f6fc"        # Bright text
COLOR_MUTED = "#8b949e"       # Muted text
COLOR_CYAN = "#00e5ff"        # Cyan accent
COLOR_BLUE = "#58a6ff"        # Primary blue
COLOR_GREEN = "#2ea043"       # Success / Installed
COLOR_AMBER = "#d29922"       # Warning / Notice
COLOR_RED = "#da3633"         # Danger / Revert
COLOR_PURPLE = "#bc8cff"      # Mode accent


class RenDesktopApp:
    """Main Application Controller for REN Desktop Assistant GUI."""

    def __init__(self, root: tk.Tk):
        self.root = root
        self.root.title("🪐 REN Desktop Assistant - Autonomous System")
        self.root.geometry("980x720")
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
            self.show_main_hud()

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
            text="🪐 Welcome to REN Desktop Assistant",
            font=("Segoe UI", 18, "bold"),
            fg=COLOR_CYAN,
            bg=COLOR_PANEL,
        )
        lbl_title.pack(anchor=tk.W, padx=20, pady=(6, 2))

        lbl_subtitle = tk.Label(
            title_box,
            text="Silent, Autonomous Windows Optimization — 100% Human-Driven with Zero AI Slop.\nPlease configure your initial preferences below:",
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

        tk.Label(
            scroll_content,
            text="REN organizes your loose downloads safely into categorized subfolders with full rollback capability.",
            font=("Segoe UI", 9),
            fg=COLOR_MUTED,
            bg=COLOR_PANEL,
        ).pack(anchor=tk.W, pady=(0, 6))

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
            activebackground=COLOR_BORDER,
            activeforeground=COLOR_CYAN,
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

        tk.Label(
            scroll_content,
            text="Helps REN tailor developer tools, debloat profiles, and system resource optimization.",
            font=("Segoe UI", 9),
            fg=COLOR_MUTED,
            bg=COLOR_PANEL,
        ).pack(anchor=tk.W, pady=(0, 6))

        self.var_profession = tk.StringVar(value=preferences.get("profession", "Software Engineer"))
        professions = [
            ("Software Engineer / Developer", "Optimizes compile speed, dev tools, and dev cache cleaning"),
            ("Designer / Content Creator", "Optimizes GPU RAM allocation, media downloads, and scratch disks"),
            ("Student / Researcher / Office", "Whisper-quiet operation, documents organization, battery conservation"),
            ("Gamer / Hardware Power User", "Ultimate performance power plan, max clock boosts, standby RAM purging"),
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
            ("programmer", "Programmer Mode (Recommended)", "Developer tools compatibility (Git, VS Code, wt), low RAM debloat, battery & compile booster"),
            ("balanced", "Balanced Mode", "Unobtrusive daily assistant, standard Windows balance, whisper-quiet background monitoring"),
            ("performance", "Performance Mode", "Maximum hardware performance, high power plan, frees standby memory for heavy workloads"),
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
                fg=COLOR_PURPLE if m_key == "programmer" else COLOR_TEXT,
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
            text="🛡️ 4. Silent Background Behavior:",
            font=("Segoe UI", 11, "bold"),
            fg=COLOR_CYAN,
            bg=COLOR_PANEL,
        ).pack(anchor=tk.W, pady=(18, 4))

        self.var_close_bg = tk.BooleanVar(value=preferences.get("close_to_background", True))
        cb_bg = tk.Checkbutton(
            scroll_content,
            text="Run silently in background when window is closed (minimize to tray)",
            variable=self.var_close_bg,
            font=("Segoe UI", 10),
            fg=COLOR_TEXT,
            bg=COLOR_PANEL,
            selectcolor="#0d1117",
            activebackground=COLOR_PANEL,
            activeforeground=COLOR_CYAN,
        )
        cb_bg.pack(anchor=tk.W, pady=2)

        self.var_human_driven = tk.BooleanVar(value=True)
        cb_hd = tk.Checkbutton(
            scroll_content,
            text="100% Human-Driven Mode: Always prompt for confirmation before system-altering actions",
            variable=self.var_human_driven,
            font=("Segoe UI", 10),
            fg=COLOR_TEXT,
            bg=COLOR_PANEL,
            selectcolor="#0d1117",
            activebackground=COLOR_PANEL,
            activeforeground=COLOR_CYAN,
        )
        cb_hd.pack(anchor=tk.W, pady=2)

        # Bottom Button Bar
        btn_bar = tk.Frame(wizard_frame, bg=COLOR_BG)
        btn_bar.pack(fill=tk.X, pady=(20, 0))

        btn_defaults = tk.Button(
            btn_bar,
            text="⚡ Use Recommended Programmer Defaults",
            font=("Segoe UI", 10),
            bg=COLOR_HEADER,
            fg=COLOR_MUTED,
            activebackground=COLOR_BORDER,
            activeforeground=COLOR_TEXT,
            command=self._apply_wizard_defaults,
            cursor="hand2",
            padx=16,
            pady=6,
        )
        btn_defaults.pack(side=tk.LEFT)

        btn_save = tk.Button(
            btn_bar,
            text="🚀 Initialize Core & Save Preferences",
            font=("Segoe UI", 11, "bold"),
            bg="#1f6feb",
            fg="#ffffff",
            activebackground="#388bfd",
            activeforeground="#ffffff",
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
        self.var_human_driven.set(True)
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
            human_driven_mode=self.var_human_driven.get(),
            onboarding_completed=True,
        )
        # Update organizer path
        organizer.folder = Path(downloads_path)
        # Apply initial mode
        modes_manager.set_mode(self.var_mode.get(), apply_optimizations=True)

        messagebox.showinfo(
            "REN Initialized",
            f"Preferences successfully saved!\nActive Mode: {self.var_mode.get().capitalize()}\nProfession: {self.var_profession.get()}\n\nWelcome to REN Desktop Assistant."
        )
        self.show_main_hud()

    # =========================================================================
    # MAIN HUD & SPECIAL TABS
    # =========================================================================

    def show_main_hud(self):
        """Builds and displays the main multi-tab HUD interface."""
        for w in self.container.winfo_children():
            w.destroy()

        # Top Banner / Header
        self.header = tk.Frame(self.container, bg=COLOR_PANEL, bd=1, relief=tk.SOLID)
        self.header.pack(fill=tk.X, padx=16, pady=(12, 8), ipady=8)

        # Header Title
        lbl_h_title = tk.Label(
            self.header,
            text="🪐 REN-AI DESKTOP ASSISTANT",
            font=("Segoe UI", 13, "bold"),
            fg=COLOR_CYAN,
            bg=COLOR_PANEL,
        )
        lbl_h_title.pack(side=tk.LEFT, padx=(16, 12))

        # Mode Badge
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
            activeforeground=COLOR_RED,
            command=self.quit_app_completely,
            cursor="hand2",
            padx=10,
        )
        btn_exit.pack(side=tk.RIGHT, padx=(6, 16))

        btn_min = tk.Button(
            self.header,
            text="Minimize to Tray",
            font=("Segoe UI", 9),
            bg=COLOR_HEADER,
            fg=COLOR_MUTED,
            activebackground=COLOR_BORDER,
            activeforeground=COLOR_TEXT,
            command=self.minimize_to_background,
            cursor="hand2",
            padx=10,
        )
        btn_min.pack(side=tk.RIGHT, padx=6)

        self.lbl_header_metrics = tk.Label(
            self.header,
            text="Loading metrics...",
            font=("Segoe UI", 9),
            fg=COLOR_MUTED,
            bg=COLOR_PANEL,
        )
        self.lbl_header_metrics.pack(side=tk.RIGHT, padx=16)

        # Tabs Container
        style = ttk.Style()
        style.theme_use("default")
        style.configure("TNotebook", background=COLOR_BG, borderwidth=0)
        style.configure("TNotebook.Tab", background=COLOR_PANEL, foreground=COLOR_TEXT, font=("Segoe UI", 10, "bold"), padding=[16, 6])
        style.map("TNotebook.Tab", background=[("selected", "#1f6feb")], foreground=[("selected", "#ffffff")])

        self.notebook = ttk.Notebook(self.container)
        self.notebook.pack(fill=tk.BOTH, expand=True, padx=16, pady=(0, 12))

        # Tab 1: Dashboard
        self.tab_dashboard = tk.Frame(self.notebook, bg=COLOR_BG)
        self.notebook.add(self.tab_dashboard, text="  📊 Dashboard  ")
        self._build_dashboard_tab()

        # Tab 2: Operational Modes
        self.tab_modes = tk.Frame(self.notebook, bg=COLOR_BG)
        self.notebook.add(self.tab_modes, text="  ⚡ Modes  ")
        self._build_modes_tab()

        # Tab 3: Downloads Organizer
        self.tab_downloads = tk.Frame(self.notebook, bg=COLOR_BG)
        self.notebook.add(self.tab_downloads, text="  📁 Downloads  ")
        self._build_downloads_tab()

        # Tab 4: Debloat & Optimizations
        self.tab_debloat = tk.Frame(self.notebook, bg=COLOR_BG)
        self.notebook.add(self.tab_debloat, text="  🛡️ Debloat  ")
        self._build_debloat_tab()

        # Tab 5: Settings / Preferences
        self.tab_settings = tk.Frame(self.notebook, bg=COLOR_BG)
        self.notebook.add(self.tab_settings, text="  ⚙️ Preferences  ")
        self._build_settings_tab()

        # Tab 6: Support & Contribute
        self.tab_support = tk.Frame(self.notebook, bg=COLOR_BG)
        self.notebook.add(self.tab_support, text="  ❤️ Support & Community  ")
        self._build_support_tab()

        # Start Periodic GUI Status Refresher
        self._refresh_gui_loop()

    # -------------------------------------------------------------------------
    # TAB 1: DASHBOARD
    # -------------------------------------------------------------------------

    def _build_dashboard_tab(self):
        pane = tk.Frame(self.tab_dashboard, bg=COLOR_BG)
        pane.pack(fill=tk.BOTH, expand=True, padx=8, pady=8)

        # Hardware Metrics Grid (Top Half)
        metrics_grid = tk.Frame(pane, bg=COLOR_BG)
        metrics_grid.pack(fill=tk.X, pady=(0, 10))

        # Card 1: CPU & RAM
        card1 = tk.Frame(metrics_grid, bg=COLOR_PANEL, bd=1, relief=tk.SOLID)
        card1.pack(side=tk.LEFT, fill=tk.BOTH, expand=True, padx=(0, 6), ipady=8)

        tk.Label(card1, text="💻 PROCESSOR & MEMORY", font=("Segoe UI", 10, "bold"), fg=COLOR_CYAN, bg=COLOR_PANEL).pack(anchor=tk.W, padx=12, pady=(4, 8))
        self.lbl_cpu = tk.Label(card1, text="CPU: -- %", font=("Segoe UI", 10), fg=COLOR_TEXT, bg=COLOR_PANEL)
        self.lbl_cpu.pack(anchor=tk.W, padx=12, pady=2)
        self.bar_cpu = ttk.Progressbar(card1, length=200, mode="determinate")
        self.bar_cpu.pack(fill=tk.X, padx=12, pady=(0, 8))

        self.lbl_ram = tk.Label(card1, text="RAM: -- % (-- GB / -- GB)", font=("Segoe UI", 10), fg=COLOR_TEXT, bg=COLOR_PANEL)
        self.lbl_ram.pack(anchor=tk.W, padx=12, pady=2)
        self.bar_ram = ttk.Progressbar(card1, length=200, mode="determinate")
        self.bar_ram.pack(fill=tk.X, padx=12, pady=(0, 4))

        # Card 2: Disk & Power
        card2 = tk.Frame(metrics_grid, bg=COLOR_PANEL, bd=1, relief=tk.SOLID)
        card2.pack(side=tk.RIGHT, fill=tk.BOTH, expand=True, padx=(6, 0), ipady=8)

        tk.Label(card2, text="⚡ POWER & STORAGE", font=("Segoe UI", 10, "bold"), fg=COLOR_CYAN, bg=COLOR_PANEL).pack(anchor=tk.W, padx=12, pady=(4, 8))
        self.lbl_disk = tk.Label(card2, text="Primary Disk: -- %", font=("Segoe UI", 10), fg=COLOR_TEXT, bg=COLOR_PANEL)
        self.lbl_disk.pack(anchor=tk.W, padx=12, pady=2)
        self.bar_disk = ttk.Progressbar(card2, length=200, mode="determinate")
        self.bar_disk.pack(fill=tk.X, padx=12, pady=(0, 8))

        self.lbl_bat = tk.Label(card2, text="Battery: --", font=("Segoe UI", 10), fg=COLOR_TEXT, bg=COLOR_PANEL)
        self.lbl_bat.pack(anchor=tk.W, padx=12, pady=2)
        self.lbl_plan = tk.Label(card2, text="Power Scheme: --", font=("Segoe UI", 9), fg=COLOR_MUTED, bg=COLOR_PANEL)
        self.lbl_plan.pack(anchor=tk.W, padx=12, pady=(0, 4))

        # Bottom Half: Human-Driven Recommendations
        rec_card = tk.Frame(pane, bg=COLOR_PANEL, bd=1, relief=tk.SOLID)
        rec_card.pack(fill=tk.BOTH, expand=True, pady=(4, 0))

        rec_header = tk.Frame(rec_card, bg=COLOR_HEADER)
        rec_header.pack(fill=tk.X, ipady=6)

        tk.Label(rec_header, text="⚡ PENDING RECOMMENDATIONS (HUMAN-DRIVEN)", font=("Segoe UI", 10, "bold"), fg=COLOR_CYAN, bg=COLOR_HEADER).pack(side=tk.LEFT, padx=12)

        btn_refresh = tk.Button(
            rec_header,
            text="🔄 Refresh",
            font=("Segoe UI", 8, "bold"),
            bg="#30363d",
            fg=COLOR_TEXT,
            command=self._refresh_recommendations_ui,
            cursor="hand2",
            padx=8,
        )
        btn_refresh.pack(side=tk.RIGHT, padx=12)

        self.rec_scroll_frame = tk.Frame(rec_card, bg=COLOR_PANEL)
        self.rec_scroll_frame.pack(fill=tk.BOTH, expand=True, padx=12, pady=8)

        self._refresh_recommendations_ui()

    def _refresh_recommendations_ui(self):
        for w in self.rec_scroll_frame.winfo_children():
            w.destroy()

        recs = action_queue.get_pending()
        if not recs:
            lbl_empty = tk.Label(
                self.rec_scroll_frame,
                text="✓ All system metrics optimal. No pending interventions required.\nREN is observing silently with zero disruptions.",
                font=("Segoe UI", 10),
                fg=COLOR_MUTED,
                bg=COLOR_PANEL,
                justify=tk.CENTER,
            )
            lbl_empty.pack(expand=True, pady=30)
            return

        for rec in recs:
            item = tk.Frame(self.rec_scroll_frame, bg="#0d1117", bd=1, relief=tk.SOLID)
            item.pack(fill=tk.X, pady=4, padx=4, ipady=4)

            top_row = tk.Frame(item, bg="#0d1117")
            top_row.pack(fill=tk.X, padx=8, pady=(4, 2))

            tk.Label(top_row, text=rec.title, font=("Segoe UI", 10, "bold"), fg=COLOR_TEXT, bg="#0d1117").pack(side=tk.LEFT)
            tk.Label(top_row, text=f"[{rec.category.upper()}]", font=("Segoe UI", 8), fg=COLOR_CYAN, bg="#0d1117").pack(side=tk.LEFT, padx=6)

            # Impact & Rationale
            tk.Label(item, text=f"Impact: {rec.impact}", font=("Segoe UI", 9), fg=COLOR_GREEN, bg="#0d1117").pack(anchor=tk.W, padx=8)
            tk.Label(item, text=f"Rationale: {rec.description}", font=("Segoe UI", 8), fg=COLOR_MUTED, bg="#0d1117").pack(anchor=tk.W, padx=8)

            btn_row = tk.Frame(item, bg="#0d1117")
            btn_row.pack(fill=tk.X, padx=8, pady=(4, 4))

            rec_id = rec.id
            btn_approve = tk.Button(
                btn_row,
                text="✓ Approve & Apply",
                font=("Segoe UI", 8, "bold"),
                bg=COLOR_GREEN,
                fg="#ffffff",
                activebackground="#3fb950",
                command=lambda r=rec_id: self._approve_recommendation(r),
                cursor="hand2",
                padx=8,
            )
            btn_approve.pack(side=tk.LEFT, padx=(0, 6))

            btn_dismiss = tk.Button(
                btn_row,
                text="✗ Dismiss",
                font=("Segoe UI", 8),
                bg=COLOR_HEADER,
                fg=COLOR_MUTED,
                activebackground=COLOR_BORDER,
                command=lambda r=rec_id: self._dismiss_recommendation(r),
                cursor="hand2",
                padx=8,
            )
            btn_dismiss.pack(side=tk.LEFT)

    def _approve_recommendation(self, rec_id: str):
        res = action_queue.approve(rec_id)
        self._refresh_recommendations_ui()
        messagebox.showinfo("Action Executed", res.get("message", "Action applied successfully."))

    def _dismiss_recommendation(self, rec_id: str):
        action_queue.dismiss(rec_id)
        self._refresh_recommendations_ui()

    # -------------------------------------------------------------------------
    # TAB 2: OPERATIONAL MODES & DEVELOPER ARSENAL
    # -------------------------------------------------------------------------

    def _build_modes_tab(self):
        pane = tk.Frame(self.tab_modes, bg=COLOR_BG)
        pane.pack(fill=tk.BOTH, expand=True, padx=12, pady=10)

        # Mode Selection Cards
        tk.Label(pane, text="⚡ SELECT OPERATING MODE", font=("Segoe UI", 11, "bold"), fg=COLOR_CYAN, bg=COLOR_BG).pack(anchor=tk.W, pady=(0, 6))

        modes_frame = tk.Frame(pane, bg=COLOR_BG)
        modes_frame.pack(fill=tk.X, pady=(0, 12))

        modes = [
            ("programmer", "🛠️ Programmer Mode", "Best compatibility for developers.\nInstalls dev tools, debloats Windows for low RAM, tunes power plan for compilation."),
            ("balanced", "⚖️ Balanced Mode", "Unobtrusive everyday assistant.\nStandard Windows balance, quiet downloads housekeeping, silent monitoring."),
            ("performance", "🚀 Performance Mode", "Maximum sustained clock speeds.\nHigh power plan, frees standby memory, zero throttling for heavy workloads."),
        ]

        self.mode_buttons = {}
        for m_key, m_name, m_desc in modes:
            card = tk.Frame(modes_frame, bg=COLOR_PANEL, bd=1, relief=tk.SOLID)
            card.pack(side=tk.LEFT, fill=tk.BOTH, expand=True, padx=4, ipady=6)

            tk.Label(card, text=m_name, font=("Segoe UI", 10, "bold"), fg=COLOR_TEXT, bg=COLOR_PANEL).pack(anchor=tk.W, padx=10, pady=(4, 2))
            tk.Label(card, text=m_desc, font=("Segoe UI", 8), fg=COLOR_MUTED, bg=COLOR_PANEL, justify=tk.LEFT, wraplength=240).pack(anchor=tk.W, padx=10, pady=(0, 6))

            btn = tk.Button(
                card,
                text="Activate Mode",
                font=("Segoe UI", 9, "bold"),
                bg="#1f6feb" if preferences.active_mode == m_key else COLOR_HEADER,
                fg="#ffffff" if preferences.active_mode == m_key else COLOR_MUTED,
                activebackground="#388bfd",
                command=lambda m=m_key: self._activate_mode(m),
                cursor="hand2",
                padx=10,
                pady=4,
            )
            btn.pack(anchor=tk.W, padx=10, pady=4)
            self.mode_buttons[m_key] = btn

        # Developer Tools Arsenal (Programmer Mode Section)
        dev_card = tk.Frame(pane, bg=COLOR_PANEL, bd=1, relief=tk.SOLID)
        dev_card.pack(fill=tk.BOTH, expand=True, pady=(4, 0))

        dev_top = tk.Frame(dev_card, bg=COLOR_HEADER)
        dev_top.pack(fill=tk.X, ipady=6)

        tk.Label(dev_top, text="🛠️ PROGRAMMER MODE: DEVELOPER TOOLS ARSENAL (WINGET)", font=("Segoe UI", 10, "bold"), fg=COLOR_CYAN, bg=COLOR_HEADER).pack(side=tk.LEFT, padx=12)

        btn_clean_cache = tk.Button(
            dev_top,
            text="🧹 Purge Dev Caches",
            font=("Segoe UI", 8, "bold"),
            bg="#30363d",
            fg=COLOR_AMBER,
            command=self._clean_dev_caches,
            cursor="hand2",
            padx=8,
        )
        btn_clean_cache.pack(side=tk.RIGHT, padx=12)

        self.dev_tools_list_frame = tk.Frame(dev_card, bg=COLOR_PANEL)
        self.dev_tools_list_frame.pack(fill=tk.BOTH, expand=True, padx=12, pady=10)

        self._refresh_dev_tools_ui()

    def _activate_mode(self, mode_name: str):
        res = modes_manager.set_mode(mode_name, apply_optimizations=True)
        self.lbl_mode_badge.config(text=f"[{mode_name.upper()} MODE]")
        for m_key, btn in self.mode_buttons.items():
            if m_key == mode_name:
                btn.config(bg="#1f6feb", fg="#ffffff", text="Active Mode")
            else:
                btn.config(bg=COLOR_HEADER, fg=COLOR_MUTED, text="Activate Mode")
        messagebox.showinfo("Mode Activated", res.get("message", f"Switched to {mode_name.capitalize()} Mode."))

    def _refresh_dev_tools_ui(self):
        for w in self.dev_tools_list_frame.winfo_children():
            w.destroy()

        tools_status = modes_manager.check_developer_tools()

        # Tools Grid
        for tool in tools_status["installed"] + tools_status["missing"]:
            t_row = tk.Frame(self.dev_tools_list_frame, bg="#0d1117", bd=1, relief=tk.SOLID)
            t_row.pack(fill=tk.X, pady=3, padx=2, ipady=3)

            is_inst = tool["is_installed"]
            badge_fg = COLOR_GREEN if is_inst else COLOR_AMBER
            badge_text = "✓ INSTALLED" if is_inst else "⚠ MISSING"

            tk.Label(t_row, text=badge_text, font=("Segoe UI", 8, "bold"), fg=badge_fg, bg="#0d1117", width=12, anchor=tk.W).pack(side=tk.LEFT, padx=8)
            tk.Label(t_row, text=tool["name"], font=("Segoe UI", 9, "bold"), fg=COLOR_TEXT, bg="#0d1117", width=24, anchor=tk.W).pack(side=tk.LEFT)
            tk.Label(t_row, text=tool["description"], font=("Segoe UI", 8), fg=COLOR_MUTED, bg="#0d1117").pack(side=tk.LEFT, padx=6)

            if not is_inst:
                btn_inst = tk.Button(
                    t_row,
                    text="Install (winget)",
                    font=("Segoe UI", 8, "bold"),
                    bg="#1f6feb",
                    fg="#ffffff",
                    activebackground="#388bfd",
                    command=lambda k=tool["key"]: self._install_dev_tool(k),
                    cursor="hand2",
                    padx=8,
                )
                btn_inst.pack(side=tk.RIGHT, padx=8)

        if tools_status["missing_count"] > 0:
            btn_inst_all = tk.Button(
                self.dev_tools_list_frame,
                text=f"⚡ Install All Missing Tools ({tools_status['missing_count']}) via Winget",
                font=("Segoe UI", 9, "bold"),
                bg="#1f6feb",
                fg="#ffffff",
                command=self._install_all_missing_tools,
                cursor="hand2",
                pady=4,
            )
            btn_inst_all.pack(anchor=tk.W, pady=(10, 0), padx=2)

    def _install_dev_tool(self, key: str):
        tool = DEV_TOOLS_CATALOG.get(key, {})
        if messagebox.askyesno("Confirm Install", f"Install {tool.get('name', key)} using official winget package?"):
            threading.Thread(target=self._run_tool_install_async, args=(key,), daemon=True).start()

    def _run_tool_install_async(self, key: str):
        res = modes_manager.install_tool(key)
        self.root.after(0, lambda: self._on_tool_installed(res))

    def _on_tool_installed(self, res: dict):
        self._refresh_dev_tools_ui()
        messagebox.showinfo("Tool Installer", res.get("message", "Done"))

    def _install_all_missing_tools(self):
        cmd = modes_manager.generate_winget_install_command()
        if messagebox.askyesno("Confirm Batch Install", f"Execute following command in PowerShell?\n\n{cmd}"):
            try:
                import subprocess
                subprocess.Popen(["powershell.exe", "-NoExit", "-Command", cmd])
            except Exception as e:
                messagebox.showerror("Execution Error", str(e))

    def _clean_dev_caches(self):
        res = modes_manager.clean_dev_caches()
        messagebox.showinfo("Dev Cache Cleaner", res.get("message", "Caches cleaned."))

    # -------------------------------------------------------------------------
    # TAB 3: DOWNLOADS ORGANIZER
    # -------------------------------------------------------------------------

    def _build_downloads_tab(self):
        pane = tk.Frame(self.tab_downloads, bg=COLOR_BG)
        pane.pack(fill=tk.BOTH, expand=True, padx=12, pady=10)

        # Folder Header
        hdr = tk.Frame(pane, bg=COLOR_PANEL, bd=1, relief=tk.SOLID)
        hdr.pack(fill=tk.X, pady=(0, 10), ipady=8)

        tk.Label(hdr, text="📁 DOWNLOADS FOLDER AUTOMATION", font=("Segoe UI", 11, "bold"), fg=COLOR_CYAN, bg=COLOR_PANEL).pack(anchor=tk.W, padx=12, pady=(2, 4))

        p_row = tk.Frame(hdr, bg=COLOR_PANEL)
        p_row.pack(fill=tk.X, padx=12, pady=2)

        self.lbl_curr_downloads = tk.Label(p_row, text=f"Active Path: {preferences.get('downloads_folder')}", font=("Segoe UI", 9), fg=COLOR_TEXT, bg=COLOR_PANEL)
        self.lbl_curr_downloads.pack(side=tk.LEFT)

        btn_ch_folder = tk.Button(
            p_row,
            text="Change Path...",
            font=("Segoe UI", 8, "bold"),
            bg=COLOR_HEADER,
            fg=COLOR_CYAN,
            command=self._change_downloads_path,
            cursor="hand2",
            padx=8,
        )
        btn_ch_folder.pack(side=tk.RIGHT)

        # Actions & Rollback Bar
        act_bar = tk.Frame(pane, bg=COLOR_PANEL, bd=1, relief=tk.SOLID)
        act_bar.pack(fill=tk.X, pady=(0, 10), ipady=8, padx=0)

        tk.Label(act_bar, text="SAFE ORGANIZATION ACTIONS & ROLLBACK", font=("Segoe UI", 10, "bold"), fg=COLOR_CYAN, bg=COLOR_PANEL).pack(anchor=tk.W, padx=12, pady=(0, 6))

        btn_box = tk.Frame(act_bar, bg=COLOR_PANEL)
        btn_box.pack(fill=tk.X, padx=12)

        btn_prev = tk.Button(
            btn_box,
            text="👁️ Dry-Run Preview",
            font=("Segoe UI", 9, "bold"),
            bg=COLOR_HEADER,
            fg=COLOR_TEXT,
            command=self._preview_downloads,
            cursor="hand2",
            padx=12,
            pady=4,
        )
        btn_prev.pack(side=tk.LEFT, padx=(0, 8))

        btn_org = tk.Button(
            btn_box,
            text="⚡ Organize Downloads Now",
            font=("Segoe UI", 9, "bold"),
            bg="#1f6feb",
            fg="#ffffff",
            command=self._execute_downloads_organization,
            cursor="hand2",
            padx=14,
            pady=4,
        )
        btn_org.pack(side=tk.LEFT, padx=(0, 8))

        # Rollback button prominently featured
        btn_undo = tk.Button(
            btn_box,
            text="⏪ Rollback / Undo Last Batch",
            font=("Segoe UI", 9, "bold"),
            bg=COLOR_HEADER,
            fg=COLOR_AMBER,
            activebackground=COLOR_BORDER,
            activeforeground=COLOR_AMBER,
            command=self._undo_downloads_organization,
            cursor="hand2",
            padx=14,
            pady=4,
        )
        btn_undo.pack(side=tk.RIGHT)

        # Output / Preview Card
        prev_card = tk.Frame(pane, bg=COLOR_PANEL, bd=1, relief=tk.SOLID)
        prev_card.pack(fill=tk.BOTH, expand=True)

        tk.Label(prev_card, text="STATUS & CATEGORY PREVIEW", font=("Segoe UI", 10, "bold"), fg=COLOR_MUTED, bg=COLOR_PANEL).pack(anchor=tk.W, padx=12, pady=(6, 4))

        self.txt_downloads_log = tk.Text(prev_card, bg="#0d1117", fg=COLOR_TEXT, font=("Consolas", 9), bd=0, wrap=tk.WORD)
        self.txt_downloads_log.pack(fill=tk.BOTH, expand=True, padx=12, pady=(0, 10))

        self._preview_downloads()

    def _change_downloads_path(self):
        f = filedialog.askdirectory(title="Select Downloads Folder")
        if f:
            preferences.set("downloads_folder", f)
            organizer.folder = Path(f)
            self.lbl_curr_downloads.config(text=f"Active Path: {f}")
            self._preview_downloads()

    def _preview_downloads(self):
        self.txt_downloads_log.delete("1.0", tk.END)
        prev = organizer.preview_organization(ignore_recent_minutes=0)
        self.txt_downloads_log.insert(tk.END, f"Downloads Path: {organizer.folder}\n")
        self.txt_downloads_log.insert(tk.END, f"Unorganized files found: {prev['total_files']} ({prev['total_size_mb']} MB)\n\n")

        if not prev["categories"]:
            self.txt_downloads_log.insert(tk.END, "✓ Downloads directory is clean! No loose unorganized files.\n")
            return

        for cat, items in prev["categories"].items():
            self.txt_downloads_log.insert(tk.END, f"[{cat}] ({len(items)} files):\n")
            for item in items[:8]:
                self.txt_downloads_log.insert(tk.END, f"  • {item['name']} ({item['size_mb']} MB)\n")
            if len(items) > 8:
                self.txt_downloads_log.insert(tk.END, f"  ... and {len(items) - 8} more files\n")
            self.txt_downloads_log.insert(tk.END, "\n")

    def _execute_downloads_organization(self):
        res = organizer.organize(dry_run=False, ignore_recent_minutes=0)
        self._preview_downloads()
        messagebox.showinfo("Organization Complete", f"Successfully categorized {res.get('moved_count', 0)} files into subfolders.")

    def _undo_downloads_organization(self):
        res = organizer.undo_last()
        self._preview_downloads()
        if res.get("success"):
            messagebox.showinfo("Rollback Complete", f"Restored {res.get('restored_count', 0)} files to original loose locations.")
        else:
            messagebox.showwarning("Rollback Notice", res.get("message", "No history to rollback."))

    # -------------------------------------------------------------------------
    # TAB 4: WINDOWS DEBLOAT & CHRIS TITUS TECH UTILITY
    # -------------------------------------------------------------------------

    def _build_debloat_tab(self):
        pane = tk.Frame(self.tab_debloat, bg=COLOR_BG)
        pane.pack(fill=tk.BOTH, expand=True, padx=12, pady=10)

        # Top Card: Chris Titus Tech (CTT) Windows Utility Script
        ctt_card = tk.Frame(pane, bg=COLOR_PANEL, bd=1, relief=tk.SOLID)
        ctt_card.pack(fill=tk.X, pady=(0, 12), ipady=8)

        ctt_top = tk.Frame(ctt_card, bg=COLOR_PANEL)
        ctt_top.pack(fill=tk.X, padx=12, pady=(2, 4))

        tk.Label(ctt_top, text="🔥 CHRIS TITUS TECH WINDOWS UTILITY (WINUTIL)", font=("Segoe UI", 11, "bold"), fg=COLOR_AMBER, bg=COLOR_PANEL).pack(side=tk.LEFT)

        btn_launch_ctt = tk.Button(
            ctt_top,
            text="🚀 Launch CTT Winutil (PowerShell)",
            font=("Segoe UI", 9, "bold"),
            bg="#1f6feb",
            fg="#ffffff",
            activebackground="#388bfd",
            command=self._launch_ctt_winutil,
            cursor="hand2",
            padx=12,
            pady=3,
        )
        btn_launch_ctt.pack(side=tk.RIGHT)

        tk.Label(
            ctt_card,
            text="The premier open-source Windows optimization suite by Chris Titus Tech.\nExecutes: 'irm https://christitus.com/win | iex' in an elevated PowerShell session to debloat, install apps, and tune Windows features.",
            font=("Segoe UI", 8),
            fg=COLOR_TEXT,
            bg=COLOR_PANEL,
            justify=tk.LEFT,
        ).pack(anchor=tk.W, padx=12, pady=(0, 4))

        # Safe Built-in Debloat Tweaks Card
        tweak_card = tk.Frame(pane, bg=COLOR_PANEL, bd=1, relief=tk.SOLID)
        tweak_card.pack(fill=tk.BOTH, expand=True, ipady=6)

        tw_header = tk.Frame(tweak_card, bg=COLOR_HEADER)
        tw_header.pack(fill=tk.X, ipady=6)

        tk.Label(tw_header, text="🛡️ SAFE BUILT-IN WINDOWS DEBLOATING & LOW RAM OPTIMIZATION", font=("Segoe UI", 10, "bold"), fg=COLOR_CYAN, bg=COLOR_HEADER).pack(side=tk.LEFT, padx=12)

        # Rollback All button
        btn_roll_all = tk.Button(
            tw_header,
            text="⏪ Rollback All Tweaks",
            font=("Segoe UI", 8, "bold"),
            bg="#30363d",
            fg=COLOR_RED,
            activebackground=COLOR_BORDER,
            command=self._rollback_all_debloat_tweaks,
            cursor="hand2",
            padx=8,
        )
        btn_roll_all.pack(side=tk.RIGHT, padx=12)

        btn_apply_all = tk.Button(
            tw_header,
            text="⚡ Apply Programmer Debloat",
            font=("Segoe UI", 8, "bold"),
            bg="#1f6feb",
            fg="#ffffff",
            command=self._apply_all_debloat_tweaks,
            cursor="hand2",
            padx=8,
        )
        btn_apply_all.pack(side=tk.RIGHT, padx=(0, 6))

        self.tweaks_list_frame = tk.Frame(tweak_card, bg=COLOR_PANEL)
        self.tweaks_list_frame.pack(fill=tk.BOTH, expand=True, padx=12, pady=10)

        self._refresh_tweaks_ui()

    def _refresh_tweaks_ui(self):
        for w in self.tweaks_list_frame.winfo_children():
            w.destroy()

        tweaks = debloat_manager.get_tweak_definitions()
        for key, info in tweaks.items():
            row = tk.Frame(self.tweaks_list_frame, bg="#0d1117", bd=1, relief=tk.SOLID)
            row.pack(fill=tk.X, pady=3, padx=2, ipady=4)

            is_app = info["is_applied"]
            badge_fg = COLOR_GREEN if is_app else COLOR_MUTED
            badge_text = "✓ APPLIED" if is_app else "READY"

            tk.Label(row, text=badge_text, font=("Segoe UI", 8, "bold"), fg=badge_fg, bg="#0d1117", width=10, anchor=tk.W).pack(side=tk.LEFT, padx=8)
            tk.Label(row, text=info["title"], font=("Segoe UI", 9, "bold"), fg=COLOR_TEXT, bg="#0d1117", width=32, anchor=tk.W).pack(side=tk.LEFT)
            tk.Label(row, text=info["impact"], font=("Segoe UI", 8), fg=COLOR_MUTED, bg="#0d1117").pack(side=tk.LEFT, padx=4)

            btn_box = tk.Frame(row, bg="#0d1117")
            btn_box.pack(side=tk.RIGHT, padx=8)

            if key == "clean_temp_caches":
                btn = tk.Button(
                    btn_box,
                    text="Purge Temp Now",
                    font=("Segoe UI", 8, "bold"),
                    bg="#30363d",
                    fg=COLOR_AMBER,
                    command=self._clean_temp_caches_action,
                    cursor="hand2",
                    padx=6,
                )
                btn.pack(side=tk.RIGHT)
            elif is_app:
                btn_rev = tk.Button(
                    btn_box,
                    text="Rollback",
                    font=("Segoe UI", 8),
                    bg=COLOR_HEADER,
                    fg=COLOR_RED,
                    command=lambda k=key: self._rollback_single_tweak(k),
                    cursor="hand2",
                    padx=6,
                )
                btn_rev.pack(side=tk.RIGHT)
            else:
                btn_app = tk.Button(
                    btn_box,
                    text="Apply",
                    font=("Segoe UI", 8, "bold"),
                    bg="#1f6feb",
                    fg="#ffffff",
                    command=lambda k=key: self._apply_single_tweak(k),
                    cursor="hand2",
                    padx=6,
                )
                btn_app.pack(side=tk.RIGHT)

    def _launch_ctt_winutil(self):
        if messagebox.askyesno(
            "Launch CTT Winutil",
            "This will launch the official Chris Titus Tech Windows Utility in an interactive PowerShell window.\n\nCommand: irm https://christitus.com/win | iex\n\nDo you wish to proceed?"
        ):
            res = debloat_manager.launch_ctt_winutil()
            messagebox.showinfo("Winutil Launched", res.get("message", "PowerShell opened."))

    def _apply_single_tweak(self, key: str):
        fn = getattr(debloat_manager, key, None)
        if fn:
            res = fn()
            self._refresh_tweaks_ui()
            messagebox.showinfo("Tweak Applied", res.get("message", "Completed."))

    def _rollback_single_tweak(self, key: str):
        fn = getattr(debloat_manager, f"rollback_{key}", None)
        if fn:
            res = fn()
            self._refresh_tweaks_ui()
            messagebox.showinfo("Rollback Complete", res.get("message", "Reverted to default."))

    def _clean_temp_caches_action(self):
        res = debloat_manager.clean_temp_caches()
        messagebox.showinfo("Clean Caches", res.get("message", "Cleaned."))

    def _apply_all_debloat_tweaks(self):
        res = debloat_manager.apply_programmer_mode_debloat()
        self._refresh_tweaks_ui()
        messagebox.showinfo("Debloat Complete", res.get("summary", "Applied."))

    def _rollback_all_debloat_tweaks(self):
        if messagebox.askyesno("Confirm Rollback", "Revert all debloat tweaks to standard Windows defaults?"):
            res = debloat_manager.rollback_all_tweaks()
            self._refresh_tweaks_ui()
            messagebox.showinfo("Rollback Complete", res.get("message", "Rolled back."))

    # -------------------------------------------------------------------------
    # TAB 5: PREFERENCES & SETTINGS
    # -------------------------------------------------------------------------

    def _build_settings_tab(self):
        pane = tk.Frame(self.tab_settings, bg=COLOR_BG)
        pane.pack(fill=tk.BOTH, expand=True, padx=20, pady=16)

        card = tk.Frame(pane, bg=COLOR_PANEL, bd=1, relief=tk.SOLID)
        card.pack(fill=tk.BOTH, expand=True, padx=0, pady=0, ipady=12)

        tk.Label(card, text="⚙️ SYSTEM CONFIGURATION & PREFERENCES", font=("Segoe UI", 12, "bold"), fg=COLOR_CYAN, bg=COLOR_PANEL).pack(anchor=tk.W, padx=20, pady=(12, 16))

        # Profession
        tk.Label(card, text="User Profession:", font=("Segoe UI", 10, "bold"), fg=COLOR_TEXT, bg=COLOR_PANEL).pack(anchor=tk.W, padx=20, pady=(4, 2))
        self.set_prof = tk.StringVar(value=preferences.get("profession", "Software Engineer"))
        cb_prof = ttk.Combobox(card, textvariable=self.set_prof, values=["Software Engineer", "Designer", "Student", "Gamer", "General"], state="readonly", width=30)
        cb_prof.pack(anchor=tk.W, padx=20, pady=(0, 12))

        # Mode
        tk.Label(card, text="Active Mode:", font=("Segoe UI", 10, "bold"), fg=COLOR_TEXT, bg=COLOR_PANEL).pack(anchor=tk.W, padx=20, pady=(4, 2))
        self.set_mode = tk.StringVar(value=preferences.active_mode)
        cb_mode = ttk.Combobox(card, textvariable=self.set_mode, values=["programmer", "balanced", "performance"], state="readonly", width=30)
        cb_mode.pack(anchor=tk.W, padx=20, pady=(0, 12))

        # Downloads Clutter Threshold
        tk.Label(card, text="Downloads Clutter Threshold (files):", font=("Segoe UI", 10, "bold"), fg=COLOR_TEXT, bg=COLOR_PANEL).pack(anchor=tk.W, padx=20, pady=(4, 2))
        self.set_thresh = tk.IntVar(value=preferences.get("downloads_clutter_threshold", 15))
        sp_thresh = tk.Spinbox(card, from_=5, to=100, textvariable=self.set_thresh, width=10, bg="#0d1117", fg=COLOR_TEXT)
        sp_thresh.pack(anchor=tk.W, padx=20, pady=(0, 12))

        # Checkboxes
        self.set_bg = tk.BooleanVar(value=preferences.get("close_to_background", True))
        tk.Checkbutton(
            card,
            text="Minimize to background when window is closed",
            variable=self.set_bg,
            font=("Segoe UI", 10),
            fg=COLOR_TEXT,
            bg=COLOR_PANEL,
            selectcolor="#0d1117",
            activebackground=COLOR_PANEL,
            activeforeground=COLOR_CYAN,
        ).pack(anchor=tk.W, padx=20, pady=4)

        # Buttons
        b_box = tk.Frame(card, bg=COLOR_PANEL)
        b_box.pack(anchor=tk.W, padx=20, pady=(20, 0))

        btn_save = tk.Button(
            b_box,
            text="💾 Save Preferences",
            font=("Segoe UI", 10, "bold"),
            bg="#1f6feb",
            fg="#ffffff",
            command=self._save_settings_tab,
            cursor="hand2",
            padx=14,
            pady=4,
        )
        btn_save.pack(side=tk.LEFT, padx=(0, 10))

        btn_rerun = tk.Button(
            b_box,
            text="🔄 Relaunch Initial Setup Wizard",
            font=("Segoe UI", 10),
            bg=COLOR_HEADER,
            fg=COLOR_MUTED,
            command=self.show_onboarding_wizard,
            cursor="hand2",
            padx=14,
            pady=4,
        )
        btn_rerun.pack(side=tk.LEFT)

    def _save_settings_tab(self):
        preferences.update(
            profession=self.set_prof.get(),
            active_mode=self.set_mode.get(),
            downloads_clutter_threshold=self.set_thresh.get(),
            close_to_background=self.set_bg.get(),
        )
        modes_manager.set_mode(self.set_mode.get(), apply_optimizations=True)
        self.lbl_mode_badge.config(text=f"[{self.set_mode.get().upper()} MODE]")
        messagebox.showinfo("Saved", "Preferences successfully updated.")

    # -------------------------------------------------------------------------
    # TAB 6: SUPPORT & CONTRIBUTE
    # -------------------------------------------------------------------------

    def _build_support_tab(self):
        pane = tk.Frame(self.tab_support, bg=COLOR_BG)
        pane.pack(fill=tk.BOTH, expand=True, padx=16, pady=12)

        # YouTube Section
        yt_card = tk.Frame(pane, bg=COLOR_PANEL, bd=1, relief=tk.SOLID)
        yt_card.pack(fill=tk.X, pady=(0, 12), ipady=8)

        tk.Label(yt_card, text="📺 YOUTUBE CHANNEL: @cyan_code", font=("Segoe UI", 11, "bold"), fg="#ff4444", bg=COLOR_PANEL).pack(anchor=tk.W, padx=16, pady=(4, 2))
        tk.Label(
            yt_card,
            text="Follow Cyan Code on YouTube for development updates, AI tutorials, devlogs, and showcase demonstrations of REN-AI.",
            font=("Segoe UI", 9),
            fg=COLOR_TEXT,
            bg=COLOR_PANEL,
        ).pack(anchor=tk.W, padx=16, pady=(0, 8))

        btn_yt = tk.Button(
            yt_card,
            text="🔴 Open @cyan_code on YouTube",
            font=("Segoe UI", 9, "bold"),
            bg="#cc0000",
            fg="#ffffff",
            activebackground="#ff0000",
            activeforeground="#ffffff",
            command=lambda: webbrowser.open("https://www.youtube.com/@cyan_code"),
            cursor="hand2",
            padx=14,
            pady=4,
        )
        btn_yt.pack(anchor=tk.W, padx=16, pady=(0, 4))

        # GitHub Section
        gh_card = tk.Frame(pane, bg=COLOR_PANEL, bd=1, relief=tk.SOLID)
        gh_card.pack(fill=tk.X, pady=(0, 12), ipady=8)

        tk.Label(gh_card, text="⭐ GITHUB SUPPORT & CONTRIBUTE: takumicodes/REN-AI", font=("Segoe UI", 11, "bold"), fg=COLOR_CYAN, bg=COLOR_PANEL).pack(anchor=tk.W, padx=16, pady=(4, 2))
        tk.Label(
            gh_card,
            text="REN-AI is an open-source cognitive desktop assistant. Help build the future of local, human-driven AI by starring the repo, reporting bugs, or contributing code skills.",
            font=("Segoe UI", 9),
            fg=COLOR_TEXT,
            bg=COLOR_PANEL,
        ).pack(anchor=tk.W, padx=16, pady=(0, 8))

        gh_btn_box = tk.Frame(gh_card, bg=COLOR_PANEL)
        gh_btn_box.pack(anchor=tk.W, padx=16, pady=(0, 4))

        btn_gh = tk.Button(
            gh_btn_box,
            text="⭐ Star on GitHub",
            font=("Segoe UI", 9, "bold"),
            bg="#238636",
            fg="#ffffff",
            activebackground="#2ea043",
            command=lambda: webbrowser.open("https://github.com/takumicodes/REN-AI"),
            cursor="hand2",
            padx=12,
            pady=4,
        )
        btn_gh.pack(side=tk.LEFT, padx=(0, 8))

        btn_issues = tk.Button(
            gh_btn_box,
            text="🐛 Report an Issue",
            font=("Segoe UI", 9),
            bg=COLOR_HEADER,
            fg=COLOR_TEXT,
            command=lambda: webbrowser.open("https://github.com/takumicodes/REN-AI/issues"),
            cursor="hand2",
            padx=10,
            pady=4,
        )
        btn_issues.pack(side=tk.LEFT, padx=(0, 8))

        btn_pr = tk.Button(
            gh_btn_box,
            text="🤝 Submit Pull Request",
            font=("Segoe UI", 9),
            bg=COLOR_HEADER,
            fg=COLOR_TEXT,
            command=lambda: webbrowser.open("https://github.com/takumicodes/REN-AI/pulls"),
            cursor="hand2",
            padx=10,
            pady=4,
        )
        btn_pr.pack(side=tk.LEFT)

        # Vision Card
        vis_card = tk.Frame(pane, bg=COLOR_PANEL, bd=1, relief=tk.SOLID)
        vis_card.pack(fill=tk.BOTH, expand=True, ipady=6)

        tk.Label(vis_card, text="🧭 THE REN PHILOSOPHY", font=("Segoe UI", 10, "bold"), fg=COLOR_PURPLE, bg=COLOR_PANEL).pack(anchor=tk.W, padx=16, pady=(4, 2))
        philosophy_text = (
            "• 100% Human-Driven: REN never mutates your system without explicit confirmation.\n"
            "• Zero AI Slop: No unprompted chatbot babble, hallucinations, or disruptive popups.\n"
            "• Developer-First: Built to give programmers maximum RAM headroom and compile speed.\n"
            "• Safe & Reversible: Every action includes full preview and 1-click rollback history."
        )
        tk.Label(vis_card, text=philosophy_text, font=("Segoe UI", 9), fg=COLOR_TEXT, bg=COLOR_PANEL, justify=tk.LEFT).pack(anchor=tk.W, padx=16, pady=4)

    # =========================================================================
    # REFRESH LOOP & BACKGROUND TRAY HANDLING
    # =========================================================================

    def _refresh_gui_loop(self):
        """Updates hardware metrics dynamically every 2 seconds."""
        try:
            snapshot = get_system_snapshot()
            cpu = snapshot["cpu_percent"]
            ram = snapshot["ram"]
            disk = snapshot["primary_disk_percent"]
            bat = snapshot["battery"]
            plan = snapshot["power_profile"]

            # Header mini status
            bat_str = f"{bat['percent']}% {'(AC)' if bat['is_plugged'] else '(Discharging)'}" if bat["has_battery"] else "AC Wall Power"
            self.lbl_header_metrics.config(text=f"CPU: {cpu}% | RAM: {ram['percent_used']}% | Disk: {disk}% | Power: {plan}")

            # Dashboard widgets
            if hasattr(self, "lbl_cpu"):
                self.lbl_cpu.config(text=f"CPU Utilization: {cpu}%")
                self.bar_cpu["value"] = min(100, max(0, cpu))

                self.lbl_ram.config(text=f"RAM: {ram['percent_used']}% ({ram['used_gb']} GB used / {ram['total_gb']} GB total)")
                self.bar_ram["value"] = min(100, max(0, ram["percent_used"]))

                self.lbl_disk.config(text=f"Primary Storage: {disk}% used")
                self.bar_disk["value"] = min(100, max(0, disk))

                self.lbl_bat.config(text=f"Battery: {bat_str}")
                self.lbl_plan.config(text=f"Power Scheme: {plan} | Context: {snapshot['context']['category'].upper()}")
        except Exception:
            pass

        # Schedule next update
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
        # Show Windows balloon / prompt if desired, or restore controller
        try:
            self._ensure_restore_controller()
        except Exception:
            pass

    def _ensure_restore_controller(self):
        """Creates a small top-level controller or notification so the user can easily restore."""
        if hasattr(self, "tray_top") and self.tray_top.winfo_exists():
            return

        self.tray_top = tk.Toplevel(self.root)
        self.tray_top.title("REN Running in BG")
        self.tray_top.geometry("300x110+50+50")
        self.tray_top.configure(bg=COLOR_PANEL)
        self.tray_top.resizable(False, False)
        self.tray_top.attributes("-topmost", True)

        tk.Label(
            self.tray_top,
            text="🪐 REN is observing in background",
            font=("Segoe UI", 9, "bold"),
            fg=COLOR_CYAN,
            bg=COLOR_PANEL,
        ).pack(pady=(10, 4))

        tk.Label(
            self.tray_top,
            text="Silent background observation active.",
            font=("Segoe UI", 8),
            fg=COLOR_MUTED,
            bg=COLOR_PANEL,
        ).pack()

        btn_row = tk.Frame(self.tray_top, bg=COLOR_PANEL)
        btn_row.pack(pady=8)

        btn_restore = tk.Button(
            btn_row,
            text="Open GUI",
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
        if messagebox.askyesno("Exit REN", "Are you sure you want to completely stop REN Desktop Assistant and exit?"):
            observer.stop()
            self.root.destroy()
            sys.exit(0)


def launch_gui():
    """Main function to start REN Desktop Assistant GUI."""
    root = tk.Tk()
    app = RenDesktopApp(root)
    root.mainloop()


if __name__ == "__main__":
    launch_gui()
