"""
Skills API Endpoints
Provides endpoints for querying unlocked dynamic skills.
"""

from fastapi import APIRouter
from typing import List, Dict, Any

from ren.skills.registry import skill_registry

router = APIRouter(prefix="/skills", tags=["Skills"])


@router.get("", response_model=List[Dict[str, Any]])
async def list_unlocked_skills():
    """Lists all active and unlocked skills from SkillRegistry."""
    skills = skill_registry.get_active_skills()
    return [
        {
            "name": s.name,
            "description": s.description,
            "is_active": s.metadata.enabled,
            "safety_level": "Safe" if s.metadata.tested else "Standard",
            "source_task": s.metadata.source_task,
        }
        for s in skills
    ]
