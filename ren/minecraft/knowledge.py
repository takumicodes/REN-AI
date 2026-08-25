"""
REN-AI Minecraft Universal Knowledge & Strategy Engine 11.0
Contains complete domain knowledge of Minecraft mechanics:
- Tech Tree & Tool Hierarchy (Wood -> Stone -> Iron -> Diamond -> Netherite)
- Ore Generation & Ideal Cave Mining Y-Levels (1.21+ / 1.20+)
- Mob Combat Tactics & Weaknesses (Zombies, Skeletons, Creepers, Endermen, Blazes, Dragon)
- Speedrunner Route & Portal Casting Tricks (Any% Survival Optimization)
- Crafting Recipes Graph & Material Optimization
"""

from typing import Dict, Any, List, Optional


class MinecraftKnowledgeBase:
    """
    Complete in-memory knowledge base of Minecraft game rules, tiers, recipes, and tactics.
    """

    # 1. Tech Tree Progression & Tool Capabilities
    TOOL_TIERS = {
        "wooden": {
            "tier_level": 0,
            "durability": 59,
            "can_harvest": ["wood", "dirt", "sand", "gravel", "stone", "cobblestone", "coal_ore"],
            "cannot_harvest": ["iron_ore", "gold_ore", "diamond_ore", "obsidian", "redstone_ore"],
            "mining_speed": 2.0
        },
        "stone": {
            "tier_level": 1,
            "durability": 131,
            "can_harvest": ["stone", "cobblestone", "coal_ore", "iron_ore", "copper_ore", "lapis_ore"],
            "cannot_harvest": ["gold_ore", "diamond_ore", "redstone_ore", "obsidian"],
            "mining_speed": 4.0
        },
        "iron": {
            "tier_level": 2,
            "durability": 250,
            "can_harvest": ["iron_ore", "gold_ore", "diamond_ore", "redstone_ore", "emerald_ore"],
            "cannot_harvest": ["obsidian", "ancient_debris"],
            "mining_speed": 6.0
        },
        "diamond": {
            "tier_level": 3,
            "durability": 1561,
            "can_harvest": ["all_ores", "obsidian", "ancient_debris", "crying_obsidian"],
            "cannot_harvest": ["bedrock"],
            "mining_speed": 8.0
        },
        "netherite": {
            "tier_level": 4,
            "durability": 2031,
            "can_harvest": ["all_ores", "obsidian", "ancient_debris"],
            "cannot_harvest": ["bedrock"],
            "mining_speed": 9.0
        }
    }

    # 2. Ideal Ore Generation Heights (Minecraft 1.18 - 1.21+)
    ORE_HEIGHT_DISTRIBUTION = {
        "coal": {"min_y": 0, "max_y": 192, "peak_y": 96, "best_location": "Mountains & exposed cave walls"},
        "copper": {"min_y": -16, "max_y": 112, "peak_y": 48, "best_location": "Dripstone caves & surface cliffs"},
        "iron": {"min_y": -64, "max_y": 256, "peak_y": 16, "best_location": "Large cave openings & mountain peaks (Y=232)"},
        "gold": {"min_y": -64, "max_y": 32, "peak_y": -16, "best_location": "Badlands / Mesa (Y=32 to 256) & Deepslate caves"},
        "lapis": {"min_y": -64, "max_y": 64, "peak_y": 0, "best_location": "Underground caves & submerged ravines"},
        "redstone": {"min_y": -64, "max_y": 16, "peak_y": -58, "best_location": "Deepslate cave floors"},
        "diamond": {"min_y": -64, "max_y": 16, "peak_y": -58, "best_location": "Deepslate caves, lava lakes & strip mining at Y=-58"},
        "ancient_debris": {"min_y": 8, "max_y": 119, "peak_y": 15, "best_location": "Nether waste bed mining with beds / TNT"}
    }

    # 3. Hostile Mob Combat Tactics
    MOB_TACTICS = {
        "zombie": {
            "danger_level": "LOW",
            "weapon": "Sword or Mace",
            "tactic": "Jump-attack critical hits with 2.5 block spacing. Retreat if swarmed."
        },
        "skeleton": {
            "danger_level": "HIGH",
            "weapon": "Shield (off-hand) + Sword/Mace",
            "tactic": "Raise shield to block arrows. Sprint-strafe in zig-zag pattern to close distance."
        },
        "creeper": {
            "danger_level": "CRITICAL",
            "weapon": "Bow or Sprint-Hit Knockback",
            "tactic": "Hit once with sprint-knockback, immediately retreat 4 blocks to reset hiss timer. Block with shield if trapped."
        },
        "spider": {
            "danger_level": "MEDIUM",
            "weapon": "Sword or Axe",
            "tactic": "Look up to hit when spider jumps. Circle-strafe around web attacks."
        },
        "witch": {
            "danger_level": "HIGH",
            "weapon": "Bow or Rapid Melee",
            "tactic": "Close distance rapidly before splash potion of poison/harming is thrown. Drink milk if poisoned."
        },
        "enderman": {
            "danger_level": "HIGH",
            "weapon": "Sword + 2-block Ceiling",
            "tactic": "Construct a 3x3 2-block high ceiling overhead so Enderman cannot reach. Attack legs. Use water bucket."
        },
        "blaze": {
            "danger_level": "HIGH",
            "weapon": "Snowballs, Bow or Melee behind pillars",
            "tactic": "Take cover behind Nether Fortress pillars during fireball burst, rush in during cooldown. Snowballs deal 3 damage."
        },
        "ender_dragon": {
            "danger_level": "BOSS",
            "weapon": "Explosive Beds & Heavy Mace Smash",
            "tactic": "Shoot/climb End Crystals. Place bed on obsidian pillar/fountain bedrock with 1 block between head. Explode bed on dragon head perch."
        }
    }

    # 4. Any% Speedrunning Knowledge Graph
    SPEEDRUN_STRATEGY = {
        "wood_rush": "Gather 3 logs -> 12 planks -> Table + Sticks -> Wooden Pickaxe (total 10 seconds).",
        "stone_rush": "Mine 3 cobble -> Stone Pickaxe -> Mine 8 cobble -> Furnace -> 3 cobble -> Stone Sword.",
        "bucket_casting": "Fill water bucket -> Find surface lava pool -> Place water against block adjacent to lava -> Obsidian frame created -> Light with Flint/Fire charge.",
        "nether_navigation": "Locate Nether Fortress (positive/negative quadrant lines) and Piglin Bastion -> Barter 12 gold for Pearls -> Collect 6 Blaze Rods.",
        "stronghold_triangulation": "Throw 1 Eye of Ender -> Record angle -> Travel 200 blocks -> Throw 2nd Eye -> Ray intersection gives Stronghold coordinates.",
        "one_cycle_dragon": "Wait for perch -> Place bed at head level -> Shield / block below head -> Detonate 4 beds -> Dragon defeated in < 15 seconds."
    }

    @classmethod
    def get_tactic_for_mob(cls, mob_name: str) -> Dict[str, str]:
        """Returns the optimal tactical combat strategy for a given mob."""
        clean = mob_name.lower().strip()
        for mob, tactic in cls.MOB_TACTICS.items():
            if mob in clean:
                return tactic
        return {"danger_level": "MEDIUM", "weapon": "Sword", "tactic": "Engage with sword and shield."}

    @classmethod
    def get_best_mining_y_level(cls, ore_name: str) -> int:
        """Returns the peak Y-level for finding a specific ore."""
        clean = ore_name.lower().strip()
        for ore, info in cls.ORE_HEIGHT_DISTRIBUTION.items():
            if ore in clean:
                return info["peak_y"]
        return 16
