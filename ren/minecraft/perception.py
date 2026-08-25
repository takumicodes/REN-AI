"""
REN-AI Minecraft Perception Engine
Transforms raw Mineflayer telemetry into compact, high-value structured world state observations.
"""

from typing import Dict, Any, List, Optional
from ren.minecraft.types import PerceptionSummary


class MinecraftPerceptionEngine:
    """
    Analyzes raw Minecraft world data into high-level tactical and survival intelligence.
    """

    HOSTILE_NAMES = {
        "zombie", "skeleton", "spider", "creeper", "enderman", "witch", "drowned",
        "husk", "phantom", "slime", "pillager", "ravager", "hoglin", "piglin_brute",
        "blaze", "ghast", "magma_cube", "wither_skeleton", "ender_dragon", "wither"
    }

    PASSIVE_NAMES = {
        "cow", "pig", "sheep", "chicken", "rabbit", "horse", "donkey", "llama",
        "goat", "cat", "wolf", "villager", "iron_golem", "squid", "salmon", "cod"
    }

    FOOD_ITEMS = {
        "beef", "porkchop", "mutton", "chicken", "rabbit", "bread", "apple",
        "cooked_beef", "cooked_porkchop", "cooked_mutton", "cooked_chicken",
        "golden_apple", "baked_potato", "carrot"
    }

    def summarize_state(self, raw_state: Dict[str, Any]) -> PerceptionSummary:
        """Constructs a PerceptionSummary from raw bridge telemetry."""
        hp = raw_state.get("hp", 20)
        food = raw_state.get("food", 20)
        pos = raw_state.get("pos", {"x": 0.0, "y": 64.0, "z": 0.0})
        inv = raw_state.get("inventory", {})
        entities = raw_state.get("entities", [])
        time_of_day = raw_state.get("timeOfDay", "day")

        # 1. Inventory Analysis
        total_logs = sum(c for k, c in inv.items() if "log" in k or "wood" in k)
        total_planks = sum(c for k, c in inv.items() if "plank" in k)
        total_cobblestone = inv.get("cobblestone", 0) + inv.get("stone", 0) + inv.get("deepslate", 0)
        total_iron = inv.get("iron_ingot", 0)
        total_food = sum(inv.get(f, 0) for f in self.FOOD_ITEMS)

        total_building_blocks = 0
        for k, v in inv.items():
            if any(b in k for b in ["plank", "dirt", "cobble", "stone", "log", "brick", "sandstone", "wool"]):
                total_building_blocks += v

        has_weapon = any("sword" in k or "mace" in k or "axe" in k for k in inv)
        has_pickaxe = any("pickaxe" in k for k in inv)
        has_axe = any("axe" in k for k in inv)
        has_shield = "shield" in inv

        equipped_weapon = None
        for cand in ["mace", "netherite_sword", "diamond_sword", "iron_sword", "stone_sword", "wooden_sword"]:
            if cand in inv:
                equipped_weapon = cand
                break

        # 2. Entity & Threat Analysis
        hostile_entities = []
        passive_entities = []
        nearest_player = None
        nearest_player_distance = 999.0

        for ent in entities:
            name = ent.get("name", "").lower()
            is_hostile = ent.get("isHostile", False) or any(h in name for h in self.HOSTILE_NAMES)
            is_animal = ent.get("isAnimal", False) or any(p in name for p in self.PASSIVE_NAMES)
            is_player = ent.get("isPlayer", False) or ent.get("type") == "player"
            dist = ent.get("distance", 99.0)

            if is_hostile:
                hostile_entities.append(ent)
            elif is_animal:
                passive_entities.append(ent)

            if is_player and dist < nearest_player_distance:
                nearest_player = ent.get("name")
                nearest_player_distance = dist

        # Threat calculation
        closest_hostile_dist = min((e.get("distance", 99.0) for e in hostile_entities), default=99.0)
        if closest_hostile_dist <= 4.0:
            threat_level = "COMBAT"
        elif closest_hostile_dist <= 12.0 or (time_of_day == "night" and len(hostile_entities) > 0):
            threat_level = "DANGER"
        elif len(hostile_entities) > 0 or time_of_day == "dusk":
            threat_level = "CAUTIOUS"
        else:
            threat_level = "SAFE"

        return PerceptionSummary(
            hp=hp,
            food=food,
            pos=pos,
            inventory=inv,
            total_logs=total_logs,
            total_planks=total_planks,
            total_cobblestone=total_cobblestone,
            total_iron=total_iron,
            total_food=total_food,
            total_building_blocks=total_building_blocks,
            entities=entities,
            hostile_entities=hostile_entities,
            passive_entities=passive_entities,
            nearest_player=nearest_player,
            nearest_player_distance=nearest_player_distance,
            time_of_day=time_of_day,
            threat_level=threat_level,
            has_weapon=has_weapon,
            has_pickaxe=has_pickaxe,
            has_axe=has_axe,
            has_shield=has_shield,
            has_shelter=total_building_blocks >= 16,
            equipped_weapon=equipped_weapon
        )
