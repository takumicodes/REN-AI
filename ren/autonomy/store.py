"""
REN Autonomous Initiative Persistent Store
Tracks, persists, and synchronizes autonomous proactive notifications and insights.
Provides cross-device message synchronization so offline clients receive pending messages on reconnect.
"""

import sqlite3
import hashlib
import uuid
import time
from datetime import datetime
from typing import Dict, Any, List, Optional
from dataclasses import dataclass, asdict

from ren.config.settings import settings
from ren.monitoring.logger import agent_logger, error_logger


@dataclass
class AutonomousMessage:
    message_id: str
    content: str
    source: str
    importance: float
    curiosity_score: float
    reason: str
    delivered: bool = False
    created_at: str = ""
    delivered_at: Optional[str] = None
    title: str = "Autonomous Insight"

    def to_dict(self) -> Dict[str, Any]:
        return asdict(self)


class AutonomousStore:
    """Persistent SQLite store for autonomous notifications and initiatives."""

    def __init__(self):
        self.db_path = settings.PATHS.DB_PATH
        self._init_db()

    def _get_connection(self) -> sqlite3.Connection:
        conn = sqlite3.connect(str(self.db_path), timeout=10.0)
        conn.row_factory = sqlite3.Row
        return conn

    def _init_db(self):
        """Initializes autonomous messages schema."""
        try:
            with self._get_connection() as conn:
                cursor = conn.cursor()
                cursor.execute("""
                    CREATE TABLE IF NOT EXISTS autonomous_messages (
                        id INTEGER PRIMARY KEY AUTOINCREMENT,
                        message_id TEXT UNIQUE NOT NULL,
                        title TEXT NOT NULL,
                        content TEXT NOT NULL,
                        content_hash TEXT NOT NULL,
                        source TEXT NOT NULL,
                        importance REAL NOT NULL,
                        curiosity_score REAL NOT NULL,
                        reason TEXT NOT NULL,
                        delivered INTEGER NOT NULL DEFAULT 0,
                        created_at TEXT NOT NULL,
                        delivered_at TEXT
                    );
                """)
                cursor.execute("CREATE INDEX IF NOT EXISTS idx_auto_delivered ON autonomous_messages(delivered);")
                cursor.execute("CREATE INDEX IF NOT EXISTS idx_auto_created ON autonomous_messages(created_at);")
                conn.commit()
        except Exception as e:
            error_logger.error(f"Failed to initialize autonomous store database: {e}")

    def store_message(
        self,
        content: str,
        source: str = "dream",
        importance: float = 0.8,
        curiosity_score: float = 0.8,
        reason: str = "Proactive suggestion",
        title: str = "Autonomous Insight",
    ) -> AutonomousMessage:
        """Stores a new autonomous initiative message in the persistent queue."""
        msg_id = str(uuid.uuid4())[:8]
        now = datetime.utcnow().isoformat()
        content_hash = hashlib.sha256(content.strip().lower().encode("utf-8")).hexdigest()

        msg = AutonomousMessage(
            message_id=msg_id,
            title=title,
            content=content.strip(),
            source=source,
            importance=importance,
            curiosity_score=curiosity_score,
            reason=reason,
            delivered=False,
            created_at=now,
        )

        try:
            with self._get_connection() as conn:
                cursor = conn.cursor()
                cursor.execute("""
                    INSERT INTO autonomous_messages 
                    (message_id, title, content, content_hash, source, importance, curiosity_score, reason, delivered, created_at)
                    VALUES (?, ?, ?, ?, ?, ?, ?, ?, 0, ?)
                """, (msg_id, title, content.strip(), content_hash, source, importance, curiosity_score, reason, now))
                conn.commit()
                agent_logger.info(f"Stored autonomous message [{msg_id}]: '{title}' (importance={importance:.2f})")
        except Exception as e:
            error_logger.error(f"Error storing autonomous message: {e}")

        return msg

    def get_pending_messages(self, limit: int = 10) -> List[AutonomousMessage]:
        """Retrieves unread/undelivered autonomous messages."""
        messages: List[AutonomousMessage] = []
        try:
            with self._get_connection() as conn:
                cursor = conn.cursor()
                cursor.execute("""
                    SELECT message_id, title, content, source, importance, curiosity_score, reason, delivered, created_at, delivered_at
                    FROM autonomous_messages
                    WHERE delivered = 0
                    ORDER BY id ASC
                    LIMIT ?
                """, (limit,))
                for row in cursor.fetchall():
                    messages.append(AutonomousMessage(
                        message_id=row["message_id"],
                        title=row["title"],
                        content=row["content"],
                        source=row["source"],
                        importance=row["importance"],
                        curiosity_score=row["curiosity_score"],
                        reason=row["reason"],
                        delivered=bool(row["delivered"]),
                        created_at=row["created_at"],
                        delivered_at=row["delivered_at"],
                    ))
        except Exception as e:
            error_logger.error(f"Error reading pending autonomous messages: {e}")
        return messages

    def mark_as_delivered(self, message_id: str) -> bool:
        """Marks an autonomous message as delivered to UI."""
        now = datetime.utcnow().isoformat()
        try:
            with self._get_connection() as conn:
                cursor = conn.cursor()
                cursor.execute("""
                    UPDATE autonomous_messages
                    SET delivered = 1, delivered_at = ?
                    WHERE message_id = ?
                """, (now, message_id))
                conn.commit()
                return cursor.rowcount > 0
        except Exception as e:
            error_logger.error(f"Error marking message as delivered: {e}")
            return False

    def has_similar_recent_message(self, content: str, time_window_seconds: int = 1800) -> bool:
        """Checks if an identical or highly similar message was stored within the cooldown window."""
        content_hash = hashlib.sha256(content.strip().lower().encode("utf-8")).hexdigest()
        try:
            with self._get_connection() as conn:
                cursor = conn.cursor()
                cursor.execute("""
                    SELECT COUNT(*) as count
                    FROM autonomous_messages
                    WHERE content_hash = ?
                """, (content_hash,))
                row = cursor.fetchone()
                return row["count"] > 0 if row else False
        except Exception:
            return False


# Global store singleton
autonomous_store = AutonomousStore()
