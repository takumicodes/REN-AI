"""
REN-AI Minecraft Comprehensive Skill Registry 12.0
Defines all embodied skills across Movement, Perception, Resource, Crafting, Survival, Building, and Interaction.
Every skill includes preconditions, expected outcomes, verification rules, timeouts, and recovery strategies.
"""

import re
from enum import Enum
from typing import Dict, Any, List, Optional, Callable
from dataclasses import dataclass, field
from ren.minecraft.types import ActionResult


class SkillCategory(str, Enum):
    MOVEMENT = "MOVEMENT"
    PERCEPTION = "PERCEPTION"
    RESOURCE = "RESOURCE"
    CRAFTING = "CRAFTING"
    SURVIVAL = "SURVIVAL"
    BUILDING = "BUILDING"
    INTERACTION = "INTERACTION"
    SYSTEM = "SYSTEM"


@dataclass
class MinecraftSkill:
    """Complete specification of an embodied Minecraft skill."""
    name: str
    category: SkillCategory
    description: str
    aliases: List[str] = field(default_factory=list)
    default_parameters: Dict[str, Any] = field(default_factory=dict)
    preconditions: List[str] = field(default_factory=list)
    expected_outcome: str = ""
    timeout_seconds: float = 30.0
    max_retries: int = 3
    recovery_strategy: str = "stop_and_replan"
    param_extractor: Optional[Callable[[str, str], Dict[str, Any]]] = None


class MinecraftSkillRegistry:
    """
    Central registry for all executable Minecraft capabilities and natural language mappings.
    """

    def __init__(self):
        self.skills: Dict[str, MinecraftSkill] = {}
        self._register_all_skills()

    def register(self, skill: MinecraftSkill):
        self.skills[skill.name] = skill

    def get_skill(self, name: str) -> Optional[MinecraftSkill]:
        return self.skills.get(name)

    def find_matching_skill(self, text: str) -> Optional[MinecraftSkill]:
        """Finds the best matching skill by alias regex."""
        clean_text = text.lower().strip()
        for skill in self.skills.values():
            for alias in skill.aliases:
                if re.search(rf"\b{re.escape(alias)}\b", clean_text, re.IGNORECASE):
                    return skill
        return None

    def _register_all_skills(self):
        # =========================================================
        # 1. MOVEMENT SKILLS
        # =========================================================
        self.register(MinecraftSkill(
            name="move_to",
            category=SkillCategory.MOVEMENT,
            description="Navigates to specific coordinates (x, y, z).",
            aliases=["go to", "move to", "walk to", "navigate to", "travel to"],
            default_parameters={"x": 0, "y": 64, "z": 0, "tolerance": 2.0},
            expected_outcome="Position within tolerance of target.",
            timeout_seconds=40.0,
            recovery_strategy="clear_path_and_repath"
        ))

        self.register(MinecraftSkill(
            name="follow_player",
            category=SkillCategory.MOVEMENT,
            description="Continuously follows a target player.",
            aliases=["follow me", "follow", "stay near me", "come with me", "walk with me", "behind me"],
            default_parameters={"player": "Player"},
            expected_outcome="Maintains distance <= 3 blocks from player.",
            timeout_seconds=600.0,
            recovery_strategy="teleport_or_sprint"
        ))

        self.register(MinecraftSkill(
            name="stop",
            category=SkillCategory.MOVEMENT,
            description="Immediately halts all active pathfinding and tasks.",
            aliases=["stop", "halt", "stay here", "wait here", "pause", "freeze", "cancel", "hold up"],
            default_parameters={},
            expected_outcome="Velocity is zero and current task is cancelled.",
            timeout_seconds=3.0,
            recovery_strategy="none"
        ))

        self.register(MinecraftSkill(
            name="flee",
            category=SkillCategory.MOVEMENT,
            description="Tactical retreat away from dangerous hostiles or hazards.",
            aliases=["flee", "run away", "retreat", "escape"],
            default_parameters={"distance": 16.0},
            expected_outcome="Distance to nearest hostile >= 16 blocks.",
            timeout_seconds=15.0,
            recovery_strategy="sprint_and_jump"
        ))

        # =========================================================
        # 2. PERCEPTION SKILLS
        # =========================================================
        self.register(MinecraftSkill(
            name="inspect_world",
            category=SkillCategory.PERCEPTION,
            description="Scans surrounding environment, entities, and lighting.",
            aliases=["status", "where are you", "hp", "health", "inventory", "what do you have", "bag", "coords", "scan"],
            default_parameters={},
            expected_outcome="Returns updated WorldState summary.",
            timeout_seconds=5.0
        ))

        self.register(MinecraftSkill(
            name="find_resource",
            category=SkillCategory.PERCEPTION,
            description="Locates nearest block matching resource type (cave ore, tree, water, lava).",
            aliases=["find wood", "find stone", "find iron", "find coal", "find diamond", "find cave"],
            default_parameters={"resource": "wood", "max_distance": 48},
            expected_outcome="Coordinates of matching block or cave entrance.",
            timeout_seconds=20.0
        ))

        # =========================================================
        # 3. RESOURCE GATHERING SKILLS
        # =========================================================
        self.register(MinecraftSkill(
            name="gather_resource",
            category=SkillCategory.RESOURCE,
            description="Finds and mines requested resource blocks.",
            aliases=[
                "gather", "mine", "chop", "dig", "cut", "harvest", "collect",
                "get wood", "chop wood", "mine stone", "gather stone", "mine iron", "gather iron"
            ],
            default_parameters={"block_type": "wood", "count": 4},
            preconditions=["tool_check_or_bare_hands"],
            expected_outcome="Inventory contains requested item count delta.",
            timeout_seconds=45.0,
            recovery_strategy="roam_and_find_alternate_vein"
        ))

        self.register(MinecraftSkill(
            name="collect_item",
            category=SkillCategory.RESOURCE,
            description="Picks up dropped item entities within proximity.",
            aliases=["pickup", "pick up items", "take items", "collect drops"],
            default_parameters={"radius": 16},
            expected_outcome="Ground items in radius are placed into inventory.",
            timeout_seconds=20.0
        ))

        # =========================================================
        # 4. CRAFTING & SMELTING SKILLS
        # =========================================================
        self.register(MinecraftSkill(
            name="craft_item",
            category=SkillCategory.CRAFTING,
            description="Deterministically crafts item with automatic pre-requisite resolution.",
            aliases=["craft", "make", "create"],
            default_parameters={"item_name": "crafting_table", "count": 1},
            expected_outcome="Item exists in inventory with increased count.",
            timeout_seconds=30.0,
            recovery_strategy="gather_missing_ingredients"
        ))

        self.register(MinecraftSkill(
            name="smelt_item",
            category=SkillCategory.CRAFTING,
            description="Smelts raw ores or food in a furnace using fuel.",
            aliases=["smelt", "cook", "bake"],
            default_parameters={"item": "raw_iron", "fuel": "coal", "count": 1},
            expected_outcome="Cooked or refined item placed in inventory.",
            timeout_seconds=45.0,
            recovery_strategy="craft_furnace_or_gather_fuel"
        ))

        self.register(MinecraftSkill(
            name="equip_item",
            category=SkillCategory.CRAFTING,
            description="Equips weapon, shield, or armor into respective equipment slots.",
            aliases=["equip", "wear", "wield", "hold"],
            default_parameters={"item_name": "stone_sword", "destination": "hand"},
            expected_outcome="Equipment slot contains item.",
            timeout_seconds=5.0
        ))

        # =========================================================
        # 5. SURVIVAL & COMBAT SKILLS
        # =========================================================
        self.register(MinecraftSkill(
            name="eat_food",
            category=SkillCategory.SURVIVAL,
            description="Consumes edible item from inventory to restore hunger and health.",
            aliases=["eat", "consume food", "have food"],
            default_parameters={},
            expected_outcome="Hunger or health increases.",
            timeout_seconds=10.0,
            recovery_strategy="hunt_or_harvest_food"
        ))

        self.register(MinecraftSkill(
            name="hunt_food",
            category=SkillCategory.SURVIVAL,
            description="Hunts passive animals for meat rations.",
            aliases=["hunt", "hunt animals", "kill cow", "kill pig", "kill sheep", "get food", "slaughter"],
            default_parameters={"animal_name": "animal", "count": 2},
            expected_outcome="Raw meat collected into inventory.",
            timeout_seconds=45.0,
            recovery_strategy="roam_for_animals"
        ))

        self.register(MinecraftSkill(
            name="sleep",
            category=SkillCategory.SURVIVAL,
            description="Places or enters bed to skip night safely.",
            aliases=["sleep", "go to bed", "sleep in bed"],
            default_parameters={},
            expected_outcome="Time of day becomes morning/day.",
            timeout_seconds=20.0
        ))

        self.register(MinecraftSkill(
            name="defend_self",
            category=SkillCategory.SURVIVAL,
            description="Engages hostile mob with shield blocks and weapon strikes.",
            aliases=["attack", "kill", "fight", "defend", "slay"],
            default_parameters={"target_name": "zombie"},
            expected_outcome="Target mob is defeated.",
            timeout_seconds=30.0,
            recovery_strategy="flee_and_heal"
        ))

        # =========================================================
        # 6. BUILDING SKILLS
        # =========================================================
        self.register(MinecraftSkill(
            name="build_house",
            category=SkillCategory.BUILDING,
            description="Procedurally constructs complete wooden house with foundation, walls, roof, and interior.",
            aliases=[
                "build house", "make house", "build me a house", "make me a house",
                "build a small wooden house", "build small house", "make a house", "construct house"
            ],
            default_parameters={"material": "wooden", "size": "small"},
            expected_outcome="Verified 4x4 house exists in Minecraft world.",
            timeout_seconds=120.0,
            recovery_strategy="clear_ground_and_retry"
        ))

        self.register(MinecraftSkill(
            name="build_shelter",
            category=SkillCategory.BUILDING,
            description="Constructs emergency nightfall shelter.",
            aliases=["build shelter", "make shelter", "make a shelter", "quick shelter", "emergency shelter"],
            default_parameters={"material": "dirt", "size": "compact"},
            expected_outcome="Enclosed 3x3 survival shelter constructed.",
            timeout_seconds=45.0
        ))

        self.register(MinecraftSkill(
            name="build_bridge",
            category=SkillCategory.BUILDING,
            description="Constructs straight bridge across gaps or chasms.",
            aliases=["build bridge", "bridge", "make bridge", "bridging"],
            default_parameters={"length": 8, "material": "oak_planks"},
            expected_outcome="Bridge blocks placed ahead.",
            timeout_seconds=40.0
        ))

        # =========================================================
        # 7. INTERACTION & SYSTEM SKILLS
        # =========================================================
        self.register(MinecraftSkill(
            name="give_item",
            category=SkillCategory.INTERACTION,
            description="Tosses specified item to a player.",
            aliases=["give", "give me", "drop item", "share", "toss"],
            default_parameters={"player": "Player", "item_name": "wood", "count": 1},
            expected_outcome="Item dropped near player.",
            timeout_seconds=15.0
        ))

        self.register(MinecraftSkill(
            name="drop_all",
            category=SkillCategory.INTERACTION,
            description="Empties entire inventory near player.",
            aliases=["give all", "drop all", "dump inventory", "give everything", "drop everything"],
            default_parameters={"player": "Player"},
            expected_outcome="All inventory items dropped.",
            timeout_seconds=25.0
        ))

        self.register(MinecraftSkill(
            name="pvp_combat",
            category=SkillCategory.INTERACTION,
            description="Friendly combat duel with player using mace and aerial combos.",
            aliases=["pvp", "fight with me", "duel", "duel me", "pvp with me"],
            default_parameters={"player": "Player"},
            expected_outcome="Engages in PvP duel.",
            timeout_seconds=120.0
        ))

        self.register(MinecraftSkill(
            name="self_test",
            category=SkillCategory.SYSTEM,
            description="Runs complete automated in-game self test of connection, skills, building, and memory.",
            aliases=["run self test", "minecraft self test", "self test", "run diagnostics", "test yourself"],
            default_parameters={},
            expected_outcome="Self-test diagnostic report produced.",
            timeout_seconds=30.0
        ))
