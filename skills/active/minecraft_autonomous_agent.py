import json
import random
import time
import sqlite3
import subprocess
from typing import List, Dict, Any

class MinecraftAutonomousAgent:
    def __init__(self, server_ip="127.0.0.1", server_port=25565, bot_name="Ren_AI_Bot"):
        self.server_ip = server_ip
        self.server_port = server_port
        self.bot_name = bot_name
        self.memory_db = "minecraft_brain.db"
        self._init_memory()
        
        # Cognitive State
        self.curiosity_score = 1.0
        self.current_goal = "EXPLORE"
        self.discovered_coords = set()
        self.knowledge_base = {} # Stores block properties learned via RL
        
    def _init_memory(self):
        """Initialize SQLite memory for Reinforcement Learning storage."""
        conn = sqlite3.connect(self.memory_db)
        cursor = conn.cursor()
        cursor.execute('''CREATE TABLE IF NOT EXISTS experience 
                          (state TEXT, action TEXT, reward REAL, next_state TEXT)''')
        conn.commit()
        conn.close()

    def perceive(self, world_data: Dict) -> Dict:
        """
        Simulates the 'Seeing' part of AGI. 
        Processes raw block data into a cognitive map.
        """
        # In a real scenario, this parses the JSON stream from the Mineflayer bot
        nearby_blocks = world_data.get("nearby_blocks", [])
        entities = world_data.get("entities", [])
        return {
            "blocks": nearby_blocks,
            "entities": entities,
            "position": world_data.get("pos")
        }

    def curiosity_engine(self, current_pos: tuple) -> str:
        """
        Drives the agent to explore unknown areas.
        If the current area is 'boring' (well-known), curiosity spikes.
        """
        if current_pos not in self.discovered_coords:
            self.discovered_coords.add(current_pos)
            return "INVESTIGATE"
        
        # If we've been here, move to a random adjacent unexplored coordinate
        return "WANDER"

    def rl_decision_loop(self, state: str, available_actions: List[str]) -> str:
        """
        Simplified Reinforcement Learning (Q-Learning approach).
        Selects action based on historical rewards stored in SQLite.
        """
        conn = sqlite3.connect(self.memory_db)
        cursor = conn.cursor()
        
        # Query for the best action for this state
        cursor.execute("SELECT action FROM experience WHERE state=? ORDER BY reward DESC LIMIT 1", (state,))
        result = cursor.fetchone()
        conn.close()

        if result and random.random() > 0.2: # 20% Exploration rate (Epsilon)
            return result[0]
        else:
            return random.choice(available_actions)

    def update_learning(self, state: str, action: str, reward: float, next_state: str):
        """Stores the outcome of an action to learn from it."""
        conn = sqlite3.connect(self.memory_db)
        cursor = conn.cursor()
        cursor.execute("INSERT INTO experience VALUES (?, ?, ?, ?)", (state, action, reward, next_state))
        conn.commit()
        conn.close()

    def execute_action(self, action: str):
        """Sends the command to the Minecraft bot backend."""
        print(f"[Ren-AI Bot] Executing Action: {action}")
        # This would send a JSON command to the Node.js Mineflayer process
        # Example: {"command": "move_to", "coords": [10, 64, 10]}
        return True

    def run_cognitive_cycle(self, world_snapshot: Dict):
        """
        The Main AGI Loop: Perceive -> Think -> Act -> Learn
        """
        # 1. Perceive
        perception = self.perceive(world_snapshot)
        pos = perception["position"]
        
        # 2. Think (Curiosity + RL)
        state_key = f"pos_{pos}"
        if self.curiosity_engine(pos) == "INVESTIGATE":
            action = "COLLECT_SAMPLE"
        else:
            action = self.rl_decision_loop(state_key, ["MOVE_NORTH", "MOVE_SOUTH", "MINE_BLOCK", "CRAFT"])

        # 3. Act
        self.execute_action(action)
        
        # 4. Learn (Reward based on discovery or survival)
        reward = 1.0 if action == "COLLECT_SAMPLE" else 0.1
        self.update_learning(state_key, action, reward, "next_state_placeholder")

# --- Integration Wrapper ---
def start_minecraft_skill(ip="127.0.0.1", port=25565):
    agent = MinecraftAutonomousAgent(server_ip=ip, server_port=port)
    print(f"Ren AI is now connecting to Minecraft LAN at {ip}:{port}...")
    
    # Mock loop to demonstrate the AGI cycle
    try:
        for i in range(5): # Running 5 cycles for demonstration
            mock_world_data = {
                "pos": (random.randint(0,100), 64, random.randint(0,100)),
                "nearby_blocks": ["grass", "dirt", "stone"],
                "entities": ["pig", "sheep"]
            }
            agent.run_cognitive_cycle(mock_world_data)
            time.sleep(1)
    except KeyboardInterrupt:
        print("Bot disconnected.")

if __name__ == "__main__":
    start_minecraft_skill()