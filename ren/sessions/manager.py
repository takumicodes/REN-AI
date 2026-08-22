"""
REN Session Manager
Handles multi-user session lifecycle, disk persistence, compaction, and per-user conversation isolation.
"""

import json
import uuid
from datetime import datetime
from pathlib import Path
from typing import List, Dict, Any, Optional

from ren.sessions.models import Session, Message, Plan
from ren.memory.summarizer import MemorySummarizer
from ren.config.settings import settings
from ren.monitoring.logger import agent_logger, error_logger


class SessionManager:
    """Manages persistent dialog sessions with strict user isolation and sliding-window compaction."""

    def __init__(self, sessions_dir: Optional[Path] = None):
        self.sessions_dir = sessions_dir or settings.PATHS.SESSIONS_DIR
        self.sessions_dir.mkdir(parents=True, exist_ok=True)
        self._active_sessions: Dict[str, Session] = {}
        self._init_default_session()

    def _get_session_path(self, session_id: str) -> Path:
        return self.sessions_dir / f"session_{session_id}.json"

    def _init_default_session(self):
        """Initializes default master session for desktop HUD."""
        default_session = self.get_active_session_for_user(user_id="default")
        self._active_sessions["default"] = default_session

    @property
    def active_session(self) -> Session:
        """Desktop compatibility property for the default master session."""
        return self.get_active_session_for_user(user_id="default")

    def get_active_session_for_user(self, user_id: str = "default") -> Session:
        """Retrieves or creates the active session for a specific user."""
        if user_id in self._active_sessions:
            return self._active_sessions[user_id]

        # Scan for user's most recent session
        user_sessions = []
        for p in self.sessions_dir.glob("session_*.json"):
            try:
                with open(p, "r", encoding="utf-8") as f:
                    data = json.load(f)
                    sess_user = data.get("user_id", "default")
                    if sess_user == user_id and not data.get("is_archived", False):
                        user_sessions.append((p.stat().st_mtime, data))
            except Exception:
                continue

        if user_sessions:
            user_sessions.sort(key=lambda x: x[0], reverse=True)
            most_recent = Session.from_dict(user_sessions[0][1])
            self._active_sessions[user_id] = most_recent
            return most_recent

        # No existing session for this user -> create fresh
        new_sess = self.create_session(user_id=user_id, title="New Conversation")
        return new_sess

    def create_session(
        self,
        user_id: str = "default",
        title: str = "New Conversation",
        project: str = "default"
    ) -> Session:
        """Creates and saves a new persistent session belonging to a specific user."""
        session = Session(
            session_id=str(uuid.uuid4())[:8],
            user_id=user_id,
            title=title,
            project=project,
            created_at=datetime.utcnow().isoformat(),
            updated_at=datetime.utcnow().isoformat(),
        )
        self.save_session(session)
        self._active_sessions[user_id] = session
        agent_logger.info(f"Created session '{session.title}' (ID: {session.session_id}) for user '{user_id}'")
        return session

    def save_session(self, session: Session) -> bool:
        """Saves session state to disk."""
        try:
            session.updated_at = datetime.utcnow().isoformat()
            path = self._get_session_path(session.session_id)
            with open(path, "w", encoding="utf-8") as f:
                json.dump(session.to_dict(), f, indent=2)
            self._active_sessions[session.user_id] = session
            return True
        except Exception as e:
            error_logger.error(f"Failed to save session {session.session_id}: {e}")
            return False

    def resume_session(self, session_id: str, user_id: Optional[str] = None) -> Optional[Session]:
        """Loads a session by ID and verifies user ownership."""
        path = self._get_session_path(session_id)
        if not path.exists():
            return None
        try:
            with open(path, "r", encoding="utf-8") as f:
                data = json.load(f)
                session = Session.from_dict(data)

                # Enforce user boundary if specified
                if user_id is not None and user_id != "default" and session.user_id != user_id:
                    agent_logger.warning(f"Unauthorized session access attempt: User '{user_id}' tried accessing session '{session_id}' owned by '{session.user_id}'")
                    return None

                self._active_sessions[session.user_id] = session
                return session
        except Exception as e:
            error_logger.error(f"Error resuming session {session_id}: {e}")
            return None

    def rename_session(self, session_id: str, new_title: str, user_id: Optional[str] = None) -> bool:
        """Renames a session with user ownership check."""
        session = self.resume_session(session_id, user_id=user_id)
        if session:
            session.title = new_title
            return self.save_session(session)
        return False

    def list_sessions(self, user_id: Optional[str] = None, include_archived: bool = False) -> List[Dict[str, Any]]:
        """Lists persistent sessions filtered strictly by user_id."""
        results = []
        for p in self.sessions_dir.glob("session_*.json"):
            try:
                with open(p, "r", encoding="utf-8") as f:
                    d = json.load(f)
                    sess_user = d.get("user_id", "default")

                    # Filter by user
                    if user_id is not None and sess_user != user_id:
                        continue

                    if not include_archived and d.get("is_archived", False):
                        continue

                    results.append({
                        "session_id": d.get("session_id"),
                        "user_id": sess_user,
                        "title": d.get("title"),
                        "project": d.get("project"),
                        "message_count": len(d.get("messages", [])),
                        "created_at": d.get("created_at"),
                        "updated_at": d.get("updated_at"),
                        "is_archived": d.get("is_archived", False),
                    })
            except Exception:
                continue

        results.sort(key=lambda x: x.get("updated_at", ""), reverse=True)
        return results

    def archive_session(self, session_id: str, user_id: Optional[str] = None) -> bool:
        """Marks a session as archived with ownership check."""
        session = self.resume_session(session_id, user_id=user_id)
        if session:
            session.is_archived = True
            return self.save_session(session)
        return False

    def delete_session(self, session_id: str, user_id: Optional[str] = None) -> bool:
        """Permanently removes a session file with ownership verification."""
        session = self.resume_session(session_id, user_id=user_id)
        if not session:
            return False

        path = self._get_session_path(session_id)
        if path.exists():
            try:
                path.unlink()
                if session.user_id in self._active_sessions and self._active_sessions[session.user_id].session_id == session_id:
                    self._active_sessions.pop(session.user_id, None)
                return True
            except Exception as e:
                error_logger.error(f"Failed deleting session {session_id}: {e}")
        return False

    def reset_current_conversation(self, user_id: str = "default") -> Session:
        """Resets the active conversation for a user by creating a fresh session."""
        agent_logger.info(f"Resetting current conversation state for user '{user_id}'...")
        new_session = self.create_session(user_id=user_id, title="New Conversation")
        return new_session

    def compact_session_if_needed(self, session: Session, max_messages: int = 10, keep_recent: int = 4):
        """Compacts older messages into a condensed summary when threshold exceeded."""
        if len(session.messages) <= max_messages:
            return

        agent_logger.info(f"Compacting session {session.session_id} (count: {len(session.messages)})...")
        old_messages = session.messages[:-keep_recent]
        recent_messages = session.messages[-keep_recent:]

        old_dicts = [{"role": m.role, "content": m.content} for m in old_messages]
        new_summary = MemorySummarizer.heuristic_summarize(old_dicts)

        if session.summary:
            session.summary = f"{session.summary} | {new_summary}"
        else:
            session.summary = new_summary

        session.messages = recent_messages
        self.save_session(session)
        agent_logger.info(f"Session compacted. New summary: {session.summary[:80]}...")


# Global session manager singleton
session_manager = SessionManager()
