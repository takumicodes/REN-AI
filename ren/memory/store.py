"""
REN Persistent Memory Store
SQLite-backed transactional persistence with automatic migration, backups, and corruption recovery.
"""

import os
import json
import sqlite3
import shutil
import time
from datetime import datetime
from pathlib import Path
from typing import Dict, Any, List, Optional, Tuple

from ren.config.settings import settings
from ren.monitoring.logger import memory_logger, error_logger


class MemoryStore:
    """Thread-safe SQLite storage engine for structured agent memories."""

    def __init__(self, db_path: Optional[Path] = None):
        self.db_path = db_path or settings.PATHS.DB_PATH
        self.backup_dir = self.db_path.parent / "backups"
        self.backup_dir.mkdir(parents=True, exist_ok=True)
        self._init_db()

    def _get_connection(self) -> sqlite3.Connection:
        """Creates a connection with WAL mode and row factory."""
        conn = sqlite3.connect(str(self.db_path), timeout=10.0)
        conn.row_factory = sqlite3.Row
        conn.execute("PRAGMA journal_mode=WAL;")
        conn.execute("PRAGMA synchronous=NORMAL;")
        return conn

    def _init_db(self):
        """Creates tables and performs migration from memory.json if necessary."""
        try:
            with self._get_connection() as conn:
                cursor = conn.cursor()

                # System facts (Key-Value facts like creator, assistant_name, mood)
                cursor.execute("""
                CREATE TABLE IF NOT EXISTS system_facts (
                    key TEXT PRIMARY KEY,
                    value_json TEXT NOT NULL,
                    updated_at TEXT NOT NULL
                );
                """)

                # Long-term facts, user preferences, knowledge
                cursor.execute("""
                CREATE TABLE IF NOT EXISTS long_term_memories (
                    id INTEGER PRIMARY KEY AUTOINCREMENT,
                    category TEXT NOT NULL,
                    key TEXT,
                    content TEXT NOT NULL,
                    importance INTEGER DEFAULT 1,
                    tags TEXT DEFAULT '',
                    access_count INTEGER DEFAULT 0,
                    created_at TEXT NOT NULL,
                    updated_at TEXT NOT NULL
                );
                """)
                cursor.execute("CREATE INDEX IF NOT EXISTS idx_ltm_category ON long_term_memories(category);")
                cursor.execute("CREATE INDEX IF NOT EXISTS idx_ltm_tags ON long_term_memories(tags);")

                # Episodic memories (tasks attempted, outcomes, errors, solutions)
                cursor.execute("""
                CREATE TABLE IF NOT EXISTS episodic_memories (
                    id INTEGER PRIMARY KEY AUTOINCREMENT,
                    task TEXT NOT NULL,
                    outcome TEXT NOT NULL,
                    actions_taken TEXT DEFAULT '',
                    error TEXT DEFAULT '',
                    solution TEXT DEFAULT '',
                    created_at TEXT NOT NULL
                );
                """)
                cursor.execute("CREATE INDEX IF NOT EXISTS idx_episode_task ON episodic_memories(task);")

                # Project memories (recognized user projects and repository state)
                cursor.execute("""
                CREATE TABLE IF NOT EXISTS project_memories (
                    id INTEGER PRIMARY KEY AUTOINCREMENT,
                    name TEXT UNIQUE NOT NULL,
                    path TEXT,
                    language TEXT,
                    framework TEXT,
                    status TEXT,
                    important_files TEXT DEFAULT '[]',
                    known_bugs TEXT DEFAULT '[]',
                    recent_changes TEXT DEFAULT '[]',
                    metadata_json TEXT DEFAULT '{}',
                    updated_at TEXT NOT NULL
                );
                """)
                conn.commit()

            # Check if migration from memory.json is needed
            self._migrate_from_legacy_json_if_needed()

        except sqlite3.DatabaseError as e:
            error_logger.error(f"Database error during initialization: {e}. Attempting recovery...")
            self.recover_corrupted_db()

    def backup_database(self) -> Optional[Path]:
        """Creates a timestamped backup copy of the SQLite database."""
        if not self.db_path.exists():
            return None
        try:
            timestamp = datetime.now().strftime("%Y%m%d_%H%M%S")
            backup_file = self.backup_dir / f"ren_memory_backup_{timestamp}.db"
            shutil.copy2(self.db_path, backup_file)
            memory_logger.info(f"Database backup saved to {backup_file}")
            
            # Keep only the last 10 backups
            backups = sorted(self.backup_dir.glob("ren_memory_backup_*.db"))
            while len(backups) > 10:
                oldest = backups.pop(0)
                try:
                    oldest.unlink()
                except Exception:
                    pass
            return backup_file
        except Exception as e:
            error_logger.error(f"Failed to create database backup: {e}")
            return None

    def recover_corrupted_db(self):
        """Attempts to recover from database corruption using backups or legacy memory.json."""
        memory_logger.warning("Initiating database recovery protocol...")
        backups = sorted(self.backup_dir.glob("ren_memory_backup_*.db"))
        recovered = False

        if backups:
            latest_backup = backups[-1]
            try:
                if self.db_path.exists():
                    corrupted_dump = self.backup_dir / f"corrupted_{int(time.time())}.db"
                    shutil.move(self.db_path, corrupted_dump)
                shutil.copy2(latest_backup, self.db_path)
                memory_logger.info(f"Restored database from backup {latest_backup}")
                recovered = True
            except Exception as e:
                error_logger.error(f"Failed restoring backup: {e}")

        if not recovered:
            # Recreate from scratch and migrate from memory.json
            if self.db_path.exists():
                try:
                    self.db_path.unlink()
                except Exception:
                    pass
            self._init_db()
            self._force_migrate_from_legacy_json()

    def _migrate_from_legacy_json_if_needed(self):
        """Migrates data from memory.json if SQLite tables are empty."""
        with self._get_connection() as conn:
            count = conn.execute("SELECT COUNT(*) FROM system_facts").fetchone()[0]
            if count == 0 and settings.PATHS.LEGACY_MEMORY_FILE.exists():
                self._force_migrate_from_legacy_json()

    def _force_migrate_from_legacy_json(self):
        """Reads memory.json and migrates all fields into SQLite tables."""
        legacy_file = settings.PATHS.LEGACY_MEMORY_FILE
        if not legacy_file.exists():
            return

        try:
            with open(legacy_file, "r", encoding="utf-8") as f:
                data = json.load(f)

            self.backup_database()
            now = datetime.utcnow().isoformat()

            with self._get_connection() as conn:
                cursor = conn.cursor()

                for key, val in data.items():
                    # Save as system fact
                    cursor.execute(
                        "INSERT OR REPLACE INTO system_facts (key, value_json, updated_at) VALUES (?, ?, ?)",
                        (key, json.dumps(val), now)
                    )

                    # Also populate long_term_memories categorized appropriately
                    if key == "skills" and isinstance(val, list):
                        for skill in val:
                            cursor.execute(
                                "INSERT INTO long_term_memories (category, key, content, importance, tags, created_at, updated_at) VALUES (?, ?, ?, ?, ?, ?, ?)",
                                ("skill", "skill", f"User skill: {skill}", 2, "skill,user", now, now)
                            )
                    elif key == "current_projects" and isinstance(val, list):
                        for proj in val:
                            cursor.execute(
                                "INSERT INTO long_term_memories (category, key, content, importance, tags, created_at, updated_at) VALUES (?, ?, ?, ?, ?, ?, ?)",
                                ("project", "project", f"Active project: {proj}", 3, "project,active", now, now)
                            )
                    elif key == "learned_from_dreams" and isinstance(val, list):
                        for item in val:
                            cursor.execute(
                                "INSERT INTO long_term_memories (category, key, content, importance, tags, created_at, updated_at) VALUES (?, ?, ?, ?, ?, ?, ?)",
                                ("dream_learning", "dream", str(item), 1, "dream,learning", now, now)
                            )
                conn.commit()

            memory_logger.info(f"Successfully migrated {len(data)} items from {legacy_file} into SQLite.")
        except Exception as e:
            error_logger.error(f"Error during legacy memory.json migration: {e}")

    def export_to_legacy_json(self):
        """Exports current memory state back to memory.json for backward compatibility."""
        try:
            export_data: Dict[str, Any] = {}
            with self._get_connection() as conn:
                rows = conn.execute("SELECT key, value_json FROM system_facts").fetchall()
                for r in rows:
                    try:
                        export_data[r["key"]] = json.loads(r["value_json"])
                    except Exception:
                        export_data[r["key"]] = r["value_json"]

            with open(settings.PATHS.LEGACY_MEMORY_FILE, "w", encoding="utf-8") as f:
                json.dump(export_data, f, indent=4)
        except Exception as e:
            error_logger.error(f"Failed to export to legacy memory.json: {e}")

    # ================= CRUD Operations =================

    def set_system_fact(self, key: str, value: Any) -> bool:
        """Stores or updates a system-level fact."""
        now = datetime.utcnow().isoformat()
        try:
            with self._get_connection() as conn:
                conn.execute(
                    "INSERT OR REPLACE INTO system_facts (key, value_json, updated_at) VALUES (?, ?, ?)",
                    (key, json.dumps(value), now)
                )
                conn.commit()
            self.export_to_legacy_json()
            return True
        except Exception as e:
            error_logger.error(f"Error setting system fact '{key}': {e}")
            return False

    def get_system_fact(self, key: str, default: Any = None) -> Any:
        """Retrieves a single system fact by key."""
        try:
            with self._get_connection() as conn:
                row = conn.execute("SELECT value_json FROM system_facts WHERE key = ?", (key,)).fetchone()
                if row:
                    return json.loads(row["value_json"])
        except Exception as e:
            error_logger.error(f"Error getting system fact '{key}': {e}")
        return default

    def get_all_system_facts(self) -> Dict[str, Any]:
        """Returns all system facts as a dictionary."""
        facts = {}
        try:
            with self._get_connection() as conn:
                rows = conn.execute("SELECT key, value_json FROM system_facts").fetchall()
                for r in rows:
                    try:
                        facts[r["key"]] = json.loads(r["value_json"])
                    except Exception:
                        facts[r["key"]] = r["value_json"]
        except Exception as e:
            error_logger.error(f"Error getting all system facts: {e}")
        return facts

    def add_long_term_memory(
        self,
        content: str,
        category: str = "general",
        key: Optional[str] = None,
        importance: int = 1,
        tags: str = "",
    ) -> int:
        """Inserts a new long-term memory entry."""
        now = datetime.utcnow().isoformat()
        try:
            with self._get_connection() as conn:
                cursor = conn.cursor()
                cursor.execute(
                    """
                    INSERT INTO long_term_memories (category, key, content, importance, tags, created_at, updated_at)
                    VALUES (?, ?, ?, ?, ?, ?, ?)
                    """,
                    (category, key or "", content, importance, tags, now, now)
                )
                conn.commit()
                return cursor.lastrowid
        except Exception as e:
            error_logger.error(f"Error adding long term memory: {e}")
            return -1

    def get_all_long_term_memories(self, category: Optional[str] = None) -> List[Dict[str, Any]]:
        """Retrieves all long-term memories or filters by category."""
        try:
            with self._get_connection() as conn:
                if category:
                    rows = conn.execute(
                        "SELECT * FROM long_term_memories WHERE category = ? ORDER BY importance DESC, id DESC",
                        (category,)
                    ).fetchall()
                else:
                    rows = conn.execute(
                        "SELECT * FROM long_term_memories ORDER BY importance DESC, id DESC"
                    ).fetchall()
                return [dict(r) for r in rows]
        except Exception as e:
            error_logger.error(f"Error fetching long-term memories: {e}")
            return []

    def record_episode(
        self,
        task: str,
        outcome: str,
        actions_taken: str = "",
        error: str = "",
        solution: str = "",
    ) -> int:
        """Records an episodic memory of an attempted task and its outcome."""
        now = datetime.utcnow().isoformat()
        try:
            with self._get_connection() as conn:
                cursor = conn.cursor()
                cursor.execute(
                    """
                    INSERT INTO episodic_memories (task, outcome, actions_taken, error, solution, created_at)
                    VALUES (?, ?, ?, ?, ?, ?)
                    """,
                    (task, outcome, actions_taken, error, solution, now)
                )
                conn.commit()
                return cursor.lastrowid
        except Exception as e:
            error_logger.error(f"Error recording episode: {e}")
            return -1

    def get_recent_episodes(self, limit: int = 5) -> List[Dict[str, Any]]:
        """Returns recent episodic task memories."""
        try:
            with self._get_connection() as conn:
                rows = conn.execute(
                    "SELECT * FROM episodic_memories ORDER BY id DESC LIMIT ?",
                    (limit,)
                ).fetchall()
                return [dict(r) for r in rows]
        except Exception as e:
            error_logger.error(f"Error fetching episodes: {e}")
            return []

    def upsert_project(
        self,
        name: str,
        path: str = "",
        language: str = "",
        framework: str = "",
        status: str = "active",
        important_files: Optional[List[str]] = None,
        known_bugs: Optional[List[str]] = None,
        recent_changes: Optional[List[str]] = None,
        metadata: Optional[Dict[str, Any]] = None,
    ) -> bool:
        """Creates or updates a tracked project record."""
        now = datetime.utcnow().isoformat()
        try:
            with self._get_connection() as conn:
                conn.execute(
                    """
                    INSERT INTO project_memories (name, path, language, framework, status, important_files, known_bugs, recent_changes, metadata_json, updated_at)
                    VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?)
                    ON CONFLICT(name) DO UPDATE SET
                        path = excluded.path,
                        language = excluded.language,
                        framework = excluded.framework,
                        status = excluded.status,
                        important_files = excluded.important_files,
                        known_bugs = excluded.known_bugs,
                        recent_changes = excluded.recent_changes,
                        metadata_json = excluded.metadata_json,
                        updated_at = excluded.updated_at
                    """,
                    (
                        name,
                        path,
                        language,
                        framework,
                        status,
                        json.dumps(important_files or []),
                        json.dumps(known_bugs or []),
                        json.dumps(recent_changes or []),
                        json.dumps(metadata or {}),
                        now
                    )
                )
                conn.commit()
            return True
        except Exception as e:
            error_logger.error(f"Error upserting project '{name}': {e}")
            return False

    def get_project(self, name: str) -> Optional[Dict[str, Any]]:
        """Fetches project record by name."""
        try:
            with self._get_connection() as conn:
                row = conn.execute("SELECT * FROM project_memories WHERE name = ?", (name,)).fetchone()
                if row:
                    res = dict(row)
                    res["important_files"] = json.loads(res.get("important_files", "[]"))
                    res["known_bugs"] = json.loads(res.get("known_bugs", "[]"))
                    res["recent_changes"] = json.loads(res.get("recent_changes", "[]"))
                    res["metadata"] = json.loads(res.get("metadata_json", "{}"))
                    return res
        except Exception as e:
            error_logger.error(f"Error fetching project '{name}': {e}")
        return None

    def get_all_projects(self) -> List[Dict[str, Any]]:
        """Returns all recognized projects."""
        try:
            with self._get_connection() as conn:
                rows = conn.execute("SELECT * FROM project_memories ORDER BY updated_at DESC").fetchall()
                result = []
                for r in rows:
                    item = dict(r)
                    item["important_files"] = json.loads(item.get("important_files", "[]"))
                    item["known_bugs"] = json.loads(item.get("known_bugs", "[]"))
                    item["recent_changes"] = json.loads(item.get("recent_changes", "[]"))
                    item["metadata"] = json.loads(item.get("metadata_json", "{}"))
                    result.append(item)
                return result
        except Exception as e:
            error_logger.error(f"Error fetching all projects: {e}")
            return []
