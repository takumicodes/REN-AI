"""
Memory Management Tools
Explicit tools allowing agent to query or store memories during plan execution.
"""

import time
from typing import Dict, Any, Optional

from ren.tools.base import BaseTool, ToolResult
from ren.security.permissions import PermissionCategory
from ren.memory.manager import memory_manager


class QueryMemoryTool(BaseTool):
    name = "query_memory"
    description = "Search long-term memory for facts, preferences, or previous solutions."
    required_permissions = [PermissionCategory.FILESYSTEM_READ]
    parameters_schema = {
        "type": "object",
        "properties": {
            "query": {"type": "string", "description": "Keywords or question to search memory for."}
        },
        "required": ["query"]
    }

    def run(self, query: str, **kwargs) -> ToolResult:
        start_t = time.perf_counter()
        context = memory_manager.get_relevant_memory_context(query)
        if not context:
            context = "No relevant memories found for this query."
        return ToolResult(
            success=True,
            output=context,
            duration=time.perf_counter() - start_t
        )


class RememberFactTool(BaseTool):
    name = "remember_fact"
    description = "Store a new fact, user preference, or project insight into long-term memory."
    required_permissions = [PermissionCategory.FILESYSTEM_WRITE]
    parameters_schema = {
        "type": "object",
        "properties": {
            "fact": {"type": "string", "description": "The information or fact to remember."},
            "category": {"type": "string", "description": "Optional category (e.g. 'preference', 'project', 'knowledge')."},
            "tags": {"type": "string", "description": "Comma-separated keywords/tags."}
        },
        "required": ["fact"]
    }

    def run(self, fact: str, category: str = "general", tags: str = "", **kwargs) -> ToolResult:
        start_t = time.perf_counter()
        mem_id = memory_manager.store_fact(
            content=fact,
            category=category,
            importance=2,
            tags=tags,
        )
        return ToolResult(
            success=True,
            output=f"Stored memory (ID: {mem_id}): {fact}",
            duration=time.perf_counter() - start_t
        )
