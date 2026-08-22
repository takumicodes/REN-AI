"""
Dream & Sleep Mode API Endpoints
Provides endpoints for toggling cognitive sleep reflection, waking up, and querying reflection logs.
"""

from fastapi import APIRouter
from typing import Dict, Any, List

import back_end
from ren.dream.daemon import DreamDaemon

router = APIRouter(prefix="/dream", tags=["Dream & Sleep Mode"])
dream_daemon = DreamDaemon()


@router.get("/status")
async def get_sleep_status() -> Dict[str, Any]:
    """Returns current awake / sleep state and reflection activity."""
    return {
        "awake": back_end.awake,
        "state": "AWAKE" if back_end.awake else "SLEEPING",
        "logs": dream_daemon.get_logs()[:5]
    }


@router.post("/sleep")
async def enter_sleep() -> Dict[str, Any]:
    """Puts REN into Dream Mode reflection."""
    back_end.awake = False
    dream_daemon.log_action("MANUAL_SLEEP: Sleep mode triggered via mobile client.")
    return {
        "status": "sleeping",
        "message": "REN entered Dream Mode."
    }


@router.post("/wake")
async def wake_up() -> Dict[str, Any]:
    """Wakes up REN into active awareness."""
    back_end.awake = True
    dream_daemon.log_action("WAKE_UP: System restored to full awareness via mobile client.")
    return {
        "status": "awake",
        "message": "REN is awake and listening."
    }


@router.get("/logs")
async def get_reflection_logs() -> List[str]:
    """Retrieves structured reflection logs from the dream daemon."""
    return dream_daemon.get_logs()
