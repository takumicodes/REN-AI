"""
REN Session Manager
Handles session lifecycle, disk persistence, compaction, and active conversation tracking.
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
    """Manages persistent dialog sessions and sliding-window compaction."""

    def __init__(self, sessions_dir: Optional[Path] = None):
        self.sessions_dir = sessions_dir or settings.PATHS.SESSIONS_DIR
        self.sessions_dir.mkdir(parents=True, exist_ok=True)
        self._active_session: Optional[Session] = None
        self._init_active_session()

    def _get_session_path(self, session_id: str) -> Path:
        return self.sessions_dir / f"session_{session_id}.json"

    def _init_active_session(self):
        """Loads most recent active session or creates a new one."""
        session_files = sorted(
            self.sessions_dir.glob("session_*.json"),
            key=lambda p: p.stat().st_mtime,
            reverse=True
        )
        if session_files:
            try:
                with open(session_files[0], "r", encoding="utf-8") as f:
                    data = json.load(f)
                    session = Session.from_dict(data)
                    if not session.is_archived:
                        self._active_session = session
                        return
            except Exception as e:
                error_logger.error(f"Failed to load recent session {session_files[0]}: {e}")

        # If none found or failed, create fresh
        self._active_session = self.create_session(title="Primary Session")

    @property
    def active_session(self) -> Session:
        if self._active_session is None:
            self._init_active_session()
        return self._active_session

    def create_session(self, title: str = "New Session", project: str = "default") -> Session:
        """Creates and saves a new persistent session."""
        session = Session(
            session_id=str(uuid.uuid4())[:8],
            title=title,
            project=project,
            created_at=datetime.utcnow().isoformat(),
            updated_at=datetime.utcnow().isoformat(),
        )
        self.save_session(session)
        self._active_session = session
        agent_logger.info(f"Created session '{session.title}' (ID: {session.session_id})")
        return session

    def save_session(self, session: Session) -> bool:
        """Saves session state to disk."""
        try:
            session.updated_at = datetime.utcnow().isoformat()
            path = self._get_session_path(session.session_id)
            with open(path, "w", encoding="utf-8") as f:
                json.dump(session.to_dict(), f, indent=2)
            return True
        except Exception as e:
            error_logger.error(f"Failed to save session {session.session_id}: {e}")
            return False

    def resume_session(self, session_id: str) -> Optional[Session]:
        """Loads a session by ID and makes it active."""
        path = self._get_session_path(session_id)
        if not path.exists():
            return None
        try:
            with open(path, "r", encoding="utf-8") as f:
                data = json.load(f)
                session = Session.from_dict(data)
                self._active_session = session
                return session
        except Exception as e:
            error_logger.error(f"Error resuming session {session_id}: {e}")
            return None

    def rename_session(self, session_id: str, new_title: str) -> bool:
        """Renames a session."""
        session = self.resume_session(session_id)
        if session:
            session.title = new_title
            return self.save_session(session)
        return False

    def list_sessions(self, include_archived: bool = False) -> List[Dict[str, Any]]:
        """Lists all persistent sessions with summaries."""
        results = []
        for p in self.sessions_dir.glob("session_*.json"):
            try:
                with open(p, "r", encoding="utf-8") as f:
                    d = json.load(f)
                    if not include_archived and d.get("is_archived", False):
                        continue
                    results.append({
                        "session_id": d.get("session_id"),
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

    def archive_session(self, session_id: str) -> bool:
        """Marks a session as archived."""
        session = self.resume_session(session_id)
        if session:
            session.is_archived = True
            return self.save_session(session)
        return False

    def delete_session(self, session_id: str) -> bool:
        """Permanently removes a session file."""
        path = self._get_session_path(session_id)
        if path.exists():
            try:
                path.unlink()
                if self._active_session and self._active_session.session_id == session_id:
                    self._init_active_session()
                return True
            except Exception as e:
                error_logger.error(f"Failed deleting session {session_id}: {e}")
        return False

    def reset_current_conversation(self) -> Session:
        """Resets the active conversation by starting a fresh session while leaving memory intact."""
        agent_logger.info("Resetting current conversation state...")
        new_session = self.create_session(title="Fresh Session")
        return new_session

    def compact_session_if_needed(self, session: Session, max_messages: int = 10, keep_recent: int = 4):
        """
        Compacts older messages into a condensed summary when message count exceeds threshold.
        Never sends hundreds of old messages to Qwen unnecessarily.
        """
        if len(session.messages) <= max_messages:
            return

        agent_logger.info(f"Compacting session {session.session_id} (count: {len(session.messages)})...")
        
        # Partition into old and recent
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
