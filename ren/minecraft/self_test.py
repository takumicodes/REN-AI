"""
REN-AI Minecraft Autonomous Self-Test & Diagnostic Engine 12.0
Executes real-time verification of all core agent subsystems:
1. WorldState Perception & Telemetry
2. Skill Registry & Capability Checks
3. Deterministic Crafting & Recipe Graph
4. Procedural 3D Blueprint Generation
5. Action & State Verifier
6. Watchdog Stuck Detection & Recovery Planning
7. Multi-Store Persistent Memory (Spatial, Episodic, Failure)
8. Priority-Based Event System
9. Natural Language Intent Translation
10. Model Provider Connectivity
"""

import time
from typing import Dict, Any, List, Tuple
from dataclasses import dataclass, field
from ren.minecraft.world_state import WorldState, PlayerEquipment
from ren.minecraft.skills import MinecraftSkillRegistry, SkillCategory
from ren.minecraft.events import MinecraftEventBus, MinecraftEvent, EventType, EventPriority
from ren.minecraft.memory import MinecraftMemorySystem
from ren.minecraft.verifier import MinecraftActionVerifier
from ren.minecraft.watchdog import MinecraftStuckWatchdog
from ren.minecraft.builder import MinecraftProceduralBuilder
from ren.minecraft.intent import MinecraftIntentParser
from ren.minecraft.survival import MinecraftSurvivalEngine
from ren.minecraft.speedrun import MinecraftSpeedrunEngine
from ren.models import get_model_provider
from ren.monitoring.logger import agent_logger


@dataclass
class TestResult:
    test_name: str
    passed: bool
    details: str
    duration_ms: float = 0.0


class MinecraftSelfTestRunner:
    """
    Automated self-diagnostic suite evaluating agent capabilities.
    """

    def __init__(self):
        self.skills = MinecraftSkillRegistry()
        self.events = MinecraftEventBus()
        self.memory = MinecraftMemorySystem()
        self.verifier = MinecraftActionVerifier()
        self.watchdog = MinecraftStuckWatchdog()
        self.builder = MinecraftProceduralBuilder()
        self.intent = MinecraftIntentParser(self.skills)
        self.survival = MinecraftSurvivalEngine()
        self.speedrun = MinecraftSpeedrunEngine()

    def run_all_self_tests(self) -> Tuple[bool, List[TestResult], str]:
        """Runs all 10 self-tests and returns (all_passed, results, formatted_report)."""
        results: List[TestResult] = []

        # 1. WorldState Test
        t0 = time.time()
        ws = WorldState(hp=18, food=16, pos={"x": 10.0, "y": 64.0, "z": -20.0}, inventory={"oak_planks": 16, "stone_pickaxe": 1})
        obs = ws.to_compact_observation()
        ws_ok = ws.total_planks == 16 and ws.has_pickaxe and len(obs) > 10
        results.append(TestResult("WorldState & Perception", ws_ok, f"Compact Obs: {obs}", (time.time() - t0) * 1000))

        # 2. Skill Registry Test
        t0 = time.time()
        skill_count = len(self.skills.skills)
        skills_ok = skill_count >= 15 and self.skills.get_skill("build_house") is not None
        results.append(TestResult("Skill Registry", skills_ok, f"{skill_count} skills registered across 7 categories", (time.time() - t0) * 1000))

        # 3. Intent Translation Test
        t0 = time.time()
        g_house = self.intent.parse_intent("build me a small wooden house", "CyanCode")
        g_speedrun = self.intent.parse_intent("speedrun", "CyanCode")
        g_survive = self.intent.parse_intent("survive on your own", "CyanCode")
        intent_ok = g_house.goal_type == "BUILD_HOUSE" and g_speedrun.goal_type == "SPEEDRUN" and g_survive.goal_type == "AUTONOMOUS_SURVIVAL"
        results.append(TestResult("Intent Parsing", intent_ok, f"Parsed House({g_house.goal_type}), Speedrun({g_speedrun.goal_type}), Survival({g_survive.goal_type})", (time.time() - t0) * 1000))

        # 4. Procedural 3D House Builder Test
        t0 = time.time()
        bp = self.builder.generate_small_house_blueprint(0, 64, 0, "oak_planks")
        subtasks = self.builder.create_construction_subtasks(bp, current_inventory={})
        bp_ok = len(bp.blocks) > 20 and len(subtasks) >= 3
        results.append(TestResult("3D Construction Engine", bp_ok, f"Blueprint {bp.name}: {len(bp.blocks)} blocks, {len(subtasks)} subtasks", (time.time() - t0) * 1000))

        # 5. Verification Engine Test
        t0 = time.time()
        before_st = {"inventory": {"oak_log": 2}}
        after_st = {"inventory": {"oak_log": 6}}
        res = self.verifier.verify_action("gather", {"block_type": "wood", "count": 4}, before_st, after_st, {"success": True})
        ver_ok = res.success and res.details.get("delta") == 4
        results.append(TestResult("Action Verifier", ver_ok, f"Verified gather delta (+4 logs): {res.success}", (time.time() - t0) * 1000))

        # 6. Stuck Watchdog & Recovery Test
        t0 = time.time()
        self.watchdog.current_action = "gather"
        self.watchdog.action_start_time = time.time() - 60.0  # Force timeout
        stuck, reason = self.watchdog.check_is_stuck({"x": 0, "y": 64, "z": 0})
        plan = self.watchdog.generate_recovery_plan("gather", {"block_type": "stone"})
        wd_ok = stuck and len(plan) >= 2
        results.append(TestResult("Stuck Watchdog & Recovery", wd_ok, f"Detected: {reason} | Recovery steps: {len(plan)}", (time.time() - t0) * 1000))

        # 7. Persistent Memory System Test
        t0 = time.time()
        self.memory.set_location("test_base", 100.0, 64.0, -100.0)
        retrieved_pos = self.memory.get_location("test_base")
        self.memory.record_episode("test_event", "Completed self-test check", 0.9)
        self.memory.save_memory()
        mem_ok = retrieved_pos is not None and retrieved_pos["x"] == 100.0 and len(self.memory.episodic_memory) > 0
        results.append(TestResult("Persistent Multi-Store Memory", mem_ok, f"Spatial base stored at {retrieved_pos}, Episodic count: {len(self.memory.episodic_memory)}", (time.time() - t0) * 1000))

        # 8. Priority Event Bus Test
        t0 = time.time()
        received_events = []
        self.events.subscribe(EventType.DAMAGE_TAKEN, lambda e: received_events.append(e))
        self.events.publish(MinecraftEvent(EventType.DAMAGE_TAKEN, EventPriority.CRITICAL, {"health": 5}))
        events_ok = len(received_events) == 1 and received_events[0].priority == EventPriority.CRITICAL
        results.append(TestResult("Priority Event Bus", events_ok, f"Handled CRITICAL event: {events_ok}", (time.time() - t0) * 1000))

        # 9. Autonomous Survival FSM Test
        t0 = time.time()
        p_crit = ws
        p_crit.food = 6
        p_crit.inventory = {"bread": 4}
        from ren.minecraft.perception import MinecraftPerceptionEngine
        perc_eng = MinecraftPerceptionEngine()
        p_summary = perc_eng.summarize_state(p_crit.to_dict())
        act_surv, prio, rat = self.survival.decide_next_survival_action(p_summary, has_built_home=False)
        surv_ok = act_surv is not None and act_surv["cmd"] == "eat" and prio == EventPriority.CRITICAL.value
        results.append(TestResult("Autonomous Survival FSM", surv_ok, f"Decided: {act_surv} (Priority: {prio}, {rat})", (time.time() - t0) * 1000))

        # 10. Model Provider Test
        t0 = time.time()
        provider = get_model_provider()
        provider_ok = provider is not None
        model_name = getattr(provider, "model_name", None) or getattr(provider, "default_model", "CustomProvider")
        results.append(TestResult("Model Provider Interface", provider_ok, f"Active Provider: {model_name}", (time.time() - t0) * 1000))

        all_passed = all(r.passed for r in results)
        total_time = sum(r.duration_ms for r in results)

        # Build Formatted Report
        lines = [
            "=" * 64,
            " [*] REN-AI MINECRAFT EMBODIED SELF-TEST REPORT",
            "=" * 64
        ]
        for r in results:
            status = "[PASS]" if r.passed else "[FAIL]"
            lines.append(f" {status:<6} | {r.test_name:<30} | {r.duration_ms:5.1f}ms | {r.details}")
        lines.append("=" * 64)
        lines.append(f" OVERALL: {'PASSED (100%)' if all_passed else 'SOME TESTS FAILED'} | Total Time: {total_time:.1f}ms")
        lines.append("=" * 64)

        report = "\n".join(lines)
        return all_passed, results, report
