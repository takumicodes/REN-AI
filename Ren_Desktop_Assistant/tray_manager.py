"""
Real Windows System Tray (Notification Area) Manager for REN-AI Windows Control Center
Features:
- Genuine Windows notification area tray icon using pystray and Pillow.
- Left-click (or double-click): Restores and focuses the main REN window.
- Right-click context menu:
    - Open REN (default item)
    - Pause Monitoring
    - Resume Monitoring
    - Settings (opens settings panel directly)
    - Exit REN (completely terminates application and observer daemon)
- Dynamic Tooltip displaying active mode and hardware metrics.
- 100% thread-safe: marshals all Tkinter window operations onto the main thread via root.after().
"""

import sys
import threading
from pathlib import Path
from typing import Optional, Callable

try:
    from PIL import Image
    import pystray
    from pystray import MenuItem as item, Menu
except ImportError:
    pystray = None
    Image = None

try:
    from .logger import logger
except ImportError:
    from logger import logger


class TrayManager:
    """Manages the Windows system tray icon, context menu, and background lifecycle."""

    def __init__(
        self,
        on_open_callback: Callable[[], None],
        on_pause_callback: Callable[[], None],
        on_resume_callback: Callable[[], None],
        on_settings_callback: Callable[[], None],
        on_exit_callback: Callable[[], None],
    ):
        self.on_open = on_open_callback
        self.on_pause = on_pause_callback
        self.on_resume = on_resume_callback
        self.on_settings = on_settings_callback
        self.on_exit = on_exit_callback

        self._icon: Optional[pystray.Icon] = None
        self._tray_thread: Optional[threading.Thread] = None
        self._is_monitoring_paused = False

    def _get_icon_image(self) -> Optional[Image.Image]:
        """Loads ren_logo.png or ren_logo.ico, with dynamic fallback."""
        if Image is None:
            return None

        base_path = Path(sys._MEIPASS) if getattr(sys, "frozen", False) else Path(__file__).parent
        for icon_name in ("ren_logo.png", "ren_logo.ico"):
            p = base_path / icon_name
            if p.exists():
                try:
                    img = Image.open(str(p))
                    return img
                except Exception as e:
                    logger.warning(f"Could not load icon {p}: {e}")

        # Fallback: create a crisp 64x64 cyan square if no image file is found
        try:
            img = Image.new("RGBA", (64, 64), color=(0, 229, 255, 255))
            return img
        except Exception:
            return None

    def start(self):
        """Starts the system tray icon in a dedicated background thread."""
        if pystray is None:
            logger.warning("pystray is not installed. System tray icon disabled.")
            return

        icon_image = self._get_icon_image()
        if icon_image is None:
            logger.warning("Could not generate or load tray icon image.")
            return

        def _handle_open(icon, item):
            self.on_open()

        def _handle_pause(icon, item):
            self._is_monitoring_paused = True
            self.on_pause()
            self._update_menu()

        def _handle_resume(icon, item):
            self._is_monitoring_paused = False
            self.on_resume()
            self._update_menu()

        def _handle_settings(icon, item):
            self.on_settings()

        def _handle_exit(icon, item):
            self.stop()
            self.on_exit()

        menu = Menu(
            item("Open REN", _handle_open, default=True),
            Menu.SEPARATOR,
            item("Pause Monitoring", _handle_pause, checked=lambda item: self._is_monitoring_paused),
            item("Resume Monitoring", _handle_resume, checked=lambda item: not self._is_monitoring_paused),
            Menu.SEPARATOR,
            item("Settings", _handle_settings),
            Menu.SEPARATOR,
            item("Exit REN", _handle_exit),
        )

        self._icon = pystray.Icon(
            name="RenControlCenter",
            icon=icon_image,
            title="REN-AI Windows Control Center\nObserving in background",
            menu=menu,
        )

        def _run():
            try:
                logger.info("Starting pystray system tray loop.")
                self._icon.run()
            except Exception as e:
                logger.warning(f"Error in system tray run loop: {e}")

        self._tray_thread = threading.Thread(target=_run, daemon=True, name="RenSystemTrayThread")
        self._tray_thread.start()

    def _update_menu(self):
        """Updates context menu state."""
        if self._icon and hasattr(self._icon, "update_menu"):
            try:
                self._icon.update_menu()
            except Exception:
                pass

    def update_tooltip(self, text: str):
        """Updates the tooltip shown when hovering over the notification area icon."""
        if self._icon:
            try:
                # Windows tooltips are limited to 127 characters
                self._icon.title = text[:127]
            except Exception:
                pass

    def stop(self):
        """Stops and removes the system tray icon."""
        if self._icon:
            try:
                self._icon.stop()
                logger.info("System tray icon stopped.")
            except Exception as e:
                logger.warning(f"Error stopping tray icon: {e}")
            self._icon = None
