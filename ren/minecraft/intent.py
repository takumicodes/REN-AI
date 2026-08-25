"""
REN-AI Minecraft Natural Language Intent Parser
Parses natural language chat and user directives into structured Goal models.
Employs instant keyword & synonym matching, skill aliases, typo normalization, and LLM fallback extraction.
"""

import re
import json
import time
from typing import Dict, Any, Optional

from ren.minecraft.types import Goal
from ren.minecraft.skills import MinecraftSkillRegistry
from ren.models import get_model_provider
from ren.monitoring.logger import agent_logger


class MinecraftIntentParser:
    """
    Robust Natural Language Intent Parser for Minecraft commands.
    """

    TYPO_CORRECTIONS = {
        "cooble": "cobble",
        "cooblestone": "cobblestone",
        "coblestone": "cobblestone",
        "cobbleston": "cobblestone",
        "wooood": "wood",
        "woodd": "wood",
        "iiron": "iron",
        "diamon": "diamond",
        "diamod": "diamond",
        "hous": "house",
        "hom": "home",
        "bridgig": "bridging",
        "bridgin": "bridging",
        "wincharge": "wind_charge",
        "windcharge": "wind_charge",
        "her": "here",
        "itmes": "items",
        "fod": "food",
        "villag": "village",
        "furnis": "furnace",
        "speeedrun": "speedrun",
        "speedun": "speedrun",
        "speerun": "speedrun",
        "spedrun": "speedrun"
    }

    def __init__(self, skill_registry: Optional[MinecraftSkillRegistry] = None):
        self.skill_registry = skill_registry or MinecraftSkillRegistry()
        self.provider = get_model_provider()

    def normalize_text(self, text: str) -> str:
        """Applies typo corrections and cleans text."""
        t = text.lower().strip()
        for k, v in self.TYPO_CORRECTIONS.items():
            t = re.sub(rf"\b{re.escape(k)}\b", v, t)
        return t

    def parse_intent(self, text: str, player_name: str = "Player") -> Goal:
        """
        Translates natural language text into a structured Goal.
        Fast path with priority-based matching, fallback to LLM only when ambiguous.
        """
        normalized = self.normalize_text(text)

        # 1. Stop / Freeze
        if any(w in normalized for w in ["stop", "halt", "stay here", "wait here", "pause", "freeze", "cancel", "hold up"]):
            return Goal(goal_type="STOP", parameters={}, raw_text=text, target_player=player_name, priority=100, created_at=time.time())

        # 1.1 Self-Test & Diagnostics
        if any(w in normalized for w in ["self test", "run self test", "minecraft self test", "run diagnostics", "test yourself", "system test"]):
            return Goal(goal_type="SELF_TEST", parameters={}, raw_text=text, target_player=player_name, priority=95, created_at=time.time())

        # 2. Speedrun Mode
        if re.search(r"\b(speedrun|speed\s*run|beat\s+the\s+game|world\s*record)\b", normalized):
            return Goal(goal_type="SPEEDRUN", parameters={}, raw_text=text, target_player=player_name, priority=90, created_at=time.time())

        # 3. Autonomous Survival Mode
        if re.search(r"\b(survive|survival|auto\s*mode|auto\s*survival|independent|play\s+alone|be\s+independent|play\s+on\s+your\s+own)\b", normalized):
            return Goal(goal_type="AUTONOMOUS_SURVIVAL", parameters={}, raw_text=text, target_player=player_name, priority=90, created_at=time.time())

        # 4. Drop All / Inventory Dump
        if any(w in normalized for w in ["give all", "drop all", "dump inventory", "give everything", "drop everything", "give all materials"]):
            return Goal(goal_type="DROP_ALL", parameters={"player": player_name}, raw_text=text, target_player=player_name, priority=85, created_at=time.time())

        # 5. Status Check
        if any(w in normalized for w in ["status", "where are you", "hp", "health", "inventory", "what do you have", "bag", "coords", "how are you"]):
            return Goal(goal_type="STATUS", parameters={}, raw_text=text, target_player=player_name, priority=80, created_at=time.time())

        # 6. Gamemode
        if any(w in normalized for w in ["mode", "gamemode", "change mode", "set mode"]):
            mode = "creative" if "creative" in normalized else "survival"
            return Goal(goal_type="GAMEMODE", parameters={"mode": mode}, raw_text=text, target_player=player_name, created_at=time.time())

        # 7. House / Shelter Building
        if any(w in normalized for w in ["make house", "build house", "make a house", "build a house", "build me a house", "make me a house", "make home", "build home", "small wooden house", "make base", "build base"]):
            return Goal(goal_type="BUILD_HOUSE", parameters={"structure_type": "small_house", "material": "wooden", "size": "small"}, raw_text=text, target_player=player_name, created_at=time.time())

        if any(w in normalized for w in ["make shelter", "build shelter", "make a shelter", "build a shelter", "shelter before night", "quick shelter", "small home fast", "emergency shelter", "make a shelter to survive"]):
            return Goal(goal_type="BUILD_SHELTER", parameters={"structure_type": "shelter", "size": "compact"}, raw_text=text, target_player=player_name, created_at=time.time())

        # 8. Hunt Animals / Food Harvesting (Evaluated BEFORE generic gathering)
        if any(w in normalized for w in ["hunt", "kill animals", "slaughter", "slay animals", "butcher", "get food", "find food", "gather food"]) or (
            any(w in normalized for w in ["cow", "pig", "sheep", "chicken", "rabbit", "animals"]) and "kill" in normalized
        ):
            count = 2
            m = re.search(r"\b(\d+)\b", normalized)
            if m: count = int(m.group(1))
            animal = "animal"
            for a in ["cow", "pig", "sheep", "chicken", "rabbit"]:
                if a in normalized:
                    animal = a
                    break
            return Goal(goal_type="HUNT_FOOD", parameters={"animal_name": animal, "count": count}, raw_text=text, target_player=player_name, created_at=time.time())

        # 9. Resource Gathering (Chop, Mine, Dig, Harvest, Collect, Get)
        if any(w in normalized for w in ["gather", "mine", "chop", "dig", "cut", "harvest", "collect", "get", "find", "fetch", "need"]) and any(w in normalized for w in ["wood", "tree", "trees", "log", "logs", "stone", "cobble", "cobblestone", "iron", "coal", "diamond", "dirt", "sand", "gravel", "ore", "birch", "oak", "spruce"]):
            count = 4
            m = re.search(r"\b(\d+)\b", normalized)
            if m: count = int(m.group(1))

            target = "wood"
            if any(w in normalized for w in ["iron", "iron_ore"]): target = "iron_ore"
            elif any(w in normalized for w in ["coal", "coal_ore"]): target = "coal_ore"
            elif any(w in normalized for w in ["diamond"]): target = "diamond_ore"
            elif any(w in normalized for w in ["stone", "cobble", "deepslate", "cobblestone"]): target = "stone"
            elif any(w in normalized for w in ["dirt", "sand", "gravel"]): target = "dirt"
            elif any(w in normalized for w in ["wood", "tree", "trees", "log", "logs", "birch", "oak", "spruce"]): target = "wood"

            return Goal(goal_type="COLLECT_RESOURCE", parameters={"resource": target, "amount": count}, raw_text=text, target_player=player_name, created_at=time.time())

        # 10. Crafting Items & Tools
        if any(w in normalized for w in ["craft", "make", "create", "build"]) and any(w in normalized for w in ["pickaxe", "sword", "axe", "shovel", "table", "furnace", "torch", "torches", "chest", "bed", "shield", "door", "planks", "tools", "mace"]):
            item = "crafting_table"
            for it in ["mace", "stone_pickaxe", "wooden_pickaxe", "iron_pickaxe", "stone_sword", "iron_sword", "crafting_table", "furnace", "torch", "shield", "chest", "white_bed", "bed", "oak_planks"]:
                if it.replace("_", " ") in normalized or it in normalized:
                    item = it
                    break
            count = 1
            m = re.search(r"\b(\d+)\b", normalized)
            if m: count = int(m.group(1))
            return Goal(goal_type="CRAFT_ITEM", parameters={"item_name": item, "count": count}, raw_text=text, target_player=player_name, created_at=time.time())

        # 10. Smelt / Cook / Furnace
        if any(w in normalized for w in ["smelt", "cook", "bake", "furnace", "melt"]):
            raw_item = "raw_iron" if "iron" in normalized else "beef"
            return Goal(goal_type="SMELT_ITEM", parameters={"item": raw_item, "fuel": "coal", "count": 2}, raw_text=text, target_player=player_name, created_at=time.time())

        # 11. Give / Drop Items
        if any(w in normalized for w in ["give me all", "drop everything", "drop all", "give all"]):
            return Goal(goal_type="DROP_ALL", parameters={"player": player_name}, raw_text=text, target_player=player_name, created_at=time.time())

        if any(w in normalized for w in ["give", "drop", "toss", "share", "pass", "hand", "throw", "spare"]):
            count = 2
            m = re.search(r"\b(\d+)\b", normalized)
            if m: count = int(m.group(1))
            item = "wood"
            for cand in ["mace", "wind_charge", "iron", "iron_ingot", "coal", "wood", "oak_log", "stone", "cobblestone", "dirt", "bread", "beef", "porkchop", "apple", "sword", "pickaxe", "axe", "torch", "food"]:
                if cand.replace("_", " ") in normalized or cand in normalized:
                    item = cand
                    break
            return Goal(goal_type="GIVE_ITEM", parameters={"player": player_name, "item_name": item, "count": count}, raw_text=text, target_player=player_name, created_at=time.time())

        # 12. PVP / Combat Duel
        if any(w in normalized for w in ["pvp", "fight with me", "fight me", "kill me", "duel", "attack me"]):
            return Goal(goal_type="PVP_COMBAT", parameters={"player": player_name}, raw_text=text, target_player=player_name, created_at=time.time())

        # 13. Attack Hostile Mobs
        if any(w in normalized for w in ["attack", "kill", "fight", "slay", "destroy", "clear"]) and any(w in normalized for w in ["zombie", "skeleton", "spider", "creeper", "drowned", "enderman", "witch", "mob", "monster", "mobs"]):
            target = "zombie"
            for m in ["skeleton", "spider", "creeper", "drowned", "enderman", "witch", "zombie"]:
                if m in normalized:
                    target = m
                    break
            return Goal(goal_type="ATTACK_MOBS", parameters={"target_name": target}, raw_text=text, target_player=player_name, created_at=time.time())

        # 14. Defend / Protect
        if any(w in normalized for w in ["defend", "protect", "guard", "bodyguard", "watch my back"]):
            return Goal(goal_type="PROTECT_PLAYER", parameters={"player": player_name}, raw_text=text, target_player=player_name, created_at=time.time())

        # 15. Follow / Navigation
        if any(w in normalized for w in ["come", "follow", "walk with", "to me", "behind me", "near me", "with me", "here", "over here", "stay near"]):
            return Goal(goal_type="FOLLOW_PLAYER", parameters={"player": player_name}, raw_text=text, target_player=player_name, created_at=time.time())

        # 16. Pickup / Take
        if any(w in normalized for w in ["take this", "pickup", "pick up", "take sword", "take item", "collect drops"]):
            return Goal(goal_type="PICKUP", parameters={}, raw_text=text, target_player=player_name, created_at=time.time())

        # 17. Bridging
        if any(w in normalized for w in ["bridging", "bridge", "make a bridge", "do bridging"]):
            mat = "wool" if "wool" in normalized else "planks"
            return Goal(goal_type="BRIDGE", parameters={"length": 8, "material": mat}, raw_text=text, target_player=player_name, created_at=time.time())

        # 18. Sleep
        if any(w in normalized for w in ["sleep", "go to bed", "bed", "sleep now", "night time"]):
            return Goal(goal_type="SLEEP", parameters={}, raw_text=text, target_player=player_name, created_at=time.time())

        # Fallback to LLM for non-standard phrasings
        llm_goal = self._llm_extract_goal(text, player_name)
        if llm_goal:
            return llm_goal

        return Goal(goal_type="CHAT", parameters={"message": text}, raw_text=text, target_player=player_name, priority=50, created_at=time.time())

    def _llm_extract_goal(self, text: str, player_name: str) -> Optional[Goal]:
        """Uses local LLM to extract structured goal for complex natural queries."""
        try:
            prompt = f"""Extract the Minecraft action goal for player '{player_name}' saying: "{text}"

Available goal_types:
BUILD_HOUSE, BUILD_SHELTER, COLLECT_RESOURCE, CRAFT_ITEM, SMELT_ITEM, FOLLOW_PLAYER, PVP_COMBAT, ATTACK_MOBS, HUNT_FOOD, EAT_FOOD, SLEEP, EXPLORE, FIND_VILLAGE, BRIDGE, GIVE_ITEM, DROP_ALL, PICKUP, AUTONOMOUS_SURVIVAL, SPEEDRUN, STOP, STATUS, CHAT.

Output ONLY valid JSON:
{{
  "goal_type": "<GOAL_TYPE>",
  "parameters": {{ ... }}
}}"""

            response = self.provider.generate(prompt, max_tokens=80, temperature=0.1)
            if not response or any(b in response.lower() for b in ["sorry", "cannot help"]):
                return None

            match = re.search(r"\{.*\}", response, re.DOTALL)
            if match:
                parsed = json.loads(match.group(0))
                g_type = parsed.get("goal_type", "CHAT")
                params = parsed.get("parameters", {})
                return Goal(
                    goal_type=g_type,
                    parameters=params,
                    raw_text=text,
                    target_player=player_name,
                    created_at=time.time()
                )
        except Exception as e:
            agent_logger.debug(f"LLM Goal extraction fallback error: {e}")
        return None
