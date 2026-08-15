"""
Skill Router
Routes incoming user requests to relevant skills via token matching, capability tags, and triggers.
"""

from typing import List, Dict, Any, Tuple
from ren.skills.registry import skill_registry, Skill
from ren.memory.retrieval import MemoryRetrieval


class SkillRouter:
    """Selects one or more relevant skills for a given user prompt."""

    @classmethod
    def select_skills(cls, query: str, top_k: int = 3) -> List[Skill]:
        """Matches user query against skill triggers and capabilities."""
        query_tokens = MemoryRetrieval.tokenize(query)
        if not query_tokens:
            return []

        active_skills = skill_registry.get_active_skills()
        scored: List[Tuple[float, Skill]] = []

        for skill in active_skills:
            score = 0.0
            meta = skill.metadata

            # Match triggers
            for t in meta.triggers:
                t_tokens = MemoryRetrieval.tokenize(t)
                if any(qt in t_tokens for qt in query_tokens):
                    score += 3.0

            # Match capabilities
            for c in meta.capabilities:
                c_tokens = MemoryRetrieval.tokenize(c)
                if any(qt in c_tokens for qt in query_tokens):
                    score += 2.5

            # Match description
            desc_tokens = MemoryRetrieval.tokenize(meta.description)
            for qt in query_tokens:
                if qt in desc_tokens:
                    score += 1.0

            # Direct name token match
            name_tokens = MemoryRetrieval.tokenize(meta.name)
            if any(qt in name_tokens for qt in query_tokens):
                score += 3.5

            if score > 1.0:
                scored.append((score, skill))

        scored.sort(key=lambda x: x[0], reverse=True)
        return [item[1] for item in scored[:top_k]]
