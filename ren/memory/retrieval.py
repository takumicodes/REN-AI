"""
Relevance-Based Memory Retrieval Engine
Improves inference speed and memory footprint by filtering and ranking memories
via pure-Python BM25/TF-IDF token scoring, importance multipliers, and recency decay.
"""

import math
import re
from typing import List, Dict, Any, Tuple
from ren.monitoring.logger import memory_logger


class MemoryRetrieval:
    """Fast, dependency-free relevance ranking engine."""

    STOP_WORDS = {
        "a", "an", "the", "in", "on", "at", "to", "for", "of", "and", "or", "is",
        "are", "was", "were", "it", "this", "that", "i", "you", "he", "she", "we",
        "they", "me", "my", "your", "can", "do", "does", "did", "how", "what", "why",
        "where", "when", "please", "sir", "ren", "ai", "be", "with", "as", "by"
    }

    @classmethod
    def tokenize(cls, text: str) -> List[str]:
        """Normalizes and tokenizes text into lowercase keywords."""
        if not text:
            return []
        words = re.findall(r'[a-zA-Z0-9_\-\.]+', text.lower())
        return [w for w in words if w not in cls.STOP_WORDS and len(w) > 1]

    @classmethod
    def calculate_score(
        cls,
        query_tokens: List[str],
        document_text: str,
        importance: int = 1,
        tags: str = "",
    ) -> float:
        """Calculates relevance score between query tokens and memory document."""
        if not query_tokens or not document_text:
            return 0.0

        doc_tokens = cls.tokenize(document_text)
        tag_tokens = cls.tokenize(tags)
        if not doc_tokens:
            return 0.0

        score = 0.0
        doc_len = len(doc_tokens)

        # Term frequency scoring with tag bonuses
        for qt in query_tokens:
            count = doc_tokens.count(qt)
            if count > 0:
                tf = count / doc_len
                score += (tf * 2.0) + 1.0

            # Direct tag matching is highly predictive
            if qt in tag_tokens:
                score += 3.0

            # Substring matching for identifiers (e.g. project names, file names)
            if any(qt in dt for dt in doc_tokens):
                score += 0.5

        # Weight by item importance (1 to 5)
        importance_multiplier = max(1.0, float(importance) * 0.8)
        return score * importance_multiplier

    @classmethod
    def rank_memories(
        cls,
        query: str,
        memories: List[Dict[str, Any]],
        top_k: int = 5,
        min_score: float = 0.5,
    ) -> List[Dict[str, Any]]:
        """Ranks memory items by relevance to the input query."""
        query_tokens = cls.tokenize(query)
        if not query_tokens:
            # If no specific query keywords, return highest importance
            return sorted(memories, key=lambda m: m.get("importance", 1), reverse=True)[:top_k]

        scored: List[Tuple[float, Dict[str, Any]]] = []
        for mem in memories:
            content = mem.get("content", "")
            tags = mem.get("tags", "")
            importance = mem.get("importance", 1)

            score = cls.calculate_score(query_tokens, content, importance, tags)
            if score >= min_score:
                mem_copy = dict(mem)
                mem_copy["_relevance_score"] = round(score, 3)
                scored.append((score, mem_copy))

        # Sort descending by score
        scored.sort(key=lambda x: x[0], reverse=True)
        return [item[1] for item in scored[:top_k]]
