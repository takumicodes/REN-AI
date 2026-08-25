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

    def generate_small_house_blueprint(self, origin_x: int, origin_y: int, origin_z: int, material: str = "oak_planks") -> StructureBlueprint:
        """
        Generates a 4x4 cozy survival house blueprint:
        - Foundation / Floor: 4x4 cobblestone/wood
        - Walls: 4x4 perimeter, 2-blocks high
        - Doorway at (x=1, z=0)
        - Ceiling/Roof at y=3
        - Interior Torches & Crafting Table
        """
        blocks: List[BlockPlacement] = []
        width = 4
        length = 4
        height = 3

        # 1. Foundation / Floor (y = 0)
        for dx in range(width):
            for dz in range(length):
                blocks.append(BlockPlacement(
                    x=origin_x + dx,
                    y=origin_y,
                    z=origin_z + dz,
                    block_type="cobblestone" if material == "wooden" else material
                ))

        # 2. Walls (y = 1 and y = 2)
        for dy in [1, 2]:
            for dx in range(width):
                for dz in range(length):
                    # Perimeter only
                    if dx == 0 or dx == width - 1 or dz == 0 or dz == length - 1:
                        # Doorway opening at dx=1, dz=0
                        if dx == 1 and dz == 0:
                            continue
                        blocks.append(BlockPlacement(
                            x=origin_x + dx,
                            y=origin_y + dy,
                            z=origin_z + dz,
                            block_type=material
                        ))

        # 3. Ceiling / Roof (y = 3)
        for dx in range(width):
            for dz in range(length):
                blocks.append(BlockPlacement(
                    x=origin_x + dx,
                    y=origin_y + height,
                    z=origin_z + dz,
                    block_type=material,
                    is_roof=True
                ))

        # Material calculation
        total_blocks = len(blocks)
        material_costs = {
            "planks": sum(1 for b in blocks if "plank" in b.block_type or b.block_type == material),
            "cobblestone": sum(1 for b in blocks if "cobble" in b.block_type),
            "torches": 2,
            "door": 1
        }

        interior_features = [
            {"feature": "torch", "pos": {"x": origin_x + 2, "y": origin_y + 2, "z": origin_z + 1}},
            {"feature": "crafting_table", "pos": {"x": origin_x + 1, "y": origin_y + 1, "z": origin_z + 2}},
            {"feature": "furnace", "pos": {"x": origin_x + 2, "y": origin_y + 1, "z": origin_z + 2}}
        ]

        return StructureBlueprint(
            name="small_house",
            width=width,
            length=length,
            height=height + 1,
            blocks=blocks,
            material_costs=material_costs,
            interior_features=interior_features
        )

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
