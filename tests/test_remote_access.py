"""
Automated Test Suite for Global Remote Access, PWA, Authentication & Security
"""

import sys
import os
import time
from pathlib import Path

# Add project root to sys.path
ROOT_DIR = Path(__file__).resolve().parent.parent
try:
    from fastapi.testclient import TestClient
    from api.server import app
    from api.auth import set_configured_access_key, get_configured_access_key, clear_failed_attempts, generate_passkey
    from api.tunnel import print_qr_code
    client = TestClient(app)
    FASTAPI_AVAILABLE = True
except ImportError:
    client = None
    FASTAPI_AVAILABLE = False


def test_pwa_endpoints():
    if not FASTAPI_AVAILABLE:
        print("  [SKIP] fastapi not installed, skipping test_pwa_endpoints")
        return
    # 1. Manifest
    res_manifest = client.get("/manifest.json")
    assert res_manifest.status_code == 200
    data = res_manifest.json()
    assert data["name"] == "REN AI Assistant"
    assert data["display"] == "standalone"

    # 2. Service Worker
    res_sw = client.get("/sw.js")
    assert res_sw.status_code == 200
    assert "ren-ai-cache" in res_sw.text

    print("PASS: PWA Manifest & Service Worker endpoints")


def test_auth_disabled_mode():
    # Clear access key -> open mode
    set_configured_access_key("")
    assert get_configured_access_key() is None

    # Check status
    res_check = client.get("/api/auth/check")
    assert res_check.status_code == 200
    assert res_check.json()["auth_required"] is False

    # Protected routes work without token
    res_status = client.get("/api/status")
    assert res_status.status_code == 200

    res_chat = client.post("/api/chat", json={"message": "who are you", "stream": False})
    assert res_chat.status_code == 200

    print("PASS: Open / Local Mode (Auth disabled)")


def test_auth_enabled_mode():
    test_key = "SECURE_TEST_KEY_987"
    set_configured_access_key(test_key)
    clear_failed_attempts("testclient")

    try:
        # 1. Check endpoint shows auth required
        res_check = client.get("/api/auth/check")
        assert res_check.status_code == 200
        assert res_check.json()["auth_required"] is True

        # 2. Request without token -> 401
        res_unauth = client.get("/api/status")
        assert res_unauth.status_code == 401

        # 3. Request with invalid token -> 401
        res_invalid = client.get("/api/status", headers={"Authorization": "Bearer WRONG_KEY"})
        assert res_invalid.status_code == 401

        # 4. Verify passkey endpoint with wrong key -> 401
        res_verify_fail = client.post("/api/auth/verify", json={"key": "WRONG_KEY"})
        assert res_verify_fail.status_code == 401

        # 5. Verify passkey endpoint with correct key -> 200
        res_verify_ok = client.post("/api/auth/verify", json={"key": test_key})
        assert res_verify_ok.status_code == 200
        assert res_verify_ok.json()["valid"] is True

        # 6. Request with Bearer header -> 200
        res_auth_header = client.get("/api/status", headers={"Authorization": f"Bearer {test_key}"})
        assert res_auth_header.status_code == 200

        # 7. Request with query param ?token= -> 200
        res_auth_param = client.get(f"/api/status?token={test_key}")
        assert res_auth_param.status_code == 200

        # 8. Chat with token -> 200
        res_chat = client.post(
            "/api/chat",
            json={"message": "who are you", "stream": False},
            headers={"Authorization": f"Bearer {test_key}"}
        )
        assert res_chat.status_code == 200

        print("PASS: Protected Remote Access (Passkey verification, Bearer & Query auth)")

    finally:
        # Restore open mode
        set_configured_access_key("")
        clear_failed_attempts("testclient")


def test_qr_code_rendering():
    # Verify QR code generator runs without error
    test_url = "https://ren-sample.trycloudflare.com?token=123456"
    print_qr_code(test_url)
    print("PASS: Terminal QR Code rendering")


def run_all():
    print("\n" + "=" * 55)
    print(" RUNNING REMOTE ACCESS & SECURITY TEST SUITE")
    print("=" * 55)
    test_pwa_endpoints()
    test_auth_disabled_mode()
    test_auth_enabled_mode()
    test_qr_code_rendering()
    print("=" * 55)
    print(" ALL REMOTE ACCESS TESTS PASSED (100% HEALTHY)\n")


if __name__ == "__main__":
    run_all()
