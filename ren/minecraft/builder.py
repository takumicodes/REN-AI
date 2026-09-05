"""
REN-AI Minecraft Procedural 3D Construction Engine
Generates verified architectural blueprints and construction subtasks for houses, shelters, towers, and bridges.
"""

from typing import Dict, Any, List, Tuple
from dataclasses import dataclass, field
from ren.minecraft.types import Subtask, TaskStatus


@dataclass
class BlockPlacement:
    x: int
    y: int
    z: int
    block_type: str = "oak_planks"
    is_doorway: bool = False
    is_roof: bool = False
    is_furniture: bool = False


@dataclass
class StructureBlueprint:
    name: str
    width: int
    length: int
    height: int
    blocks: List[BlockPlacement] = field(default_factory=list)
    material_costs: Dict[str, int] = field(default_factory=dict)
    interior_features: List[Dict[str, Any]] = field(default_factory=list)


class MinecraftProceduralBuilder:
    """
    Procedural 3D Builder for deterministic construction of shelters, houses, towers, and bridges.
    """

    def generate_medieval_cottage_blueprint(self, origin_x: int, origin_y: int, origin_z: int) -> StructureBlueprint:
        """
        Generates an aesthetic 6x6 Medieval Timber Cottage:
        - Corner Pillars: Oak logs (y=0 to y=4)
        - Foundation / Floor: Cobblestone (y=0)
        - Walls: Oak planks with Glass Windows (y=1 to y=3)
        - Doorway: (x=2, z=0)
        - Pitched Overhanging Roof: Oak planks & Cobblestone trim (y=4, y=5)
        - Complete Interior: Bed, Crafting Table, Furnace, Chest, Torches
        """
        blocks: List[BlockPlacement] = []
        width = 6
        length = 6
        height = 4

        # 1. Foundation / Floor (y = 0)
        for dx in range(width):
            for dz in range(length):
                blocks.append(BlockPlacement(
                    x=origin_x + dx,
                    y=origin_y,
                    z=origin_z + dz,
                    block_type="cobblestone"
                ))

        # 2. Walls, Corner Logs, and Windows (y = 1 to y = 3)
        for dy in range(1, height):
            for dx in range(width):
                for dz in range(length):
                    # Perimeter only
                    if dx == 0 or dx == width - 1 or dz == 0 or dz == length - 1:
                        # Corner log pillars
                        if (dx == 0 or dx == width - 1) and (dz == 0 or dz == length - 1):
                            blocks.append(BlockPlacement(
                                x=origin_x + dx,
                                y=origin_y + dy,
                                z=origin_z + dz,
                                block_type="oak_log"
                            ))
                        # Door opening
                        elif dx == 2 and dz == 0 and dy in [1, 2]:
                            continue
                        # Glass Windows at eye level (dy=2, middle of walls)
                        elif dy == 2 and (dx in [2, 3] or dz in [2, 3]):
                            blocks.append(BlockPlacement(
                                x=origin_x + dx,
                                y=origin_y + dy,
                                z=origin_z + dz,
                                block_type="glass"
                            ))
                        else:
                            blocks.append(BlockPlacement(
                                x=origin_x + dx,
                                y=origin_y + dy,
                                z=origin_z + dz,
                                block_type="oak_planks"
                            ))

        # 3. Pitched Aesthetic Roof (y = 4 and y = 5)
        for dx in range(width):
            for dz in range(length):
                blocks.append(BlockPlacement(
                    x=origin_x + dx,
                    y=origin_y + height,
                    z=origin_z + dz,
                    block_type="oak_planks",
                    is_roof=True
                ))

        # Peak Roof Row (dx=2, 3 across length)
        for dx in [2, 3]:
            for dz in range(length):
                blocks.append(BlockPlacement(
                    x=origin_x + dx,
                    y=origin_y + height + 1,
                    z=origin_z + dz,
                    block_type="cobblestone",
                    is_roof=True
                ))

        material_costs = {
            "oak_planks": sum(1 for b in blocks if b.block_type == "oak_planks"),
            "oak_log": sum(1 for b in blocks if b.block_type == "oak_log"),
            "cobblestone": sum(1 for b in blocks if b.block_type == "cobblestone"),
            "glass": sum(1 for b in blocks if b.block_type == "glass"),
            "door": 1,
            "torches": 4
        }

        interior_features = [
            {"feature": "crafting_table", "pos": {"x": origin_x + 1, "y": origin_y + 1, "z": origin_z + 4}},
            {"feature": "furnace", "pos": {"x": origin_x + 2, "y": origin_y + 1, "z": origin_z + 4}},
            {"feature": "chest", "pos": {"x": origin_x + 4, "y": origin_y + 1, "z": origin_z + 4}},
            {"feature": "white_bed", "pos": {"x": origin_x + 4, "y": origin_y + 1, "z": origin_z + 1}},
            {"feature": "torch", "pos": {"x": origin_x + 2, "y": origin_y + 3, "z": origin_z + 1}},
            {"feature": "torch", "pos": {"x": origin_x + 3, "y": origin_y + 3, "z": origin_z + 4}}
        ]

        return StructureBlueprint(
            name="medieval_cottage",
            width=width,
            length=length,
            height=height + 2,
            blocks=blocks,
            material_costs=material_costs,
            interior_features=interior_features
        )

    def generate_modern_villa_blueprint(self, origin_x: int, origin_y: int, origin_z: int) -> StructureBlueprint:
        """
        Generates an aesthetic 8x8 Modern Luxury Villa:
        - Foundation: Smooth stone / quartz
        - Large panoramic glass facades
        - 2nd Floor Balcony with open terrace
        - Complete interior amenities
        """
        blocks: List[BlockPlacement] = []
        width = 8
        length = 8
        height = 6

        # Floor 1 (y=0)
        for dx in range(width):
            for dz in range(length):
                blocks.append(BlockPlacement(x=origin_x + dx, y=origin_y, z=origin_z + dz, block_type="smooth_stone"))

        # Floor 1 Walls (y=1 to y=3)
        for dy in range(1, 4):
            for dx in range(width):
                for dz in range(length):
                    if dx == 0 or dx == width - 1 or dz == 0 or dz == length - 1:
                        if dx in [3, 4] and dz == 0 and dy in [1, 2]:
                            continue # Double doorway
                        elif dy in [1, 2] and (dx in [1, 2, 5, 6] or dz in [2, 3, 4, 5]):
                            blocks.append(BlockPlacement(x=origin_x + dx, y=origin_y + dy, z=origin_z + dz, block_type="glass"))
                        else:
                            blocks.append(BlockPlacement(x=origin_x + dx, y=origin_y + dy, z=origin_z + dz, block_type="oak_planks"))

        # Floor 2 Ceiling / Floor (y=4)
        for dx in range(width):
            for dz in range(length):
                blocks.append(BlockPlacement(x=origin_x + dx, y=origin_y + 4, z=origin_z + dz, block_type="smooth_stone"))

        # Floor 2 Balcony & Master Bedroom (y=5, y=6)
        for dx in range(width // 2):
            for dz in range(length):
                if dx == 0 or dx == (width // 2) - 1 or dz == 0 or dz == length - 1:
                    blocks.append(BlockPlacement(x=origin_x + dx, y=origin_y + 5, z=origin_z + dz, block_type="oak_planks"))

        # Roof (y=6)
        for dx in range(width // 2):
            for dz in range(length):
                blocks.append(BlockPlacement(x=origin_x + dx, y=origin_y + 6, z=origin_z + dz, block_type="smooth_stone", is_roof=True))

        return StructureBlueprint(
            name="modern_villa",
            width=width,
            length=length,
            height=height + 1,
            blocks=blocks,
            material_costs={"building_blocks": len(blocks)},
            interior_features=[
                {"feature": "crafting_table", "pos": {"x": origin_x + 1, "y": origin_y + 1, "z": origin_z + 6}},
                {"feature": "furnace", "pos": {"x": origin_x + 2, "y": origin_y + 1, "z": origin_z + 6}},
                {"feature": "chest", "pos": {"x": origin_x + 6, "y": origin_y + 1, "z": origin_z + 6}},
                {"feature": "white_bed", "pos": {"x": origin_x + 2, "y": origin_y + 5, "z": origin_z + 4}},
                {"feature": "torch", "pos": {"x": origin_x + 4, "y": origin_y + 3, "z": origin_z + 4}}
            ]
        )

    def generate_small_house_blueprint(self, origin_x: int, origin_y: int, origin_z: int, material: str = "oak_planks") -> StructureBlueprint:
        """
        Generates a 5x5 cozy survival house blueprint:
        - Foundation / Floor: 5x5 cobblestone/wood
        - Walls: 5x5 perimeter with Glass Windows and Corner Logs
        - Doorway at (x=2, z=0)
        - Ceiling/Roof with interior furnishings
        """
        return self.generate_medieval_cottage_blueprint(origin_x, origin_y, origin_z)

    def generate_quick_shelter_blueprint(self, origin_x: int, origin_y: int, origin_z: int, material: str = "dirt") -> StructureBlueprint:
        """
        Generates a fast 3x3 survival shelter for nightfall defense.
        """
        blocks: List[BlockPlacement] = []
        width = 3
        length = 3
        height = 2

        # Walls (y = 0 and y = 1)
        for dy in range(height):
            for dx in range(width):
                for dz in range(length):
                    if dx == 0 or dx == width - 1 or dz == 0 or dz == length - 1:
                        # Door opening
                        if dx == 1 and dz == 0:
                            continue
                        blocks.append(BlockPlacement(
                            x=origin_x + dx,
                            y=origin_y + dy,
                            z=origin_z + dz,
                            block_type=material
                        ))

        # Roof (y = 2)
        for dx in range(width):
            for dz in range(length):
                blocks.append(BlockPlacement(
                    x=origin_x + dx,
                    y=origin_y + height,
                    z=origin_z + dz,
                    block_type=material,
                    is_roof=True
                ))

        material_costs = {"building_blocks": len(blocks)}

        return StructureBlueprint(
            name="quick_shelter",
            width=width,
            length=length,
            height=height + 1,
            blocks=blocks,
            material_costs=material_costs
        )

    def create_construction_subtasks(
        self,
        blueprint: StructureBlueprint,
        current_inventory: Dict[str, int]
    ) -> List[Subtask]:
        """
        Decomposes the blueprint into a sequence of verified executable construction subtasks.
        """
        subtasks: List[Subtask] = []
        task_counter = 1

        # 1. Material Verification & Gathering
        total_building_blocks = sum(
            c for k, c in current_inventory.items()
            if any(b in k for b in ["plank", "dirt", "cobble", "stone", "log"])
        )
        required_blocks = len(blueprint.blocks)

        if total_building_blocks < required_blocks:
            needed = required_blocks - total_building_blocks
            logs_needed = max(3, (needed + 3) // 4)
            subtasks.append(Subtask(
                id=f"build_step_{task_counter}",
                action="gather",
                parameters={"block_type": "wood", "count": logs_needed}
            ))
            task_counter += 1

            subtasks.append(Subtask(
                id=f"build_step_{task_counter}",
                action="craft",
                parameters={"item_name": "oak_planks", "count": logs_needed}
            ))
            task_counter += 1

        # 2. Main 3D Construction Execution Step (Node.js verified placement)
        subtasks.append(Subtask(
            id=f"build_step_{task_counter}",
            action="build_structure",
            parameters={
                "structure_name": blueprint.name,
                "width": blueprint.width,
                "length": blueprint.length,
                "height": blueprint.height,
                "blocks": [{"x": b.x, "y": b.y, "z": b.z, "type": b.block_type} for b in blueprint.blocks],
                "interior": blueprint.interior_features
            }
        ))
        task_counter += 1

        return subtasks
