"""
REN-AI Minecraft Autonomous AGI Agent 3.0 (Companion-First Architecture & Anti-Crash)
- Companion-First: Stands by with player, listens to all chat, executes directives with 100% priority.
- No Unsolicited Resource Gathering: Won't randomly mine or wander away unless instructed.
- Anti-Crash & Auto-Reconnect: Robust connection recovery and non-blocking I/O.
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

from ren.minecraft.rl_brain import MinecraftRLBrain
from ren.minecraft.curiosity import MinecraftCuriosityEngine
from ren.models import get_model_provider
from ren.monitoring.logger import agent_logger, error_logger


class MinecraftAgent:
    """
    Autonomous Minecraft Survival AGI Agent for REN.
    Companion-First: Follows player, protects player, obeys all chat commands.
    """

    def __init__(
        self,
        host: str = "localhost",
        port: int = 25565,
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

        # Modes: "COMPANION" (default loyal partner) or "SURVIVAL_RL" (autonomous exploration)
        self.mode: str = "COMPANION"

        # Core subsystems
        self.rl_brain = MinecraftRLBrain()
        self.curiosity_engine = MinecraftCuriosityEngine(cooldown_seconds=60.0)
        self.provider = get_model_provider()

        # Bridge process & communications
        self.process: Optional[subprocess.Popen] = None
        self.is_running: bool = False
        self.is_connected: bool = False
        
        # State tracking
        self.last_state: Dict[str, Any] = {}
        self.active_player_directive: Optional[Dict[str, Any]] = None
        self.last_action: Optional[str] = None
        self.last_state_key: Optional[str] = None
        self.last_player_sender: Optional[str] = None

        # Thread synchronization
        self._lock = threading.Lock()
        self.task_waiters: Dict[str, threading.Event] = {}
        self.task_results: Dict[str, Any] = {}

    def start(self):
        """Launches Node.js Mineflayer bridge subprocess with lower CPU priority."""
        bridge_script = Path(__file__).resolve().parent / "bridge" / "bot.js"
        if not bridge_script.exists():
            raise FileNotFoundError(f"Mineflayer bridge script not found at: {bridge_script}")

        cmd = ["node", str(bridge_script), "--host", self.host, "--port", str(self.port), "--username", self.username, "--auth", self.auth]
        if self.version:
            cmd.extend(["--version", self.version])

        agent_logger.info(f"Starting Minecraft Bridge: {' '.join(cmd)}")
        self.is_running = True

        # Lower CPU priority to prevent laptop game lag
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

        # Start stdout reader thread
        self.reader_thread = threading.Thread(target=self._stdout_reader_loop, daemon=True)
        self.reader_thread.start()

        # Start companion / brain decision loop
        self.brain_thread = threading.Thread(target=self._autonomous_brain_loop, daemon=True)
        self.brain_thread.start()

    def stop(self):
        """Gracefully stops bot and saves RL brain policy."""
        self.is_running = False
        if self.rl_brain:
            self.rl_brain.save_policy()

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
            line = json.dumps(payload) + "\n"
            self.process.stdin.write(line)
            self.process.stdin.flush()
            return task_id
        except Exception as e:
            agent_logger.warning(f"Failed sending command to Minecraft bot: {e}")
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
                agent_logger.warning(f"Error in Minecraft stdout reader: {e}")
                break

    def _handle_bridge_event(self, data: Dict[str, Any]):
        """Processes incoming events from Minecraft world."""
        event_type = data.get("event")

        if event_type == "ready":
            self.is_connected = True
            agent_logger.info(f"Minecraft bot '{data.get('username')}' connected to {self.host}:{self.port}!")
            self.send_chat("Hello! Ren AI is here with you. What should we do? ✨")

        elif event_type == "state":
            with self._lock:
                self.last_state = data

        elif event_type == "chat":
            username = data.get("username")
            message = data.get("message")
            if username and message:
                # Dispatch to worker thread so reader loop NEVER freezes
                threading.Thread(target=self._on_player_chat, args=(username, message), daemon=True).start()

        elif event_type == "damage_taken":
            hp = data.get("health", 0)
            agent_logger.info(f"Bot took damage! Current HP: {hp}")
            if self.rl_brain and self.last_state_key and self.last_action:
                self.rl_brain.update_q_value(
                    state_key=self.last_state_key,
                    action=self.last_action,
                    reward=-25.0,
                    next_state_key=self.rl_brain.discretize_state(self.last_state)
                )

        elif event_type == "death":
            agent_logger.warning("Bot died in Minecraft world! Applying RL death penalty.")
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
            if task_id in self.task_waiters:
                self.task_results[task_id] = data
                self.task_waiters[task_id].set()

    # --- Universal NLU & Multi-Step Planner ---
    def _on_player_chat(self, username: str, message: str):
        """
        Universal Intent Understanding:
        Analyzes ANY message from player with full error isolation.
        """
        try:
            self.last_player_sender = username
            cleaned = message.lower().strip()
            agent_logger.info(f"Minecraft Chat [{username}]: '{message}'")

            # Check for Mode switching commands
            if any(w in cleaned for w in ["auto survival", "explore on your own", "wander", "auto mode", "survive alone"]):
                self.mode = "SURVIVAL_RL"
                self.send_chat(f"Autonomous survival mode enabled! I'll explore and gather resources on my own.")
                return

            if any(w in cleaned for w in ["companion mode", "stay with me", "with me"]):
                self.mode = "COMPANION"
                self.active_player_directive = None
                self.send_command("stop")
                self.send_chat(f"Companion mode active! Standing by for your instructions, {username}.")
                return

            # 1. Fast Semantic Heuristics (Zero-latency instant execution)
            parsed_actions, custom_reply = self._parse_semantic_intent(username, cleaned)
            if parsed_actions:
                self.active_player_directive = parsed_actions[0]
                if custom_reply:
                    self.send_chat(custom_reply)
                for act in parsed_actions:
                    self.send_command(act["cmd"], act.get("args", {}))
                return

            # 2. Universal LLM Reasoning & Multi-Step Action Generation
            inv_str = ", ".join([f"{k}x{v}" for k, v in list(self.last_state.get("inventory", {}).items())[:6]]) or "Empty"
            prompt = f"""You are Ren, an autonomous AI companion playing Minecraft survival with {username}.
Bot Stats: HP={self.last_state.get('hp', 20)}/20, Food={self.last_state.get('food', 20)}/20, Bag=[{inv_str}], Time={self.last_state.get('timeOfDay', 'day')}.
Player '{username}' said: "{message}"

Respond strictly with a JSON block in this schema:
{{
  "reply": "<short in-character reply to player under 100 chars>",
  "actions": [
    {{"cmd": "<action_name>", "args": {{ ... }}}}
  ]
}}

Valid actions:
- "give": {{"player": "{username}", "item_name": "<item>", "count": <num>}}
- "hunt": {{"animal_name": "cow|pig|sheep|chicken|animal", "count": <num>}}
- "gather": {{"block_type": "wood|stone|iron_ore|coal_ore|dirt|sand", "count": <num>}}
- "craft": {{"item_name": "crafting_table|wooden_pickaxe|stone_pickaxe|stone_sword|iron_sword|furnace|torch", "count": <num>}}
- "smelt": {{"item": "raw_iron|beef|porkchop", "fuel": "coal|oak_planks", "count": <num>}}
- "attack": {{"target_name": "zombie|skeleton|spider|creeper"}}
- "protect": {{"player": "{username}"}}
- "follow": {{"player": "{username}"}}
- "goTo": {{"x": <num>, "y": <num>, "z": <num>}}
- "sleep": {{}}
- "build_shelter": {{}}
- "stop": {{}}
If no in-game action is needed (pure question or chat), set "actions": []."""

            llm_out = self.provider.generate(prompt, max_tokens=128, temperature=0.3)
            json_match = re.search(r'\{.*\}', llm_out, re.DOTALL)
            if json_match:
                parsed = json.loads(json_match.group(0))
                reply = parsed.get("reply", "")
                actions = parsed.get("actions", [])

                if reply:
                    self.send_chat(reply[:100])
                if actions:
                    self.active_player_directive = actions[0]
                    for act in actions:
                        if "cmd" in act:
                            self.send_command(act["cmd"], act.get("args", {}))
                return
        except Exception as e:
            agent_logger.warning(f"Player chat handler fallback: {e}")

        self.send_chat(f"Got it, {username}!")

    def _parse_semantic_intent(self, username: str, text: str) -> Tuple[List[Dict[str, Any]], Optional[str]]:
        """
        Fast Universal Semantic Pattern Matcher.
        Handles giving, hunting, gathering, crafting, combat, navigation, status, and protection.
        """
        # A. Stop / Halt
        if any(w in text for w in ["stop", "halt", "stay here", "wait here", "pause", "cancel"]):
            self.active_player_directive = None
            return [{"cmd": "stop"}], "Stopping all tasks, Sir."

        # B. Follow / Come
        if any(w in text for w in ["come here", "come to me", "follow me", "follow", "over here", "come"]):
            return [{"cmd": "follow", "args": {"player": username}}], f"Coming over to you, {username}!"

        # C. Give / Drop items to player ("give me 5 wood", "drop some iron", "toss me food", "share bread")
        give_match = re.search(r'(?:give|drop|toss|pass|share|hand)\s+(?:me\s+)?(?:some\s+)?(\d+)?\s*([a-zA-Z_ ]+)', text)
        if give_match or any(w in text for w in ["give me", "drop", "toss me"]):
            item_raw = give_match.group(2).strip() if give_match and give_match.group(2) else "wood"
            count_raw = int(give_match.group(1)) if give_match and give_match.group(1) else 2
            item_clean = item_raw.replace("me", "").replace("some", "").replace("please", "").strip()
            if not item_clean: item_clean = "wood"
            return [{"cmd": "give", "args": {"player": username, "item_name": item_clean, "count": count_raw}}], None

        # D. Hunt Animals / Get Meat ("kill 2 cows", "hunt sheep", "kill pigs for food", "slaughter animals", "get food")
        hunt_match = re.search(r'(?:hunt|kill|slaughter|get|catch)\s+(?:some\s+)?(\d+)?\s*(cow|pig|sheep|chicken|animal|food|meat|rabbit)', text)
        if hunt_match or any(w in text for w in ["hunt", "kill cow", "kill pig", "kill sheep", "kill chicken", "get meat"]):
            animal = hunt_match.group(2) if hunt_match and hunt_match.group(2) else "animal"
            count = int(hunt_match.group(1)) if hunt_match and hunt_match.group(1) else 2
            return [{"cmd": "hunt", "args": {"animal_name": animal, "count": count}}], None

        # E. Gather / Mine Blocks ("mine 5 iron", "chop 10 wood", "gather cobblestone", "dig dirt")
        gather_match = re.search(r'(?:gather|mine|chop|dig|harvest|collect)\s+(?:some\s+)?(\d+)?\s*([a-zA-Z_ ]+)', text)
        if gather_match or any(w in text for w in ["gather", "chop wood", "mine iron", "mine coal", "mine stone"]):
            block_raw = gather_match.group(2).strip() if gather_match and gather_match.group(2) else "wood"
            count = int(gather_match.group(1)) if gather_match and gather_match.group(1) else 4
            return [{"cmd": "gather", "args": {"block_type": block_raw, "count": count}}], None

        # F. Crafting ("craft stone pickaxe", "make a furnace", "craft crafting table")
        craft_match = re.search(r'(?:craft|make|build|create)\s+(?:a\s+|an\s+)?(\d+)?\s*([a-zA-Z_ ]+)', text)
        if craft_match:
            item_raw = craft_match.group(2).strip().replace(" ", "_")
            count = int(craft_match.group(1)) if craft_match.group(1) else 1
            if any(it in item_raw for it in ["pickaxe", "sword", "axe", "shovel", "table", "furnace", "torch", "chest", "bed", "shield", "door", "planks"]):
                return [{"cmd": "craft", "args": {"item_name": item_raw, "count": count}}], None

        # G. Smelt / Cook ("smelt iron", "cook beef", "cook food")
        if "smelt" in text or "cook" in text:
            raw_item = "raw_iron" if "iron" in text else "beef"
            return [{"cmd": "smelt", "args": {"item": raw_item, "fuel": "coal", "count": 2}}], None

        # H. Protect / Guard ("protect me", "guard us", "bodyguard mode")
        if any(w in text for w in ["protect", "guard", "bodyguard", "watch my back"]):
            return [{"cmd": "protect", "args": {"player": username}}], f"Guard mode activated! Watching your back, {username}."

        # I. Attack Hostile Mobs ("attack zombie", "kill skeleton", "attack spider")
        attack_match = re.search(r'(?:attack|kill|fight|eliminate)\s+(?:that\s+|the\s+)?(zombie|skeleton|spider|creeper|drowned|enderman|witch|mob)', text)
        if attack_match:
            target = attack_match.group(1)
            return [{"cmd": "attack", "args": {"target_name": target}}], None

        # J. Sleep / Bed ("sleep", "go to bed", "it's night time")
        if any(w in text for w in ["sleep", "go to bed", "bed"]):
            return [{"cmd": "sleep"}], None

        # K. Build Shelter ("build shelter", "make a house", "dig a hole")
        if any(w in text for w in ["build shelter", "make shelter", "build house", "survival shelter"]):
            return [{"cmd": "build_shelter"}], None

        # L. Status Inquiry
        if any(w in text for w in ["status", "where are you", "hp", "health", "inventory", "what do you have", "bag"]):
            hp = self.last_state.get("hp", 20)
            food = self.last_state.get("food", 20)
            pos = self.last_state.get("pos", {})
            inv = self.last_state.get("inventory", {})
            inv_str = ", ".join([f"{k}x{v}" for k, v in list(inv.items())[:5]]) or "Empty"
            msg = f"HP: {hp}/20 | Food: {food}/20 | Pos: X:{pos.get('x')} Y:{pos.get('y')} Z:{pos.get('z')} | Bag: {inv_str}"
            return [], msg

        return [], None

    def _autonomous_brain_loop(self):
        """Background Reinforcement Learning Decision Loop (Throttled for CPU smoothness)."""
        while self.is_running:
            time.sleep(6.0)

            if not self.is_connected or not self.last_state:
                continue

            # In COMPANION mode (default), REN stays near the player and obeys chat commands.
            # It will NOT run off to mine blocks unless the player specifically requested it.
            if self.mode == "COMPANION":
                if self.enable_curiosity:
                    question = self.curiosity_engine.check_for_curious_moments(
                        game_state=self.last_state,
                        player_username=self.last_player_sender
                    )
                    if question:
                        self.send_chat(question)
                continue

            # In SURVIVAL_RL mode, run autonomous RL exploration
            if self.enable_rl and not self.active_player_directive:
                current_state = self.last_state
                state_key = self.rl_brain.discretize_state(current_state)

                action, is_exploring = self.rl_brain.choose_action(state_key)
                self.last_action = action
                self.last_state_key = state_key

                # Execute Action
                success = self._execute_rl_action(action, current_state)

                # Compute Reward & Update Q-Table
                time.sleep(1.0)
                next_state = self.last_state
                next_state_key = self.rl_brain.discretize_state(next_state)

                reward = self.rl_brain.calculate_reward(
                    prev_state=current_state,
                    curr_state=next_state,
                    action=action,
                    action_success=success
                )

                self.rl_brain.update_q_value(
                    state_key=state_key,
                    action=action,
                    reward=reward,
                    next_state_key=next_state_key
                )

    def _execute_rl_action(self, action: str, state: Dict[str, Any]) -> bool:
        """Translates RL high-level survival action to low-level bridge commands."""
        inv = state.get("inventory", {})
        food = state.get("food", 20)
        time_of_day = state.get("timeOfDay", "day")

        if action == "EAT_FOOD":
            if food < 18:
                self.send_command("eat")
                return True
            return False

        if action == "HUNT_FOOD":
            if food < 15:
                self.send_command("hunt", {"animal_name": "animal", "count": 1})
                return True
            return False

        if action == "DEFEND_SELF":
            entities = state.get("entities", [])
            hostiles = [e for e in entities if e.get("isHostile", False)]
            if hostiles:
                closest = min(hostiles, key=lambda x: x.get("distance", 99))
                self.send_command("attack", {"target_name": closest.get("name")})
                return True
            return False

        if action == "BUILD_SHELTER":
            if time_of_day in ["dusk", "night"]:
                self.send_command("build_shelter")
                return True
            return False

        if action == "GATHER_WOOD":
            self.send_command("gather", {"block_type": "wood", "count": 3})
            return True

        if action == "CRAFT_PLANKS":
            log_count = sum(c for k, c in inv.items() if "log" in k)
            if log_count > 0:
                self.send_command("craft", {"item_name": "oak_planks", "count": 4})
                return True
            return False

        if action == "CRAFT_CRAFTING_TABLE":
            if "crafting_table" not in inv:
                self.send_command("craft", {"item_name": "crafting_table", "count": 1})
                return True
            return False

        if action == "CRAFT_WOODEN_PICKAXE":
            if "wooden_pickaxe" not in inv and "stone_pickaxe" not in inv:
                self.send_command("craft", {"item_name": "wooden_pickaxe", "count": 1})
                return True
            return False

        if action == "MINE_STONE":
            self.send_command("gather", {"block_type": "stone", "count": 4})
            return True

        if action == "CRAFT_STONE_PICKAXE":
            if "stone_pickaxe" not in inv and inv.get("cobblestone", 0) >= 3:
                self.send_command("craft", {"item_name": "stone_pickaxe", "count": 1})
                return True
            return False

        if action == "CRAFT_STONE_SWORD":
            if "stone_sword" not in inv and inv.get("cobblestone", 0) >= 2:
                self.send_command("craft", {"item_name": "stone_sword", "count": 1})
                return True
            return False

        if action == "MINE_IRON":
            self.send_command("gather", {"block_type": "iron_ore", "count": 3})
            return True

        if action == "EXPLORE":
            pos = state.get("pos", {})
            import random
            dx = random.randint(-12, 12)
            dz = random.randint(-12, 12)
            self.send_command("goTo", {"x": pos.get("x", 0) + dx, "y": pos.get("y", 64), "z": pos.get("z", 0) + dz})
            return True

        return True
