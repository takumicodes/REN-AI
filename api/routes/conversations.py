"""
Conversations & Sessions API Endpoints
Manages multi-user dialog session lifecycle, switching, history retrieval, and deletions with user isolation.
"""

from fastapi import APIRouter, HTTPException, Depends
from pydantic import BaseModel
from typing import List, Dict, Any, Optional

from ren.sessions.manager import session_manager
from ren.monitoring.logger import agent_logger
from api.user_session import get_current_user_id

router = APIRouter(prefix="/conversations", tags=["Conversations"])


class CreateSessionRequest(BaseModel):
    title: Optional[str] = "New Conversation"
    project: Optional[str] = "default"


class RenameSessionRequest(BaseModel):
    title: str


@router.get("", response_model=List[Dict[str, Any]])
async def list_conversations(
    include_archived: bool = False,
    user_id: str = Depends(get_current_user_id)
):
    """Lists persistent conversations strictly for the authenticated user session."""
    sessions = session_manager.list_sessions(user_id=user_id, include_archived=include_archived)
    active_session = session_manager.get_active_session_for_user(user_id=user_id)
    active_id = active_session.session_id if active_session else None

    for s in sessions:
        s["is_active"] = (s.get("session_id") == active_id)

    return sessions


@router.post("", response_model=Dict[str, Any])
async def create_conversation(
    req: CreateSessionRequest,
    user_id: str = Depends(get_current_user_id)
):
    """Creates a new empty persistent conversation session belonging to the user."""
    session = session_manager.create_session(
        user_id=user_id,
        title=req.title or "New Conversation",
        project=req.project or "default"
    )
    return {
        "session_id": session.session_id,
        "user_id": session.user_id,
        "title": session.title,
        "project": session.project,
        "created_at": session.created_at,
        "updated_at": session.updated_at,
        "messages": [],
        "is_active": True,
    }


@router.get("/{session_id}", response_model=Dict[str, Any])
async def get_conversation(
    session_id: str,
    user_id: str = Depends(get_current_user_id)
):
    """Retrieves a persistent conversation with full history, ensuring user ownership."""
    session = session_manager.resume_session(session_id, user_id=user_id)
    if not session:
        raise HTTPException(status_code=404, detail=f"Conversation session '{session_id}' not found.")
    
    active_session = session_manager.get_active_session_for_user(user_id=user_id)
    is_active = (active_session.session_id == session.session_id) if active_session else False

    return {
        "session_id": session.session_id,
        "user_id": session.user_id,
        "title": session.title,
        "project": session.project,
        "created_at": session.created_at,
        "updated_at": session.updated_at,
        "messages": [m.to_dict() for m in session.messages],
        "summary": session.summary,
        "is_active": is_active,
    }


@router.post("/{session_id}/activate", response_model=Dict[str, Any])
async def activate_conversation(
    session_id: str,
    user_id: str = Depends(get_current_user_id)
):
    """Switches active session for this user to the specified conversation."""
    session = session_manager.resume_session(session_id, user_id=user_id)
    if not session:
        raise HTTPException(status_code=404, detail=f"Conversation session '{session_id}' not found.")
    
    return {
        "success": True,
        "session_id": session.session_id,
        "title": session.title,
        "message": f"Active conversation set to '{session.title}'."
    }


@router.patch("/{session_id}", response_model=Dict[str, Any])
async def rename_conversation(
    session_id: str,
    req: RenameSessionRequest,
    user_id: str = Depends(get_current_user_id)
):
    """Renames an existing conversation with ownership validation."""
    success = session_manager.rename_session(session_id, req.title, user_id=user_id)
    if not success:
        raise HTTPException(status_code=404, detail=f"Conversation '{session_id}' not found or unauthorized.")
    return {"success": True, "session_id": session_id, "title": req.title}


@router.delete("/{session_id}", response_model=Dict[str, Any])
async def delete_conversation(
    session_id: str,
    user_id: str = Depends(get_current_user_id)
):
    """Permanently deletes a persistent conversation file with ownership validation."""
    success = session_manager.delete_session(session_id, user_id=user_id)
    if not success:
        raise HTTPException(status_code=404, detail=f"Conversation session '{session_id}' not found or unauthorized.")
    return {"success": True, "deleted_session_id": session_id}
