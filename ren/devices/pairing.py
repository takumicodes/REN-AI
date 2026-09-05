"""
REN Multi-Device Pairing & QR Code Architecture
Implements secure one-time challenges, replay protection, device registration,
endpoint rotation, and persistent device identity decoupled from ephemeral Cloudflare URLs.
"""

import time
import uuid
import secrets
import json
import base64
import io
import threading
from dataclasses import dataclass, field, asdict
from typing import Dict, Optional, Any, Tuple, List
from pathlib import Path

import qrcode

from ren.core.device_context import (
    device_manager,
    DeviceInfo,
    DeviceType,
    PlatformType,
    ConnectionState,
)
from ren.monitoring.logger import agent_logger, error_logger
from ren.core.events import event_bus, EventType


@dataclass
class PairingChallenge:
    pairing_id: str
    challenge: str
    backend_endpoint: str
    expires_at: float
    created_at: float = field(default_factory=time.time)
    is_used: bool = False
    user_id: str = "default"

    @property
    def is_expired(self) -> bool:
        return time.time() > self.expires_at

    def to_payload(self) -> Dict[str, Any]:
        """Payload encoded inside the pairing QR code."""
        return {
            "type": "ren_pairing",
            "protocol_version": 1,
            "backend_endpoint": self.backend_endpoint,
            "pairing_id": self.pairing_id,
            "challenge": self.challenge,
            "expires_at": int(self.expires_at),
        }


class QRCodeService:
    """Generates ASCII terminal QR codes and base64 PNG images for PC UI."""

    @staticmethod
    def generate_qr_base64(payload_dict: Dict[str, Any]) -> str:
        """Encodes payload dictionary into a base64-encoded PNG image."""
        payload_json = json.dumps(payload_dict, separators=(",", ":"))
        qr = qrcode.QRCode(
            version=None,
            error_correction=qrcode.constants.ERROR_CORRECT_M,
            box_size=8,
            border=2,
        )
        qr.add_data(payload_json)
        qr.make(fit=True)
        img = qr.make_image(fill_color="black", back_color="white")
        buffered = io.BytesIO()
        img.save(buffered, format="PNG")
        b64_str = base64.b64encode(buffered.getvalue()).decode("utf-8")
        return f"data:image/png;base64,{b64_str}"

    @staticmethod
    def print_terminal_qr(payload_dict: Dict[str, Any]):
        """Renders ASCII QR code into the terminal."""
        payload_json = json.dumps(payload_dict, separators=(",", ":"))
        qr = qrcode.QRCode(
            version=None,
            error_correction=qrcode.constants.ERROR_CORRECT_L,
            box_size=1,
            border=1,
        )
        qr.add_data(payload_json)
        qr.make(fit=True)
        qr.print_ascii(invert=True)


class PairingManager:
    """Thread-safe manager for device pairing, authentication, and endpoint rotation."""

    def __init__(self, default_ttl_seconds: int = 300):
        self.default_ttl = default_ttl_seconds
        self._challenges: Dict[str, PairingChallenge] = {}
        self._device_tokens: Dict[str, str] = {}  # device_id -> auth_token
        self._current_endpoint: str = "http://localhost:8000"
        self._lock = threading.Lock()

    def set_backend_endpoint(self, endpoint: str):
        """Updates the current active Cloudflare or LAN endpoint."""
        with self._lock:
            old = self._current_endpoint
            self._current_endpoint = endpoint.rstrip("/")
        if old != self._current_endpoint:
            agent_logger.info(f"Backend endpoint rotated: {self._current_endpoint}")

    def get_backend_endpoint(self) -> str:
        with self._lock:
            return self._current_endpoint

    def create_pairing_challenge(
        self,
        endpoint: Optional[str] = None,
        user_id: str = "default",
        ttl_seconds: Optional[int] = None
    ) -> PairingChallenge:
        """Generates a secure, short-lived one-time challenge."""
        ttl = ttl_seconds or self.default_ttl
        ep = (endpoint or self._current_endpoint).rstrip("/")
        pairing_id = f"pair_{secrets.token_hex(6)}"
        challenge = secrets.token_urlsafe(24)
        expires_at = time.time() + ttl

        ch = PairingChallenge(
            pairing_id=pairing_id,
            challenge=challenge,
            backend_endpoint=ep,
            expires_at=expires_at,
            user_id=user_id
        )

        with self._lock:
            # Clean up old expired challenges
            now = time.time()
            self._challenges = {k: v for k, v in self._challenges.items() if v.expires_at > now}
            self._challenges[pairing_id] = ch

        agent_logger.info(f"Generated new pairing challenge [{pairing_id}] (expires in {ttl}s)")
        return ch

    def get_current_qr_data(self, user_id: str = "default") -> Dict[str, Any]:
        """Retrieves active pairing challenge and returns base64 PNG QR code with expiration countdown."""
        ch = self.create_pairing_challenge(user_id=user_id)
        payload = ch.to_payload()
        qr_b64 = QRCodeService.generate_qr_base64(payload)
        return {
            "pairing_id": ch.pairing_id,
            "backend_endpoint": ch.backend_endpoint,
            "expires_at": int(ch.expires_at),
            "ttl_seconds": int(ch.expires_at - time.time()),
            "qr_image_base64": qr_b64,
            "payload": payload
        }

    def verify_and_pair(
        self,
        pairing_id: str,
        challenge: str,
        device_id: str,
        device_name: str = "Phone",
        platform_str: str = "android",
        capabilities: Optional[List[str]] = None,
        user_id: str = "default"
    ) -> Tuple[bool, str, Optional[Dict[str, Any]]]:
        """
        Validates pairing challenge, enforces replay protection, registers device identity,
        and returns a persistent device token.
        """
        with self._lock:
            ch = self._challenges.get(pairing_id)
            if not ch:
                return False, "Invalid pairing ID or challenge expired.", None

            # Replay protection
            if ch.is_used:
                return False, "Pairing challenge has already been used (replay rejected).", None

            # Expiration check
            if ch.is_expired:
                return False, "Pairing challenge has expired. Scan a new QR code on your PC.", None

            # Challenge comparison
            if not secrets.compare_digest(ch.challenge, challenge):
                return False, "Cryptographic challenge mismatch.", None

            # Mark used immediately
            ch.is_used = True

            # Resolve platform
            plat = PlatformType.ANDROID if "android" in platform_str.lower() else (
                PlatformType.IOS if "ios" in platform_str.lower() else PlatformType.UNKNOWN
            )

            # Generate or preserve device token
            device_token = secrets.token_hex(20)
            self._device_tokens[device_id] = device_token

        # Register or update device identity in DeviceManager
        dev_info = DeviceInfo(
            device_id=device_id,
            user_id=user_id,
            device_type=DeviceType.PHONE,
            platform=plat,
            name=device_name,
            capabilities=capabilities or ["battery", "storage", "notifications", "camera"],
            permissions=["filesystem_read", "camera_capture", "notifications"],
            connection_state=ConnectionState.CONNECTED,
            last_seen=time.time(),
            metadata={"endpoint": ch.backend_endpoint}
        )
        device_manager.register_device(dev_info)

        agent_logger.info(f"Successfully paired device '{device_name}' ({device_id})")

        return True, "Device successfully paired.", {
            "status": "paired",
            "device_id": device_id,
            "device_name": device_name,
            "device_token": device_token,
            "backend_endpoint": ch.backend_endpoint,
            "connection_state": "connected"
        }

    def validate_device_token(self, device_id: str, token: str) -> bool:
        """Verifies if device token is valid and active."""
        with self._lock:
            stored = self._device_tokens.get(device_id)
            if not stored:
                return False
            return secrets.compare_digest(stored, token)

    def revoke_device(self, device_id: str) -> bool:
        """Revokes a paired device permanently."""
        with self._lock:
            self._device_tokens.pop(device_id, None)
        device_manager.set_device_disconnected(device_id)
        agent_logger.info(f"Revoked pairing for device: {device_id}")
        return True

    def disconnect_device(self, device_id: str) -> bool:
        """Marks device as disconnected (can reconnect)."""
        device_manager.set_device_disconnected(device_id)
        return True


# Global pairing manager singleton
pairing_manager = PairingManager()
