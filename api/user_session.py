"""
REN User Session & Identity Resolution
Provides secure anonymous user session identity tracking per browser instance.
Ensures every browser/client maintains its own isolated conversations, active state, and memory.
"""

import uuid
import secrets
from typing import Optional
from fastapi import Request, Response


def generate_user_id() -> str:
    """Generates a secure, random user session identifier."""
    return f"usr_{secrets.token_hex(8)}"


def get_current_user_id(request: Request, response: Response) -> str:
    """
    FastAPI dependency resolving the caller's unique user identity.
    Checks cookie, custom header, and query param, or assigns a new unique ID.
    """
    user_id = None

    # 1. Check custom header (sent by modern mobile web client / fetch)
    header_val = request.headers.get("X-User-Session-ID") or request.headers.get("X-User-ID")
    if header_val and header_val.strip():
        user_id = header_val.strip()

    # 2. Check Cookie
    if not user_id:
        cookie_val = request.cookies.get("ren_user_id")
        if cookie_val and cookie_val.strip():
            user_id = cookie_val.strip()

    # 3. Check Query parameter
    if not user_id:
        param_val = request.query_params.get("user_id")
        if param_val and param_val.strip():
            user_id = param_val.strip()

    # 4. Generate new if not present
    if not user_id:
        user_id = generate_user_id()

    # Set cookie and header on response to persist across page reloads
    response.set_cookie(
        key="ren_user_id",
        value=user_id,
        max_age=365 * 24 * 3600,  # 1 year persistence
        httponly=False,           # Allow JavaScript client to read for state
        samesite="lax",
    )
    response.headers["X-User-Session-ID"] = user_id

    return user_id
