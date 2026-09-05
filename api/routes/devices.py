"""
Device Management & QR Pairing API Endpoints
Provides secure pairing handshakes, heartbeat telemetry, device listing, and disconnection/revocation.
"""

from typing import Optional, List, Dict, Any
from pydantic import BaseModel
from fastapi import APIRouter, HTTPException, Depends

from ren.devices.pairing import pairing_manager
from ren.core.device_context import device_manager
from api.user_session import get_current_user_id

router = APIRouter(prefix="/devices", tags=["Devices"])


class PairingVerifyRequest(BaseModel):
    pairing_id: str
    challenge: str
    device_id: str
    device_name: Optional[str] = "Phone"
    platform: Optional[str] = "android"
    capabilities: Optional[List[str]] = None


class HeartbeatRequest(BaseModel):
    device_id: str
    battery: Optional[Dict[str, Any]] = None
    storage: Optional[Dict[str, Any]] = None


@router.get("/pairing/qr")
async def get_pairing_qr(user_id: str = Depends(get_current_user_id)):
    """Generates a temporary one-time pairing QR payload and base64 PNG image for the PC UI."""
    return pairing_manager.get_current_qr_data(user_id=user_id)


@router.post("/pairing/verify")
async def verify_pairing(req: PairingVerifyRequest, user_id: str = Depends(get_current_user_id)):
    """
    Called by phone client after scanning PC QR code.
    Validates cryptographic challenge, enforces one-time use, and returns device credentials.
    """
    success, msg, data = pairing_manager.verify_and_pair(
        pairing_id=req.pairing_id,
        challenge=req.challenge,
        device_id=req.device_id,
        device_name=req.device_name or "Phone",
        platform_str=req.platform or "android",
        capabilities=req.capabilities,
        user_id=user_id
    )
    if not success:
        raise HTTPException(status_code=400, detail=msg)
    return data


@router.get("")
async def list_devices(user_id: str = Depends(get_current_user_id)):
    """Lists all registered devices and their live connection status."""
    devices = device_manager.list_devices(user_id=user_id)
    return [d.to_dict() for d in devices]


@router.post("/heartbeat")
async def device_heartbeat(req: HeartbeatRequest, user_id: str = Depends(get_current_user_id)):
    """Periodic telemetry report from phone companion (battery, storage, connection alive)."""
    device_manager.update_device_heartbeat(
        device_id=req.device_id,
        battery=req.battery,
        storage=req.storage
    )
    return {"status": "ok", "device_id": req.device_id}


@router.post("/{device_id}/disconnect")
async def disconnect_device(device_id: str, user_id: str = Depends(get_current_user_id)):
    """Marks a connected device as disconnected."""
    pairing_manager.disconnect_device(device_id)
    return {"status": "disconnected", "device_id": device_id}


@router.post("/{device_id}/revoke")
async def revoke_device(device_id: str, user_id: str = Depends(get_current_user_id)):
    """Revokes device pairing permanently."""
    pairing_manager.revoke_device(device_id)
    return {"status": "revoked", "device_id": device_id}
