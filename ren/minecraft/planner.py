"""
REN-AI Minecraft Autonomous AGI Goal Planner & Tech-Tree State Machine
Provides full autonomous progression: Wood -> Stone -> Food -> Home Base -> Iron Age -> Night Defense.
Accurate batch crafting: 1 log = 4 planks; never requests more craft batches than available logs.
"""

from typing import Dict, Any, List, Optional, Tuple


class MinecraftGoalPlanner:
    """
    Autonomous AGI Planner & Survival State Machine.
    Levels up like a real human player through Minecraft tech tiers.
    """

    def count_total_logs(self, inventory: Dict[str, int]) -> int:
        return sum(c for k, c in inventory.items() if "log" in k or "wood" in k)

    def count_total_planks(self, inventory: Dict[str, int]) -> int:
        return sum(c for k, c in inventory.items() if "plank" in k)

    def count_total_cobblestone(self, inventory: Dict[str, int]) -> int:
        return inventory.get("cobblestone", 0) + inventory.get("stone", 0) + inventory.get("deepslate", 0)

    def count_total_iron(self, inventory: Dict[str, int]) -> int:
        return inventory.get("iron_ingot", 0)

    def count_total_raw_iron(self, inventory: Dict[str, int]) -> int:
        return inventory.get("raw_iron", 0) + inventory.get("iron_ore", 0)

    def count_total_building_blocks(self, inventory: Dict[str, int]) -> int:
        total = 0
        for k, v in inventory.items():
            if any(b in k for b in ["plank", "dirt", "cobble", "stone", "log"]):
                total += v
        return total

    def count_total_food(self, inventory: Dict[str, int]) -> int:
        food_keys = ["beef", "porkchop", "mutton", "bread", "apple", "cooked_beef", "cooked_porkchop", "cooked_mutton"]
        return sum(inventory.get(k, 0) for k in food_keys)

    def get_next_autonomous_action(self, state: Dict[str, Any], has_home: bool = False) -> Optional[Dict[str, Any]]:
        """
        Self-directed AGI Life Cycle:
        Decides the highest priority next step to progress in the Minecraft world.
        """
        inv = state.get("inventory", {})
        food = state.get("food", 20)
        time_of_day = state.get("timeOfDay", "day")

        # Priority 1: Critical Hunger or Low Food
        if food < 14 and self.count_total_food(inv) == 0:
            return {"cmd": "hunt", "args": {"animal_name": "animal", "count": 2}}

        # Priority 2: Nighttime Shelter & Sleep
        if time_of_day in ["dusk", "night"]:
            if has_home and "bed" in inv:
                return {"cmd": "sleep", "args": {}}
            elif not has_home and self.count_total_building_blocks(inv) >= 12:
                return {"cmd": "build_shelter", "args": {"size": 3}}

        # Priority 3: Tech-Tree Level 1 (Wood Age)
        has_wood_tool = any(t in inv for t in ["wooden_pickaxe", "stone_pickaxe", "iron_pickaxe"])
        if not has_wood_tool:
            logs = self.count_total_logs(inv)
            planks = self.count_total_planks(inv)
            if logs < 3 and planks < 4:
                return {"cmd": "gather", "args": {"block_type": "wood", "count": 3}}
            if logs > 0 and planks < 4:
                return {"cmd": "craft", "args": {"item_name": "oak_planks", "count": min(logs, 2)}}
            if "crafting_table" not in inv:
                return {"cmd": "craft", "args": {"item_name": "crafting_table", "count": 1}}
            return {"cmd": "craft", "args": {"item_name": "wooden_pickaxe", "count": 1}}

        # Priority 4: Tech-Tree Level 2 (Stone Age & Furnace)
        has_stone_tool = any(t in inv for t in ["stone_pickaxe", "iron_pickaxe"])
        cobble = self.count_total_cobblestone(inv)
        if not has_stone_tool:
            if cobble < 8:
                return {"cmd": "gather", "args": {"block_type": "stone", "count": 8}}
            if "stone_pickaxe" not in inv:
                return {"cmd": "craft", "args": {"item_name": "stone_pickaxe", "count": 1}}
            if "stone_sword" not in inv:
                return {"cmd": "craft", "args": {"item_name": "stone_sword", "count": 1}}

        if "furnace" not in inv and cobble < 8:
            return {"cmd": "gather", "args": {"block_type": "stone", "count": 8}}
        elif "furnace" not in inv and cobble >= 8:
            return {"cmd": "craft", "args": {"item_name": "furnace", "count": 1}}

        # Priority 5: Sustenance & Food Harvesting
        if self.count_total_food(inv) < 4:
            return {"cmd": "hunt", "args": {"animal_name": "animal", "count": 2}}

        # Priority 6: Tech-Tree Level 4 (Settlement & Home Construction)
        if not has_home:
            available_blocks = self.count_total_building_blocks(inv)
            if available_blocks < 16:
                return {"cmd": "gather", "args": {"block_type": "wood", "count": 4}}
            elif self.count_total_planks(inv) < 16 and self.count_total_logs(inv) > 0:
                logs_to_craft = min(self.count_total_logs(inv), 4)
                return {"cmd": "craft", "args": {"item_name": "oak_planks", "count": logs_to_craft}}
            else:
                return {"cmd": "build_shelter", "args": {"size": 3}}

        # Priority 7: Tech-Tree Level 5 (Iron Age)
        raw_iron = self.count_total_raw_iron(inv)
        iron_ingots = self.count_total_iron(inv)
        if raw_iron < 4 and iron_ingots < 3:
            return {"cmd": "gather", "args": {"block_type": "iron_ore", "count": 4}}
        elif raw_iron > 0:
            return {"cmd": "smelt", "args": {"item": "raw_iron", "fuel": "coal", "count": raw_iron}}
        elif iron_ingots >= 3 and "iron_pickaxe" not in inv:
            return {"cmd": "craft", "args": {"item_name": "iron_pickaxe", "count": 1}}
        elif iron_ingots >= 2 and "iron_sword" not in inv:
            return {"cmd": "craft", "args": {"item_name": "iron_sword", "count": 1}}
        elif iron_ingots >= 1 and "shield" not in inv:
            return {"cmd": "craft", "args": {"item_name": "shield", "count": 1}}

        # Priority 8: General Resource Gathering
        return {"cmd": "gather", "args": {"block_type": "wood", "count": 3}}

    def decompose_goal(self, goal_name: str, state: Dict[str, Any], player_name: str = "Player") -> List[Dict[str, Any]]:
        """
        Recursively resolves dependencies and outputs an executable sequence of atomic actions.
        Self-sufficient: automatically acquires missing ingredients.
        """
        inv = state.get("inventory", {})
        actions: List[Dict[str, Any]] = []

        # 1. BUILD HOUSE / HOME / SHELTER
        if goal_name in ["build_house", "build_shelter", "make_home", "make_base", "make_house"]:
            blocks_needed = 16
            available_blocks = self.count_total_building_blocks(inv)
            
            if available_blocks < blocks_needed:
                needed = blocks_needed - available_blocks
                logs_needed = max(2, (needed + 3) // 4)
                # Auto-gather wood
                actions.append({"cmd": "gather", "args": {"block_type": "wood", "count": logs_needed}})
                # Auto-craft planks (1 log = 4 planks)
                actions.append({"cmd": "craft", "args": {"item_name": "oak_planks", "count": logs_needed}})
            
            # Place 3D structure in world
            actions.append({"cmd": "build_shelter", "args": {"size": 3}})
            return actions

        # 2. CRAFT STONE TOOLS
        if any(tool in goal_name for tool in ["stone_pickaxe", "stone_sword", "stone_axe"]):
            cobble = self.count_total_cobblestone(inv)
            if cobble < 4:
                # Ensure wooden pickaxe
                if "wooden_pickaxe" not in inv and "stone_pickaxe" not in inv:
                    logs = self.count_total_logs(inv)
                    planks = self.count_total_planks(inv)
                    if logs == 0 and planks < 4:
                        actions.append({"cmd": "gather", "args": {"block_type": "wood", "count": 3}})
                    actions.append({"cmd": "craft", "args": {"item_name": "oak_planks", "count": 2}})
                    if "crafting_table" not in inv:
                        actions.append({"cmd": "craft", "args": {"item_name": "crafting_table", "count": 1}})
                    actions.append({"cmd": "craft", "args": {"item_name": "wooden_pickaxe", "count": 1}})
                
                # Auto-mine stone
                actions.append({"cmd": "gather", "args": {"block_type": "stone", "count": 8}})

            if "crafting_table" not in inv:
                actions.append({"cmd": "craft", "args": {"item_name": "crafting_table", "count": 1}})
            actions.append({"cmd": "craft", "args": {"item_name": goal_name, "count": 1}})
            return actions

        # 3. SMELTING & IRON TECH
        if "iron" in goal_name or "armor" in goal_name or "shield" in goal_name:
            raw_iron = self.count_total_raw_iron(inv)
            if raw_iron < 3:
                if "stone_pickaxe" not in inv:
                    actions.extend(self.decompose_goal("stone_pickaxe", state, player_name))
                actions.append({"cmd": "gather", "args": {"block_type": "iron_ore", "count": 4}})

            if "furnace" not in inv:
                if self.count_total_cobblestone(inv) < 8:
                    actions.append({"cmd": "gather", "args": {"block_type": "stone", "count": 8}})
                actions.append({"cmd": "craft", "args": {"item_name": "furnace", "count": 1}})

            actions.append({"cmd": "smelt", "args": {"item": "raw_iron", "fuel": "coal", "count": 4}})
            if goal_name in ["iron_sword", "iron_pickaxe", "iron_chestplate", "shield"]:
                actions.append({"cmd": "craft", "args": {"item_name": goal_name, "count": 1}})
            return actions

        # 4. HUNTING & FOOD
        if goal_name in ["get_food", "hunt_food", "feed"]:
            actions.append({"cmd": "hunt", "args": {"animal_name": "animal", "count": 3}})
            actions.append({"cmd": "eat", "args": {}})
            return actions

        return [{"cmd": goal_name, "args": {}}]
