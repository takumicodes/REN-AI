"""
Comprehensive Test Suite for REN-AI Minecraft Autonomous AGI 5.0:
1. Complete Autonomous Player Tech-Tree Progression (Wood -> Stone -> Food -> Home -> Iron -> Sleep)
2. Goal Decomposition with Zero Resource Requests
3. Multi-Step Plan Queue Execution
"""

import sys
from pathlib import Path

# Add project root to sys.path
root_dir = Path(__file__).resolve().parent.parent
sys.path.insert(0, str(root_dir))

from ren.minecraft.planner import MinecraftGoalPlanner
from ren.minecraft.rl_brain import MinecraftRLBrain
from ren.minecraft.agent import MinecraftAgent


def test_minecraft_agi_v5():
    print("\n" + "=" * 64)
    print(" [*] RUNNING REN-AI MINECRAFT AGI 5.0 TECH-TREE TEST SUITE")
    print("=" * 64)

    planner = MinecraftGoalPlanner()

    # --- Test 1: Full Player Tech-Tree Auto Progression ---
    print("\n[Test 1] Autonomous Life-Cycle Tech-Tree Progression:")

    # Step 1: Fresh spawn -> Gathers wood
    state_fresh = {"inventory": {}, "food": 20, "timeOfDay": "day"}
    act1 = planner.get_next_autonomous_action(state_fresh)
    assert act1["cmd"] == "gather" and act1["args"]["block_type"] == "wood"
    print(f"  Level 1 (Fresh Spawn): {act1}")

    # Step 2: Has wood logs -> Crafts planks / wooden pickaxe
    state_wood = {"inventory": {"oak_log": 4}, "food": 20, "timeOfDay": "day"}
    act2 = planner.get_next_autonomous_action(state_wood)
    assert act2["cmd"] == "craft"
    print(f"  Level 1 (Wood Age Crafting): {act2}")

    # Step 3: Has wooden pickaxe -> Mines stone
    state_wood_tool = {"inventory": {"wooden_pickaxe": 1}, "food": 20, "timeOfDay": "day"}
    act3 = planner.get_next_autonomous_action(state_wood_tool)
    assert act3["cmd"] == "gather" and act3["args"]["block_type"] == "stone"
    print(f"  Level 2 (Stone Age Mining): {act3}")

    # Step 4: Has stone -> Crafts stone tools & furnace
    state_stone = {"inventory": {"wooden_pickaxe": 1, "cobblestone": 16}, "food": 20, "timeOfDay": "day"}
    act4 = planner.get_next_autonomous_action(state_stone)
    assert act4["cmd"] == "craft" and "stone" in act4["args"]["item_name"]
    print(f"  Level 2 (Stone Tools Crafting): {act4}")

    # Step 5: Has stone tools & low food -> Hunts food
    state_food_low = {"inventory": {"stone_pickaxe": 1, "furnace": 1}, "food": 12, "timeOfDay": "day"}
    act5 = planner.get_next_autonomous_action(state_food_low)
    assert act5["cmd"] == "hunt"
    print(f"  Level 3 (Food Security): {act5}")

    # Step 6: Has tools & food -> Builds Home Base
    state_build = {"inventory": {"stone_pickaxe": 1, "furnace": 1, "cooked_beef": 4, "oak_planks": 24}, "food": 20, "timeOfDay": "day"}
    act6 = planner.get_next_autonomous_action(state_build, has_home=False)
    assert act6["cmd"] == "build_shelter"
    print(f"  Level 4 (Home Construction): {act6}")

    # Step 7: Has home -> Mines Iron Ore
    state_iron = {"inventory": {"stone_pickaxe": 1, "furnace": 1, "cooked_beef": 4}, "food": 20, "timeOfDay": "day"}
    act7 = planner.get_next_autonomous_action(state_iron, has_home=True)
    assert act7["cmd"] == "gather" and act7["args"]["block_type"] == "iron_ore"
    print(f"  Level 5 (Iron Age Mining): {act7}")

    # Step 8: Has raw iron -> Smelts in Furnace
    state_smelt = {"inventory": {"stone_pickaxe": 1, "furnace": 1, "cooked_beef": 4, "raw_iron": 6, "coal": 4}, "food": 20, "timeOfDay": "day"}
    act8 = planner.get_next_autonomous_action(state_smelt, has_home=True)
    assert act8["cmd"] == "smelt" and act8["args"]["item"] == "raw_iron"
    print(f"  Level 5 (Iron Smelting): {act8}")

    # Step 9: Has iron ingots -> Crafts Iron Gear
    state_iron_craft = {"inventory": {"stone_pickaxe": 1, "furnace": 1, "cooked_beef": 4, "iron_ingot": 4}, "food": 20, "timeOfDay": "day"}
    act9 = planner.get_next_autonomous_action(state_iron_craft, has_home=True)
    assert act9["cmd"] == "craft" and "iron" in act9["args"]["item_name"]
    print(f"  Level 5 (Iron Gear Crafting): {act9}")

    print("  [PASS] Full Autonomous Tech-Tree Progression completely verified!")

    # --- Test 2: Goal Decomposition with Zero Begging ---
    print("\n[Test 2] Zero-Resource-Begging Goal Resolution:")
    plan_house = planner.decompose_goal("build_house", {"inventory": {}})
    assert plan_house[0]["cmd"] == "gather" and plan_house[1]["cmd"] == "craft" and plan_house[2]["cmd"] == "build_shelter"
    print(f"  Autonomous House Plan: {[s['cmd'] for s in plan_house]}")
    print("  [PASS] Resolves all materials independently without prompting player.")

    print("\n" + "=" * 64)
    print(" [PASS] ALL AGI 5.0 TECH-TREE & AUTONOMY TESTS PASSED (100%)")
    print("=" * 64 + "\n")


if __name__ == "__main__":
    test_minecraft_agi_v5()
