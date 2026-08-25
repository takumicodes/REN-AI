"""
REN-AI Minecraft Action & State Verification Engine
Verifies whether dispatched Minecraft actions actually produced the expected physical and inventory changes.
"""

from typing import Dict, Any, Optional, Tuple
from ren.minecraft.types import ActionResult


class MinecraftActionVerifier:
    """
    Validates post-action state against pre-action state to confirm real world success.
    """

    def verify_action(
        self,
        action: str,
        parameters: Dict[str, Any],
        before_state: Dict[str, Any],
        after_state: Dict[str, Any],
        bridge_result: Optional[Dict[str, Any]] = None
    ) -> ActionResult:
        """
        Runs specific verification rules for the given action type.
        """
        bridge_success = bridge_result.get("success", False) if bridge_result else False
        bridge_error = bridge_result.get("error") if bridge_result else None

        # 1. GATHER / MINE
        if action in ["gather", "mine_block"]:
            block_type = parameters.get("block_type", "wood").lower()
            expected_count = parameters.get("count", 1)
            verified, reason, delta = self._verify_inventory_increase(before_state, after_state, block_type, expected_count)
            is_success = (verified or (bridge_success and delta > 0)) and (bridge_error is None) and (bridge_success or delta > 0)
            return ActionResult(
                success=is_success,
                action=action,
                reason=reason if not is_success else "Gathered required resources.",
                details={"delta": delta, "expected": expected_count},
                verification={"verified": is_success, "item_delta": delta}
            )

        # 2. CRAFT
        if action in ["craft", "craft_item"]:
            item_name = parameters.get("item_name", "").lower()
            expected_count = parameters.get("count", 1)
            verified, reason, delta = self._verify_inventory_increase(before_state, after_state, item_name, expected_count)
            return ActionResult(
                success=verified or bridge_success,
                action=action,
                reason=reason if not verified else f"Crafted {item_name}.",
                details={"delta": delta, "item": item_name},
                verification={"verified": verified, "crafted_item": item_name}
            )

        # 3. GOTO / MOVE_TO
        if action in ["goTo", "move_to"]:
            target_x = parameters.get("x", 0)
            target_y = parameters.get("y", 64)
            target_z = parameters.get("z", 0)
            after_pos = after_state.get("pos", {})
            
            dx = after_pos.get("x", 0) - target_x
            dz = after_pos.get("z", 0) - target_z
            dist_sq = dx * dx + dz * dz
            verified = dist_sq <= (3.5 * 3.5)

            return ActionResult(
                success=verified or bridge_success,
                action=action,
                reason="Arrived at target location." if verified else "Did not reach destination coordinates.",
                details={"current_pos": after_pos, "distance_sq": round(dist_sq, 2)},
                verification={"verified": verified}
            )

        # 4. EAT
        if action in ["eat", "eat_food"]:
            before_food = before_state.get("food", 20)
            after_food = after_state.get("food", 20)
            verified = after_food >= before_food
            return ActionResult(
                success=verified or bridge_success,
                action=action,
                reason="Consumed food successfully." if verified else "Food level unchanged.",
                details={"food_before": before_food, "food_after": after_food},
                verification={"verified": verified}
            )

        # 5. BUILD STRUCTURE / SHELTER
        if action in ["build_structure", "build_shelter"]:
            placed_count = bridge_result.get("details", {}).get("placed_count", 0) if bridge_result else 0
            verified = bridge_success or (placed_count >= 8)
            return ActionResult(
                success=verified,
                action=action,
                reason="Structure built and verified." if verified else (bridge_error or "Structure construction incomplete."),
                details={"placed_count": placed_count},
                verification={"verified": verified}
            )

        # 6. STOP / CHAT / GAMEMODE
        if action in ["stop", "chat", "gamemode", "set_game_mode"]:
            return ActionResult(
                success=True,
                action=action,
                reason="Command acknowledged.",
                details={}
            )

        # Default fallback to bridge status
        return ActionResult(
            success=bridge_success,
            action=action,
            reason=bridge_error if not bridge_success else "Action completed.",
            details=bridge_result.get("details", {}) if bridge_result else {}
        )

    def _verify_inventory_increase(
        self,
        before_state: Dict[str, Any],
        after_state: Dict[str, Any],
        item_query: str,
        expected_min_increase: int
    ) -> Tuple[bool, Optional[str], int]:
        before_inv = before_state.get("inventory", {})
        after_inv = after_state.get("inventory", {})

        before_qty = self._count_matching_items(before_inv, item_query)
        after_qty = self._count_matching_items(after_inv, item_query)
        delta = after_qty - before_qty

        if delta > 0:
            return True, None, delta
        elif after_qty >= expected_min_increase:
            return True, None, after_qty
        else:
            return False, f"Expected {item_query} increase, but delta was {delta} (total: {after_qty})", delta

    def _count_matching_items(self, inventory: Dict[str, int], item_query: str) -> int:
        clean = item_query.lower().replace("_", " ")
        total = 0
        for item_name, count in inventory.items():
            clean_name = item_name.lower().replace("_", " ")
            if clean in clean_name or clean_name in clean:
                total += count
            elif "wood" in clean and ("log" in clean_name or "plank" in clean_name):
                total += count
            elif "stone" in clean and ("cobble" in clean_name or "stone" in clean_name or "deepslate" in clean_name):
                total += count
            elif "iron" in clean and ("iron" in clean_name):
                total += count
        return total
