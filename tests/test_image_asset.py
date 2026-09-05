"""
Tests for Phase 4: Image Asset Pipeline, Metadata Security, and Media Routes.
"""

import unittest
from fastapi.testclient import TestClient
from ren.media.image_asset import ImageAssetManager, MockImageProvider, image_asset_manager
from api.server import app


class TestImageAssetPipeline(unittest.TestCase):

    def setUp(self):
        self.asset_mgr = image_asset_manager
        self.client = TestClient(app)

    def test_mock_image_generation_and_asset_creation(self):
        # Generate image using Mock provider
        asset = self.asset_mgr.generate_image(
            prompt="A majestic cybernetic falcon over Tokyo",
            width=512,
            height=512,
            provider_name="mock",
            user_id="default"
        )
        self.assertIsNotNone(asset.id)
        self.assertEqual(asset.type, "image")
        self.assertEqual(asset.mime_type, "image/gif")
        self.assertTrue(asset.url.startswith("/api/assets/images/"))

        # Verify no file path leaked in public dict
        data = asset.to_dict()
        self.assertNotIn("_local_file_path", data)
        self.assertNotIn("D:\\", str(data))
        self.assertNotIn("C:\\", str(data))

    def test_asset_api_route(self):
        from api.auth import get_configured_access_key
        token = get_configured_access_key() or ""
        headers = {"Authorization": f"Bearer {token}"} if token else {}

        # Create an asset
        asset = self.asset_mgr.generate_image(
            prompt="Futuristic neon holographic interface",
            width=512,
            height=512,
            provider_name="mock",
            user_id="default"
        )

        # GET /api/assets/images/{asset.id}
        resp = self.client.get(f"/api/assets/images/{asset.id}", headers=headers)
        self.assertEqual(resp.status_code, 200)
        self.assertEqual(resp.headers.get("content-type"), "image/gif")

        # GET /api/assets/images/{asset.id}/info
        info_resp = self.client.get(f"/api/assets/images/{asset.id}/info", headers=headers)
        self.assertEqual(info_resp.status_code, 200)
        info_data = info_resp.json()
        self.assertEqual(info_data["id"], asset.id)
        self.assertEqual(info_data["type"], "image")

    def test_invalid_and_path_traversal_access(self):
        from api.auth import get_configured_access_key
        token = get_configured_access_key() or ""
        headers = {"Authorization": f"Bearer {token}"} if token else {}

        # Non-existent asset
        resp = self.client.get("/api/assets/images/non_existent_id", headers=headers)
        self.assertEqual(resp.status_code, 404)

        # Path traversal attempt in ID
        resp2 = self.client.get("/api/assets/images/../../etc/passwd", headers=headers)
        # Should either 404 or 400, never serve system files
        self.assertIn(resp2.status_code, [404, 400])


if __name__ == "__main__":
    unittest.main()
