"""
Developer / Admin Mode API Endpoints
Provides endpoints for secure developer authentication, capability inspection,
and developer mode lifecycle management without leaking secrets.
"""

from fastapi import APIRouter, HTTPException, Header, Depends
from pydantic import BaseModel
from typing import Dict, Any, Optional

from ren.security.developer_mode import developer_mode_manager, DeveloperCapabilities
from api.user_session import get_current_user_id

router = APIRouter(prefix="/developer", tags=["Developer Mode"])


class DeveloperAuthRequest(BaseModel):
    secret: str


class UpdateCapabilitiesRequest(BaseModel):
    debug: Optional[bool] = None
    skill_development: Optional[bool] = None
    advanced_tools: Optional[bool] = None
    autonomous_tools: Optional[bool] = None
    verbose_telemetry: Optional[bool] = None


@router.post("/auth")
async def authenticate_developer(
    req: DeveloperAuthRequest,
    user_id: str = Depends(get_current_user_id)
) -> Dict[str, Any]:
    """Authenticates with the developer secret and returns an isolated session token."""
    token = developer_mode_manager.authenticate_session(req.secret)
    if not token:
        raise HTTPException(status_code=403, detail="Invalid developer secret.")

    caps = developer_mode_manager.get_capabilities(token)
    return {
        "authenticated": True,
        "token": token,
        "capabilities": caps.to_dict(),
    }


@router.get("/status")
async def get_developer_status(
    x_dev_token: Optional[str] = Header(None, alias="X-Developer-Token"),
    user_id: str = Depends(get_current_user_id)
) -> Dict[str, Any]:
    """Returns the current developer mode status and active capabilities."""
    is_active = developer_mode_manager.is_developer_mode_active(x_dev_token)
    caps = developer_mode_manager.get_capabilities(x_dev_token)
    return {
        "active": is_active,
        "capabilities": caps.to_dict(),
    }


@router.post("/capabilities")
async def update_developer_capabilities(
    req: UpdateCapabilitiesRequest,
    x_dev_token: Optional[str] = Header(None, alias="X-Developer-Token"),
    user_id: str = Depends(get_current_user_id)
) -> Dict[str, Any]:
    """Updates capability flags for an active developer session."""
    if not developer_mode_manager.is_developer_mode_active(x_dev_token):
        raise HTTPException(status_code=403, detail="Developer mode not active.")

    updates = {k: v for k, v in req.dict().items() if v is not None}
    caps = developer_mode_manager.update_capabilities(updates, token=x_dev_token)
    return {
        "status": "updated",
        "capabilities": caps.to_dict(),
    }


@router.post("/revoke")
async def revoke_developer_session(
    x_dev_token: Optional[str] = Header(None, alias="X-Developer-Token"),
    user_id: str = Depends(get_current_user_id)
) -> Dict[str, Any]:
    """Deactivates developer mode for this session."""
    developer_mode_manager.revoke_session(x_dev_token)
    return {"status": "revoked", "active": False}
