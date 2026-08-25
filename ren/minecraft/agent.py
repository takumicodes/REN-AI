"""
REN-AI Minecraft Autonomous Embodied Agent 12.0
Unified Closed-Loop Coordinator:
PERCEIVE -> REMEMBER -> UNDERSTAND -> SET GOAL -> PLAN -> ACT -> OBSERVE RESULT -> VERIFY -> LEARN -> RECOVER -> REPLAN -> CONTINUE.
Integrates WorldState, EventBus, Multi-Store Memory, Procedural 3D Builder, Survival FSM, and Watchdog.
"""

import os
import sys
import re
import json
import time
import queue
import subprocess
import threading
import psutil
from pathlib import Path
from typing import Dict, Any, Optional, Callable, List, Tuple

from ren.minecraft.types import Goal, Task, Subtask, TaskStatus, PerceptionSummary, ActionResult, SurvivalPriority
from ren.minecraft.world_state import WorldState, PlayerEquipment
from ren.minecraft.events import MinecraftEventBus, MinecraftEvent, EventType, EventPriority
from ren.minecraft.memory import MinecraftMemorySystem
from ren.minecraft.skills import MinecraftSkillRegistry
from ren.minecraft.intent import MinecraftIntentParser
from ren.minecraft.planner import MinecraftGoalPlanner
from ren.minecraft.builder import MinecraftProceduralBuilder
from ren.minecraft.perception import MinecraftPerceptionEngine
from ren.minecraft.verifier import MinecraftActionVerifier
from ren.minecraft.watchdog import MinecraftStuckWatchdog
from ren.minecraft.survival import MinecraftSurvivalEngine
from ren.minecraft.task import MinecraftTaskManager
from ren.minecraft.rl_brain import MinecraftRLBrain
from ren.minecraft.curiosity import MinecraftCuriosityEngine
from ren.minecraft.speedrun import MinecraftSpeedrunEngine
from ren.minecraft.self_test import MinecraftSelfTestRunner
from ren.models import get_model_provider
from ren.monitoring.logger import agent_logger, error_logger


class MinecraftAgent:
    """
    Unified Autonomous Embodied Minecraft Agent for REN.
    Reliably translates natural language into verified, stateful in-game actions with full closed-loop control.
    """

    def __init__(
        self,
        host: str = "localhost",
        port: int = 1234,
        username: str = "RenAI",
        version: Optional[str] = None,
        auth: str = "offline",
        enable_rl: bool = True,
        enable_curiosity: bool = True
    ):
        self.host = host
        self.port = port
        self.username = username
        self.version = version
        self.auth = auth
        self.enable_rl = enable_rl
        self.enable_curiosity = enable_curiosity

        # Operational Modes: "COMPANION", "AUTONOMOUS_AGI", or "SPEEDRUN"
        self.mode: str = "SPEEDRUN"

        # Core Architectural Subsystems
        self.events = MinecraftEventBus()
        self.memory = MinecraftMemorySystem()
        self.world_state = WorldState()
        self.skill_registry = MinecraftSkillRegistry()
        self.intent_parser = MinecraftIntentParser(self.skill_registry)
        self.planner = MinecraftGoalPlanner()
        self.builder = MinecraftProceduralBuilder()
        self.perception_engine = MinecraftPerceptionEngine()
        self.verifier = MinecraftActionVerifier()
        self.watchdog = MinecraftStuckWatchdog()
        self.survival_engine = MinecraftSurvivalEngine()
        self.task_manager = MinecraftTaskManager()
        self.rl_brain = MinecraftRLBrain()
        self.curiosity_engine = MinecraftCuriosityEngine(cooldown_seconds=60.0)
        self.speedrun_engine = MinecraftSpeedrunEngine()
        self.self_test_runner = MinecraftSelfTestRunner()
        self.provider = get_model_provider()

        # Bridge Process & Communications
        self.process: Optional[subprocess.Popen] = None
        self.is_running: bool = False
        self.is_connected: bool = False

        # State Tracking
        self.last_state: Dict[str, Any] = {}
        self.pre_action_state: Dict[str, Any] = {}
        self.last_player_sender: Optional[str] = None
        self.last_action: Optional[str] = None
        self.last_state_key: Optional[str] = None
        self.has_built_home: bool = False

        # Concurrency & Locks
        self.is_busy: bool = False
        self.current_task_id: Optional[str] = None
        self._lock = threading.Lock()
        self.task_waiters: Dict[str, threading.Event] = {}
        self.task_results: Dict[str, Any] = {}

    def start(self):
        """Launches Node.js Mineflayer bridge subprocess with nice CPU priority."""
        bridge_script = Path(__file__).resolve().parent / "bridge" / "bot.js"
        if not bridge_script.exists():
            raise FileNotFoundError(f"Mineflayer bridge script not found at: {bridge_script}")

        cmd = [
            "node", str(bridge_script),
            "--host", self.host,
            "--port", str(self.port),
            "--username", self.username,
            "--auth", self.auth
        ]
        if self.version:
            cmd.extend(["--version", self.version])

        agent_logger.info(f"Starting Minecraft Bridge: {' '.join(cmd)}")
        self.is_running = True

        try:
            current_proc = psutil.Process()
            if sys.platform == "win32":
                current_proc.nice(psutil.BELOW_NORMAL_PRIORITY_CLASS)
        except Exception:
            pass

        self.process = subprocess.Popen(
            cmd,
            stdin=subprocess.PIPE,
            stdout=subprocess.PIPE,
            stderr=subprocess.PIPE,
            text=True,
            bufsize=1,
            cwd=str(bridge_script.parent)
        )

        self.reader_thread = threading.Thread(target=self._stdout_reader_loop, daemon=True)
        self.reader_thread.start()

        self.brain_thread = threading.Thread(target=self._autonomous_brain_loop, daemon=True)
        self.brain_thread.start()

    def stop(self):
        """Gracefully stops bot, saves memory, task state, and RL brain policy."""
        self.is_running = False
        if self.memory:
            self.memory.save_memory()
        if self.rl_brain:
            self.rl_brain.save_policy()
        if self.task_manager:
            self.task_manager.save_state()

        if self.process:
            try:
                self.send_command("chat", {"message": "See you later! Ren is logging off. 👋"})
                time.sleep(0.3)
                self.process.terminate()
            except Exception:
                pass

    def send_command(self, cmd: str, args: Optional[Dict[str, Any]] = None) -> Optional[str]:
        """Sends a JSON action command to the Node.js bridge."""
        if not self.process or not self.process.stdin:
            return None

        task_id = f"task_{int(time.time() * 1000)}"
        payload = {"cmd": cmd, "task_id": task_id, **(args or {})}

        try:
            with self._lock:
                self.pre_action_state = dict(self.last_state)

            if cmd not in ["chat", "stop"]:
                self.is_busy = True
                self.current_task_id = task_id
                self.watchdog.start_action_monitor(cmd, self.last_state.get("pos", {}))

            line = json.dumps(payload) + "\n"
            self.process.stdin.write(line)
            self.process.stdin.flush()
            return task_id
        except Exception as e:
            agent_logger.warning(f"Failed sending command to Minecraft bot: {e}")
            self.is_busy = False
            return None

    def send_chat(self, message: str):
        """Sends in-game public chat message."""
        self.send_command("chat", {"message": message})

    def _stdout_reader_loop(self):
        """Reads JSON event stream from Node.js bridge without blocking."""
        while self.is_running and self.process and self.process.stdout:
            try:
                line = self.process.stdout.readline()
                if not line:
                    break

                line = line.strip()
                if not line:
                    continue

                try:
                    event_data = json.loads(line)
                    self._handle_bridge_event(event_data)
                except json.JSONDecodeError:
                    agent_logger.debug(f"Mineflayer raw: {line}")
                except Exception as e:
                    agent_logger.error(f"Error handling bridge event: {e}", exc_info=True)
            except Exception as e:
                agent_logger.warning(f"Error in Minecraft stdout reader: {e}")
                break

    def _update_world_state(self, data: Dict[str, Any]):
        """Parses bridge telemetry into typed WorldState model."""
        eq_data = data.get("equipment", {})
        eq = PlayerEquipment(
            main_hand=eq_data.get("main_hand"),
            off_hand=eq_data.get("off_hand"),
            helmet=eq_data.get("helmet"),
            chestplate=eq_data.get("chestplate"),
            leggings=eq_data.get("leggings"),
            boots=eq_data.get("boots")
        )

        entities = data.get("entities", [])
        hostiles = [e for e in entities if e.get("isHostile")]
        passives = [e for e in entities if e.get("isAnimal")]
        players = [e for e in entities if e.get("isPlayer")]

        nearest_p = None
        nearest_d = 999.0
        if players:
            p_sorted = sorted(players, key=lambda p: p.get("distance", 999.0))
            nearest_p = p_sorted[0].get("name")
            nearest_d = p_sorted[0].get("distance", 999.0)

        pois = data.get("pois", {})

        self.world_state = WorldState(
            hp=data.get("hp", 20),
            max_hp=data.get("max_hp", 20),
            food=data.get("food", 20),
            saturation=data.get("saturation", 5.0),
            pos=data.get("pos", {"x": 0.0, "y": 64.0, "z": 0.0}),
            yaw=data.get("yaw", 0.0),
            pitch=data.get("pitch", 0.0),
            dimension=data.get("dimension", "overworld"),
            biome=data.get("biome", "plains"),
            inventory=data.get("inventory", {}),
            equipment=eq,
            time_of_day=data.get("timeOfDay", "day"),
            raw_time=data.get("rawTime", 1000),
            hostile_mobs=hostiles,
            passive_animals=passives,
            nearby_players=players,
            nearest_player=nearest_p,
            nearest_player_distance=nearest_d,
            nearby_crafting_tables=pois.get("crafting_tables", []),
            nearby_furnaces=pois.get("furnaces", []),
            nearby_beds=pois.get("beds", []),
            nearby_chests=pois.get("chests", []),
            nearby_hazards=pois.get("hazards", []),
            active_goal=self.task_manager.active_task.name if self.task_manager.active_task else None,
            active_subtask=self.task_manager.active_task.current_subtask.action if self.task_manager.active_task and self.task_manager.active_task.current_subtask else None,
            task_progress=self.task_manager.active_task.progress_percentage if self.task_manager.active_task else 0.0,
            is_moving=data.get("activeTask") is not None,
            threat_level="DANGER" if len(hostiles) > 0 else "SAFE"
        )

    def _handle_bridge_event(self, data: Dict[str, Any]):
        """Processes incoming events from Minecraft world."""
        event_type = data.get("event")

        if event_type == "ready":
            self.is_connected = True
            self.events.publish(MinecraftEvent(EventType.PLAYER_JOINED, EventPriority.LOW, data))
            agent_logger.info(f"Minecraft bot '{data.get('username')}' connected to {self.host}:{self.port}!")
            self.send_chat("Hello! Ren AI is online with verified task execution and procedural builder. ✨")

        elif event_type == "state":
            with self._lock:
                self.last_state = data
                self._update_world_state(data)
            self.watchdog.update_position(data.get("pos", {}))

        elif event_type == "chat":
            username = data.get("username")
            message = data.get("message")
            if username and message:
                self.events.publish(MinecraftEvent(EventType.PLAYER_SPOKE, EventPriority.LOW, {"username": username, "message": message}))
                threading.Thread(target=self._on_player_chat, args=(username, message), daemon=True).start()

        elif event_type == "damage_taken":
            hp = data.get("health", 0)
            agent_logger.info(f"Bot took damage! Current HP: {hp}")
            self.events.publish(MinecraftEvent(EventType.DAMAGE_TAKEN, EventPriority.CRITICAL, {"health": hp}))
            if self.rl_brain and self.last_state_key and self.last_action:
                self.rl_brain.update_q_value(
                    state_key=self.last_state_key,
                    action=self.last_action,
                    reward=-25.0,
                    next_state_key=self.rl_brain.discretize_state(self.last_state)
                )

        elif event_type == "death":
            agent_logger.warning("Bot died in Minecraft world! Applying RL death penalty.")
            self.events.publish(MinecraftEvent(EventType.DEATH, EventPriority.CRITICAL, data))
            
            # Save death location in spatial memory
            death_pos = data.get("position") or self.last_state.get("pos", {})
            if death_pos:
                self.memory.set_location("death_point", death_pos.get("x", 0), death_pos.get("y", 64), death_pos.get("z", 0))
                self.memory.record_episode("death", f"Died at X:{int(death_pos.get('x',0))} Z:{int(death_pos.get('z',0))}", importance=0.9, location=death_pos)

            self.is_busy = False
            self.task_manager.cancel_active_task("Bot died in game.")
            if self.rl_brain and self.last_state_key and self.last_action:
                self.rl_brain.update_q_value(
                    state_key=self.last_state_key,
                    action=self.last_action,
                    reward=-200.0,
                    next_state_key="DEAD"
                )
            self.send_chat("Ouch! I died... Respawning right now!")

        elif event_type == "task_done":
            task_id = data.get("task_id")
            cmd = data.get("cmd")
            if cmd == "chat":
                return

            self.is_busy = False
            self.current_task_id = None

            # Action Verification
            action_result = self.verifier.verify_action(
                action=cmd,
                parameters={},
                before_state=self.pre_action_state,
                after_state=self.last_state,
                bridge_result=data
            )

            if action_result.success:
                agent_logger.info(f"[VERIFY] Action={cmd} Success=True Details={action_result.details}")
            else:
                agent_logger.warning(f"[FAIL] Action={cmd} Reason={action_result.reason}")
                self.memory.record_failure(cmd, action_result.reason or "Verification failed", self.last_state)

            self.watchdog.record_action_result(action_result.success, cmd, action_result.reason)
            if cmd in ["build_structure", "build_shelter"] and action_result.success:
                self.has_built_home = True
                curr_pos = self.last_state.get("pos", {})
                self.memory.record_structure("small_house", curr_pos, {"width": 4, "length": 4, "height": 3}, action_result.details.get("placed_count", 0))
                self.memory.set_location("home_base", curr_pos.get("x", 0), curr_pos.get("y", 64), curr_pos.get("z", 0))

            # Signal any waiting threads
            if task_id in self.task_waiters:
                self.task_results[task_id] = action_result
                self.task_waiters[task_id].set()

            # Advance or Recover Persistent Task
            if self.task_manager.active_task:
                task_name = self.task_manager.active_task.name
                if action_result.success:
                    next_subtask = self.task_manager.advance_subtask()
                    if next_subtask:
                        threading.Thread(target=self._execute_subtask, args=(next_subtask,), daemon=True).start()
                    else:
                        self.events.publish(MinecraftEvent(EventType.TASK_COMPLETED, EventPriority.MEDIUM, {"task": task_name}))
                        self.memory.record_goal_completion(task_name, 10.0, True)
                else:
                    can_retry = self.task_manager.fail_current_subtask(action_result.reason or "Verification failed")
                    if can_retry and self.task_manager.active_task:
                        current_sub = self.task_manager.active_task.current_subtask
                        if current_sub:
                            time.sleep(1.0)
                            threading.Thread(target=self._execute_subtask, args=(current_sub,), daemon=True).start()
                    else:
                        self.events.publish(MinecraftEvent(EventType.TASK_FAILED, EventPriority.HIGH, {"task": task_name, "reason": action_result.reason}))

    def _on_player_chat(self, username: str, message: str):
        """
        Universal Intent Understanding & Task Execution:
        Translates natural language to verified Tasks.
        """
        try:
            self.last_player_sender = username
            agent_logger.info(f"Minecraft Chat [{username}]: '{message}'")

            # Parse Structured Goal
            goal = self.intent_parser.parse_intent(message, username)
            g_type = goal.goal_type
            agent_logger.info(f"[INTENT PARSED] GoalType: {g_type}, Params: {goal.parameters}")

            # 1. Stop Directive
            if g_type == "STOP":
                self.mode = "COMPANION"
                self.speedrun_engine.is_active = False
                self.task_manager.cancel_active_task("User stopped tasks")
                self.send_command("stop")
                self.send_chat(f"Stopped all tasks, {username}!")
                return

            # 1.1 Self-Test & Diagnostic Engine
            if g_type == "SELF_TEST":
                self.send_chat("Running complete Minecraft Embodied Self-Test... 🧪")
                passed, results, report = self.self_test_runner.run_all_self_tests()
                agent_logger.info(f"\n{report}")
                if passed:
                    self.send_chat(f"✅ Self-Test PASSED (100%)! All 10 embodied systems verified! 🚀")
                else:
                    failed_names = [r.test_name for r in results if not r.passed]
                    self.send_chat(f"⚠️ Self-Test completed with issues in: {', '.join(failed_names)}")
                return

            # 2. Speedrun Mode
            if g_type == "SPEEDRUN":
                self.mode = "SPEEDRUN"
                self.task_manager.cancel_active_task("Switched to speedrun")
                start_msg = self.speedrun_engine.start_speedrun()
                self.send_chat(start_msg)
                return

            # 3. Autonomous Survival Mode
            if g_type == "AUTONOMOUS_SURVIVAL":
                self.mode = "AUTONOMOUS_AGI"
                self.task_manager.cancel_active_task("Switched to autonomous survival")
                self.send_chat("Autonomous survival mode activated! Surviving and exploring independently.")
                return

            # 4. Status Check
            if g_type == "STATUS":
                p = self.perception_engine.summarize_state(self.last_state)
                inv_summary = ", ".join([f"{k}x{v}" for k, v in list(p.inventory.items())[:5]]) or "Empty"
                task_name = self.task_manager.active_task.name if self.task_manager.active_task else "Idle"
                msg = f"HP: {p.hp}/20 | Food: {p.food}/20 | Task: {task_name} | Pos: X:{int(p.pos['x'])} Z:{int(p.pos['z'])} | Bag: {inv_summary}"
                self.send_chat(msg)
                return

            # 5. Interactive Tasks (Default to COMPANION mode with top priority)
            self.mode = "COMPANION"
            self.task_manager.cancel_active_task("New player directive")

            # Plan hierarchical task
            task = self.planner.create_task_from_goal(goal, self.last_state)
            self.task_manager.create_task(task.name, goal, task.subtasks)
            agent_logger.info(f"[TASK CREATED] '{task.name}' with {len(task.subtasks)} subtasks. Progress: 0%")

            # Friendly acknowledgment
            if g_type == "BUILD_HOUSE":
                self.send_chat(f"Starting 3D construction of your wooden house, {username}! 🔨")
            elif g_type == "PVP_COMBAT":
                self.send_chat(f"Weapons armed! Let's duel, {username}! ⚔️")
            elif g_type == "FOLLOW_PLAYER":
                self.send_chat(f"Following you closely, {username}! 🏃")
            elif g_type == "COLLECT_RESOURCE":
                res = goal.parameters.get("resource", "resources")
                amt = goal.parameters.get("amount", 4)
                self.send_chat(f"Gathering {amt}x {res} for you right now!")
            else:
                self.send_chat(f"On it, {username}!")

            # Execute first subtask
            first_subtask = self.task_manager.active_task.current_subtask
            if first_subtask:
                self._execute_subtask(first_subtask)

        except Exception as e:
            agent_logger.warning(f"Error handling player chat: {e}")
            self.send_chat(f"Understood, {username}!")

    def _execute_subtask(self, subtask: Subtask):
        """Dispatches an atomic subtask to the Minecraft bridge."""
        if not subtask or not self.is_running:
            return

        cmd = subtask.action
        args = subtask.parameters
        agent_logger.info(f"[GOAL] {self.task_manager.active_task.name if self.task_manager.active_task else 'Task'}")
        agent_logger.info(f"[ACTION] {cmd} ({subtask.id}) with {args}")
        self.send_command(cmd, args)

    def _autonomous_brain_loop(self):
        """Background Decision & Watchdog Loop."""
        while self.is_running:
            time.sleep(3.0)

            if not self.is_connected or not self.last_state:
                continue

            pos = self.last_state.get("pos", {})

            # 1. Stuck Detection Watchdog
            if self.is_busy:
                is_stuck, reason = self.watchdog.check_is_stuck(pos)
                if is_stuck:
                    agent_logger.warning(f"[WATCHDOG TRIGGERED] {reason}")
                    if self.task_manager.active_task and self.task_manager.active_task.current_subtask:
                        curr_sub = self.task_manager.active_task.current_subtask
                        recovery_steps = self.watchdog.generate_recovery_plan(curr_sub.action, curr_sub.parameters)
                        for step in recovery_steps:
                            agent_logger.info(f"[RECOVERY] Executing recovery action: {step['cmd']}")
                            self.send_command(step["cmd"], step.get("args", {}))
                            time.sleep(0.5)
                        self.is_busy = False
                continue

            # If executing an active task, do not interrupt
            if self.task_manager.active_task and self.task_manager.active_task.status == TaskStatus.IN_PROGRESS:
                continue

            # 2. Speedrun Mode Execution
            if self.mode == "SPEEDRUN":
                action, split_msg = self.speedrun_engine.get_next_speedrun_action(self.last_state)
                if split_msg:
                    self.send_chat(split_msg)
                if action:
                    self.send_command(action["cmd"], action.get("args", {}))
                continue

            # 3. Companion Mode (Curiosity Observations)
            if self.mode == "COMPANION":
                perception = self.perception_engine.summarize_state(self.last_state)
                if self.enable_curiosity and perception.threat_level == "SAFE" and perception.hp >= 16:
                    question = self.curiosity_engine.check_for_curious_moments(
                        game_state=self.last_state,
                        player_username=self.last_player_sender
                    )
                    if question:
                        self.send_chat(question)
                continue

            # 4. Autonomous Survival Mode Execution (Priority FSM)
            if self.mode == "AUTONOMOUS_AGI":
                perception = self.perception_engine.summarize_state(self.last_state)
                action_dict, priority, rationale = self.survival_engine.decide_next_survival_action(perception, self.has_built_home)

                if action_dict:
                    agent_logger.info(f"[AUTONOMOUS SURVIVAL] Priority: {priority.value} | Action: {action_dict['cmd']} | Rationale: {rationale}")
                    self.send_command(action_dict["cmd"], action_dict.get("args", {}))

                # RL Q-learning update if enabled
                if self.enable_rl:
                    current_state = self.last_state
                    state_key = self.rl_brain.discretize_state(current_state)
                    rl_act, _ = self.rl_brain.choose_action(state_key)
                    self.last_action = rl_act
                    self.last_state_key = state_key

    def _parse_semantic_intent(self, username: str, text: str) -> Tuple[List[Dict[str, Any]], Optional[str]]:
        """Backward compatibility helper for parsing direct semantic actions."""
        goal = self.intent_parser.parse_intent(text, username)
        g_type = goal.goal_type
        params = goal.parameters

        if g_type == "COLLECT_RESOURCE":
            return [{"cmd": "gather", "args": {"block_type": params.get("resource", "wood"), "count": params.get("amount", 4)}}], None
        elif g_type == "HUNT_FOOD":
            return [{"cmd": "hunt", "args": {"animal_name": params.get("animal_name", "animal"), "count": params.get("count", 2)}}], None
        elif g_type == "CRAFT_ITEM":
            return [{"cmd": "craft", "args": {"item_name": params.get("item_name", "crafting_table"), "count": params.get("count", 1)}}], None
        elif g_type == "SMELT_ITEM":
            return [{"cmd": "smelt", "args": {"item": params.get("item", "raw_iron"), "fuel": params.get("fuel", "coal"), "count": params.get("count", 2)}}], None
        elif g_type == "GIVE_ITEM":
            return [{"cmd": "give", "args": {"player": params.get("player", username), "item_name": params.get("item_name", "wood"), "count": params.get("count", 2)}}], None
        elif g_type == "DROP_ALL":
            return [{"cmd": "drop_all", "args": {"player": params.get("player", username)}}], None
        elif g_type == "PVP_COMBAT":
            return [{"cmd": "pvp", "args": {"player": params.get("player", username)}}], None
        elif g_type == "PROTECT_PLAYER":
            return [{"cmd": "protect", "args": {"player": params.get("player", username)}}], None
        elif g_type == "ATTACK_MOBS":
            target = params.get("target_name") or params.get("target") or "zombie"
            return [{"cmd": "attack", "args": {"target_name": target}}], None
        elif g_type == "FOLLOW_PLAYER":
            return [{"cmd": "follow", "args": {"player": params.get("player", username)}}], None
        elif g_type in ["BUILD_HOUSE", "BUILD_SHELTER"]:
            return [{"cmd": "build_shelter", "args": {"size": 3}}], None
        elif g_type == "SLEEP":
            return [{"cmd": "sleep", "args": {}}], None
        elif g_type == "STOP":
            return [{"cmd": "stop", "args": {}}], None
        elif g_type == "BRIDGE":
            return [{"cmd": "bridge", "args": {"length": params.get("length", 8), "material": params.get("material", "wool")}}], None

        task = self.planner.create_task_from_goal(goal, self.last_state)
        return [{"cmd": s.action, "args": s.parameters} for s in task.subtasks], None
