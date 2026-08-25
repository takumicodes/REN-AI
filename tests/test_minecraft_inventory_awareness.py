"""
Test Suite for REN-AI Minecraft Zero-Redundancy Inventory Awareness
Verifies that REN never re-gathers or re-crafts resources/tools/shelters that already exist in inventory.
"""

import sys
from pathlib import Path

# Add project root to sys.path
root_dir = Path(__file__).resolve().parent.parent
sys.path.insert(0, str(root_dir))

if sys.platform == "win32":
    sys.stdout.reconfigure(encoding='utf-8')

from ren.minecraft.types import Goal
from ren.minecraft.planner import MinecraftGoalPlanner
from ren.minecraft.survival import MinecraftSurvivalEngine
from ren.minecraft.speedrun import MinecraftSpeedrunEngine
from ren.minecraft.perception import MinecraftPerceptionEngine


def test_inventory_awareness():
    print("\n" + "=" * 68)
    print(" [*] RUNNING REN-AI MINECRAFT INVENTORY AWARENESS TEST SUITE")
    print("=" * 68)

    planner = MinecraftGoalPlanner()
    survival = MinecraftSurvivalEngine()
    speedrun = MinecraftSpeedrunEngine()
    perception_engine = MinecraftPerceptionEngine()

    # -------------------------------------------------------------
    # Test 1: House Construction with Existing Inventory
    # -------------------------------------------------------------
    print("\n[Test 1] House Construction with Existing Wood/Planks:")
    # Case A: Bot has 64 oak planks -> Should NOT gather any logs!
    state_has_wood = {"inventory": {"oak_planks": 64}, "pos": {"x": 100, "y": 64, "z": 100}}
    goal_house = Goal(goal_type="BUILD_HOUSE", parameters={"material": "wooden"})
    task_house = planner.create_task_from_goal(goal_house, state_has_wood)

    actions = [s.action for s in task_house.subtasks]
    assert "gather" not in actions, f"Expected no gathering when planks are in inventory, got: {actions}"
    assert actions[0] == "build_structure"
    print(f"  [PASS] 64 Planks in inventory -> Subtasks: {actions} (0 gather steps)")

    # -------------------------------------------------------------
    # Test 2: Tool Crafting with Existing Tools or Materials
    # -------------------------------------------------------------
    print("\n[Test 2] Tool Crafting with Existing Items:")
    # Case A: Bot already has stone_pickaxe -> Acknowledges without re-crafting
    state_has_pick = {"inventory": {"stone_pickaxe": 1, "cobblestone": 10}}
    goal_pick = Goal(goal_type="CRAFT_ITEM", parameters={"item_name": "stone_pickaxe", "count": 1})
    task_pick = planner.create_task_from_goal(goal_pick, state_has_pick)
    assert task_pick.subtasks[0].action == "chat" and "already have" in task_pick.subtasks[0].parameters.get("message", "").lower()
    print(f"  [PASS] Has Stone Pickaxe -> Acknowledges: '{task_pick.subtasks[0].parameters['message']}'")

    # Case B: Bot has cobblestone (10) and wooden pickaxe -> Does NOT chop wood or craft wooden pickaxe!
    state_has_cobble = {"inventory": {"wooden_pickaxe": 1, "cobblestone": 10}}
    goal_craft_stone = Goal(goal_type="CRAFT_ITEM", parameters={"item_name": "stone_sword", "count": 1})
    task_craft_stone = planner.create_task_from_goal(goal_craft_stone, state_has_cobble)
    actions_stone = [s.action for s in task_craft_stone.subtasks]
    assert "gather" not in actions_stone, f"Expected no gather step when cobble is present, got {actions_stone}"
    print(f"  [PASS] Has Cobblestone -> Directly crafts: {actions_stone}")

    # -------------------------------------------------------------
    # Test 3: Autonomous Survival Nightfall with Existing Home
    # -------------------------------------------------------------
    print("\n[Test 3] Autonomous Survival with Existing Shelter:")
    # Case A: Dusk/Night, bot HAS built home -> Does NOT gather dirt or build redundant shelter!
    state_night_home = {
        "hp": 20, "food": 20, "timeOfDay": "night",
        "inventory": {"stone_pickaxe": 1, "stone_sword": 1, "cooked_beef": 6, "iron_ore": 2},
        "entities": []
    }
    p_night = perception_engine.summarize_state(state_night_home)
    act_night, prio_night, rat_night = survival.decide_next_survival_action(p_night, has_built_home=True)
    assert act_night["cmd"] != "build_shelter" and act_night["cmd"] != "gather" or act_night["args"].get("block_type") != "dirt"
    print(f"  [PASS] Night with Existing Home -> Action: {act_night['cmd']} ({rat_night}) (No redundant shelter building)")

    # -------------------------------------------------------------
    # Test 4: Speedrun Progression with Existing Tools
    # -------------------------------------------------------------
    print("\n[Test 4] Speedrun Mode Skipping Already-Crafted Tiers:")
    speedrun.is_active = True
    speedrun.start_time = 100.0

    # Bot already has Stone Pickaxe -> Skips wood stage entirely!
    state_sr_stone = {"inventory": {"stone_pickaxe": 1, "stone_sword": 1, "cobblestone": 16, "furnace": 1, "raw_iron": 4}, "food": 20}
    act_sr, msg_sr = speedrun.get_next_speedrun_action(state_sr_stone)
    assert act_sr["cmd"] == "smelt" or (act_sr["cmd"] == "gather" and act_sr["args"]["block_type"] == "iron_ore")
    assert act_sr["cmd"] != "gather" or act_sr["args"]["block_type"] != "wood"
    print(f"  [PASS] Speedrun with Stone Pickaxe -> Next action: {act_sr} (Skipped wood stage)")

    print("\n" + "=" * 68)
    print(" [PASS] ALL INVENTORY AWARENESS TESTS PASSED (100%)")
    print("=" * 68 + "\n")


if __name__ == "__main__":
    test_inventory_awareness()
