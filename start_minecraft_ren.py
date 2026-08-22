"""
REN-AI Minecraft Survival AGI Launcher
Runs REN as an autonomous Minecraft player with Reinforcement Learning and Curiosity.
Does NOT require running the desktop GUI or web server.

Usage:
    python start_minecraft_ren.py
    python start_minecraft_ren.py --host 127.0.0.1 --port 25565 --username RenAI --version 1.20.1
"""

import sys
import time
import argparse
import threading
from pathlib import Path

# Add project root to sys.path
root_dir = Path(__file__).resolve().parent
sys.path.insert(0, str(root_dir))

from ren.minecraft.agent import MinecraftAgent
from ren.monitoring.logger import agent_logger


def print_banner():
    banner = r"""
================================================================
  🎮 REN-AI MINECRAFT SURVIVAL AGI AGENT
  Companion Mode | Full AGI Actions | Universal Chat Control
================================================================
"""
    print(banner)


def main():
    parser = argparse.ArgumentParser(description="REN-AI Minecraft Autonomous Survival Agent")
    parser.add_argument("--host", type=str, default="localhost", help="Minecraft server host (default: localhost)")
    parser.add_argument("--port", type=int, default=25565, help="Minecraft server port (default: 25565)")
    parser.add_argument("--username", type=str, default="RenAI", help="Bot in-game username (default: RenAI)")
    parser.add_argument("--version", type=str, default=None, help="Minecraft version (e.g. 1.20.1, auto-detect if omitted)")
    parser.add_argument("--auth", type=str, default="offline", choices=["offline", "microsoft"], help="Authentication mode")
    parser.add_argument("--no-rl", action="store_true", help="Disable autonomous reinforcement learning exploration")
    parser.add_argument("--no-curiosity", action="store_true", help="Disable curiosity questions in chat")

    args = parser.parse_args()

    print_banner()
    print(f" [*] Connecting to Minecraft Server at {args.host}:{args.port}")
    print(f" [*] Bot Username     : {args.username}")
    print(f" [*] Auth Mode        : {args.auth}")
    print(f" [*] Mode             : COMPANION (Loyal Partner)")
    print(f" [*] RL Learning      : {'ENABLED' if not args.no_rl else 'DISABLED'}")
    print(f" [*] Curiosity Engine : {'ENABLED' if not args.no_curiosity else 'DISABLED'}")
    print("\n Type in Minecraft chat or type below in terminal to command Ren (e.g. 'follow me', 'give me 5 wood', 'kill cows', 'status', 'exit')\n")

    agent = MinecraftAgent(
        host=args.host,
        port=args.port,
        username=args.username,
        version=args.version,
        auth=args.auth,
        enable_rl=not args.no_rl,
        enable_curiosity=not args.no_curiosity
    )

    def console_reader_loop():
        """Reads stdin in background without terminating if input closes."""
        while agent.is_running:
            try:
                line = sys.stdin.readline()
                if not line:
                    time.sleep(0.5)
                    continue

                cmd = line.strip()
                if not cmd:
                    continue

                if cmd.lower() in ["exit", "quit", "q"]:
                    print("\n [*] Stopping Minecraft Agent...")
                    agent.stop()
                    break

                if cmd.startswith("/"):
                    agent.send_chat(cmd[1:])
                else:
                    agent._on_player_chat("ConsoleUser", cmd)

            except Exception:
                time.sleep(1.0)

    try:
        agent.start()

        # Start input thread
        input_thread = threading.Thread(target=console_reader_loop, daemon=True)
        input_thread.start()

        # Keep main thread alive reliably
        while agent.is_running:
            time.sleep(0.5)

    except KeyboardInterrupt:
        print("\n [*] Stopping Minecraft Agent (Ctrl+C)...")
    finally:
        agent.stop()
        print("\n [✓] Minecraft Agent shutdown complete. Q-Table policy saved.\n")


if __name__ == "__main__":
    main()
