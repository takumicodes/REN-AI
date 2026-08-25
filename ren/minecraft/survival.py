"""
REN-AI Minecraft Priority-Based Autonomous Survival Controller 11.0
Implements a strict priority hierarchy (CRITICAL -> HIGH -> MEDIUM -> LOW) for genuine in-game survival.
Prioritizes life preservation, tool crafting mastery, combat defense, shelter, and resource independence.
"""

from typing import Dict, Any, Optional, List, Tuple
from ren.minecraft.types import PerceptionSummary, SurvivalPriority, Subtask
from ren.monitoring.logger import agent_logger


class MinecraftSurvivalEngine:
    """
    State machine and decision tree governing independent Minecraft survival.
    """

    def decide_next_survival_action(
        self,
        perception: PerceptionSummary,
        has_built_home: bool = False
    ) -> Tuple[Optional[Dict[str, Any]], SurvivalPriority, str]:
        """
        Evaluates world state through the strict priority hierarchy.
        Returns: (action_dict: Optional[Dict], priority: SurvivalPriority, rationale: str)
        """
        hp = perception.hp
        food = perception.food
        time_of_day = perception.time_of_day
        threat = perception.threat_level
        inv = perception.inventory

        # ==========================================
        # 1. CRITICAL PRIORITY (Life Preservation)
        # ==========================================

        # 1.1 Emergency Eating (Starvation or Low Health healing)
        if (food < 10 or (hp < 16 and food < 18)) and perception.total_food > 0:
            return {"cmd": "eat", "args": {}}, SurvivalPriority.CRITICAL, "Critical hunger/healing required"

        # 1.2 Dangerous Low Health Combat / Escape
        if threat in ["COMBAT", "DANGER"] and len(perception.hostile_entities) > 0:
            closest_mob = min(perception.hostile_entities, key=lambda e: e.get("distance", 99.0))
            mob_name = closest_mob.get("name", "zombie")
            dist = closest_mob.get("distance", 99.0)

            # If unarmed or critically wounded, flee from dangerous mobs (witches, skeletons, creepers)
            if hp <= 8 or (not perception.has_weapon and dist > 3.0):
                flee_x = perception.pos["x"] + (15 if closest_mob.get("position", {}).get("x", 0) < perception.pos["x"] else -15)
                flee_z = perception.pos["z"] + (15 if closest_mob.get("position", {}).get("z", 0) < perception.pos["z"] else -15)
                return {"cmd": "goTo", "args": {"x": flee_x, "y": perception.pos["y"], "z": flee_z}}, SurvivalPriority.CRITICAL, f"Tactical retreat from {mob_name} (low HP/unarmed)"

            # Engage hostile mob with weapon & shield
            return {"cmd": "attack", "args": {"target_name": mob_name}}, SurvivalPriority.CRITICAL, f"Eliminating nearby hostile: {mob_name}"

        # ==========================================
        # 2. HIGH PRIORITY (Shelter, Tools & Food)
        # ==========================================

        # 2.1 Nightfall / Dusk Shelter Construction & Sleep
        if time_of_day in ["dusk", "night"]:
            if "white_bed" in inv or "bed" in inv:
                return {"cmd": "sleep", "args": {}}, SurvivalPriority.HIGH, "Sleeping through the dangerous night"
            elif not has_built_home:
                if perception.total_building_blocks >= 12:
                    return {"cmd": "build_shelter", "args": {"size": 3}}, SurvivalPriority.HIGH, "Building nightfall survival shelter"
                else:
                    return {"cmd": "gather", "args": {"block_type": "dirt", "count": 6}}, SurvivalPriority.HIGH, "Gathering blocks for emergency shelter"

        # 2.2 Food Depletion Warning
        if food < 14 and perception.total_food == 0:
            return {"cmd": "hunt", "args": {"animal_name": "animal", "count": 2}}, SurvivalPriority.HIGH, "Hunting for sustenance"

        # 2.3 Tier 1 Tool Acquisition (Wood -> Planks -> Crafting Table -> Sticks -> Wooden Pickaxe)
        if not perception.has_pickaxe:
            if perception.total_logs == 0 and perception.total_planks < 4:
                return {"cmd": "gather", "args": {"block_type": "wood", "count": 4}}, SurvivalPriority.HIGH, "Chopping wood for initial tools"
            if perception.total_planks < 4 and perception.total_logs > 0:
                return {"cmd": "craft", "args": {"item_name": "oak_planks", "count": min(perception.total_logs, 3)}}, SurvivalPriority.HIGH, "Crafting wood planks"
            if "crafting_table" not in inv:
                return {"cmd": "craft", "args": {"item_name": "crafting_table", "count": 1}}, SurvivalPriority.HIGH, "Crafting workbench"
            if inv.get("stick", 0) < 2:
                return {"cmd": "craft", "args": {"item_name": "stick", "count": 1}}, SurvivalPriority.HIGH, "Crafting sticks for tools"
            return {"cmd": "craft", "args": {"item_name": "wooden_pickaxe", "count": 1}}, SurvivalPriority.HIGH, "Crafting wooden pickaxe"

        # 2.4 Tier 2 Tool & Weapon Acquisition (Stone Pickaxe & Sword)
        has_stone_pickaxe = any(k in inv for k in ["stone_pickaxe", "iron_pickaxe", "diamond_pickaxe"])
        if not has_stone_pickaxe:
            if perception.total_cobblestone < 6:
                return {"cmd": "gather", "args": {"block_type": "stone", "count": 6}}, SurvivalPriority.HIGH, "Mining cobblestone for stone tier"
            if "crafting_table" not in inv:
                return {"cmd": "craft", "args": {"item_name": "crafting_table", "count": 1}}, SurvivalPriority.HIGH, "Placing crafting table"
            if inv.get("stick", 0) < 2:
                return {"cmd": "craft", "args": {"item_name": "stick", "count": 1}}, SurvivalPriority.HIGH, "Crafting sticks for stone pickaxe"
            return {"cmd": "craft", "args": {"item_name": "stone_pickaxe", "count": 1}}, SurvivalPriority.HIGH, "Upgrading to stone pickaxe"

        if not perception.has_weapon:
            if perception.total_cobblestone >= 2:
                return {"cmd": "craft", "args": {"item_name": "stone_sword", "count": 1}}, SurvivalPriority.HIGH, "Crafting stone sword for defense"
            else:
                return {"cmd": "gather", "args": {"block_type": "stone", "count": 4}}, SurvivalPriority.HIGH, "Gathering stone for weapon"

        # ==========================================
        # 3. MEDIUM PRIORITY (Settlement & Iron Age)
        # ==========================================

        # 3.1 Furnace Crafting & Cooking Food
        if "furnace" not in inv and perception.total_cobblestone >= 8:
            return {"cmd": "craft", "args": {"item_name": "furnace", "count": 1}}, SurvivalPriority.MEDIUM, "Crafting furnace for smelting"

        raw_meat = sum(inv.get(k, 0) for k in ["beef", "porkchop", "mutton", "chicken"])
        if raw_meat > 0 and "furnace" in inv:
            fuel = "coal" if "coal" in inv else "oak_planks"
            raw_type = "beef" if "beef" in inv else ("porkchop" if "porkchop" in inv else "mutton")
            return {"cmd": "smelt", "args": {"item": raw_type, "fuel": fuel, "count": raw_meat}}, SurvivalPriority.MEDIUM, f"Cooking {raw_meat}x {raw_type} rations"

        # 3.2 Permanent Base Construction
        if not has_built_home and perception.total_building_blocks >= 16:
            return {"cmd": "build_shelter", "args": {"size": 3}}, SurvivalPriority.MEDIUM, "Constructing permanent base shelter"

        # 3.3 Iron Progression
        raw_iron = inv.get("raw_iron", 0) + inv.get("iron_ore", 0)
        iron_ingots = perception.total_iron

        if iron_ingots >= 3 and "iron_pickaxe" not in inv:
            return {"cmd": "craft", "args": {"item_name": "iron_pickaxe", "count": 1}}, SurvivalPriority.MEDIUM, "Crafting iron pickaxe"
        elif iron_ingots >= 1 and not perception.has_shield:
            return {"cmd": "craft", "args": {"item_name": "shield", "count": 1}}, SurvivalPriority.MEDIUM, "Crafting shield for combat defense"
        elif iron_ingots >= 2 and "iron_sword" not in inv:
            return {"cmd": "craft", "args": {"item_name": "iron_sword", "count": 1}}, SurvivalPriority.MEDIUM, "Crafting iron sword for combat"
        elif (raw_iron + iron_ingots) < 4:
            return {"cmd": "gather", "args": {"block_type": "iron_ore", "count": 4}}, SurvivalPriority.MEDIUM, "Mining iron ore for armor/shield"
        elif raw_iron > 0 and "furnace" in inv:
            fuel = "coal" if "coal" in inv else "oak_planks"
            return {"cmd": "smelt", "args": {"item": "raw_iron", "fuel": fuel, "count": raw_iron}}, SurvivalPriority.MEDIUM, "Smelting raw iron"

        # 3.4 Food Stockpiling
        if perception.total_food < 4:
            return {"cmd": "hunt", "args": {"animal_name": "animal", "count": 2}}, SurvivalPriority.MEDIUM, "Hunting to replenish rations"

        # ==========================================
        # 4. LOW PRIORITY (Exploration & Resource Expansion)
        # ==========================================

        # General wood/stone stockpiling
        if perception.total_logs < 4:
            return {"cmd": "gather", "args": {"block_type": "wood", "count": 4}}, SurvivalPriority.LOW, "Harvesting timber stockpile"

        # Exploration
        import random
        dx = random.randint(-16, 16)
        dz = random.randint(-16, 16)
        target_pos = {
            "x": perception.pos["x"] + dx,
            "y": perception.pos["y"],
            "z": perception.pos["z"] + dz
        }
        return {"cmd": "goTo", "args": target_pos}, SurvivalPriority.LOW, "Scouting terrain and resources"
