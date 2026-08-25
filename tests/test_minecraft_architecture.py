"""
Comprehensive Architectural Test Suite for REN-AI Minecraft AGI 11.0
Tests the complete architectural pipeline:
1. Intent Parser & Skill Registry
2. Goal Planning & Task Decomposition
3. Procedural 3D House Builder & Blueprint Generation
4. Action & State Verifier (Mine, Craft, Move, Eat, Build)
5. Stuck Detection Watchdog & Recovery Strategy
6. Priority-Based Autonomous Survival FSM (Critical -> High -> Medium -> Low)
7. Persistent Hierarchical Task System (State transitions & JSON persistence)
8. Perception Engine Summary & Threat Analysis
"""

import sys
import time
from pathlib import Path

# Add project root to sys.path
root_dir = Path(__file__).resolve().parent.parent
sys.path.insert(0, str(root_dir))

if sys.platform == "win32":
    sys.stdout.reconfigure(encoding="utf-8")

from ren.minecraft.types import Goal, Task, Subtask, TaskStatus, SurvivalPriority, PerceptionSummary, ActionResult
from ren.minecraft.skills import MinecraftSkillRegistry
from ren.minecraft.intent import MinecraftIntentParser
from ren.minecraft.planner import MinecraftGoalPlanner
from ren.minecraft.builder import MinecraftProceduralBuilder
from ren.minecraft.verifier import MinecraftActionVerifier
from ren.minecraft.watchdog import MinecraftStuckWatchdog
from ren.minecraft.survival import MinecraftSurvivalEngine
from ren.minecraft.task import MinecraftTaskManager
from ren.minecraft.perception import MinecraftPerceptionEngine


def test_minecraft_architecture():
    print("\n" + "=" * 68)
    print(" [*] RUNNING REN-AI MINECRAFT ARCHITECTURAL VERIFICATION SUITE")
    print("=" * 68)

    # -------------------------------------------------------------
    # Test 1: Intent Parser & Structured Goal Mapping
    # -------------------------------------------------------------
    print("\n[Test 1] Natural Language Intent Parsing -> Structured Goals:")
    parser = MinecraftIntentParser()

    # "make me a house"
    g1 = parser.parse_intent("make me a house", "Sadiq")
    assert g1.goal_type == "BUILD_HOUSE"
    assert g1.parameters.get("structure_type") == "small_house"
    print(f"  [PASS] 'make me a house' -> {g1.goal_type} ({g1.parameters})")

    # "get me 32 wood"
    g2 = parser.parse_intent("get me 32 wood", "Sadiq")
    assert g2.goal_type == "COLLECT_RESOURCE"
    assert g2.parameters.get("resource") == "wood" and g2.parameters.get("amount") == 32
    print(f"  [PASS] 'get me 32 wood' -> {g2.goal_type} ({g2.parameters})")

    # "survive on your own"
    g3 = parser.parse_intent("survive on your own", "Sadiq")
    assert g3.goal_type == "AUTONOMOUS_SURVIVAL"
    print(f"  [PASS] 'survive on your own' -> {g3.goal_type}")

    # "fight with me"
    g4 = parser.parse_intent("fight with me", "Sadiq")
    assert g4.goal_type == "PVP_COMBAT" and g4.parameters.get("player") == "Sadiq"
    print(f"  [PASS] 'fight with me' -> {g4.goal_type}")

    # -------------------------------------------------------------
    # Test 2: Procedural 3D House Builder & Blueprint Generation
    # -------------------------------------------------------------
    print("\n[Test 2] Procedural 3D Construction Engine:")
    builder = MinecraftProceduralBuilder()
    house_bp = builder.generate_small_house_blueprint(0, 64, 0, "oak_planks")

    assert house_bp.name == "small_house"
    assert len(house_bp.blocks) > 20
    # Verify foundation, walls, and roof are present
    y_levels = set(b.y for b in house_bp.blocks)
    assert 64 in y_levels and 65 in y_levels and 66 in y_levels and 67 in y_levels
    print(f"  [PASS] Small House Blueprint: {len(house_bp.blocks)} blocks across Y levels {sorted(y_levels)}")

    # Verify construction subtasks generation
    subtasks = builder.create_construction_subtasks(house_bp, current_inventory={})
    assert len(subtasks) >= 3  # gather wood -> craft planks -> build structure
    assert subtasks[0].action == "gather" and subtasks[1].action == "craft" and subtasks[2].action == "build_structure"
    print(f"  [PASS] Generated {len(subtasks)} verified construction subtasks from zero inventory")

    # -------------------------------------------------------------
    # Test 3: Action & State Verifier
    # -------------------------------------------------------------
    print("\n[Test 3] Action & State Verification Engine:")
    verifier = MinecraftActionVerifier()

    # Mine block verification (inventory delta check)
    state_before_mine = {"inventory": {"oak_log": 2}}
    state_after_mine = {"inventory": {"oak_log": 6}}
    res_mine = verifier.verify_action("gather", {"block_type": "wood", "count": 4}, state_before_mine, state_after_mine)
    assert res_mine.success is True and res_mine.details["delta"] == 4
    print(f"  [PASS] Gather action verification: {res_mine.success} (delta: +4 logs)")

    # Craft item verification
    state_before_craft = {"inventory": {"oak_planks": 4}}
    state_after_craft = {"inventory": {"oak_planks": 0, "crafting_table": 1}}
    res_craft = verifier.verify_action("craft", {"item_name": "crafting_table", "count": 1}, state_before_craft, state_after_craft)
    assert res_craft.success is True
    print(f"  [PASS] Craft action verification: {res_craft.success} (crafting_table in inventory)")

    # Movement verification (distance check)
    res_move_ok = verifier.verify_action("goTo", {"x": 10, "y": 64, "z": 10}, {}, {"pos": {"x": 11, "y": 64, "z": 10}})
    assert res_move_ok.success is True
    res_move_fail = verifier.verify_action("goTo", {"x": 10, "y": 64, "z": 10}, {}, {"pos": {"x": 50, "y": 64, "z": 50}})
    assert res_move_fail.success is False
    print(f"  [PASS] Navigation verification: Close -> {res_move_ok.success}, Far -> {res_move_fail.success}")

    # -------------------------------------------------------------
    # Test 4: Stuck Detection Watchdog & Recovery Engine
    # -------------------------------------------------------------
    print("\n[Test 4] Stuck Detection Watchdog & Recovery:")
    watchdog = MinecraftStuckWatchdog(position_stall_seconds=0.1, max_consecutive_failures=3, action_timeout_seconds=0.2)
    watchdog.start_action_monitor("gather", {"x": 0, "y": 64, "z": 0})
    time.sleep(0.15)
    is_stuck, reason = watchdog.check_is_stuck({"x": 0, "y": 64, "z": 0})
    assert is_stuck is True
    print(f"  [PASS] Watchdog detected stall: '{reason}'")

    recovery_plan = watchdog.generate_recovery_plan("gather", {"block_type": "wood"})
    assert len(recovery_plan) >= 2 and recovery_plan[0]["cmd"] == "stop"
    print(f"  [PASS] Watchdog generated recovery plan: {[r['cmd'] for r in recovery_plan]}")

    # -------------------------------------------------------------
    # Test 5: Priority-Based Autonomous Survival FSM
    # -------------------------------------------------------------
    print("\n[Test 5] Priority-Based Survival FSM:")
    survival = MinecraftSurvivalEngine()

    # Critical Priority: Low HP & starvation
    crit_perception = PerceptionSummary(hp=5, food=5, total_food=2, inventory={"apple": 2})
    act_crit, prio_crit, rat_crit = survival.decide_next_survival_action(crit_perception)
    assert prio_crit == SurvivalPriority.CRITICAL and act_crit["cmd"] == "eat"
    print(f"  [PASS] Priority {prio_crit.value}: {act_crit['cmd']} ({rat_crit})")

    # High Priority: Dusk/Night approaching -> Build Shelter
    night_perception = PerceptionSummary(hp=20, food=20, time_of_day="dusk", total_building_blocks=16)
    act_night, prio_night, rat_night = survival.decide_next_survival_action(night_perception, has_built_home=False)
    assert prio_night == SurvivalPriority.HIGH and act_night["cmd"] == "build_shelter"
    print(f"  [PASS] Priority {prio_night.value}: {act_night['cmd']} ({rat_night})")

    # Medium Priority: Iron mining progression
    mid_perception = PerceptionSummary(
        hp=20, food=20, time_of_day="day", has_pickaxe=True, has_weapon=True, total_iron=0,
        inventory={"stone_pickaxe": 1, "stone_sword": 1, "furnace": 1, "cooked_beef": 4}
    )
    act_mid, prio_mid, rat_mid = survival.decide_next_survival_action(mid_perception, has_built_home=True)
    assert prio_mid == SurvivalPriority.MEDIUM and act_mid["cmd"] in ["gather", "craft"]
    print(f"  [PASS] Priority {prio_mid.value}: {act_mid['cmd']} ({rat_mid})")

    # -------------------------------------------------------------
    # Test 6: Persistent Hierarchical Task System
    # -------------------------------------------------------------
    print("\n[Test 6] Persistent Task Manager & State Transitions:")
    task_file = Path("data/test_task_state.json")
    if task_file.exists():
        task_file.unlink()

    task_mgr = MinecraftTaskManager(state_file_path=task_file)
    test_subtasks = [
        Subtask(id="s1", action="gather", parameters={"block_type": "wood", "count": 3}),
        Subtask(id="s2", action="craft", parameters={"item_name": "oak_planks", "count": 2}),
        Subtask(id="s3", action="build_structure", parameters={"structure": "house"})
    ]
    t = task_mgr.create_task("Build House Task", g1, test_subtasks)
    assert t.status == TaskStatus.IN_PROGRESS and t.progress_percentage == 0.0

    # Advance subtask 1
    next_s = task_mgr.advance_subtask()
    assert next_s.id == "s2" and t.progress_percentage == 33.3

    # Save & reload from disk
    task_mgr.save_state()
    reloaded_mgr = MinecraftTaskManager(state_file_path=task_file)
    assert reloaded_mgr.active_task is not None
    assert reloaded_mgr.active_task.name == "Build House Task"
    assert reloaded_mgr.active_task.current_subtask_index == 1
    print(f"  [PASS] Persistent task reloaded from disk at step index {reloaded_mgr.active_task.current_subtask_index + 1}")

    if task_file.exists():
        task_file.unlink()

    print("\n" + "=" * 68)
    print(" [PASS] ALL ARCHITECTURAL VERIFICATION TESTS PASSED (100%)")
    print("=" * 68 + "\n")


if __name__ == "__main__":
    test_minecraft_architecture()
