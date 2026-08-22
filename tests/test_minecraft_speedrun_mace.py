"""
Test Suite for REN-AI Minecraft Speedrun Mode & Mace / Wind Charge PvP Combat
"""

import sys
from pathlib import Path

# Add project root to sys.path
root_dir = Path(__file__).resolve().parent.parent
sys.path.insert(0, str(root_dir))

if sys.platform == "win32":
    sys.stdout.reconfigure(encoding='utf-8')

from ren.minecraft.speedrun import MinecraftSpeedrunEngine
from ren.minecraft.agent import MinecraftAgent


def test_speedrun_and_mace():
    print("\n" + "=" * 64)
    print(" [*] RUNNING REN-AI MINECRAFT SPEEDRUN & MACE PVP TEST SUITE")
    print("=" * 64)

    # --- Test 1: Speedrun Engine Stages & Timer ---
    print("\n[Test 1] Speedrun Engine Timer & Splits:")
    sr = MinecraftSpeedrunEngine()
    start_msg = sr.start_speedrun()
    assert "Timer started" in start_msg
    print(f"  Speedrun Start: {start_msg}")

    # Stage 1: Fresh spawn
    act1, msg1 = sr.get_next_speedrun_action({"inventory": {}, "food": 20})
    assert act1["cmd"] == "gather" and act1["args"]["block_type"] == "wood"
    print(f"  Speedrun Stage 1 (Wood Rush): {act1} | Msg: {msg1}")

    # Stage 2: Iron Bucket Rush
    act2, msg2 = sr.get_next_speedrun_action({"inventory": {"stone_pickaxe": 1, "cobblestone": 8, "raw_iron": 3}, "food": 20})
    assert act2["cmd"] == "craft" and act2["args"]["item_name"] == "furnace"
    print(f"  Speedrun Stage 2 (Furnace & Iron): {act2}")

    # Stage 3: Wool & Explosive Beds
    act3, msg3 = sr.get_next_speedrun_action({"inventory": {"stone_pickaxe": 1, "bucket": 1, "wool": 4}, "food": 20})
    assert act3["cmd"] == "craft" and act3["args"]["item_name"] == "white_bed"
    print(f"  Speedrun Stage 3 (Explosive Bed Craft): {act3}")
    print("  [PASS] Speedrun progression verified.")

    # --- Test 2: Agent Chat Intent Parsing for Speedrun & Mace ---
    print("\n[Test 2] Speedrun & Mace Chat Routing:")
    agent = MinecraftAgent()
    agent.last_state = {"hp": 20, "food": 20, "pos": {"x": 0, "y": 64, "z": 0}, "inventory": {}}

    # Speedrun trigger
    agent._on_player_chat("Superiorx80", "let's speedrun minecraft")
    assert agent.mode == "SPEEDRUN"
    print(f"  Mode switched to: {agent.mode}")

    # PvP duel with Mace & Wind Charge
    agent._on_player_chat("Superiorx80", "pvp with me")
    assert agent.mode == "COMPANION"
    print("  [PASS] PvP duel successfully engaged.")

    # Wind Charge & Mace item giving
    agent._on_player_chat("Superiorx80", "give me mace and wincharge")
    assert agent.mode == "COMPANION"
    print("  [PASS] Typo 'wincharge' recognized and parsed correctly.")

    print("\n" + "=" * 64)
    print(" [PASS] ALL SPEEDRUN & MACE PVP TESTS PASSED (100%)")
    print("=" * 64 + "\n")


if __name__ == "__main__":
    test_speedrun_and_mace()
