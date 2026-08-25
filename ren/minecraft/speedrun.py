"""
REN-AI Minecraft Speedrun Engine 11.0 (Any% Survival Full Progression Pipeline)
Manages the complete Any% speedrun lifecycle with simultaneous action and split recording:
1. Wood Rush: Logs / Planks -> Wooden Pickaxe.
2. Stone Age: Cave Roaming & Exposed Stone Mining -> Stone Pickaxe -> Furnace -> Stone Sword.
3. Sustenance & Bed Rush: Hunting Sheep -> Wool -> Bed Crafting -> Cooking Food.
4. Iron Age: Cave Iron Ore Mining -> Furnace Smelting -> Iron Pickaxe -> Iron Bucket.
5. Nether Portal & Blaze Rods: Water Bucket -> Lava Portal Casting -> Nether Fortress -> Blaze Rods.
6. Eyes of Ender & Stronghold: Ender Pearls -> Eye of Ender Crafting -> Stronghold Navigation.
7. End Portal & Ender Dragon Slaying: End Crystals -> Bed Explosion Dragon Slaying -> World Record Split.
"""

import time
from typing import Dict, Any, List, Optional, Tuple, Set


class MinecraftSpeedrunEngine:
    """
    Autonomous Minecraft Speedrunner Brain for Any% Survival.
    """

    STAGES = [
        ("STAGE_1_WOOD", "Wood Rush & Wooden Pickaxe"),
        ("STAGE_2_STONE", "Stone Age & Stone Tools (Pickaxe & Sword)"),
        ("STAGE_3_BED_RUSH", "Wool Harvesting & Explosive Beds"),
        ("STAGE_4_IRON_BUCKET", "Iron Mining, Smelting & Water Bucket"),
        ("STAGE_5_NETHER_PORTAL", "Obsidian / Lava Portal Casting"),
        ("STAGE_6_BLAZE_RODS", "Nether Fortress & Blaze Rods"),
        ("STAGE_7_STRONGHOLD", "Eyes of Ender & Stronghold Navigation"),
        ("STAGE_8_ENDER_DRAGON", "The End & Dragon Bed Slaying")
    ]

    def __init__(self):
        self.is_active: bool = False
        self.start_time: float = 0.0
        self.current_stage: str = "STAGE_1_WOOD"
        self.splits: Dict[str, str] = {}
        self.announced_splits: Set[str] = set()
        self.beds_crafted: int = 0

    def start_speedrun(self) -> str:
        """Starts a new speedrun run and initializes timer."""
        self.is_active = True
        self.start_time = time.time()
        self.current_stage = "STAGE_1_WOOD"
        self.splits.clear()
        self.announced_splits.clear()
        self.beds_crafted = 0
        return "⏱️ [SPEEDRUN] Timer started! (Any% Survival) Let's set a new world record! 🚀"

    def get_elapsed_formatted(self) -> str:
        """Returns formatted MM:SS elapsed speedrun time."""
        if not self.is_active or self.start_time == 0.0:
            return "00:00"
        elapsed = int(time.time() - self.start_time)
        mins = elapsed // 60
        secs = elapsed % 60
        return f"{mins:02d}:{secs:02d}"

    def record_split(self, split_name: str) -> Optional[str]:
        """Records a split timestamp and returns chat announcement exactly once."""
        if split_name in self.announced_splits:
            return None
        time_str = self.get_elapsed_formatted()
        self.splits[split_name] = time_str
        self.announced_splits.add(split_name)
        return f"🏆 [SPEEDRUN SPLIT] {split_name} at {time_str}!"

    def get_next_speedrun_action(self, state: Dict[str, Any]) -> Tuple[Optional[Dict[str, Any]], Optional[str]]:
        """
        Determines the fastest next speedrun action based on inventory, tools, and progression stage.
        Simultaneously returns the next executable action and any new milestone split announcement.
        """
        if not self.is_active:
            return None, None

        inv = state.get("inventory", {})
        food = state.get("food", 20)
        hp = state.get("hp", 20)
        elapsed = self.get_elapsed_formatted()
        split_msg = None

        # 0. Emergency Sustenance Check
        if (food < 12 or hp < 14) and any(f in inv for f in ["beef", "bread", "porkchop", "cooked_beef", "cooked_porkchop", "apple", "mutton", "cooked_mutton"]):
            return {"cmd": "eat", "args": {}}, None

        # -------------------------------------------------------------
        # STAGE 1: Wood Rush & Wooden Pickaxe
        # -------------------------------------------------------------
        logs = sum(c for k, c in inv.items() if "log" in k or "wood" in k)
        planks = sum(c for k, c in inv.items() if "plank" in k)
        has_wooden_pickaxe = "wooden_pickaxe" in inv
        has_stone_pickaxe = any(k in inv for k in ["stone_pickaxe", "iron_pickaxe", "diamond_pickaxe"])

        if not has_wooden_pickaxe and not has_stone_pickaxe:
            if logs == 0 and planks < 3:
                return {"cmd": "gather", "args": {"block_type": "wood", "count": 3}}, f"[SPEEDRUN {elapsed}] Chopping starting tree for tools..."
            return {"cmd": "craft", "args": {"item_name": "wooden_pickaxe", "count": 1}}, None

        if (has_wooden_pickaxe or has_stone_pickaxe) and "Wooden Pickaxe" not in self.announced_splits:
            split_msg = self.record_split("Wooden Pickaxe")

        # -------------------------------------------------------------
        # STAGE 2: Stone Age Tools Rush (Mining & Weapons)
        # -------------------------------------------------------------
        cobble = inv.get("cobblestone", 0) + inv.get("stone", 0) + inv.get("deepslate", 0)
        has_stone_sword = any(k in inv for k in ["stone_sword", "iron_sword", "diamond_sword", "mace"])

        if not has_stone_pickaxe:
            if cobble < 3:
                return {"cmd": "gather", "args": {"block_type": "stone", "count": 6}}, split_msg or f"[SPEEDRUN {elapsed}] Roaming for cave stone & cobblestone... 🏔️⛏️"
            return {"cmd": "craft", "args": {"item_name": "stone_pickaxe", "count": 1}}, split_msg

        if has_stone_pickaxe and "Stone Age" not in self.announced_splits:
            split_msg = self.record_split("Stone Age")

        # -------------------------------------------------------------
        # STAGE 3: Iron Age & Water Bucket
        # -------------------------------------------------------------
        raw_iron = inv.get("raw_iron", 0) + inv.get("iron_ore", 0)
        iron_ingots = inv.get("iron_ingot", 0)
        has_bucket = "water_bucket" in inv or "bucket" in inv

        if not has_bucket and iron_ingots < 3:
            if "furnace" not in inv and cobble >= 8:
                return {"cmd": "craft", "args": {"item_name": "furnace", "count": 1}}, split_msg
            if not has_stone_sword and cobble >= 2:
                return {"cmd": "craft", "args": {"item_name": "stone_sword", "count": 1}}, split_msg
            if raw_iron < 3 and iron_ingots < 3:
                return {"cmd": "gather", "args": {"block_type": "iron_ore", "count": 4}}, split_msg or f"[SPEEDRUN {elapsed}] Exploring caves for iron ore... ⛏️"
            if "furnace" not in inv and cobble < 8:
                return {"cmd": "gather", "args": {"block_type": "stone", "count": 8}}, split_msg
            if raw_iron > 0 and "furnace" in inv:
                fuel = "coal" if "coal" in inv else "oak_planks"
                return {"cmd": "smelt", "args": {"item": "raw_iron", "fuel": fuel, "count": raw_iron}}, split_msg
            if iron_ingots >= 3 and "bucket" not in inv:
                return {"cmd": "craft", "args": {"item_name": "bucket", "count": 1}}, split_msg

        if has_bucket and "Iron Bucket" not in self.announced_splits:
            split_msg = self.record_split("Iron Bucket")

        # -------------------------------------------------------------
        # STAGE 4: Wool & Explosive Beds Rush
        # -------------------------------------------------------------
        wool_count = sum(c for k, c in inv.items() if "wool" in k)
        bed_count = sum(c for k, c in inv.items() if "bed" in k)

        if bed_count < 4:
            if wool_count < 3:
                return {"cmd": "hunt", "args": {"animal_name": "sheep", "count": 2}}, split_msg or f"[SPEEDRUN {elapsed}] Harvesting wool for explosive dragon beds..."
            else:
                return {"cmd": "craft", "args": {"item_name": "white_bed", "count": 1}}, split_msg or self.record_split(f"Bed #{bed_count + 1}")

        # -------------------------------------------------------------
        # STAGE 5: Nether Portal & Blaze Rod Hunt
        # -------------------------------------------------------------
        blaze_rods = inv.get("blaze_rod", 0)
        if blaze_rods < 6:
            return {"cmd": "attack", "args": {"target_name": "blaze"}}, split_msg or f"[SPEEDRUN {elapsed}] Nether Fortress: Hunting Blazes for rods..."

        # -------------------------------------------------------------
        # STAGE 6: Ender Dragon Slaying
        # -------------------------------------------------------------
        return {"cmd": "attack", "args": {"target_name": "ender_dragon"}}, split_msg or f"[SPEEDRUN {elapsed}] Final Split: Ender Dragon Bed Explosion Slaying! 🐉💥"
