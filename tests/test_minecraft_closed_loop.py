"""
Integration Test Suite for REN-AI Minecraft Closed-Loop Architecture
Verifies:
PERCEIVE -> REMEMBER -> UNDERSTAND -> SET GOAL -> PLAN -> ACT -> OBSERVE RESULT -> VERIFY -> LEARN -> RECOVER -> REPLAN -> CONTINUE.
"""

import sys
from pathlib import Path
root_dir = Path(__file__).resolve().parent.parent
if str(root_dir) not in sys.path:
    sys.path.insert(0, str(root_dir))

from ren.minecraft.agent import MinecraftAgent
from ren.minecraft.world_state import WorldState
from ren.minecraft.events import EventType, EventPriority, MinecraftEvent
from ren.minecraft.types import Goal, TaskStatus


def test_closed_loop_architecture():
    print("\n" + "=" * 68)
    print(" [*] RUNNING REN-AI MINECRAFT CLOSED-LOOP EMBODIED ARCHITECTURE SUITE")
    print("=" * 68)

    agent = MinecraftAgent()
    agent.last_state = {
        "hp": 20,
        "food": 20,
        "pos": {"x": 0.0, "y": 64.0, "z": 0.0},
        "inventory": {"oak_log": 4},
        "entities": [],
        "timeOfDay": "day"
    }

    # -------------------------------------------------------------
    # Test 1: "REN, build me a house" -> Goal -> Plan -> Verify -> Memory
    # -------------------------------------------------------------
    print("\n[Test 1] Closed-Loop 'build me a house' Execution:")
    agent._on_player_chat("CyanCode", "REN, build me a house")

    assert agent.task_manager.active_task is not None
    assert agent.task_manager.active_task.name == "Build Small House"
    assert len(agent.task_manager.active_task.subtasks) >= 3
    print(f"  [PASS] Hierarchical Task Planned: {agent.task_manager.active_task.name} ({len(agent.task_manager.active_task.subtasks)} subtasks)")

    # Simulate subtask 1 completion (gather wood)
    agent._handle_bridge_event({
        "event": "task_done",
        "task_id": "step_1",
        "cmd": "gather",
        "success": True,
        "details": {"count": 12}
    })
    assert agent.task_manager.active_task.current_subtask_index == 1
    print(f"  [PASS] Subtask 1 verified and advanced to step {agent.task_manager.active_task.current_subtask_index + 1}")

    # Simulate final construction completion & spatial memory update
    agent._handle_bridge_event({
        "event": "task_done",
        "task_id": "step_final",
        "cmd": "build_structure",
        "success": True,
        "details": {"placed_count": 54}
    })
    assert agent.has_built_home is True
    assert agent.memory.get_location("home_base") is not None
    print(f"  [PASS] Structure verified and saved to spatial memory: {agent.memory.get_location('home_base')}")

    # -------------------------------------------------------------
    # Test 2: "REN, survive on your own" -> Autonomous Survival Controller
    # -------------------------------------------------------------
    print("\n[Test 2] Autonomous Survival Controller Activation:")
    agent._on_player_chat("CyanCode", "REN, survive on your own")
    assert agent.mode == "AUTONOMOUS_AGI"
    print("  [PASS] Autonomous survival mode activated.")

    # Critical Hunger Reflex
    agent.last_state["food"] = 5
    agent.last_state["inventory"]["cooked_beef"] = 3
    p = agent.perception_engine.summarize_state(agent.last_state)
    act_surv, prio, rat = agent.survival_engine.decide_next_survival_action(p, has_built_home=True)
    assert act_surv["cmd"] == "eat"
    assert prio.value == "CRITICAL"
    print(f"  [PASS] CRITICAL Survival Reflex Triggered: {act_surv['cmd']} ({rat})")

    # -------------------------------------------------------------
    # Test 3: Action Failure -> Recovery & Failure Memory
    # -------------------------------------------------------------
    print("\n[Test 3] Action Failure Detection, Diagnosis & Recovery:")
    # Simulate action failure
    agent._handle_bridge_event({
        "event": "task_done",
        "task_id": "test_fail",
        "cmd": "gather",
        "success": False,
        "error": "No oak_log found within 32 blocks"
    })
    assert len(agent.memory.failure_memory) > 0
    assert agent.memory.failure_memory[-1]["action"] == "gather"
    print(f"  [PASS] Failure recorded in memory: {agent.memory.failure_memory[-1]['reason']}")

    # -------------------------------------------------------------
    # Test 4: Stuck Detection Watchdog Recovery Plan
    # -------------------------------------------------------------
    print("\n[Test 4] Stuck Watchdog Detection & Recovery Plan Generation:")
    agent.watchdog.current_action = "gather"
    agent.watchdog.action_start_time = 0.0  # Force timeout
    stuck, reason = agent.watchdog.check_is_stuck({"x": 0, "y": 64, "z": 0})
    assert stuck is True
    plan = agent.watchdog.generate_recovery_plan("gather", {"block_type": "stone"})
    assert len(plan) >= 2
    print(f"  [PASS] Watchdog triggered: {reason} | Recovery steps: {[p['cmd'] for p in plan]}")

    # -------------------------------------------------------------
    # Test 5: Self-Test Diagnostic Chat Command
    # -------------------------------------------------------------
    print("\n[Test 5] Self-Test Diagnostic Chat Trigger:")
    agent._on_player_chat("CyanCode", "run self test")
    print("  [PASS] Self-test chat command executed.")

    print("\n" + "=" * 68)
    print(" [PASS] ALL CLOSED-LOOP ARCHITECTURAL TESTS PASSED (100%)")
    print("=" * 68 + "\n")


if __name__ == "__main__":
    test_closed_loop_architecture()
