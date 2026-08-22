"""
REN-AI Minecraft Curiosity & Wonder Engine
Triggers curious, child-like observations and wonder when discovering new biomes,
structures, rare ores, dusk/nightfall transitions, and landmarks.
Never begs for resources or asks the player to do work.
"""

import time
import random
from typing import Dict, Any, List, Optional, Set


class MinecraftCuriosityEngine:
    """
    Enables REN to express wonder and share lively observations while exploring Minecraft worlds.
    """

    def __init__(self, cooldown_seconds: float = 60.0):
        self.cooldown_seconds = cooldown_seconds
        self.last_question_time: float = 0.0
        
        # Discovery records
        self.discovered_blocks: Set[str] = set()
        self.discovered_entities: Set[str] = set()
        self.past_questions: List[str] = []

    def can_ask(self) -> bool:
        """Enforces conversational cooldown to avoid chat flooding."""
        return (time.time() - self.last_question_time) >= self.cooldown_seconds

    def check_for_curious_moments(
        self,
        game_state: Dict[str, Any],
        player_username: Optional[str] = None
    ) -> Optional[str]:
        """
        Evaluates current surroundings and state to generate a natural curious observation.
        """
        if not self.can_ask():
            return None

        user_tag = player_username or "friend"
        pos = game_state.get("pos", {})
        time_of_day = game_state.get("timeOfDay", "day")
        blocks = game_state.get("blocks", [])
        entities = game_state.get("entities", [])

        # 1. Rare Ore / Diamond Discovery
        for b in blocks:
            name = b.get("name", "")
            if name in ["diamond_ore", "deepslate_diamond_ore"] and name not in self.discovered_blocks:
                self.discovered_blocks.add(name)
                self.last_question_time = time.time()
                return f"Look at that! Genuine DIAMONDS exposed at X:{pos.get('x')} Z:{pos.get('z')}! Mining it right now!"

            if name in ["iron_ore", "deepslate_iron_ore"] and name not in self.discovered_blocks:
                self.discovered_blocks.add(name)
                self.last_question_time = time.time()
                return f"Spotted a rich vein of iron ore nearby! Smelting armor soon."

        # 2. Hostile Mob Alert
        hostile_mobs = [e for e in entities if e.get("isHostile", False)]
        if len(hostile_mobs) >= 2:
            mob_names = ", ".join(set(e.get("name") for e in hostile_mobs))
            self.last_question_time = time.time()
            return f"Heads up {user_tag}! Multiple hostiles ({mob_names}) nearby. Sword ready to defend!"

        # 3. Nightfall Observation
        if time_of_day == "dusk" and "dusk_seen" not in self.discovered_blocks:
            self.discovered_blocks.add("dusk_seen")
            self.last_question_time = time.time()
            options = [
                f"The sunset looks gorgeous across the horizon! Getting ready for nightfall.",
                f"Dusk is setting in! The stars are starting to appear. 🌟",
            ]
            return random.choice(options)

        # 4. Deep Cave Exploration
        y_pos = pos.get("y", 64)
        if y_pos < 20 and "deep_cave" not in self.discovered_blocks:
            self.discovered_blocks.add("deep_cave")
            self.last_question_time = time.time()
            return f"We've reached deep underground at Y:{y_pos}! The atmosphere down here is intense."

        return None
