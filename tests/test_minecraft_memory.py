"""
Unit Test Suite for REN-AI Minecraft Multi-Store Memory System
"""

import sys
import tempfile
from pathlib import Path
root_dir = Path(__file__).resolve().parent.parent
if str(root_dir) not in sys.path:
    sys.path.insert(0, str(root_dir))

from ren.minecraft.memory import MinecraftMemorySystem


def test_minecraft_memory():
    print("\n" + "=" * 64)
    print(" [*] RUNNING MINECRAFT MULTI-STORE MEMORY TESTS")
    print("=" * 64)

    with tempfile.TemporaryDirectory() as tmpdir:
        mem_file = Path(tmpdir) / "test_minecraft_memory.json"
        mem = MinecraftMemorySystem(str(mem_file))

        # 1. Spatial Memory
        mem.set_location("home_base", 150.0, 64.0, -200.0)
        mem.set_location("cave_entrance", 180.0, 62.0, -210.0)

        loc = mem.get_location("home_base")
        assert loc == {"x": 150.0, "y": 64.0, "z": -200.0}

        poi_name, poi_pos, poi_dist = mem.find_nearest_poi({"x": 152.0, "z": -201.0})
        assert poi_name == "home_base"
        assert poi_dist < 3.0
        print("  [PASS] Spatial POI storage and nearest proximity search verified.")

        # 2. Episodic Memory
        mem.record_episode("found_diamonds", "Mined 4x diamonds in deepslate cave", 0.9, {"x": 180, "y": -58, "z": -210})
        assert len(mem.episodic_memory) == 1
        assert mem.episodic_memory[0].importance == 0.9
        print("  [PASS] Episodic event recording verified.")

        # 3. Structure Memory
        mem.record_structure("small_house", {"x": 150, "y": 64, "z": -200}, {"width": 4, "length": 4, "height": 3}, 54)
        assert "small_house" in mem.structure_memory
        print("  [PASS] Procedural structure recording verified.")

        # 4. Failure Memory & Repeated Mistake Prevention
        mem.record_failure("gather", "Unreachable top block", {"block": "oak_log"})
        mem.record_failure("gather", "Unreachable top block", {"block": "oak_log"})
        mem.record_failure("gather", "Unreachable top block", {"block": "oak_log"})
        assert mem.is_action_frequently_failing("gather", threshold=3) is True
        assert mem.is_action_frequently_failing("craft", threshold=3) is False
        print("  [PASS] Failure tracking and streak detection verified.")

        # 5. Persistence across reboots
        mem.save_memory()
        assert mem_file.exists()

        mem_reloaded = MinecraftMemorySystem(str(mem_file))
        assert mem_reloaded.get_location("home_base") == {"x": 150.0, "y": 64.0, "z": -200.0}
        assert len(mem_reloaded.episodic_memory) == 1
        assert "small_house" in mem_reloaded.structure_memory
        print("  [PASS] Persistence and disk re-loading verified.")

    print("\n" + "=" * 64)
    print(" [PASS] ALL MEMORY SYSTEM TESTS PASSED (100%)")
    print("=" * 64 + "\n")


if __name__ == "__main__":
    test_minecraft_memory()
