"""
REN-AI Public Tunnel Manager
Manages global secure HTTPS tunnels (Cloudflare Quick Tunnel, ngrok) and terminal QR code display.
Allows anyone from anywhere in the world to access REN-AI on their mobile phone without port forwarding.
"""

import os
import sys
import re
import time
import shutil
import platform
import subprocess
import urllib.request
from pathlib import Path
from typing import Optional, Tuple

import qrcode
from ren.monitoring.logger import agent_logger, error_logger

ROOT_DIR = Path(__file__).resolve().parent.parent
TOOLS_DIR = ROOT_DIR / "data" / "tools"


def get_cloudflared_executable() -> Optional[Path]:
    """Finds or downloads the standalone cloudflared binary."""
    TOOLS_DIR.mkdir(parents=True, exist_ok=True)
    exe_name = "cloudflared.exe" if sys.platform == "win32" else "cloudflared"
    local_binary = TOOLS_DIR / exe_name

    # 1. Check if already present in data/tools/
    if local_binary.exists() and os.access(local_binary, os.X_OK if sys.platform != "win32" else os.F_OK):
        return local_binary

    # 2. Check if installed in system PATH
    system_cf = shutil.which("cloudflared")
    if system_cf:
        return Path(system_cf)

    # 3. Auto-download official standalone binary from Cloudflare releases
    print("Cloudflare tunnel binary not found. Downloading official cloudflared binary...")
    arch = platform.machine().lower()
    system = sys.platform

    if system == "win32":
        url = "https://github.com/cloudflare/cloudflared/releases/latest/download/cloudflared-windows-amd64.exe"
    elif system == "darwin":
        url = "https://github.com/cloudflare/cloudflared/releases/latest/download/cloudflared-darwin-amd64"
    else:  # linux
        if "arm" in arch or "aarch" in arch:
            url = "https://github.com/cloudflare/cloudflared/releases/latest/download/cloudflared-linux-arm64"
        else:
            url = "https://github.com/cloudflare/cloudflared/releases/latest/download/cloudflared-linux-amd64"

    try:
        urllib.request.urlretrieve(url, str(local_binary))
        if sys.platform != "win32":
            os.chmod(local_binary, 0o755)
        print(f"cloudflared downloaded successfully to {local_binary}")
        return local_binary
    except Exception as e:
        error_logger.error(f"Failed downloading cloudflared binary: {e}")
        return None


class TunnelManager:
    """Orchestrates secure public HTTPS tunnels."""

    def __init__(self, port: int = 8000, provider: str = "cloudflare"):
        self.port = port
        self.provider = provider.lower()
        self.process: Optional[subprocess.Popen] = None
        self.public_url: Optional[str] = None

    def start(self, timeout: int = 25) -> Optional[str]:
        """Starts the public tunnel and returns the public HTTPS URL."""
        if self.provider == "ngrok":
            return self._start_ngrok()
        return self._start_cloudflare(timeout=timeout)

    def _start_cloudflare(self, timeout: int = 25) -> Optional[str]:
        """Launches Cloudflare Quick Tunnel (Free, zero-config HTTPS)."""
        cf_bin = get_cloudflared_executable()
        if not cf_bin or not cf_bin.exists():
            print("Error: Could not obtain cloudflared binary.")
            return None

        cmd = [
            str(cf_bin),
            "tunnel",
            "--url",
            f"http://127.0.0.1:{self.port}",
            "--no-autoupdate",
        ]

        print("Opening secure Cloudflare HTTPS tunnel...")
        try:
            self.process = subprocess.Popen(
                cmd,
                stdout=subprocess.PIPE,
                stderr=subprocess.STDOUT,
                text=True,
                bufsize=1,
                encoding="utf-8",
                errors="replace",
            )

            start_t = time.time()
            url_pattern = re.compile(r"https://[a-zA-Z0-9-]+\.trycloudflare\.com")

            while time.time() - start_t < timeout:
                line = self.process.stdout.readline()
                if not line:
                    if self.process.poll() is not None:
                        break
                    time.sleep(0.1)
                    continue

                match = url_pattern.search(line)
                if match:
                    self.public_url = match.group(0)
                    agent_logger.info(f"Cloudflare tunnel established: {self.public_url}")
                    return self.public_url

            if not self.public_url:
                print("Cloudflare tunnel timed out while waiting for URL.")
        except Exception as e:
            error_logger.error(f"Error starting Cloudflare tunnel: {e}")

        return None

    def _start_ngrok(self) -> Optional[str]:
        """Launches ngrok tunnel via pyngrok."""
        try:
            from pyngrok import ngrok
            auth_token = os.getenv("NGROK_AUTHTOKEN")
            if auth_token:
                ngrok.set_auth_token(auth_token)

            tunnel = ngrok.connect(self.port, "http")
            self.public_url = tunnel.public_url
            if self.public_url.startswith("http://"):
                self.public_url = self.public_url.replace("http://", "https://")
            agent_logger.info(f"ngrok tunnel established: {self.public_url}")
            return self.public_url
        except Exception as e:
            error_logger.error(f"Error starting ngrok tunnel: {e}")
            return None

    def stop(self):
        """Terminates active tunnel process."""
        if self.process:
            try:
                self.process.terminate()
                self.process.wait(timeout=3)
            except Exception:
                try:
                    self.process.kill()
                except Exception:
                    pass
            self.process = None

        if self.provider == "ngrok":
            try:
                from pyngrok import ngrok
                ngrok.kill()
            except Exception:
                pass


def print_qr_code(url: str):
    """Renders a high-contrast ASCII QR code directly in the terminal."""
    try:
        qr = qrcode.QRCode(
            version=1,
            error_correction=qrcode.constants.ERROR_CORRECT_L,
            box_size=1,
            border=1,
        )
        qr.add_data(url)
        qr.make(fit=True)
        print("\nScan this QR code with your phone camera to open REN:")
        qr.print_ascii(invert=True)
    except Exception as e:
        agent_logger.debug(f"QR code render skipped: {e}")
