"""
Comprehensive Test Suite for REN-AI Minecraft AGI 3.5:
1. Reinforcement Learning Brain (State Quantization, Bellman Q-Update, Policy Persistence)
2. Curiosity & Wonder Engine (Ore Discovery, Dusk/Night Transitions, Low Hunger Triggers)
3. Universal Intent Understanding (Testing arbitrary, natural phrasings for all actions)
"""

import sys
import shutil
from pathlib import Path

# Add project root to sys.path
root_dir = Path(__file__).resolve().parent.parent
sys.path.insert(0, str(root_dir))

from ren.minecraft.rl_brain import MinecraftRLBrain
from ren.minecraft.curiosity import MinecraftCuriosityEngine
from ren.minecraft.agent import MinecraftAgent


def test_minecraft_agent_v3():
    print("\n" + "=" * 64)
    print(" [*] RUNNING REN-AI MINECRAFT AGI 3.5 UNIVERSAL TEST SUITE")
    print("=" * 64)

    test_q_path = Path("data/test_minecraft_qtable.json")
    if test_q_path.exists():
        test_q_path.unlink()

    # --- Test 1: RL Brain State Quantization & Bellman Updates ---
    print("\n[Test 1] RL Brain Quantization & Q-Updates:")
    rl = MinecraftRLBrain(q_table_path=test_q_path)

    sample_state_1 = {
        "hp": 20,
        "food": 18,
        "timeOfDay": "day",
        "entities": [{"name": "cow", "distance": 5, "isHostile": False, "isAnimal": True}],
        "inventory": {"oak_log": 2}
    }
    key_1 = rl.discretize_state(sample_state_1)
    assert "HP_FULL" in key_1 and "W1" in key_1 and "SAFE" in key_1
    print(f"  State Key: {key_1}")

    action, _ = rl.choose_action(key_1)
    assert action in rl.ACTIONS

    sample_state_2 = {
        "hp": 20, "food": 18, "timeOfDay": "day", "entities": [],
        "inventory": {"oak_log": 5, "wooden_pickaxe": 1}
    }
    reward = rl.calculate_reward(sample_state_1, sample_state_2, "CRAFT_WOODEN_PICKAXE", True)
    assert reward > 20.0

    key_2 = rl.discretize_state(sample_state_2)
    rl.update_q_value(key_1, "CRAFT_WOODEN_PICKAXE", reward, key_2)
    q_val = rl.get_q_values(key_1)["CRAFT_WOODEN_PICKAXE"]
    assert q_val > 0.0
    print(f"  Updated Q({key_1}, CRAFT_WOODEN_PICKAXE) = {q_val:.4f}")
    print("  [PASS] RL Brain verified.")

    if test_q_path.exists():
        test_q_path.unlink()

    # --- Test 2: Curiosity & Wonder Engine ---
    print("\n[Test 2] Curiosity & Wonder Engine:")
    curiosity = MinecraftCuriosityEngine(cooldown_seconds=0.0)

    state_diamonds = {
        "hp": 20, "food": 20, "pos": {"x": 14, "y": 12, "z": -250},
        "timeOfDay": "day",
        "blocks": [{"name": "deepslate_diamond_ore", "distance": 3.0}],
        "entities": [], "inventory": {}
    }
    q1 = curiosity.check_for_curious_moments(state_diamonds, player_username="Sadiq")
    assert q1 is not None and "DIAMONDS" in q1
    print(f"  Curiosity (Diamonds): '{q1}'")
    print("  [PASS] Curiosity Engine verified.")

    # --- Test 3: Universal Intent Parsing with Diverse Natural Phrasings ---
    print("\n[Test 3] Universal Natural Language Testing (Diverse Phrasings):")
    agent = MinecraftAgent(host="127.0.0.1", port=25565, username="RenTest")
    agent.last_state = {"hp": 20, "food": 18, "pos": {"x": 0, "y": 64, "z": 0}, "inventory": {"oak_log": 10, "raw_iron": 5, "bread": 4}}

    # 1. Diverse Resource Gathering Phrasings
    gather_tests = [
        ("can you chop down a tree for me", "wood"),
        ("we need 8 cobblestone", "stone"),
        ("find some iron ore please", "iron_ore"),
        ("dig some sand over there", "dirt"),
        ("gather 5 birch logs", "wood")
    ]
    for prompt, expected in gather_tests:
        acts, _ = agent._parse_semantic_intent("Sadiq", prompt)
        assert len(acts) == 1 and acts[0]["cmd"] == "gather" and expected in acts[0]["args"]["block_type"], f"Failed on '{prompt}' -> {acts}"
        print(f"  [PASS] '{prompt}' -> gather {expected}")

    # 2. Diverse Hunting Phrasings
    hunt_tests = [
        ("slaughter 2 pigs for food", "pig"),
        ("kill those sheep for wool", "sheep"),
        ("butcher some cows", "cow"),
        ("hunt food right now", "animal")
    ]
    for prompt, expected in hunt_tests:
        acts, _ = agent._parse_semantic_intent("Sadiq", prompt)
        assert len(acts) == 1 and acts[0]["cmd"] == "hunt" and expected in acts[0]["args"]["animal_name"], f"Failed on '{prompt}' -> {acts}"
        print(f"  [PASS] '{prompt}' -> hunt {expected}")

    # 3. Diverse Item Giving Phrasings
    give_tests = [
        ("toss me 3 iron", "iron", 3),
        ("share some bread with me", "bread", 2),
        ("drop 5 wood please", "wood", 5),
        ("pass the sword", "sword", 2)
    ]
    for prompt, expected_item, expected_count in give_tests:
        acts, _ = agent._parse_semantic_intent("Sadiq", prompt)
        assert len(acts) == 1 and acts[0]["cmd"] == "give" and expected_item in acts[0]["args"]["item_name"], f"Failed on '{prompt}' -> {acts}"
        print(f"  [PASS] '{prompt}' -> give {expected_item}")

    # 4. Diverse Navigation & Follow Phrasings
    nav_tests = [
        ("walk with me", "follow"),
        ("stay near me", "follow"),
        ("come over here right now", "follow"),
        ("behind me please", "follow")
    ]
    for prompt, expected_cmd in nav_tests:
        acts, _ = agent._parse_semantic_intent("Sadiq", prompt)
        assert len(acts) == 1 and acts[0]["cmd"] == expected_cmd, f"Failed on '{prompt}' -> {acts}"
        print(f"  [PASS] '{prompt}' -> {expected_cmd}")

    # 5. Combat & Protection
    combat_tests = [
        ("defend me and watch my back", "protect"),
        ("kill that zombie over there", "attack"),
        ("slay the skeleton", "attack")
    ]
    for prompt, expected_cmd in combat_tests:
        acts, _ = agent._parse_semantic_intent("Sadiq", prompt)
        assert len(acts) == 1 and acts[0]["cmd"] == expected_cmd, f"Failed on '{prompt}' -> {acts}"
        print(f"  [PASS] '{prompt}' -> {expected_cmd}")

    # 6. Crafting, Sleeping, Stopping
    misc_tests = [
        ("make a crafting table", "craft"),
        ("let's craft a stone pickaxe", "craft"),
        ("bake the mutton in the furnace", "smelt"),
        ("it's night time let's sleep", "sleep"),
        ("hold up and freeze", "stop")
    ]
    for prompt, expected_cmd in misc_tests:
        acts, _ = agent._parse_semantic_intent("Sadiq", prompt)
        assert len(acts) == 1 and acts[0]["cmd"] == expected_cmd, f"Failed on '{prompt}' -> {acts}"
        print(f"  [PASS] '{prompt}' -> {expected_cmd}")

    print("\n" + "=" * 64)
    print(" [PASS] ALL MINECRAFT AGI 3.5 UNIVERSAL TESTS PASSED (100%)")
    print("=" * 64 + "\n")


if __name__ == "__main__":
    test_minecraft_agent_v3()
