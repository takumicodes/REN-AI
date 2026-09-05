import unittest
from ren.core.device_context import (
    DeviceContext,
    DeviceInfo,
    DeviceType,
    PlatformType,
    ConnectionState,
    DeviceManager,
    device_manager,
)
from ren.core.events import EventBus, EventType
from ren.tools.system import BatteryStatusTool, SystemStatusTool
from ren.core.router import IntentRouter


class TestDeviceContextAndRouting(unittest.TestCase):

    def setUp(self):
        self.dev_mgr = device_manager
        # Register a companion phone
        phone_info = DeviceInfo(
            device_id="phone_abc123",
            user_id="default",
            device_type=DeviceType.PHONE,
            platform=PlatformType.ANDROID,
            name="Pixel 8 Pro",
            capabilities=["battery", "storage", "notifications"],
            connection_state=ConnectionState.CONNECTED,
            battery_info={"level": 82, "charging": False},
            storage_info={"free_gb": 45}
        )
        self.dev_mgr.register_device(phone_info)

    def test_explicit_pc_routing(self):
        ctx = self.dev_mgr.resolve_context(
            query="Check status on my PC",
            source_device_id="phone_abc123"
        )
        self.assertEqual(ctx.target_device_id, "pc_host")
        self.assertTrue(ctx.is_target_host)

    def test_explicit_phone_routing(self):
        ctx = self.dev_mgr.resolve_context(
            query="How is the battery on my phone?",
            source_device_id="pc_host"
        )
        self.assertEqual(ctx.target_device_id, "phone_abc123")
        self.assertFalse(ctx.is_target_host)

    def test_source_device_default_for_battery(self):
        # When asked from phone: defaults to phone
        ctx_phone = self.dev_mgr.resolve_context(
            query="What is my battery?",
            source_device_id="phone_abc123"
        )
        self.assertEqual(ctx_phone.target_device_id, "phone_abc123")

        # When asked from PC: defaults to PC
        ctx_pc = self.dev_mgr.resolve_context(
            query="What is my battery?",
            source_device_id="pc_host"
        )
        self.assertEqual(ctx_pc.target_device_id, "pc_host")

    def test_battery_status_tool_device_awareness(self):
        tool = BatteryStatusTool()
        # Test phone battery inspection
        ctx_phone = DeviceContext(
            user_id="default",
            source_device_id="phone_abc123",
            target_device_id="phone_abc123"
        )
        res_phone = tool.run(device_context=ctx_phone)
        self.assertTrue(res_phone.success)
        self.assertIn("Phone Battery", res_phone.output)

        # Test PC battery inspection
        ctx_pc = DeviceContext(
            user_id="default",
            source_device_id="pc_host",
            target_device_id="pc_host"
        )
        res_pc = tool.run(device_context=ctx_pc)
        self.assertTrue(res_pc.success)
        self.assertIn("PC Battery", res_pc.output)

    def test_fast_route_downloads_ambiguity(self):
        ambiguous_ctx = DeviceContext(
            user_id="default",
            source_device_id="phone_abc123",
            target_device_id="phone_abc123",
            is_ambiguous=True
        )
        handled, msg = IntentRouter.try_fast_route(
            "organize downloads",
            device_context=ambiguous_ctx
        )
        self.assertTrue(handled)
        self.assertIn("Would you like me to organize Downloads on your PC or your Phone?", msg)

    def test_event_bus_new_event_types(self):
        bus = EventBus()
        received = []

        def callback(evt, data):
            received.append((evt, data))

        bus.subscribe(EventType.DEVICE_CONNECTED, callback)
        bus.subscribe(EventType.UPGRADE_COMPLETED, callback)

        bus.publish(EventType.DEVICE_CONNECTED, {"device_id": "test_dev"})
        bus.publish(EventType.UPGRADE_COMPLETED, {"version": "2.0"})

        self.assertEqual(len(received), 2)
        self.assertEqual(received[0][0], EventType.DEVICE_CONNECTED)
        self.assertEqual(received[1][0], EventType.UPGRADE_COMPLETED)


if __name__ == "__main__":
    unittest.main()
