"""
REN-AI Minecraft Agent Control Tool
Provides full control over the autonomous Minecraft embodied agent from the Desktop HUD,
Web/Mobile clients, and natural language agent requests.
"""

import time
import threading
from typing import Dict, Any, Optional

from ren.tools.base import BaseTool, ToolResult
from ren.security.permissions import PermissionCategory
from ren.monitoring.logger import agent_logger

# Global Minecraft agent instance manager
_global_mc_agent: Optional[Any] = None
_mc_lock = threading.Lock()


class MinecraftControlTool(BaseTool):
    name = "minecraft_control"
    description = (
        "Controls and interacts with the autonomous Minecraft embodied agent (Ren). "
        "Allows launching the bot into a Minecraft world/server, stopping it, checking its live in-game status "
        "(HP, food, coordinates, inventory), sending in-game chat, and executing autonomous tasks (build house, speedrun, explore, hunt, pvp)."
    )
    required_permissions = [PermissionCategory.PROCESS_START]
    parameters_schema = {
        "type": "object",
        "properties": {
            "action": {
                "type": "string",
                "enum": ["start", "stop", "status", "chat", "command"],
                "description": "The control action to perform on the Minecraft agent."
            },
            "host": {
                "type": "string",
                "description": "Minecraft server host IP or domain (default: 'localhost' or '127.0.0.1')."
            },
            "port": {
                "type": "integer",
                "description": "Minecraft server port (default: 25565 or 1234)."
            },
            "username": {
                "type": "string",
                "description": "In-game bot player name (default: 'RenAI')."
            },
            "version": {
                "type": "string",
                "description": "Optional Minecraft version string (e.g. '1.20.1', '1.20.4')."
            },
            "mode": {
                "type": "string",
                "enum": ["AUTONOMOUS_AGI", "COMPANION", "SPEEDRUN"],
                "description": "Operational autonomy mode: 'AUTONOMOUS_AGI' (free exploration & survival), 'COMPANION' (loyal partner), or 'SPEEDRUN'."
            },
            "message": {
                "type": "string",
                "description": "Chat message or in-game command text (e.g. 'build a small wooden house', 'follow me', 'gather 10 iron', 'explore')."
            }
        },
        "required": ["action"]
    }

    def run(
        self,
        action: str,
        host: str = "localhost",
        port: int = 25565,
        username: str = "RenAI",
        version: Optional[str] = None,
        mode: str = "AUTONOMOUS_AGI",
        message: Optional[str] = None,
        **kwargs
    ) -> ToolResult:
        global _global_mc_agent
        start_t = time.perf_counter()
        action_clean = action.lower().strip()

        try:
            from ren.minecraft.agent import MinecraftAgent

            if action_clean == "start":
                with _mc_lock:
                    if _global_mc_agent and _global_mc_agent.is_running:
                        return ToolResult(
                            success=True,
                            output=f"Minecraft agent '{_global_mc_agent.username}' is already active and running on {_global_mc_agent.host}:{_global_mc_agent.port}.",
                            duration=time.perf_counter() - start_t
                        )

                    _global_mc_agent = MinecraftAgent(
                        host=host,
                        port=port,
                        username=username,
                        version=version,
                        enable_rl=True,
                        enable_curiosity=True
                    )
                    _global_mc_agent.mode = mode
                    _global_mc_agent.start()

                return ToolResult(
                    success=True,
                    output=(
                        f"🎮 Minecraft Agent '{username}' successfully initialized and connecting to {host}:{port}!\n"
                        f"Autonomy Mode: {mode}\n"
                        f"Reinforcement Learning: ENABLED (Cloud 31B Hermes brain active)\n"
                        f"Perception & Curiosity: ONLINE"
                    ),
                    duration=time.perf_counter() - start_t
                )

            elif action_clean == "stop":
                with _mc_lock:
                    if not _global_mc_agent or not _global_mc_agent.is_running:
                        return ToolResult(
                            success=True,
                            output="Minecraft agent is not currently running.",
                            duration=time.perf_counter() - start_t
                        )
                    _global_mc_agent.stop()
                    _global_mc_agent = None

                return ToolResult(
                    success=True,
                    output="Minecraft agent has been disconnected and shut down. Memory and Q-table policy saved.",
                    duration=time.perf_counter() - start_t
                )

            elif action_clean == "status":
                with _mc_lock:
                    if not _global_mc_agent or not _global_mc_agent.is_running:
                        return ToolResult(
                            success=True,
                            output="Minecraft Agent is currently OFFLINE. Use action='start' to launch Ren into a world.",
                            duration=time.perf_counter() - start_t
                        )

                    state = _global_mc_agent.last_state
                    pos = state.get("pos", {})
                    hp = state.get("hp", 20)
                    food = state.get("food", 20)
                    inv = state.get("inventory", {})
                    active_task = _global_mc_agent.task_manager.active_task.name if _global_mc_agent.task_manager.active_task else "Idle / Autonomous Exploring"

                    inv_summary = ", ".join([f"{k}x{v}" for k, v in list(inv.items())[:6]]) or "Empty"

                    report = (
                        f"🎮 Minecraft Agent Status:\n"
                        f"- Name: {_global_mc_agent.username} (Connected: {_global_mc_agent.is_connected})\n"
                        f"- Server: {_global_mc_agent.host}:{_global_mc_agent.port}\n"
                        f"- Mode: {_global_mc_agent.mode}\n"
                        f"- Health: {hp}/20 | Hunger: {food}/20\n"
                        f"- Position: X:{int(pos.get('x',0))}, Y:{int(pos.get('y',64))}, Z:{int(pos.get('z',0))}\n"
                        f"- Active Task: {active_task}\n"
                        f"- Inventory: {inv_summary}"
                    )
                    return ToolResult(success=True, output=report, duration=time.perf_counter() - start_t)

            elif action_clean in ["chat", "command"]:
                if not message:
                    return ToolResult(success=False, error="Message or command text must be provided.", exit_code=1)

                with _mc_lock:
                    if not _global_mc_agent or not _global_mc_agent.is_running:
                        return ToolResult(
                            success=False,
                            error="Minecraft agent is not currently running. Please start it first.",
                            exit_code=1,
                            duration=time.perf_counter() - start_t
                        )

                    if action_clean == "chat":
                        _global_mc_agent.send_chat(message)
                        return ToolResult(
                            success=True,
                            output=f"Sent chat to Minecraft world: \"{message}\"",
                            duration=time.perf_counter() - start_t
                        )
                    else:
                        _global_mc_agent._on_player_chat("User", message)
                        return ToolResult(
                            success=True,
                            output=f"Dispatched in-game command to Ren: \"{message}\"",
                            duration=time.perf_counter() - start_t
                        )

            return ToolResult(
                success=False,
                error=f"Unknown action '{action}'. Valid actions: 'start', 'stop', 'status', 'chat', 'command'.",
                exit_code=1,
                duration=time.perf_counter() - start_t
            )

        except Exception as e:
            agent_logger.error(f"Error in MinecraftControlTool: {e}", exc_info=True)
            return ToolResult(
                success=False,
                error=f"Minecraft control error: {str(e)}",
                exit_code=1,
                duration=time.perf_counter() - start_t
            )
