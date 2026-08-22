"""
REN-AI Minecraft Reinforcement Learning Survival Brain
Implements Tabular Q-Learning with state quantization, reward shaping, experience replay,
and persistent policy optimization across game sessions.
"""

import os
import json
import random
from pathlib import Path
from typing import Dict, Any, List, Tuple, Optional

from ren.config.settings import settings
from ren.monitoring.logger import agent_logger


class MinecraftRLBrain:
    """
    Reinforcement Learning Survival Policy for REN in Minecraft.
    Continuously balances basic survival, resource progression, threat defense, and goal execution.
    """

    ACTIONS = [
        "GATHER_WOOD",
        "CRAFT_PLANKS",
        "CRAFT_CRAFTING_TABLE",
        "CRAFT_WOODEN_PICKAXE",
        "MINE_STONE",
        "CRAFT_STONE_PICKAXE",
        "CRAFT_STONE_SWORD",
        "MINE_COAL",
        "CRAFT_TORCHES",
        "MINE_IRON",
        "CRAFT_FURNACE",
        "HUNT_FOOD",
        "EAT_FOOD",
        "BUILD_SHELTER",
        "DEFEND_SELF",
        "RETREAT_SAFETY",
        "EXPLORE",
        "FOLLOW_PLAYER",
        "IDLE_OBSERVE"
    ]

    def __init__(
        self,
        q_table_path: Optional[Path] = None,
        learning_rate: float = 0.15,
        discount_factor: float = 0.90,
        epsilon: float = 0.20,
        epsilon_decay: float = 0.995,
        min_epsilon: float = 0.05
    ):
        self.q_table_path = q_table_path or (settings.PATHS.DATA_DIR / "minecraft_rl_qtable.json")
        self.learning_rate = learning_rate
        self.discount_factor = discount_factor
        self.epsilon = epsilon
        self.epsilon_decay = epsilon_decay
        self.min_epsilon = min_epsilon

        self.q_table: Dict[str, Dict[str, float]] = {}
        self.total_steps: int = 0
        self.total_reward: float = 0.0
        self.episode_count: int = 0
        self.experience_memory: List[Dict[str, Any]] = []

        self.load_policy()

    def discretize_state(self, game_state: Dict[str, Any]) -> str:
        """
        Quantizes continuous raw game telemetry into a discrete state key.
        Components:
        - HP Tier: CRIT (<8), LOW (8-14), FULL (>14)
        - Food Tier: STARVE (<8), HUNGRY (8-15), FULL (>15)
        - Time: DAY, DUSK, NIGHT
        - Threat: SAFE, THREAT_NEAR, COMBAT
        - Tool Tier: T0_NONE, T1_WOOD, T2_STONE, T3_IRON
        - Wood Tier: W0 (0 logs), W1 (1-3 logs), W2 (4+ logs)
        - Food Count: F0 (0 food), F1 (1-3 food), F2 (4+ food)
        """
        hp = game_state.get("hp", 20)
        if hp < 8:
            hp_tier = "HP_CRIT"
        elif hp < 15:
            hp_tier = "HP_LOW"
        else:
            hp_tier = "HP_FULL"

        food = game_state.get("food", 20)
        if food < 8:
            food_tier = "FD_STARVE"
        elif food < 16:
            food_tier = "FD_HUNGRY"
        else:
            food_tier = "FD_FULL"

        time_of_day = game_state.get("timeOfDay", "day").upper()

        entities = game_state.get("entities", [])
        hostile_mobs = [e for e in entities if e.get("isHostile", False)]
        if any(e.get("distance", 99) < 6 for e in hostile_mobs):
            threat = "COMBAT"
        elif len(hostile_mobs) > 0:
            threat = "THREAT_NEAR"
        else:
            threat = "SAFE"

        inv = game_state.get("inventory", {})
        
        # Tool progression
        if any("iron" in item for item in inv):
            tool_tier = "T3_IRON"
        elif any("stone" in item for item in inv):
            tool_tier = "T2_STONE"
        elif any("wooden" in item for item in inv):
            tool_tier = "T1_WOOD"
        else:
            tool_tier = "T0_NONE"

        # Wood count
        log_count = sum(count for item, count in inv.items() if "log" in item)
        if log_count == 0:
            wood_tier = "W0"
        elif log_count < 4:
            wood_tier = "W1"
        else:
            wood_tier = "W2"

        # Food item count
        edible_count = sum(
            count for item, count in inv.items()
            if any(f in item for f in ["bread", "beef", "porkchop", "chicken", "mutton", "apple", "carrot"])
        )
        if edible_count == 0:
            food_count_tier = "FC0"
        elif edible_count < 4:
            food_count_tier = "FC1"
        else:
            food_count_tier = "FC2"

        return f"{hp_tier}|{food_tier}|{time_of_day}|{threat}|{tool_tier}|{wood_tier}|{food_count_tier}"

    def get_q_values(self, state_key: str) -> Dict[str, float]:
        """Returns action Q-values for the given state, initializing if absent."""
        if state_key not in self.q_table:
            # Optimistic initialization for exploration
            self.q_table[state_key] = {a: 0.0 for a in self.ACTIONS}
        return self.q_table[state_key]

    def choose_action(self, state_key: str, legal_actions: Optional[List[str]] = None) -> Tuple[str, bool]:
        """
        Selects an action using Epsilon-Greedy policy.
        Returns: (chosen_action: str, is_exploration: bool)
        """
        available = legal_actions or self.ACTIONS
        q_vals = self.get_q_values(state_key)

        # Exploration vs Exploitation
        if random.random() < self.epsilon:
            return random.choice(available), True

        # Best Q-value action (with random tie-breaking)
        best_val = max(q_vals[a] for a in available)
        best_actions = [a for a in available if q_vals[a] == best_val]
        return random.choice(best_actions), False

    def calculate_reward(
        self,
        prev_state: Dict[str, Any],
        curr_state: Dict[str, Any],
        action: str,
        action_success: bool,
        task_directive: Optional[str] = None
    ) -> float:
        """
        Reward Shaping Function for Survival, Resource Acquisition & Goal Completion.
        """
        reward = 0.0

        # Baseline survival tick reward
        reward += 0.5

        # 1. Health differential
        prev_hp = prev_state.get("hp", 20)
        curr_hp = curr_state.get("hp", 20)
        hp_diff = curr_hp - prev_hp
        if hp_diff < 0:
            reward += hp_diff * 4.0  # -4 per HP lost (e.g. -20 for 5 HP damage)
        elif hp_diff > 0:
            reward += hp_diff * 2.0  # +2 per HP healed

        # 2. Death penalty
        if curr_hp <= 0:
            reward -= 200.0

        # 3. Hunger differential
        prev_food = prev_state.get("food", 20)
        curr_food = curr_state.get("food", 20)
        food_diff = curr_food - prev_food
        if food_diff > 0:
            reward += food_diff * 1.5

        # 4. Inventory progression rewards
        prev_inv = prev_state.get("inventory", {})
        curr_inv = curr_state.get("inventory", {})

        # Wood gathered
        curr_logs = sum(c for k, c in curr_inv.items() if "log" in k)
        prev_logs = sum(c for k, c in prev_inv.items() if "log" in k)
        if curr_logs > prev_logs:
            reward += (curr_logs - prev_logs) * 8.0

        # Cobblestone / Stone mined
        curr_stone = curr_inv.get("cobblestone", 0)
        prev_stone = prev_inv.get("cobblestone", 0)
        if curr_stone > prev_stone:
            reward += (curr_stone - prev_stone) * 6.0

        # Iron ore mined
        curr_iron = curr_inv.get("raw_iron", 0) + curr_inv.get("iron_ingot", 0)
        prev_iron = prev_inv.get("raw_iron", 0) + prev_inv.get("iron_ingot", 0)
        if curr_iron > prev_iron:
            reward += (curr_iron - prev_iron) * 25.0

        # Tool crafting advancement
        for tool, points in [
            ("wooden_pickaxe", 20.0),
            ("stone_pickaxe", 40.0),
            ("stone_sword", 35.0),
            ("iron_pickaxe", 80.0),
            ("iron_sword", 75.0),
            ("furnace", 30.0),
            ("crafting_table", 15.0),
            ("torch", 10.0),
        ]:
            if tool in curr_inv and tool not in prev_inv:
                reward += points

        # 5. Nighttime shelter reward
        if curr_state.get("timeOfDay") == "night" and action == "BUILD_SHELTER" and action_success:
            reward += 50.0

        # 6. Player Directive Completion
        if task_directive and action_success:
            reward += 100.0

        # Penalty for failed action
        if not action_success:
            reward -= 5.0

        return reward

    def update_q_value(self, state_key: str, action: str, reward: float, next_state_key: str):
        """Standard Bellman Temporal Difference Q-Value update."""
        current_q = self.get_q_values(state_key)[action]
        next_max_q = max(self.get_q_values(next_state_key).values())

        new_q = current_q + self.learning_rate * (reward + self.discount_factor * next_max_q - current_q)
        self.q_table[state_key][action] = round(new_q, 4)

        self.total_steps += 1
        self.total_reward += reward

        # Record in experience memory
        self.experience_memory.append({
            "state": state_key,
            "action": action,
            "reward": reward,
            "next_state": next_state_key
        })
        if len(self.experience_memory) > 1000:
            self.experience_memory.pop(0)

        # Decay exploration
        self.epsilon = max(self.min_epsilon, self.epsilon * self.epsilon_decay)

        # Periodic policy save (every 20 updates)
        if self.total_steps % 20 == 0:
            self.save_policy()

    def save_policy(self):
        """Persists trained Q-table and metadata to disk."""
        try:
            self.q_table_path.parent.mkdir(parents=True, exist_ok=True)
            payload = {
                "metadata": {
                    "total_steps": self.total_steps,
                    "total_reward": round(self.total_reward, 2),
                    "epsilon": round(self.epsilon, 4),
                    "states_explored": len(self.q_table),
                },
                "q_table": self.q_table
            }
            with open(self.q_table_path, "w", encoding="utf-8") as f:
                json.dump(payload, f, indent=2)
        except Exception as e:
            agent_logger.warning(f"Failed saving Minecraft RL Q-table: {e}")

    def load_policy(self):
        """Loads previous Q-table experience from disk."""
        if not self.q_table_path.exists():
            return
        try:
            with open(self.q_table_path, "r", encoding="utf-8") as f:
                payload = json.load(f)
                self.q_table = payload.get("q_table", {})
                meta = payload.get("metadata", {})
                self.total_steps = meta.get("total_steps", 0)
                self.total_reward = meta.get("total_reward", 0.0)
                self.epsilon = meta.get("epsilon", self.epsilon)
                agent_logger.info(
                    f"Loaded Minecraft RL Brain: {len(self.q_table)} states, {self.total_steps} steps, eps={self.epsilon:.3f}"
                )
        except Exception as e:
            agent_logger.warning(f"Failed loading Minecraft RL Q-table: {e}")
