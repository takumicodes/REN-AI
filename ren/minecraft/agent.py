"""
REN-AI Minecraft Autonomous AGI Agent 10.0 (Speedrun Mode & Wind Charge / Mace PvP)
- Any% Survival Speedrun Mode: Timer, splits, iron rush, bed explosions, dragon slaying.
- Mace & Wind Charge PvP: Performs aerial smash attacks with Wind Charge propulsion and Mace crushing blows.
- Instant Companion Priority & Strict Command Routing.
- Complete Command Coverage:
  * 'speedrun' / 'beat the game' -> starts Any% survival speedrun.
  * 'make house' / 'make a small home fast' -> 3D walking builder.
  * 'change game mode to survival' / 'creative' -> executes /gamemode.
  * 'give me all items' / 'drop everything' -> drops entire inventory.
  * 'take this sword' / 'pickup' -> collects nearby items and equips weapon.
  * 'do bridging' / 'bridge with wool' -> builds bridge across chasm.
  * 'kill all mobs nearby' -> clears hostile mobs in 32-block radius.
  * 'pvp with me' / 'fight with me' -> draws mace/sword and duels player.
  * 'follow me' / 'come here' -> dynamic sprint following.
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
from ren.minecraft.planner import MinecraftGoalPlanner
from ren.minecraft.speedrun import MinecraftSpeedrunEngine
from ren.models import get_model_provider
from ren.monitoring.logger import agent_logger, error_logger


class MinecraftAgent:
    """
    Autonomous Minecraft Survival AGI Agent for REN.
    Supports Companion, Autonomous RL, and Any% Speedrun modes.
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

        # Modes: "COMPANION", "AUTONOMOUS_AGI", or "SPEEDRUN"
        self.mode: str = "COMPANION"

        self.rl_brain = MinecraftRLBrain()
        self.curiosity_engine = MinecraftCuriosityEngine(cooldown_seconds=60.0)
        self.planner = MinecraftGoalPlanner()
        self.speedrun_engine = MinecraftSpeedrunEngine()
        self.provider = get_model_provider()

        self.process: Optional[subprocess.Popen] = None
        self.is_running: bool = False
        self.is_connected: bool = False
        
        self.last_state: Dict[str, Any] = {}
        self.active_player_directive: Optional[Dict[str, Any]] = None
        self.plan_queue: List[Dict[str, Any]] = []
        self.last_action: Optional[str] = None
        self.last_state_key: Optional[str] = None
        self.last_player_sender: Optional[str] = None

        self.is_busy: bool = False
        self.current_task_id: Optional[str] = None
        self.task_start_time: float = 0.0

        self._lock = threading.Lock()
        self.task_waiters: Dict[str, threading.Event] = {}
        self.task_results: Dict[str, Any] = {}

    def start(self):
        """Launches Node.js Mineflayer bridge subprocess."""
        bridge_script = Path(__file__).resolve().parent / "bridge" / "bot.js"
        if not bridge_script.exists():
            raise FileNotFoundError(f"Mineflayer bridge script not found at: {bridge_script}")

        cmd = ["node", str(bridge_script), "--host", self.host, "--port", str(self.port), "--username", self.username, "--auth", self.auth]
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
            if cmd not in ["chat", "stop"]:
                self.is_busy = True
                self.current_task_id = task_id
                self.task_start_time = time.time()

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
                agent_logger.warning(f"Error in Minecraft stdout reader: {e}")
                break

    def _handle_bridge_event(self, data: Dict[str, Any]):
        """Processes incoming events from Minecraft world."""
        event_type = data.get("event")

        if event_type == "ready":
            self.is_connected = True
            agent_logger.info(f"Minecraft bot '{data.get('username')}' connected to {self.host}:{self.port}!")
            self.send_chat("Hello! Ren AI is online with Speedrun & Mace combat enabled! ✨")

        elif event_type == "state":
            with self._lock:
                self.last_state = data

        elif event_type == "chat":
            username = data.get("username")
            message = data.get("message")
            if username and message:
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
            self.is_busy = False
            self.plan_queue.clear()
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
            self.is_busy = False
            self.current_task_id = None

            if task_id in self.task_waiters:
                self.task_results[task_id] = data
                self.task_waiters[task_id].set()

            if self.plan_queue:
                threading.Thread(target=self._execute_next_plan_step, daemon=True).start()

    def _on_player_chat(self, username: str, message: str):
        """Universal Intent Understanding with 100% priority."""
        try:
            self.last_player_sender = username
            cleaned = self._normalize_minecraft_text(message)
            agent_logger.info(f"Minecraft Chat [{username}]: '{message}' (Normalized: '{cleaned}')")

            # 1. Speedrun Mode Trigger
            if any(w in cleaned for w in ["speedrun", "speed run", "beat the game", "world record", "speedrun mode"]):
                self.mode = "SPEEDRUN"
                self.plan_queue.clear()
                self.is_busy = False
                start_msg = self.speedrun_engine.start_speedrun()
                self.send_chat(start_msg)
                return

            # 2. Autonomous Mode Trigger
            if any(w in cleaned for w in ["auto survival", "explore on your own", "wander", "auto mode", "survive alone", "be independent", "independent mode", "play on your own"]):
                if not any(stop_w in cleaned for stop_w in ["stop", "deactivate", "disable", "cancel", "turn off"]):
                    self.mode = "AUTONOMOUS_AGI"
                    self.plan_queue.clear()
                    self.is_busy = False
                    self.send_chat("Autonomous survival mode activated! Surviving and exploring.")
                    return

            # Default: ANY player command switches to COMPANION mode immediately!
            self.mode = "COMPANION"
            self.plan_queue.clear()
            self.is_busy = False

            # 3. Stop / Deactivate Auto Mode
            if any(w in cleaned for w in ["stop auto mode", "deactivate auto mode", "disable auto mode", "cancel auto", "turn off auto", "stop", "halt", "freeze"]):
                self.speedrun_engine.is_active = False
                self.send_command("stop")
                self.send_chat(f"Stopped all tasks, {username}!")
                return

            # 4. Gamemode Switch
            if "survival" in cleaned and any(w in cleaned for w in ["mode", "gamemode", "change", "set", "keep"]):
                self.send_command("gamemode", {"mode": "survival"})
                return

            if "creative" in cleaned and any(w in cleaned for w in ["mode", "gamemode", "change", "set", "keep"]):
                self.send_command("gamemode", {"mode": "creative"})
                return

            # 5. Take Items / Pick up
            if any(w in cleaned for w in ["take this", "take the", "pickup", "pick up", "take sword", "take item", "take mace"]):
                self.send_command("pickup")
                return

            # 6. Drop All Items
            if any(w in cleaned for w in ["give me all", "give all", "drop all", "drop everything", "all items"]):
                self.send_command("drop_all", {"player": username})
                return

            # 7. Bridging
            if any(w in cleaned for w in ["bridging", "bridge", "make a bridge", "do bridging"]):
                material = "wool" if "wool" in cleaned else "planks"
                self.send_command("bridge", {"length": 8, "material": material})
                return

            # 8. Kill All Mobs
            if any(w in cleaned for w in ["kill all mobs", "kill mobs", "slay all", "clear mobs", "defeat monsters"]):
                self.send_command("kill_all_mobs")
                return

            # 9. PVP / Fight Player (Mace & Wind Charge combo enabled!)
            if any(w in cleaned for w in ["pvp", "fight with me", "fight me", "kill me", "duel", "attack me"]):
                self.send_command("pvp", {"player": username})
                return

            # 10. Follow Player
            if any(w in cleaned for w in ["follow me", "follow", "come to me", "come here", "come her", "with me", "stay with me", "near me"]):
                self.send_command("follow", {"player": username})
                return

            # 11. Build House / Shelter
            if any(w in cleaned for w in ["make house", "build house", "make home", "build home", "make a small home", "make shelter", "build shelter", "make base", "build base"]):
                self.send_command("build_shelter", {"size": 3})
                return

            # 12. Crafting specific tools (including Mace!)
            for target_tool in ["mace", "stone_pickaxe", "stone_sword", "iron_pickaxe", "iron_sword", "iron_chestplate", "shield"]:
                if target_tool.replace("_", " ") in cleaned or target_tool in cleaned:
                    plan = self.planner.decompose_goal(target_tool, self.last_state, username)
                    self.plan_queue = plan
                    self._execute_next_plan_step()
                    return

            # 13. Gather / Give Items (including Wind Charge and Mace)
            if any(w in cleaned for w in ["give", "drop", "toss", "share", "pass", "get"]):
                item = "wood"
                count = 2
                count_m = re.search(r'\b(\d+)\b', cleaned)
                if count_m: count = int(count_m.group(1))
                for cand in ["mace", "wind_charge", "iron", "coal", "wood", "stone", "cobblestone", "dirt", "bread", "beef", "pork", "apple", "sword", "pickaxe", "axe", "torch", "food", "tools"]:
                    if cand.replace("_", " ") in cleaned or cand in cleaned:
                        item = cand
                        break

                if item == "tools":
                    item = "wood"
                self.send_command("gather", {"block_type": item, "count": count})
                return

            # 14. Fast Semantic Matcher
            parsed_actions, custom_reply = self._parse_semantic_intent(username, cleaned)
            if parsed_actions:
                self.active_player_directive = parsed_actions[0]
                if custom_reply:
                    self.send_chat(custom_reply)
                for act in parsed_actions:
                    self.send_command(act["cmd"], act.get("args", {}))
                return

            # 15. Fallback LLM Reasoning with REN
            inv_str = ", ".join([f"{k}x{v}" for k, v in list(self.last_state.get("inventory", {}).items())[:6]]) or "Empty"
            prompt = f"""You are Ren, an autonomous AI entity in Minecraft playing with {username}.
Respond in 1 short lively sentence and output Minecraft action JSON.
Stats: HP={self.last_state.get('hp', 20)}/20, Food={self.last_state.get('food', 20)}/20, Bag=[{inv_str}].
Player '{username}': "{message}"

JSON format:
{{
  "reply": "<short reply>",
  "actions": [{{"cmd": "<follow|pvp|gather|hunt|craft|build_shelter|attack|sleep|stop>", "args": {{ ... }}}}]
}}"""

            llm_out = self.provider.generate(prompt, max_tokens=100, temperature=0.3)
            if any(bad in llm_out.lower() for bad in ["sorry", "language model", "cannot help", "as an ai"]):
                llm_out = ""

            json_match = re.search(r'\{.*\}', llm_out, re.DOTALL) if llm_out else None
            if json_match:
                parsed = json.loads(json_match.group(0))
                reply = parsed.get("reply", "")
                actions = parsed.get("actions", [])
                if reply:
                    self.send_chat(reply[:100])
                if actions:
                    self.plan_queue = actions
                    self._execute_next_plan_step()
                return
        except Exception as e:
            agent_logger.warning(f"Player chat handler fallback: {e}")

        self.send_chat(f"On it, {username}!")

    def _normalize_minecraft_text(self, text: str) -> str:
        """Corrects common Minecraft typos and variations."""
        t = text.lower().strip()
        typos = {
            "cooble": "cobble",
            "cooblestone": "cobblestone",
            "coblestone": "cobblestone",
            "cobbleston": "cobblestone",
            "bridgig": "bridging",
            "bridgin": "bridging",
            "wincharge": "wind_charge",
            "windcharge": "wind_charge",
            "her": "here",
            "itmes": "items",
            "hous": "house",
            "hom": "home"
        }
        for k, v in typos.items():
            t = re.sub(rf'\b{k}\b', v, t)
        return t

    def _execute_next_plan_step(self):
        """Executes the next atomic action in the AGI plan queue sequentially."""
        if not self.plan_queue or self.is_busy:
            return

        next_action = self.plan_queue.pop(0)
        cmd = next_action.get("cmd")
        args = next_action.get("args", {})

        agent_logger.info(f"Executing AGI Plan Step: {cmd} with {args}")
        self.send_command(cmd, args)

    def _parse_semantic_intent(self, username: str, text: str) -> Tuple[List[Dict[str, Any]], Optional[str]]:
        """Universal Fuzzy Intent Matcher."""
        if any(w in text for w in ["stop", "halt", "stay here", "wait here", "pause", "freeze", "cancel", "hold up"]):
            self.active_player_directive = None
            self.plan_queue.clear()
            self.is_busy = False
            return [{"cmd": "stop"}], "Stopping all tasks, Sir."

        if any(w in text for w in ["give", "drop", "toss", "share", "pass", "hand", "throw", "spare"]):
            count_match = re.search(r'\b(\d+)\b', text)
            count = int(count_match.group(1)) if count_match else 2

            item = "wood"
            for candidate in ["mace", "wind_charge", "iron", "coal", "wood", "log", "plank", "stone", "cobblestone", "dirt", "bread", "beef", "pork", "apple", "sword", "pickaxe", "axe", "torch", "food"]:
                if candidate in text:
                    item = candidate
                    break

            return [{"cmd": "give", "args": {"player": username, "item_name": item, "count": count}}], None

        if any(w in text for w in ["gather", "mine", "chop", "dig", "cut", "harvest", "collect", "get", "find", "fetch", "need"]) and any(w in text for w in ["wood", "tree", "log", "stone", "cobble", "iron", "coal", "diamond", "dirt", "sand", "gravel", "ore", "birch", "oak", "spruce"]):
            count_match = re.search(r'\b(\d+)\b', text)
            count = int(count_match.group(1)) if count_match else 4

            target = "wood"
            if any(w in text for w in ["iron", "iron_ore"]): target = "iron_ore"
            elif any(w in text for w in ["coal", "coal_ore"]): target = "coal_ore"
            elif any(w in text for w in ["diamond"]): target = "diamond_ore"
            elif any(w in text for w in ["stone", "cobble", "deepslate", "cobblestone"]): target = "stone"
            elif any(w in text for w in ["dirt", "sand", "gravel"]): target = "dirt"
            elif any(w in text for w in ["wood", "tree", "log", "birch", "oak", "spruce"]): target = "wood"

            return [{"cmd": "gather", "args": {"block_type": target, "count": count}}], None

        if any(w in text for w in ["hunt", "kill", "slaughter", "slay", "butcher"]) and any(w in text for w in ["cow", "pig", "sheep", "chicken", "rabbit", "animal", "meat", "food", "beef", "pork", "mutton", "wool"]):
            count_match = re.search(r'\b(\d+)\b', text)
            count = int(count_match.group(1)) if count_match else 2

            animal = "animal"
            for a in ["cow", "pig", "sheep", "chicken", "rabbit"]:
                if a in text:
                    animal = a
                    break

            return [{"cmd": "hunt", "args": {"animal_name": animal, "count": count}}], None

        if any(w in text for w in ["craft", "make", "create", "build"]) and any(w in text for w in ["pickaxe", "sword", "axe", "shovel", "table", "furnace", "torch", "chest", "bed", "shield", "door", "planks", "tools"]):
            item = "crafting_table"
            for it in ["stone_pickaxe", "wooden_pickaxe", "stone_sword", "iron_sword", "crafting_table", "furnace", "torch", "shield", "chest", "bed", "oak_planks"]:
                if it.replace("_", " ") in text or it in text:
                    item = it
                    break

            count_match = re.search(r'\b(\d+)\b', text)
            count = int(count_match.group(1)) if count_match else 1
            return [{"cmd": "craft", "args": {"item_name": item, "count": count}}], None

        if any(w in text for w in ["smelt", "cook", "bake", "furnace", "melt"]):
            raw_item = "raw_iron" if "iron" in text else "beef"
            return [{"cmd": "smelt", "args": {"item": raw_item, "fuel": "coal", "count": 2}}], None

        if any(w in text for w in ["protect", "guard", "bodyguard", "watch my back", "defend", "shield me"]):
            return [{"cmd": "protect", "args": {"player": username}}], f"Guard mode activated! Watching your back, {username}."

        if any(w in text for w in ["attack", "kill", "fight", "slay", "destroy"]) and any(w in text for w in ["zombie", "skeleton", "spider", "creeper", "drowned", "enderman", "witch", "mob", "monster"]):
            target = "zombie"
            for m in ["skeleton", "spider", "creeper", "drowned", "enderman", "witch", "zombie"]:
                if m in text:
                    target = m
                    break
            return [{"cmd": "attack", "args": {"target_name": target}}], None

        if any(w in text for w in ["come", "follow", "walk with", "to me", "behind me", "near me", "with me"]) or (text in ["here", "over here"]):
            return [{"cmd": "follow", "args": {"player": username}}], f"Coming over to you, {username}!"

        if any(w in text for w in ["sleep", "go to bed", "bed", "sleep now", "night time"]):
            return [{"cmd": "sleep"}], None

        if any(w in text for w in ["status", "where are you", "hp", "health", "inventory", "what do you have", "bag", "coords"]):
            hp = self.last_state.get("hp", 20)
            food = self.last_state.get("food", 20)
            pos = self.last_state.get("pos", {})
            inv = self.last_state.get("inventory", {})
            inv_str = ", ".join([f"{k}x{v}" for k, v in list(inv.items())[:5]]) or "Empty"
            msg = f"HP: {hp}/20 | Food: {food}/20 | Pos: X:{pos.get('x')} Y:{pos.get('y')} Z:{pos.get('z')} | Bag: {inv_str}"
            return [], msg

        return [], None

    def _autonomous_brain_loop(self):
        """Background Decision Loop (Speedrun / Autonomous RL / Companion)."""
        while self.is_running:
            time.sleep(4.0)

            if not self.is_connected or not self.last_state:
                continue

            if self.is_busy and (time.time() - self.task_start_time) > 60.0:
                self.is_busy = False

            if self.is_busy or self.plan_queue:
                continue

            # 1. SPEEDRUN MODE
            if self.mode == "SPEEDRUN" and not self.is_busy:
                action, split_msg = self.speedrun_engine.get_next_speedrun_action(self.last_state)
                if split_msg:
                    self.send_chat(split_msg)
                if action:
                    self.send_command(action["cmd"], action.get("args", {}))
                continue

            # 2. COMPANION MODE
            if self.mode == "COMPANION":
                if self.enable_curiosity:
                    question = self.curiosity_engine.check_for_curious_moments(
                        game_state=self.last_state,
                        player_username=self.last_player_sender
                    )
                    if question:
                        self.send_chat(question)
                continue

            # 3. AUTONOMOUS AGI MODE (RL Survival)
            if self.mode == "AUTONOMOUS_AGI" and not self.is_busy:
                current_state = self.last_state
                state_key = self.rl_brain.discretize_state(current_state)

                action, is_exploring = self.rl_brain.choose_action(state_key)
                self.last_action = action
                self.last_state_key = state_key

                success = self._execute_rl_action(action, current_state)

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
        """Translates RL survival action to low-level bridge commands."""
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
                self.send_command("build_shelter", {"size": 3})
                return True
            return False

        if action == "GATHER_WOOD":
            self.send_command("gather", {"block_type": "wood", "count": 3})
            return True

        if action == "CRAFT_PLANKS":
            log_count = sum(c for k, c in inv.items() if "log" in k)
            if log_count > 0:
                self.send_command("craft", {"item_name": "oak_planks", "count": min(log_count, 2)})
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
