"""
REN-AI Minecraft World State Representation Engine 12.0
Compact, structured, typed WorldState capturing real-time physics, inventory, entities, environment, and task status.
Provides high-efficiency compact observations for deterministic decision engines and LLM planners.
"""

from dataclasses import dataclass, field
from typing import Dict, Any, List, Optional, Tuple


@dataclass
class PlayerEquipment:
    """Equipment worn or held by the agent."""
    main_hand: Optional[str] = None
    off_hand: Optional[str] = None
    helmet: Optional[str] = None
    chestplate: Optional[str] = None
    leggings: Optional[str] = None
    boots: Optional[str] = None
    armor_points: int = 0

    def to_dict(self) -> Dict[str, Any]:
        return {
            "main_hand": self.main_hand,
            "off_hand": self.off_hand,
            "helmet": self.helmet,
            "chestplate": self.chestplate,
            "leggings": self.leggings,
            "boots": self.boots,
            "armor_points": self.armor_points
        }


@dataclass
class WorldState:
    """
    Compact, structured snapshot of the agent and environment state.
    """
    # 1. Vitals & Position
    hp: int = 20
    max_hp: int = 20
    food: int = 20
    saturation: float = 5.0
    pos: Dict[str, float] = field(default_factory=lambda: {"x": 0.0, "y": 64.0, "z": 0.0})
    yaw: float = 0.0
    pitch: float = 0.0
    dimension: str = "overworld"
    biome: str = "plains"

    # 2. Inventory & Equipment
    inventory: Dict[str, int] = field(default_factory=dict)
    equipment: PlayerEquipment = field(default_factory=PlayerEquipment)
    free_slots: int = 36

    # 3. Environment & Time
    time_of_day: str = "day"  # "day", "dusk", "night"
    raw_time: int = 1000
    is_raining: bool = False
    light_level: int = 15

    # 4. Entities & Surroundings
    hostile_mobs: List[Dict[str, Any]] = field(default_factory=list)
    passive_animals: List[Dict[str, Any]] = field(default_factory=list)
    nearby_players: List[Dict[str, Any]] = field(default_factory=list)
    dropped_items: List[Dict[str, Any]] = field(default_factory=list)
    nearest_player: Optional[str] = None
    nearest_player_distance: float = 999.0

    # 5. Nearby Blocks & POIs
    nearby_crafting_tables: List[Dict[str, int]] = field(default_factory=list)
    nearby_furnaces: List[Dict[str, int]] = field(default_factory=list)
    nearby_beds: List[Dict[str, int]] = field(default_factory=list)
    nearby_chests: List[Dict[str, int]] = field(default_factory=list)
    nearby_hazards: List[Dict[str, Any]] = field(default_factory=list)  # lava, fire, cactus

    # 6. Navigation & Task State
    current_destination: Optional[Dict[str, float]] = None
    is_moving: bool = False
    is_stuck: bool = False
    path_status: str = "idle"  # "idle", "navigating", "arrived", "unreachable"
    active_goal: Optional[str] = None
    active_subtask: Optional[str] = None
    task_progress: float = 0.0
    last_action: Optional[str] = None
    last_action_result: Optional[str] = None
    threat_level: str = "SAFE"  # "SAFE", "CAUTION", "DANGER", "COMBAT"

    # -------------------------------------------------------------
    # Helper Accessors
    # -------------------------------------------------------------
    @property
    def total_logs(self) -> int:
        return sum(c for k, c in self.inventory.items() if "log" in k or "wood" in k)

    @property
    def total_planks(self) -> int:
        return sum(c for k, c in self.inventory.items() if "plank" in k)

    @property
    def total_cobblestone(self) -> int:
        return self.inventory.get("cobblestone", 0) + self.inventory.get("stone", 0) + self.inventory.get("deepslate", 0)

    @property
    def total_iron(self) -> int:
        return self.inventory.get("iron_ingot", 0)

    @property
    def total_raw_iron(self) -> int:
        return self.inventory.get("raw_iron", 0) + self.inventory.get("iron_ore", 0)

    @property
    def total_food(self) -> int:
        food_keys = ["beef", "porkchop", "mutton", "chicken", "bread", "apple", "cooked_beef", "cooked_porkchop", "cooked_mutton", "cooked_chicken"]
        return sum(self.inventory.get(k, 0) for k in food_keys)

    @property
    def total_building_blocks(self) -> int:
        return sum(c for k, c in self.inventory.items() if any(b in k for b in ["plank", "dirt", "cobble", "stone", "log", "brick", "wool"]))

    @property
    def has_weapon(self) -> bool:
        if self.equipment.main_hand and any(w in self.equipment.main_hand for w in ["sword", "axe", "mace"]):
            return True
        return any(k in self.inventory for k in ["mace", "diamond_sword", "iron_sword", "stone_sword", "wooden_sword", "diamond_axe", "iron_axe", "stone_axe"])

    @property
    def has_pickaxe(self) -> bool:
        if self.equipment.main_hand and "pickaxe" in self.equipment.main_hand:
            return True
        return any(k in self.inventory for k in ["diamond_pickaxe", "iron_pickaxe", "stone_pickaxe", "wooden_pickaxe"])

    @property
    def has_shield(self) -> bool:
        return "shield" in self.inventory or (self.equipment.off_hand and "shield" in self.equipment.off_hand)

    def has_item(self, name: str, min_count: int = 1) -> bool:
        clean = name.lower().replace(" ", "_")
        for item, count in self.inventory.items():
            if clean in item or item in clean:
                if count >= min_count:
                    return True
        return False

    def get_item_count(self, name: str) -> int:
        clean = name.lower().replace(" ", "_")
        total = 0
        for item, count in self.inventory.items():
            if clean in item or item in clean:
                total += count
        return total

    # -------------------------------------------------------------
    # Compact LLM & Diagnostic Observations
    # -------------------------------------------------------------
    def to_compact_observation(self) -> str:
        """
        Generates a token-efficient text summary for LLM prompts and logging.
        Never bloats prompt tokens with massive block arrays.
        """
        inv_preview = ", ".join([f"{k}:{v}" for k, v in list(self.inventory.items())[:6]]) or "empty"
        hostiles = ", ".join([f"{h['name']}({h.get('distance', 0)}m)" for h in self.hostile_mobs[:3]]) or "none"
        player_info = f"{self.nearest_player}({self.nearest_player_distance:.1f}m)" if self.nearest_player else "none"

        return (
            f"[HP:{self.hp}/20|FD:{self.food}/20|Time:{self.time_of_day}|Threat:{self.threat_level}] "
            f"Pos:({int(self.pos.get('x',0))},{int(self.pos.get('y',64))},{int(self.pos.get('z',0))}) "
            f"Inv:[{inv_preview}] Hostiles:[{hostiles}] Player:[{player_info}] "
            f"Task:[{self.active_goal or 'IDLE'}:{self.active_subtask or 'NONE'} {self.task_progress:.0f}%]"
        )

    def to_dict(self) -> Dict[str, Any]:
        return {
            "hp": self.hp,
            "max_hp": self.max_hp,
            "food": self.food,
            "saturation": self.saturation,
            "pos": self.pos,
            "yaw": self.yaw,
            "pitch": self.pitch,
            "dimension": self.dimension,
            "biome": self.biome,
            "inventory": self.inventory,
            "equipment": self.equipment.to_dict(),
            "free_slots": self.free_slots,
            "time_of_day": self.time_of_day,
            "raw_time": self.raw_time,
            "threat_level": self.threat_level,
            "hostile_mobs": self.hostile_mobs,
            "passive_animals": self.passive_animals,
            "nearby_players": self.nearby_players,
            "nearest_player": self.nearest_player,
            "nearest_player_distance": self.nearest_player_distance,
            "active_goal": self.active_goal,
            "active_subtask": self.active_subtask,
            "task_progress": self.task_progress,
            "is_moving": self.is_moving,
            "is_stuck": self.is_stuck,
            "path_status": self.path_status
        }
