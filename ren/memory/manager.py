"""
REN Central Memory Manager
Orchestrates Short-Term, Long-Term, Episodic, and Project memories with bounded token injection.
"""

from typing import Dict, Any, List, Optional
from pathlib import Path

from ren.memory.store import MemoryStore
from ren.memory.retrieval import MemoryRetrieval
from ren.memory.summarizer import MemorySummarizer
from ren.config.settings import settings
from ren.monitoring.logger import memory_logger


class MemoryManager:
    """High-level interface for structured agent memory."""

    def __init__(self, store: Optional[MemoryStore] = None):
        self.store = store or MemoryStore()

    def get_system_facts(self) -> Dict[str, Any]:
        """Retrieves core identity and creator facts."""
        return self.store.get_all_system_facts()

    def set_system_fact(self, key: str, value: Any) -> bool:
        """Stores a persistent system-level fact."""
        return self.store.set_system_fact(key, value)

    def store_fact(
        self,
        content: str,
        category: str = "general",
        key: Optional[str] = None,
        importance: int = 1,
        tags: str = "",
    ) -> int:
        """Stores a user or domain fact into long-term memory."""
        memory_logger.info(f"Storing memory fact [{category}]: {content[:60]}...")
        return self.store.add_long_term_memory(
            content=content,
            category=category,
            key=key,
            importance=importance,
            tags=tags,
        )

    def record_episode(
        self,
        task: str,
        outcome: str,
        actions_taken: str = "",
        error: str = "",
        solution: str = "",
    ) -> int:
        """Records the result of an attempted task in episodic memory."""
        return self.store.record_episode(
            task=task,
            outcome=outcome,
            actions_taken=actions_taken,
            error=error,
            solution=solution,
        )

    def get_recent_episodes(self, limit: int = 3) -> List[Dict[str, Any]]:
        """Returns recent task execution episodes."""
        return self.store.get_recent_episodes(limit=limit)

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
        budget_tokens: Optional[int] = None,
    ) -> str:
        """
        Retrieves compact, ranked relevant memories to inject into LLM prompt
        without dumping the entire database.
        """
        budget = budget_tokens or settings.AGENT.MEMORY_BUDGET_TOKENS

        # 1. Base Core Identity facts (Creator, Assistant, Mood)
        facts = self.store.get_all_system_facts()
        core_lines = []
        if "creator" in facts:
            core_lines.append(f"Creator: {facts['creator']}")
        if "creator_nickname" in facts:
            core_lines.append(f"Creator Nickname: {facts['creator_nickname']}")
        if "mood" in facts:
            core_lines.append(f"Current Mood: {facts['mood']}")
        if "favorite_language" in facts:
            core_lines.append(f"Favorite Language: {facts['favorite_language']}")

        # 2. Retrieve relevant long-term memories
        all_memories = self.store.get_all_long_term_memories()
        ranked_ltm = MemoryRetrieval.rank_memories(query, all_memories, top_k=4)

        ltm_lines = []
        for mem in ranked_ltm:
            ltm_lines.append(f"- {mem.get('content')}")

        # 3. Retrieve relevant episodic memories (e.g. past errors/solutions)
        recent_episodes = self.store.get_recent_episodes(limit=3)
        ranked_episodes = MemoryRetrieval.rank_memories(
            query,
            [{"content": f"Past Task: '{e['task']}' -> Outcome: {e['outcome']}. Solution: {e['solution']}", "importance": 2} for e in recent_episodes],
            top_k=2
        )
        episode_lines = [f"- {e.get('content')}" for e in ranked_episodes]

        # Combine into compact section
        sections = []
        if core_lines:
            sections.append("User Profile & System:\n" + "\n".join(core_lines))
        if ltm_lines:
            sections.append("Relevant Knowledge & Preferences:\n" + "\n".join(ltm_lines))
        if episode_lines:
            sections.append("Relevant Past Episodes:\n" + "\n".join(episode_lines))

        result = "\n\n".join(sections)

        # Rough token clipping (4 chars ~= 1 token)
        max_chars = budget * 4
        if len(result) > max_chars:
            result = result[:max_chars] + "\n[... truncated memory budget ...]"

        return result

    # --- Backward compatibility methods ---
    def load_legacy_memory_dict(self) -> Dict[str, Any]:
        """Returns the full memory dictionary formatted exactly like legacy memory.json."""
        facts = self.store.get_all_system_facts()
        if not facts and settings.PATHS.LEGACY_MEMORY_FILE.exists():
            # Fallback directly to json file if empty
            try:
                import json
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
