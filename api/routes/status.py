"""
Status and Health Endpoints
Provides system monitoring, model telemetry, and agent health information.
"""

from fastapi import APIRouter
from typing import Dict, Any

from ren.config.settings import settings
from ren.models import get_model_provider
from ren.monitoring.performance import perf_monitor
from ren.sessions.manager import session_manager
from ren.skills.registry import skill_registry
from ren.memory.manager import memory_manager
import back_end

router = APIRouter(tags=["Status"])


@router.get("/health")
async def health_check() -> Dict[str, Any]:
    """Health check endpoint verifying model and runtime availability."""
    provider = get_model_provider()
    ollama_health = provider.health_check()
    
    return {
        "status": "healthy" if ollama_health.get("online", False) else "degraded",
        "name": settings.ASSISTANT_NAME,
        "creator": settings.CREATOR_NAME,
        "version": settings.VERSION,
        "ollama": ollama_health,
        "memory": {
            "creator": memory_manager.get_system_facts().get("creator", settings.CREATOR_NAME),
            "mood": memory_manager.get_system_facts().get("mood", "normal"),
        }
    }


@router.get("/status")
async def system_status_endpoint() -> Dict[str, Any]:
    """Retrieves live host metrics, active session, and agent state."""
    snapshot = perf_monitor.get_system_snapshot()
    provider = get_model_provider()
    
    active_session_id = None
    try:
        active_session_id = session_manager.active_session.session_id
    except Exception:
        pass

    sessions_count = len(session_manager.list_sessions(include_archived=False))
    skills = skill_registry.get_unlocked_skill_names()
    ollama_health = provider.health_check()

    return {
        "system": {
            "cpu_percent": snapshot.get("cpu_percent", 0.0),
            "ram_percent": snapshot.get("ram_percent", 0.0),
            "ram_available_mb": snapshot.get("ram_available_mb", 0.0),
            "disk_percent": snapshot.get("disk_percent", 0.0),
            "temperature_c": snapshot.get("temperature_c"),
        },
        "agent": {
            "active_session_id": active_session_id,
            "active_model": provider.model_name if hasattr(provider, "model_name") else settings.MODEL.MODEL_NAME,
            "is_processing": back_end.is_processing,
            "awake": back_end.awake,
            "ollama_online": ollama_health.get("online", False),
        },
        "ollama": ollama_health,
        "stats": {
            "total_sessions": sessions_count,
            "total_skills": len(skills),
        }
    }
