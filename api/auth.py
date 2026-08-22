"""
REN-AI Authentication and Access Control Module
Provides token verification, passkey generation, rate limiting, and FastAPI security dependencies.
"""

import os
import secrets
import time
from typing import Optional, Dict
from fastapi import Request, HTTPException, Security, Depends
from fastapi.security import HTTPBearer, HTTPAuthorizationCredentials

security = HTTPBearer(auto_error=False)

from pathlib import Path

# Failed attempt tracker for brute-force prevention: ip -> list of timestamps
_failed_attempts: Dict[str, list] = {}
MAX_FAILED_ATTEMPTS = 5
LOCKOUT_WINDOW_SECONDS = 60


def load_dotenv_if_present():
    """Lightweight .env loader without third-party dependencies."""
    env_file = Path(__file__).resolve().parent.parent / ".env"
    if env_file.exists():
        try:
            with open(env_file, "r", encoding="utf-8") as f:
                for line in f:
                    line = line.strip()
                    if line and not line.startswith("#") and "=" in line:
                        k, v = line.split("=", 1)
                        k = k.strip()
                        v = v.strip().strip("'\"")
                        if k and k not in os.environ:
                            os.environ[k] = v
        except Exception:
            pass


def get_configured_access_key() -> Optional[str]:
    """Retrieves access key from environment (REN_AUTH_TOKEN or REN_ACCESS_KEY) or None if auth is disabled."""
    load_dotenv_if_present()
    key = os.getenv("REN_AUTH_TOKEN", "").strip() or os.getenv("REN_ACCESS_KEY", "").strip()
    return key if key else None


def set_configured_access_key(key: str):
    """Sets or updates the active access key."""
    os.environ["REN_AUTH_TOKEN"] = key.strip()
    os.environ["REN_ACCESS_KEY"] = key.strip()


def generate_passkey(length: int = 6) -> str:
    """Generates a secure numeric or alphanumeric passkey."""
    return "".join(secrets.choice("23456789ABCDEFGHJKLMNPQRSTUVWXYZ") for _ in range(length))


def is_auth_enabled() -> bool:
    """Checks if access control is currently enabled."""
    return get_configured_access_key() is not None


def is_rate_limited(ip: str) -> bool:
    """Checks if the given IP address has exceeded failed attempt threshold."""
    now = time.time()
    attempts = _failed_attempts.get(ip, [])
    # Filter attempts within the window
    recent = [t for t in attempts if now - t < LOCKOUT_WINDOW_SECONDS]
    _failed_attempts[ip] = recent
    return len(recent) >= MAX_FAILED_ATTEMPTS


def record_failed_attempt(ip: str):
    """Records a failed authentication attempt for rate limiting."""
    now = time.time()
    if ip not in _failed_attempts:
        _failed_attempts[ip] = []
    _failed_attempts[ip].append(now)


def clear_failed_attempts(ip: str):
    """Clears failed attempts on successful login."""
    _failed_attempts.pop(ip, None)


def verify_token(provided_token: Optional[str], ip: str = "unknown") -> bool:
    """Verifies provided token against configured access key."""
    configured_key = get_configured_access_key()
    if not configured_key:
        return True  # Auth is disabled

    if is_rate_limited(ip):
        raise HTTPException(
            status_code=429,
            detail=f"Too many failed login attempts. Please wait {LOCKOUT_WINDOW_SECONDS} seconds."
        )

    if not provided_token:
        record_failed_attempt(ip)
        return False

    # Constant time comparison to prevent timing attacks
    if secrets.compare_digest(provided_token.strip(), configured_key):
        clear_failed_attempts(ip)
        return True

    record_failed_attempt(ip)
    return False


async def require_auth(
    request: Request,
    credentials: Optional[HTTPAuthorizationCredentials] = Security(security)
) -> bool:
    """FastAPI dependency enforcing authentication on protected endpoints."""
    configured_key = get_configured_access_key()
    if not configured_key:
        return True  # Auth is disabled

    client_ip = request.client.host if request.client else "unknown"

    # 1. Check Bearer token from header
    token = None
    if credentials and credentials.credentials:
        token = credentials.credentials

    # 2. Check query parameter ?token= or ?key= (useful for SSE EventSource / media streams)
    if not token:
        token = request.query_params.get("token") or request.query_params.get("key")

    # 3. Check custom X-Access-Key header
    if not token:
        token = request.headers.get("X-Access-Key")

    if not verify_token(token, ip=client_ip):
        raise HTTPException(
            status_code=401,
            detail="Authentication required. Invalid or missing access passkey.",
            headers={"WWW-Authenticate": "Bearer"},
        )

    return True
