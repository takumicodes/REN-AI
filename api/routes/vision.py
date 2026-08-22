"""
Vision & Sensory API Endpoints
Processes mobile camera snapshots, person presence detection, and sensory telemetry.
"""

from fastapi import APIRouter, HTTPException, Depends
from pydantic import BaseModel
from typing import Dict, Any, Optional

from ren.monitoring.logger import agent_logger
from api.user_session import get_current_user_id
from api.auth import require_auth

router = APIRouter(prefix="/vision", tags=["Vision & Sensors"])


class VisionSnapshotRequest(BaseModel):
    image_base64: Optional[str] = None
    prompt: Optional[str] = "Describe what you see in front of the camera."
    person_detected: Optional[bool] = False
    face_count: Optional[int] = 0


@router.post("/analyze")
async def analyze_snapshot(
    req: VisionSnapshotRequest,
    user_id: str = Depends(get_current_user_id)
) -> Dict[str, Any]:
    """Analyzes a mobile camera snapshot for objects, people, and visual context."""
    agent_logger.info(f"Vision snapshot received from user '{user_id}'. Person detected: {req.person_detected}, Faces: {req.face_count}")

    # Generate sensory reaction
    if req.face_count and req.face_count > 1:
        scene_summary = f"I see multiple people in front of the camera ({req.face_count} people detected)."
    elif req.person_detected or (req.face_count and req.face_count == 1):
        scene_summary = "I see someone right in front of me looking at the screen."
    else:
        scene_summary = "I see the room and surroundings through your phone camera."

    return {
        "success": True,
        "summary": scene_summary,
        "person_detected": bool(req.person_detected or (req.face_count and req.face_count > 0)),
        "face_count": req.face_count or 0,
    }


class SensorEventRequest(BaseModel):
    event_type: str  # SHAKE_DETECTED, BATTERY_LOW, ORIENTATION_CHANGE
    details: Optional[Dict[str, Any]] = None


@router.post("/event")
async def handle_sensor_event(
    req: SensorEventRequest,
    user_id: str = Depends(get_current_user_id)
) -> Dict[str, Any]:
    """Processes debounced local sensory events from the phone."""
    event_type = req.event_type.upper()
    agent_logger.info(f"Sensory event '{event_type}' from user '{user_id}'")

    if event_type == "SHAKE_DETECTED":
        return {
            "reaction": "😵 Whoa... you're making me dizzy! Please don't shake me too hard!",
            "action": "shake_reaction"
        }
    elif event_type == "BATTERY_LOW":
        return {
            "reaction": "⚠️ Battery is getting low on your device. You might want to plug me in soon!",
            "action": "battery_warning"
        }
    elif event_type == "PERSON_DETECTED":
        return {
            "reaction": "👋 Hello! I see someone there.",
            "action": "presence_detected"
        }

    return {"status": "received", "event_type": event_type}
