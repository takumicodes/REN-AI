"""
Single Instance & Inter-Process Wakeup Manager for REN-AI Windows Control Center
Features:
- Windows Named Mutex ensures only one instance of REN runs at any time.
- Local loopback IPC (127.0.0.1) allows a newly launched 2nd instance to wake up
  and restore the existing instance even when it is minimized or hidden in the system tray.
- Zero external dependencies.
"""

import sys
import socket
import threading
from typing import Optional, Callable

try:
    from .logger import logger
except ImportError:
    from logger import logger

SINGLE_INSTANCE_PORT = 52418
MUTEX_NAME = "RenControlCenterSingleInstanceMutex"


class SingleInstanceManager:
    """Manages single-instance enforcement and inter-instance wakeups."""

    def __init__(self, on_wake_callback: Optional[Callable[[], None]] = None):
        self.on_wake_callback = on_wake_callback
        self._mutex = None
        self._server_sock: Optional[socket.socket] = None
        self._listener_thread: Optional[threading.Thread] = None
        self._running = False

    def acquire(self) -> bool:
        """
        Attempts to acquire single instance ownership.
        If another instance is already running, notifies it to restore and returns False.
        If this is the primary instance, starts IPC listener and returns True.
        """
        # Step 1: Check if another instance is already listening on the loopback port
        client_sock = socket.socket(socket.AF_INET, socket.SOCK_STREAM)
        try:
            client_sock.settimeout(1.5)
            client_sock.connect(("127.0.0.1", SINGLE_INSTANCE_PORT))
            client_sock.sendall(b"REN_RESTORE_WINDOW\n")
            logger.info("Notified existing REN Control Center instance to wake up.")
            return False  # Existing instance signaled; this instance should exit
        except (socket.error, ConnectionRefusedError, TimeoutError, OSError):
            pass  # No running instance responded
        finally:
            try:
                client_sock.close()
            except Exception:
                pass

        # Step 2: On Windows, acquire named mutex for OS-level protection
        if sys.platform == "win32":
            try:
                import ctypes
                ERROR_ALREADY_EXISTS = 183
                self._mutex = ctypes.windll.kernel32.CreateMutexW(None, False, MUTEX_NAME)
                last_err = ctypes.windll.kernel32.GetLastError()
                if last_err == ERROR_ALREADY_EXISTS:
                    logger.info("Windows Mutex already held by another process.")
                    # Try to find and bring existing window to front via Windows API
                    for title in ("🪐 REN-AI Windows Control Center", "🪐 REN-AI Desktop Assistant"):
                        hwnd = ctypes.windll.user32.FindWindowW(None, title)
                        if hwnd:
                            ctypes.windll.user32.ShowWindow(hwnd, 9)  # SW_RESTORE
                            ctypes.windll.user32.SetForegroundWindow(hwnd)
                            break
                    return False
            except Exception as e:
                logger.warning(f"Failed to acquire Windows named mutex: {e}")

        # Step 3: We are the primary instance. Start the background wakeup listener
        self._start_ipc_server()
        return True

    def _start_ipc_server(self):
        """Starts a lightweight localhost socket server to listen for wakeup signals from duplicate launches."""
        try:
            self._server_sock = socket.socket(socket.AF_INET, socket.SOCK_STREAM)
            self._server_sock.setsockopt(socket.SOL_SOCKET, socket.SO_REUSEADDR, 1)
            self._server_sock.bind(("127.0.0.1", SINGLE_INSTANCE_PORT))
            self._server_sock.listen(2)
            self._running = True

            self._listener_thread = threading.Thread(target=self._listen_loop, daemon=True, name="RenIPCListener")
            self._listener_thread.start()
            logger.info("Single-instance IPC server started on port %d", SINGLE_INSTANCE_PORT)
        except Exception as e:
            logger.warning(f"Could not bind single-instance IPC socket on port {SINGLE_INSTANCE_PORT}: {e}")

    def _listen_loop(self):
        """Background loop waiting for wakeup signals from 2nd instances."""
        while self._running and self._server_sock:
            try:
                conn, _ = self._server_sock.accept()
                data = conn.recv(1024)
                conn.close()
                if b"REN_RESTORE_WINDOW" in data:
                    logger.info("Received wake signal from 2nd instance. Triggering restore callback.")
                    if self.on_wake_callback:
                        self.on_wake_callback()
            except Exception:
                if not self._running:
                    break

    def release(self):
        """Releases the mutex and closes the IPC socket on application exit."""
        self._running = False
        if self._server_sock:
            try:
                self._server_sock.close()
            except Exception:
                pass
            self._server_sock = None

        if self._mutex and sys.platform == "win32":
            try:
                import ctypes
                ctypes.windll.kernel32.CloseHandle(self._mutex)
            except Exception:
                pass
            self._mutex = None
        logger.info("Single instance manager released.")
