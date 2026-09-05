"""
Autonomy & Proactive Initiative API Endpoints
Provides endpoints for querying autonomous initiative status, pending notifications,
message delivery acknowledgements, and manual trigger cycles.
"""

from fastapi import APIRouter, HTTPException, Depends
from pydantic import BaseModel
from typing import Dict, Any, List, Optional

from ren.autonomy.engine import autonomy_engine
from ren.autonomy.store import autonomous_store
from ren.config.settings import settings
from api.user_session import get_current_user_id

router = APIRouter(prefix="/autonomy", tags=["Autonomy Engine"])


class ToggleAutonomyRequest(BaseModel):
    enabled: bool


class AckMessageRequest(BaseModel):
    message_id: str


@router.get("/status")
async def get_autonomy_status(user_id: str = Depends(get_current_user_id)) -> Dict[str, Any]:
    """Returns current autonomy engine status, parameters, and quiet hour status."""
    return {
        "enabled": autonomy_engine.is_enabled,
        "cooldown_seconds": settings.AUTONOMY.COOLDOWN_SECONDS,
        "min_curiosity": settings.AUTONOMY.MIN_CURIOSITY_THRESHOLD,
        "min_importance": settings.AUTONOMY.MIN_IMPORTANCE_THRESHOLD,
        "max_per_hour": settings.AUTONOMY.MAX_MESSAGES_PER_HOUR,
        "is_quiet_hours": autonomy_engine.is_quiet_hours(),
    }


@router.post("/toggle")
async def toggle_autonomy(
    req: ToggleAutonomyRequest,
    user_id: str = Depends(get_current_user_id)
) -> Dict[str, Any]:
    """Enables or disables autonomous proactive communications."""
    autonomy_engine.set_enabled(req.enabled)
    return {"status": "ok", "enabled": autonomy_engine.is_enabled}


@router.get("/pending")
async def get_pending_initiatives(
    limit: int = 10,
    user_id: str = Depends(get_current_user_id)
) -> List[Dict[str, Any]]:
    """Retrieves unread/undelivered autonomous initiative messages for the client."""
    msgs = autonomous_store.get_pending_messages(limit=limit)
    return [m.to_dict() for m in msgs]


@router.post("/ack")
async def acknowledge_message(
    req: AckMessageRequest,
    user_id: str = Depends(get_current_user_id)
) -> Dict[str, Any]:
    """Marks an autonomous message as delivered/read."""
    success = autonomous_store.mark_as_delivered(req.message_id)
    return {"status": "ok", "delivered": success, "message_id": req.message_id}


@router.post("/trigger")
async def trigger_inspection_cycle(
    user_id: str = Depends(get_current_user_id)
) -> Dict[str, Any]:
    """Manually executes an autonomous inspection cycle."""
    autonomy_engine.run_inspection_cycle()
    return {"status": "executed", "message": "Autonomy inspection cycle completed."}
