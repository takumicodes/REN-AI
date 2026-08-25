"""
Unit Test Suite for REN-AI Minecraft Priority-Based Event System
"""

import sys
from pathlib import Path
root_dir = Path(__file__).resolve().parent.parent
if str(root_dir) not in sys.path:
    sys.path.insert(0, str(root_dir))

from ren.minecraft.events import MinecraftEventBus, MinecraftEvent, EventType, EventPriority


def test_event_bus():
    print("\n" + "=" * 64)
    print(" [*] RUNNING MINECRAFT PRIORITY EVENT BUS TESTS")
    print("=" * 64)

    bus = MinecraftEventBus()
    type_handled = []
    priority_handled = []

    # 1. Subscriptions
    bus.subscribe(EventType.DAMAGE_TAKEN, lambda e: type_handled.append(e))
    bus.subscribe_priority(EventPriority.CRITICAL, lambda e: priority_handled.append(e))

    # 2. Publish Events
    ev1 = MinecraftEvent(
        event_type=EventType.DAMAGE_TAKEN,
        priority=EventPriority.CRITICAL,
        data={"health": 6}
    )
    bus.publish(ev1)

    ev2 = MinecraftEvent(
        event_type=EventType.RESOURCE_FOUND,
        priority=EventPriority.MEDIUM,
        data={"resource": "diamond_ore", "coords": {"x": 14, "y": -58, "z": 200}}
    )
    bus.publish(ev2)

    assert len(type_handled) == 1
    assert type_handled[0].event_type == EventType.DAMAGE_TAKEN
    assert len(priority_handled) == 1
    assert priority_handled[0].priority == EventPriority.CRITICAL
    print("  [PASS] Event publishing & subscription verified.")

    # 3. Filtering & History
    crit_events = bus.get_recent_events(limit=5, min_priority=EventPriority.HIGH)
    assert len(crit_events) == 1
    assert crit_events[0].event_type == EventType.DAMAGE_TAKEN
    print("  [PASS] Priority filtering & event history verified.")

    print("\n" + "=" * 64)
    print(" [PASS] ALL EVENT BUS TESTS PASSED (100%)")
    print("=" * 64 + "\n")


if __name__ == "__main__":
    test_event_bus()
