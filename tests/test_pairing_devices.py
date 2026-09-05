"""
Tests for Phase 5: Device Manager, QR Connect, Pairing Handshake, and Endpoint Rotation.
"""

import unittest
import time
from fastapi.testclient import TestClient
from ren.devices.pairing import PairingManager, QRCodeService, pairing_manager
from ren.core.device_context import device_manager, DeviceType, ConnectionState
from api.server import app
from api.auth import get_configured_access_key


class TestPairingAndDevices(unittest.TestCase):

    def setUp(self):
        self.mgr = PairingManager(default_ttl_seconds=300)
        self.client = TestClient(app)
        token = get_configured_access_key() or ""
        self.headers = {"Authorization": f"Bearer {token}"} if token else {}

    def test_qr_generation_and_payload(self):
        ch = self.mgr.create_pairing_challenge(endpoint="https://ren-test.trycloudflare.com")
        self.assertTrue(ch.pairing_id.startswith("pair_"))
        self.assertFalse(ch.is_expired)
        self.assertFalse(ch.is_used)

        payload = ch.to_payload()
        self.assertEqual(payload["type"], "ren_pairing")
        self.assertEqual(payload["protocol_version"], 1)
        self.assertEqual(payload["backend_endpoint"], "https://ren-test.trycloudflare.com")

        # Test base64 QR generation
        qr_b64 = QRCodeService.generate_qr_base64(payload)
        self.assertTrue(qr_b64.startswith("data:image/png;base64,"))

    def test_successful_pairing_handshake(self):
        ch = self.mgr.create_pairing_challenge(endpoint="https://ren-tunnel.xyz")

        success, msg, data = self.mgr.verify_and_pair(
            pairing_id=ch.pairing_id,
            challenge=ch.challenge,
            device_id="phone_pixel_99",
            device_name="Pixel 8 Pro",
            platform_str="android"
        )
        self.assertTrue(success)
        self.assertEqual(data["status"], "paired")
        self.assertEqual(data["device_id"], "phone_pixel_99")
        self.assertTrue(len(data["device_token"]) > 10)

        # Verify device is registered in device_manager
        dev = device_manager.get_device("phone_pixel_99")
        self.assertIsNotNone(dev)
        self.assertEqual(dev.name, "Pixel 8 Pro")
        self.assertEqual(dev.connection_state, ConnectionState.CONNECTED)

    def test_replay_protection(self):
        ch = self.mgr.create_pairing_challenge(endpoint="https://ren-tunnel.xyz")

        # First use -> Success
        success1, _, _ = self.mgr.verify_and_pair(
            pairing_id=ch.pairing_id,
            challenge=ch.challenge,
            device_id="phone_replay_test"
        )
        self.assertTrue(success1)

        # Second use -> Rejected
        success2, msg2, _ = self.mgr.verify_and_pair(
            pairing_id=ch.pairing_id,
            challenge=ch.challenge,
            device_id="phone_replay_test"
        )
        self.assertFalse(success2)
        self.assertIn("replay", msg2.lower())

    def test_expiration_rejection(self):
        # Create challenge with 0 TTL
        ch = self.mgr.create_pairing_challenge(ttl_seconds=-1)
        self.assertTrue(ch.is_expired)

        success, msg, _ = self.mgr.verify_and_pair(
            pairing_id=ch.pairing_id,
            challenge=ch.challenge,
            device_id="phone_expired_test"
        )
        self.assertFalse(success)
        self.assertIn("expired", msg.lower())

    def test_endpoint_rotation_preserves_device_identity(self):
        # Initial endpoint
        self.mgr.set_backend_endpoint("https://tunnel-1.trycloudflare.com")
        ch1 = self.mgr.create_pairing_challenge()
        self.mgr.verify_and_pair(ch1.pairing_id, ch1.challenge, "phone_persistent_id")

        dev1 = device_manager.get_device("phone_persistent_id")
        self.assertIsNotNone(dev1)

        # Endpoint changes upon backend restart
        self.mgr.set_backend_endpoint("https://tunnel-2-new.trycloudflare.com")
        ch2 = self.mgr.create_pairing_challenge()
        # Phone reconnects / scans new QR
        success, _, data = self.mgr.verify_and_pair(ch2.pairing_id, ch2.challenge, "phone_persistent_id")
        self.assertTrue(success)
        self.assertEqual(data["backend_endpoint"], "https://tunnel-2-new.trycloudflare.com")

        # Identity preserved (no duplicate device created)
        all_phones = [d for d in device_manager.list_devices() if d.device_id == "phone_persistent_id"]
        self.assertEqual(len(all_phones), 1)

    def test_pairing_api_endpoints(self):
        # 1. GET /api/devices/pairing/qr
        res_qr = self.client.get("/api/devices/pairing/qr", headers=self.headers)
        self.assertEqual(res_qr.status_code, 200)
        qr_data = res_qr.json()
        self.assertIn("pairing_id", qr_data)
        self.assertIn("qr_image_base64", qr_data)

        pairing_id = qr_data["pairing_id"]
        challenge = qr_data["payload"]["challenge"]

        # 2. POST /api/devices/pairing/verify
        res_pair = self.client.post("/api/devices/pairing/verify", json={
            "pairing_id": pairing_id,
            "challenge": challenge,
            "device_id": "phone_api_test_01",
            "device_name": "Galaxy S24",
            "platform": "android"
        }, headers=self.headers)
        self.assertEqual(res_pair.status_code, 200)
        self.assertEqual(res_pair.json()["status"], "paired")

        # 3. POST /api/devices/heartbeat
        res_hb = self.client.post("/api/devices/heartbeat", json={
            "device_id": "phone_api_test_01",
            "battery": {"level": 94, "charging": True},
            "storage": {"free_gb": 128}
        }, headers=self.headers)
        self.assertEqual(res_hb.status_code, 200)

        # 4. GET /api/devices
        res_devs = self.client.get("/api/devices", headers=self.headers)
        self.assertEqual(res_devs.status_code, 200)
        devs = res_devs.json()
        self.assertTrue(any(d["device_id"] == "phone_api_test_01" for d in devs))

        # 5. POST /api/devices/{id}/disconnect
        res_disc = self.client.post("/api/devices/phone_api_test_01/disconnect", headers=self.headers)
        self.assertEqual(res_disc.status_code, 200)

        # 6. POST /api/devices/{id}/revoke
        res_rev = self.client.post("/api/devices/phone_api_test_01/revoke", headers=self.headers)
        self.assertEqual(res_rev.status_code, 200)


if __name__ == "__main__":
    unittest.main()
