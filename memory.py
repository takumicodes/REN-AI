"""
REN Memory Bridge (Backward Compatible Interface)
Connects legacy load_memory/save_memory calls to the SQLite-backed MemoryManager.
"""

from typing import Dict, Any
from ren.memory.manager import memory_manager


def load_memory() -> Dict[str, Any]:
    """Loads memory dictionary from the SQLite MemoryManager."""
    return memory_manager.load_legacy_memory_dict()


def save_memory(memory_dict: Dict[str, Any]) -> bool:
    """Saves memory dictionary through SQLite MemoryManager and syncs memory.json."""
    return memory_manager.save_legacy_memory_dict(memory_dict)