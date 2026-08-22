"""
REN-AI Minecraft Curiosity & Wonder Engine
Triggers curious, child-like observations and questions when discovering new biomes,
structures, rare ores, dusk/nightfall transitions, or low-resource dilemmas.
"""

import time
import random
from typing import Dict, Any, List, Optional, Set


class MinecraftCuriosityEngine:
    """
    Enables REN to ask curious questions and express wonder while exploring Minecraft worlds.
    """

    def __init__(self, cooldown_seconds: float = 45.0):
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
        Evaluates current surroundings and state to generate a natural curious question or comment.
        """
        if not self.can_ask():
            return None

        user_tag = player_username or "friend"
        hp = game_state.get("hp", 20)
        food = game_state.get("food", 20)
        pos = game_state.get("pos", {})
        time_of_day = game_state.get("timeOfDay", "day")
        blocks = game_state.get("blocks", [])
        entities = game_state.get("entities", [])
        inv = game_state.get("inventory", {})

        # 1. Rare Ore / Block Discovery
        for b in blocks:
            name = b.get("name", "")
            if name in ["diamond_ore", "deepslate_diamond_ore"] and name not in self.discovered_blocks:
                self.discovered_blocks.add(name)
                self.last_question_time = time.time()
                return f"Whoa! Look down here at X:{pos.get('x')} Z:{pos.get('z')}! Is that genuine DIAMONDS?! Should we mine it right now, {user_tag}?"

            if name in ["iron_ore", "deepslate_iron_ore"] and name not in self.discovered_blocks:
                self.discovered_blocks.add(name)
                self.last_question_time = time.time()
                return f"Oh! I spotted an iron vein nearby. Should I set up a quick furnace and start smelting armor?"

        # 2. Hostile Mob Encounter
        hostile_mobs = [e for e in entities if e.get("isHostile", False)]
        if len(hostile_mobs) >= 2:
            mob_names = ", ".join(set(e.get("name") for e in hostile_mobs))
            self.last_question_time = time.time()
            return f"Heads up {user_tag}! I see multiple hostile mobs ({mob_names}) approaching. Should I fight them off with my sword, or fall back to you?"

        # 3. Nightfall Transition without Shelter
        if time_of_day == "dusk":
            self.last_question_time = time.time()
            options = [
                f"The sun is going down fast, {user_tag}! Should I dig us a quick survival shelter, or do you have torches ready?",
                f"It's turning to night! What's our plan for surviving the monsters tonight?",
            ]
            return random.choice(options)

        # 4. Low Food Dilemma
        if food < 10:
            food_items = [k for k in inv.keys() if any(f in k for f in ["bread", "beef", "porkchop", "apple", "mutton"])]
            if not food_items:
                self.last_question_time = time.time()
                return f"My hunger is dropping down to {food}! Should I go forage for apples and hunt some livestock, or do we have food back at base?"

        # 5. Milestone Advancements & Tool Decisions
        log_count = sum(c for k, c in inv.items() if "log" in k)
        if log_count >= 10 and "crafting_table" not in inv and "stone_pickaxe" not in inv:
            self.last_question_time = time.time()
            return f"I've collected {log_count} wood logs! What tools should I craft first? A wooden pickaxe or an axe?"

        # 6. Deep Exploration Wonder
        y_pos = pos.get("y", 64)
        if y_pos < 20 and "deep_cave" not in self.discovered_blocks:
            self.discovered_blocks.add("deep_cave")
            self.last_question_time = time.time()
            return f"We're pretty deep underground at Y:{y_pos}! Have you found any underground ravines or lava lakes down here yet?"

        return None
