"""
REN-AI Server Entry Point
Launches the FastAPI backend and Mobile Web Client interface.
Supports local LAN Wi-Fi access as well as global public HTTPS tunneling from any country / network.

Usage:
    # 1. Local Network Access (Same Wi-Fi)
    python server.py

    # 2. Global Public Access (Any phone network/country, Zero-Config HTTPS)
    python server.py --public

    # 3. Global Access with Custom Passkey
    python server.py --public --key MySecretKey123
"""

import sys
import os
import time
import argparse
import threading
from pathlib import Path

# Ensure UTF-8 console output on Windows
if sys.platform == "win32":
    try:
        sys.stdout.reconfigure(encoding="utf-8")
        sys.stderr.reconfigure(encoding="utf-8")
    except Exception:
        pass

# Add project root to sys.path
ROOT_DIR = Path(__file__).resolve().parent
if str(ROOT_DIR) not in sys.path:
    sys.path.insert(0, str(ROOT_DIR))

import uvicorn
from api.server import get_local_ip
from api.auth import set_configured_access_key, generate_passkey, get_configured_access_key
from api.tunnel import TunnelManager, print_qr_code


def main():
    parser = argparse.ArgumentParser(description="REN-AI Mobile Web Client & API Server")
    parser.add_argument("--host", type=str, default=os.getenv("REN_SERVER_HOST", "0.0.0.0"), help="Host IP to bind (default: 0.0.0.0)")
    parser.add_argument("--port", type=int, default=int(os.getenv("REN_SERVER_PORT", "8000")), help="Port number (default: 8000)")
    parser.add_argument("--public", "--tunnel", action="store_true", dest="public", help="Expose REN globally over secure public HTTPS tunnel for remote access from any country/network")
    parser.add_argument("--tunnel-provider", type=str, default=os.getenv("REN_TUNNEL_PROVIDER", "cloudflare"), choices=["cloudflare", "ngrok"], help="Tunnel provider (default: cloudflare)")
    parser.add_argument("--key", "--passkey", type=str, default=os.getenv("REN_ACCESS_KEY", ""), help="Security access passkey for remote clients")
    parser.add_argument("--no-qr", action="store_true", help="Disable printing terminal QR code")
    parser.add_argument("--reload", action="store_true", help="Enable auto-reloading for development")
    args = parser.parse_args()

    local_ip = get_local_ip()
    os.environ["REN_SERVER_HOST"] = args.host
    os.environ["REN_SERVER_PORT"] = str(args.port)

    # Configure Access Key Authentication
    passkey = args.key.strip()
    if args.public and not passkey:
        # Automatically generate a secure 6-character passkey for public remote mode
        passkey = generate_passkey(6)

    if passkey:
        set_configured_access_key(passkey)

    tunnel_mgr = None
    public_url = None

    if args.public:
        tunnel_mgr = TunnelManager(port=args.port, provider=args.tunnel_provider)
        print("\n[+] Initializing Global Public HTTPS Tunnel...")
        public_url = tunnel_mgr.start(timeout=25)

    print("\n" + "=" * 62)
    print(" 🪐 REN-AI SERVER & MOBILE CLIENT READY")
    print("=" * 62)
    print(f"  • Local Desktop    : http://localhost:{args.port}")
    print(f"  • Same Wi-Fi Access: http://{local_ip}:{args.port}")

    if public_url:
        phone_url_with_token = f"{public_url}?token={passkey}" if passkey else public_url
        print("=" * 62)
        print(" 🌍 GLOBAL REMOTE PHONE ACCESS (ANY NETWORK / COUNTRY):")
        print(f"  • Public HTTPS URL : {public_url}")
        if passkey:
            print(f"  • Security Passkey : {passkey}")
            print(f"  • Auto-Login URL   : {phone_url_with_token}")
        print("=" * 62)

        if not args.no_qr:
            print_qr_code(phone_url_with_token)
    elif passkey:
        print(f"  • Security Passkey : {passkey}")
        print("=" * 62)

    try:
        uvicorn.run(
            "api.server:app",
            host=args.host,
            port=args.port,
            reload=args.reload,
            log_level="info",
        )
    finally:
        if tunnel_mgr:
            print("\nShutting down public tunnel...")
            tunnel_mgr.stop()


if __name__ == "__main__":
    main()
