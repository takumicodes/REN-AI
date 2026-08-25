"""
REN Central Memory Manager
Orchestrates Short-Term, Long-Term, Episodic, and Project memories with bounded token injection.
Syncs bidirectional changes with memory.json and injects comprehensive creator/assistant identity facts.
"""

import json
from typing import Dict, Any, List, Optional
from pathlib import Path

from ren.memory.store import MemoryStore
from ren.memory.retrieval import MemoryRetrieval
from ren.memory.summarizer import MemorySummarizer
from ren.config.settings import settings
from ren.monitoring.logger import memory_logger, error_logger


class MemoryManager:
    """High-level interface for structured agent memory."""

    def __init__(self, store: Optional[MemoryStore] = None):
        self.store = store or MemoryStore()
        # Automatically sync memory.json if present
        self.sync_from_legacy_json()

    def sync_from_legacy_json(self):
        """Ensures all fields in memory.json are loaded into system_facts."""
        legacy_file = settings.PATHS.LEGACY_MEMORY_FILE
        if legacy_file.exists():
            try:
                with open(legacy_file, "r", encoding="utf-8") as f:
                    data = json.load(f)
                for k, v in data.items():
                    self.store.set_system_fact(k, v)
            except Exception as e:
                error_logger.debug(f"MemoryManager json sync note: {e}")

    def get_system_facts(self) -> Dict[str, Any]:
        """Retrieves core identity and creator facts."""
        self.sync_from_legacy_json()
        return self.store.get_all_system_facts()

    def set_system_fact(self, key: str, value: Any) -> bool:
        """Stores a persistent system-level fact and updates memory.json."""
        res = self.store.set_system_fact(key, value)
        self.store.export_to_legacy_json()
        return res

    def store_fact(
        self,
        content: str,
        category: str = "general",
        key: Optional[str] = None,
        importance: int = 1,
        tags: str = "",
        user_id: str = "default",
    ) -> int:
        """Stores a user or domain fact into long-term memory."""
        memory_logger.info(f"Storing memory fact [{category}] for user '{user_id}': {content[:60]}...")
        return self.store.add_long_term_memory(
            content=content,
            category=category,
            key=key,
            importance=importance,
            tags=tags,
            user_id=user_id,
        )

    def record_episode(
        self,
        task: str,
        outcome: str,
        actions_taken: str = "",
        error: str = "",
        solution: str = "",
        user_id: str = "default",
    ) -> int:
        """Records the result of an attempted task in episodic memory."""
        return self.store.record_episode(
            task=task,
            outcome=outcome,
            actions_taken=actions_taken,
            error=error,
            solution=solution,
            user_id=user_id,
        )

    def get_recent_episodes(self, limit: int = 3, user_id: str = "default") -> List[Dict[str, Any]]:
        """Returns recent task execution episodes for user."""
        return self.store.get_recent_episodes(limit=limit, user_id=user_id)

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
        """Updates persistent project profile."""
        return self.store.upsert_project(
            name=name,
            path=path,
            language=language,
            framework=framework,
            status=status,
            important_files=important_files,
            known_bugs=known_bugs,
            recent_changes=recent_changes,
            metadata=metadata,
        )

    def get_project(self, name: str) -> Optional[Dict[str, Any]]:
        """Retrieves project memory profile."""
        return self.store.get_project(name)

    def get_all_projects(self) -> List[Dict[str, Any]]:
        """Lists all known projects."""
        return self.store.get_all_projects()

    def get_relevant_memory_context(
        self,
        query: str,
        user_id: str = "default",
        budget_tokens: Optional[int] = None,
    ) -> str:
        """
        Retrieves compact, rich identity facts and relevant memories for the prompt.
        """
        budget = budget_tokens or settings.AGENT.MEMORY_BUDGET_TOKENS
        self.sync_from_legacy_json()

        # 1. Base Core Identity & Creator Profile from memory.json / system_facts
        facts = self.store.get_all_system_facts()
        core_lines = []

        creator = facts.get("creator", "Sadiq")
        nickname = facts.get("creator_nickname", "Cyan Code")
        assistant = facts.get("assistant_name", "Ren")
        yt_channel = facts.get("youtube_channel", "Cyan Code")

        core_lines.append(f"- Assistant Name: {assistant}")
        core_lines.append(f"- Creator: {creator} (also known as {nickname})")
        core_lines.append(f"- YouTube Channel: {yt_channel}")

        if "favorite_language" in facts:
            core_lines.append(f"- Favorite Language: {facts['favorite_language']}")
        if "mood" in facts:
            core_lines.append(f"- Current Mood: {facts['mood']}")

        # Projects
        if "current_projects" in facts and isinstance(facts["current_projects"], list):
            core_lines.append(f"- Current Projects: {', '.join(facts['current_projects'])}")

        # Skills & Expertise
        if "skills" in facts and isinstance(facts["skills"], list):
            core_lines.append(f"- Creator Skills & Expertise: {', '.join(facts['skills'])}")

        # Computer Hardware
        if "computer" in facts and isinstance(facts["computer"], dict):
            c = facts["computer"]
            core_lines.append(f"- Computer / Hardware: RAM: {c.get('ram')}, OS: {c.get('os')}, Storage: {c.get('storage')}")

        # YouTube Videos
        if "youtube_videos" in facts and isinstance(facts["youtube_videos"], list):
            vid_titles = [v.get("title", "") for v in facts["youtube_videos"] if isinstance(v, dict)]
            if vid_titles:
                core_lines.append(f"- Recent YouTube Uploads: {'; '.join(vid_titles[:3])}")

        # Dream Insights
        if "learned_from_dreams" in facts and isinstance(facts["learned_from_dreams"], list):
            core_lines.append(f"- Dream Insights: {'; '.join(facts['learned_from_dreams'][:2])}")

        # Any extra key-value pairs
        for k, v in facts.items():
            if k not in [
                "creator", "creator_nickname", "assistant_name", "youtube_channel",
                "favorite_language", "mood", "current_projects", "skills",
                "computer", "youtube_videos", "learned_from_dreams"
            ]:
                core_lines.append(f"- {k}: {v}")

        # 2. Retrieve relevant long-term memories strictly for this user
        all_memories = self.store.get_all_long_term_memories(user_id=user_id)
        ranked_ltm = MemoryRetrieval.rank_memories(query, all_memories, top_k=4)

        ltm_lines = []
        for mem in ranked_ltm:
            ltm_lines.append(f"- {mem.get('content')}")

        # 3. Retrieve relevant episodic memories (filtering out invalid or corrupted entries)
        recent_episodes = self.store.get_recent_episodes(limit=3, user_id=user_id)
        valid_episodes = [
            e for e in recent_episodes
            if "alibaba" not in e.get("solution", "").lower() and "qwen" not in e.get("solution", "").lower()
        ]
        ranked_episodes = MemoryRetrieval.rank_memories(
            query,
            [{"content": f"Past Task: '{e['task']}' -> Outcome: {e['outcome']}. Solution: {e['solution']}", "importance": 2} for e in valid_episodes],
            top_k=2
        )
        episode_lines = [f"- {e.get('content')}" for e in ranked_episodes]

        # Combine into structured section
        sections = []
        if core_lines:
            sections.append("[Memory: Identity, Creator & Projects Profile]\n" + "\n".join(core_lines))
        if ltm_lines:
            sections.append("[Relevant Knowledge & Preferences]\n" + "\n".join(ltm_lines))
        if episode_lines:
            sections.append("[Relevant Past Episodes]\n" + "\n".join(episode_lines))

        result = "\n\n".join(sections)

        # Token budget clipping
        max_chars = budget * 4
        if len(result) > max_chars:
            result = result[:max_chars] + "\n[... truncated memory budget ...]"

        return result

    # --- Backward compatibility methods ---
    def load_legacy_memory_dict(self) -> Dict[str, Any]:
        """Returns the full memory dictionary formatted exactly like legacy memory.json."""
        facts = self.store.get_all_system_facts()
        if not facts and settings.PATHS.LEGACY_MEMORY_FILE.exists():
            try:
                with open(settings.PATHS.LEGACY_MEMORY_FILE, "r", encoding="utf-8") as f:
                    return json.load(f)
            except Exception:
                pass
        return facts

    def save_legacy_memory_dict(self, memory_dict: Dict[str, Any]) -> bool:
        """Saves a legacy full dictionary into SQLite and syncs memory.json."""
        for k, v in memory_dict.items():
            self.store.set_system_fact(k, v)
        self.store.export_to_legacy_json()
        return True


# Global manager singleton
memory_manager = MemoryManager()
