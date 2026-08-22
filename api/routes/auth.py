"""
Authentication API Endpoints
Handles login verification, passkey validation, and auth status queries.
"""

from fastapi import APIRouter, Request, HTTPException
from pydantic import BaseModel
from typing import Dict, Any

from api.auth import is_auth_enabled, verify_token, get_configured_access_key

router = APIRouter(prefix="/auth", tags=["Authentication"])


class VerifyKeyRequest(BaseModel):
    key: str


@router.get("/check")
async def check_auth_status() -> Dict[str, Any]:
    """Returns whether access key authentication is required."""
    return {
        "auth_required": is_auth_enabled()
    }


@router.post("/verify")
async def verify_passkey(req: VerifyKeyRequest, request: Request) -> Dict[str, Any]:
    """Verifies user passkey and returns session token."""
    client_ip = request.client.host if request.client else "unknown"
    is_valid = verify_token(req.key, ip=client_ip)

    if not is_valid:
        raise HTTPException(status_code=401, detail="Invalid access passkey.")

    return {
        "valid": True,
        "token": req.key.strip(),
        "message": "Access granted."
    }
