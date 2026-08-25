"""
REN-AI Minecraft Goal Planner & Task Decomposition Engine
Decomposes structured Goals into verified, sequential Tasks and Subtasks.
Smart inventory awareness: NEVER re-gathers or re-crafts items already present in inventory.
"""

from typing import Dict, Any, List, Optional
from ren.minecraft.types import Goal, Task, Subtask, TaskStatus
from ren.minecraft.builder import MinecraftProceduralBuilder


class MinecraftGoalPlanner:
    """
    Translates high-level Goals into concrete, verifiable hierarchical Tasks.
    """

    def __init__(self):
        self.builder = MinecraftProceduralBuilder()

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
            if any(b in k for b in ["plank", "dirt", "cobble", "stone", "log", "brick", "wool"]):
                total += v
        return total

    def count_total_food(self, inventory: Dict[str, int]) -> int:
        food_keys = ["beef", "porkchop", "mutton", "bread", "apple", "cooked_beef", "cooked_porkchop", "cooked_mutton"]
        return sum(inventory.get(k, 0) for k in food_keys)

    def create_task_from_goal(self, goal: Goal, state: Dict[str, Any]) -> Task:
        """
        Main entry point: Converts a Goal into a persistent Task with verified Subtasks.
        Checks current inventory state to avoid redundant gathering or crafting.
        """
        g_type = goal.goal_type
        params = goal.parameters
        inv = state.get("inventory", {})
        pos = state.get("pos", {"x": 0.0, "y": 64.0, "z": 0.0})
        user = goal.target_player or "Player"
        subtasks: List[Subtask] = []
        step_id = 1

        # 1. BUILD_HOUSE
        if g_type == "BUILD_HOUSE":
            origin_x = int(pos.get("x", 0)) + 3
            origin_y = int(pos.get("y", 64))
            origin_z = int(pos.get("z", 0))
            material = params.get("material", "wooden")
            mat_block = "oak_planks" if material == "wooden" else "cobblestone"

            blueprint = self.builder.generate_small_house_blueprint(origin_x, origin_y, origin_z, mat_block)
            subtasks = self.builder.create_construction_subtasks(blueprint, inv)
            return Task(
                id=f"task_{g_type.lower()}",
                name="Build Small House",
                goal=goal,
                subtasks=subtasks
            )

        # 2. BUILD_SHELTER
        if g_type == "BUILD_SHELTER":
            origin_x = int(pos.get("x", 0)) + 2
            origin_y = int(pos.get("y", 64))
            origin_z = int(pos.get("z", 0))
            blueprint = self.builder.generate_quick_shelter_blueprint(origin_x, origin_y, origin_z, "dirt")
            subtasks = self.builder.create_construction_subtasks(blueprint, inv)
            return Task(
                id=f"task_{g_type.lower()}",
                name="Build Survival Shelter",
                goal=goal,
                subtasks=subtasks
            )

        # 3. COLLECT_RESOURCE
        if g_type == "COLLECT_RESOURCE":
            res = params.get("resource", "wood")
            amt = params.get("amount", 4)
            subtasks.append(Subtask(
                id=f"step_{step_id}",
                action="gather",
                parameters={"block_type": res, "count": amt}
            ))
            return Task(
                id=f"task_{g_type.lower()}",
                name=f"Collect {amt}x {res}",
                goal=goal,
                subtasks=subtasks
            )

        # 4. CRAFT_ITEM
        if g_type == "CRAFT_ITEM":
            item_name = params.get("item_name", "crafting_table")
            amt = params.get("count", 1)

            # Check if item is ALREADY in inventory
            if item_name in inv and inv[item_name] >= amt:
                subtasks.append(Subtask(
                    id=f"step_{step_id}",
                    action="chat",
                    parameters={"message": f"I already have {amt}x {item_name.replace('_', ' ')} ready in my inventory! 🎒"}
                ))
                return Task(
                    id=f"task_{g_type.lower()}",
                    name=f"Have {amt}x {item_name}",
                    goal=goal,
                    subtasks=subtasks
                )

            # Auto-resolve pre-requisites only if ingredients are truly missing
            if "stone_pickaxe" in item_name or "stone_sword" in item_name or "stone_axe" in item_name:
                cobble_count = self.count_total_cobblestone(inv)
                if cobble_count < 3:
                    has_pick = any(k in inv for k in ["wooden_pickaxe", "stone_pickaxe", "iron_pickaxe", "diamond_pickaxe"])
                    if not has_pick:
                        if self.count_total_logs(inv) == 0 and self.count_total_planks(inv) < 4:
                            subtasks.append(Subtask(id=f"step_{step_id}", action="gather", parameters={"block_type": "wood", "count": 3}))
                            step_id += 1
                        if self.count_total_planks(inv) < 4:
                            subtasks.append(Subtask(id=f"step_{step_id}", action="craft", parameters={"item_name": "oak_planks", "count": 2}))
                            step_id += 1
                        if "crafting_table" not in inv:
                            subtasks.append(Subtask(id=f"step_{step_id}", action="craft", parameters={"item_name": "crafting_table", "count": 1}))
                            step_id += 1
                        subtasks.append(Subtask(id=f"step_{step_id}", action="craft", parameters={"item_name": "wooden_pickaxe", "count": 1}))
                        step_id += 1
                    subtasks.append(Subtask(id=f"step_{step_id}", action="gather", parameters={"block_type": "stone", "count": 6}))
                    step_id += 1

            if item_name != "crafting_table" and "crafting_table" not in inv:
                subtasks.append(Subtask(id=f"step_{step_id}", action="craft", parameters={"item_name": "crafting_table", "count": 1}))
                step_id += 1

            subtasks.append(Subtask(id=f"step_{step_id}", action="craft", parameters={"item_name": item_name, "count": amt}))
            return Task(
                id=f"task_{g_type.lower()}",
                name=f"Craft {amt}x {item_name}",
                goal=goal,
                subtasks=subtasks
            )

        # 5. SMELT_ITEM
        if g_type == "SMELT_ITEM":
            item = params.get("item", "raw_iron")
            fuel = params.get("fuel", "coal")
            amt = params.get("count", 4)
            if "furnace" not in inv and self.count_total_cobblestone(inv) < 8:
                subtasks.append(Subtask(id=f"step_{step_id}", action="gather", parameters={"block_type": "stone", "count": 8}))
                step_id += 1
            if "furnace" not in inv:
                subtasks.append(Subtask(id=f"step_{step_id}", action="craft", parameters={"item_name": "furnace", "count": 1}))
                step_id += 1
            subtasks.append(Subtask(id=f"step_{step_id}", action="smelt", parameters={"item": item, "fuel": fuel, "count": amt}))
            return Task(
                id=f"task_{g_type.lower()}",
                name=f"Smelt {item}",
                goal=goal,
                subtasks=subtasks
            )

        # 6. FOLLOW_PLAYER
        if g_type == "FOLLOW_PLAYER":
            target = params.get("player", user)
            subtasks.append(Subtask(id=f"step_{step_id}", action="follow", parameters={"player": target}))
            return Task(id="task_follow", name=f"Follow {target}", goal=goal, subtasks=subtasks)

        # 7. PVP_COMBAT
        if g_type == "PVP_COMBAT":
            target = params.get("player", user)
            subtasks.append(Subtask(id=f"step_{step_id}", action="pvp", parameters={"player": target}))
            return Task(id="task_pvp", name=f"Duel {target}", goal=goal, subtasks=subtasks)

        # 8. PROTECT_PLAYER
        if g_type in ["PROTECT_PLAYER", "PROTECT"]:
            target = params.get("player", user)
            subtasks.append(Subtask(id=f"step_{step_id}", action="protect", parameters={"player": target}))
            return Task(id="task_protect", name=f"Protect {target}", goal=goal, subtasks=subtasks)

        # 9. ATTACK_MOBS
        if g_type == "ATTACK_MOBS":
            target = params.get("target_name")
            if target and target != "hostile":
                subtasks.append(Subtask(id=f"step_{step_id}", action="attack", parameters={"target_name": target}))
            else:
                subtasks.append(Subtask(id=f"step_{step_id}", action="kill_all_mobs", parameters={}))
            return Task(id="task_clear_mobs", name="Attack Hostiles", goal=goal, subtasks=subtasks)

        # 10. HUNT_FOOD
        if g_type == "HUNT_FOOD":
            animal = params.get("animal_name", "animal")
            amt = params.get("count", 2)
            subtasks.append(Subtask(id=f"step_{step_id}", action="hunt", parameters={"animal_name": animal, "count": amt}))
            return Task(id="task_hunt", name=f"Hunt {animal}", goal=goal, subtasks=subtasks)

        # 11. EAT_FOOD
        if g_type == "EAT_FOOD":
            subtasks.append(Subtask(id=f"step_{step_id}", action="eat", parameters={}))
            return Task(id="task_eat", name="Eat Food", goal=goal, subtasks=subtasks)

        # 12. SLEEP
        if g_type == "SLEEP":
            subtasks.append(Subtask(id=f"step_{step_id}", action="sleep", parameters={}))
            return Task(id="task_sleep", name="Sleep in Bed", goal=goal, subtasks=subtasks)

        # 13. BRIDGE
        if g_type == "BRIDGE":
            length = params.get("length", 8)
            mat = params.get("material", "wool")
            subtasks.append(Subtask(id=f"step_{step_id}", action="bridge", parameters={"length": length, "material": mat}))
            return Task(id="task_bridge", name="Construct Bridge", goal=goal, subtasks=subtasks)

        # 14. GIVE_ITEM
        if g_type == "GIVE_ITEM":
            item = params.get("item_name", "wood")
            amt = params.get("count", 2)
            target = params.get("player", user)
            subtasks.append(Subtask(id=f"step_{step_id}", action="give", parameters={"player": target, "item_name": item, "count": amt}))
            return Task(id="task_give", name=f"Give {item} to {target}", goal=goal, subtasks=subtasks)

        # 15. DROP_ALL
        if g_type == "DROP_ALL":
            target = params.get("player", user)
            subtasks.append(Subtask(id=f"step_{step_id}", action="drop_all", parameters={"player": target}))
            return Task(id="task_drop_all", name="Drop All Items", goal=goal, subtasks=subtasks)

        # 16. PICKUP
        if g_type == "PICKUP":
            subtasks.append(Subtask(id=f"step_{step_id}", action="pickup", parameters={}))
            return Task(id="task_pickup", name="Pickup Drops", goal=goal, subtasks=subtasks)

        # 17. GAMEMODE
        if g_type == "GAMEMODE":
            mode = params.get("mode", "survival")
            subtasks.append(Subtask(id=f"step_{step_id}", action="gamemode", parameters={"mode": mode}))
            return Task(id="task_gamemode", name=f"Set Gamemode {mode}", goal=goal, subtasks=subtasks)

        # 18. STOP
        if g_type == "STOP":
            subtasks.append(Subtask(id=f"step_{step_id}", action="stop", parameters={}))
            return Task(id="task_stop", name="Stop All Tasks", goal=goal, subtasks=subtasks)

        # Default fallback
        subtasks.append(Subtask(id=f"step_{step_id}", action=g_type.lower(), parameters=params))
        return Task(id=f"task_{g_type.lower()}", name=g_type, goal=goal, subtasks=subtasks)

    def decompose_goal(self, goal_name: str, state: Dict[str, Any], player_name: str = "Player") -> List[Dict[str, Any]]:
        """Legacy helper for backward compatibility."""
        goal = Goal(goal_type=goal_name.upper(), parameters={"item_name": goal_name}, target_player=player_name)
        task = self.create_task_from_goal(goal, state)
        return [{"cmd": s.action, "args": s.parameters} for s in task.subtasks]

    def get_next_autonomous_action(self, state: Dict[str, Any], has_home: bool = False) -> Optional[Dict[str, Any]]:
        """Legacy helper for tech tree state machine."""
        from ren.minecraft.perception import MinecraftPerceptionEngine
        from ren.minecraft.survival import MinecraftSurvivalEngine
        pe = MinecraftPerceptionEngine()
        se = MinecraftSurvivalEngine()
        summary = pe.summarize_state(state)
        act, _, _ = se.decide_next_survival_action(summary, has_home)
        return act
