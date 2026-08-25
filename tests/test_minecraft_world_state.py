"""
Unit Test Suite for REN-AI Minecraft WorldState & Perception Model
"""

import sys
from pathlib import Path
root_dir = Path(__file__).resolve().parent.parent
if str(root_dir) not in sys.path:
    sys.path.insert(0, str(root_dir))

from ren.minecraft.world_state import WorldState, PlayerEquipment


def test_world_state_model():
    print("\n" + "=" * 64)
    print(" [*] RUNNING MINECRAFT WORLDSTATE UNIT TESTS")
    print("=" * 64)

    eq = PlayerEquipment(
        main_hand="iron_sword",
        off_hand="shield",
        helmet="iron_helmet",
        chestplate="iron_chestplate"
    )

    ws = WorldState(
        hp=18,
        food=14,
        saturation=4.5,
        pos={"x": 120.5, "y": 64.0, "z": -350.2},
        biome="forest",
        inventory={
            "oak_log": 4,
            "oak_planks": 12,
            "cobblestone": 16,
            "iron_ingot": 3,
            "raw_iron": 6,
            "cooked_beef": 5,
            "stone_pickaxe": 1
        },
        equipment=eq,
        time_of_day="day",
        active_goal="Build House",
        active_subtask="gather",
        task_progress=33.3
    )

    # 1. Properties & Accessors
    assert ws.total_logs == 4, f"Expected 4 logs, got {ws.total_logs}"
    assert ws.total_planks == 12, f"Expected 12 planks, got {ws.total_planks}"
    assert ws.total_cobblestone == 16, f"Expected 16 cobble, got {ws.total_cobblestone}"
    assert ws.total_iron == 3, f"Expected 3 iron, got {ws.total_iron}"
    assert ws.total_raw_iron == 6, f"Expected 6 raw iron, got {ws.total_raw_iron}"
    assert ws.total_food == 5, f"Expected 5 food, got {ws.total_food}"
    assert ws.has_weapon is True
    assert ws.has_pickaxe is True
    assert ws.has_shield is True
    assert ws.has_item("planks", 10) is True
    assert ws.has_item("diamond", 1) is False
    assert ws.get_item_count("oak_log") == 4
    print("  [PASS] WorldState properties and helper accessors verified.")

    # 2. Compact Observation Generation
    compact_obs = ws.to_compact_observation()
    assert "[HP:18/20|FD:14/20|Time:day|Threat:SAFE]" in compact_obs
    assert "Pos:(120,64,-350)" in compact_obs
    assert len(compact_obs) < 250, "Compact observation must remain token-efficient"
    print(f"  [PASS] Compact observation verified ({len(compact_obs)} chars): {compact_obs}")

    # 3. Serialization
    d = ws.to_dict()
    assert d["hp"] == 18
    assert d["biome"] == "forest"
    assert d["equipment"]["main_hand"] == "iron_sword"
    print("  [PASS] WorldState serialization verified.")

    print("\n" + "=" * 64)
    print(" [PASS] ALL WORLDSTATE TESTS PASSED (100%)")
    print("=" * 64 + "\n")


if __name__ == "__main__":
    test_world_state_model()
