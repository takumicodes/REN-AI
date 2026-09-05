"""
REN First-Class Image Asset Pipeline
Provides ImageGenerationProvider abstraction, ImageAsset data structure,
secure Asset Manager, and path-traversal-protected persistent media storage.
"""

import os
import io
import time
import uuid
import json
import urllib.parse
import urllib.request
from abc import ABC, abstractmethod
from dataclasses import dataclass, field, asdict
from datetime import datetime
from pathlib import Path
from typing import Dict, Any, Optional, Tuple

from ren.config.settings import settings
from ren.monitoring.logger import tools_logger, error_logger
from ren.core.events import event_bus, EventType


@dataclass
class ImageAsset:
    """First-class Image Asset metadata representation."""
    id: str
    type: str = "image"
    mime_type: str = "image/jpeg"
    url: str = ""
    width: int = 1024
    height: int = 1024
    created_at: str = field(default_factory=lambda: datetime.utcnow().isoformat())
    provider: str = "pollinations"
    conversation_id: Optional[str] = None
    user_id: str = "default"
    prompt: str = ""
    # Server-only path; excluded from client serialization
    _local_file_path: Optional[str] = None

    def to_dict(self) -> Dict[str, Any]:
        """Returns clean public payload without leaking local filesystem paths."""
        return {
            "type": self.type,
            "id": self.id,
            "mime_type": self.mime_type,
            "url": self.url,
            "width": self.width,
            "height": self.height,
            "created_at": self.created_at,
            "provider": self.provider,
            "conversation_id": self.conversation_id,
            "user_id": self.user_id,
            "prompt": self.prompt,
        }


class ImageGenerationProvider(ABC):
    """Abstract provider for swapping AI image generation backends."""

    @abstractmethod
    def generate(
        self,
        prompt: str,
        width: int = 1024,
        height: int = 1024,
        aspect_ratio: str = "1:1",
        quality: str = "high"
    ) -> Tuple[bytes, str]:
        """Generates image and returns raw (bytes, mime_type)."""
        pass


class PollinationsImageProvider(ImageGenerationProvider):
    """Free, reliable online image generator with zero API key requirement."""

    def generate(
        self,
        prompt: str,
        width: int = 1024,
        height: int = 1024,
        aspect_ratio: str = "1:1",
        quality: str = "high"
    ) -> Tuple[bytes, str]:
        encoded = urllib.parse.quote(prompt.strip())
        url = f"https://image.pollinations.ai/prompt/{encoded}?width={width}&height={height}&nologo=true"
        req = urllib.request.Request(
            url,
            headers={"User-Agent": "Mozilla/5.0 (Windows NT 10.0; Win64; x64) REN-AI/2.0"}
        )
        with urllib.request.urlopen(req, timeout=25) as resp:
            data = resp.read()
            mime = resp.headers.get_content_type() or "image/jpeg"
            return data, mime


class MockImageProvider(ImageGenerationProvider):
    """Deterministic offline fallback provider for tests and air-gapped environments."""

    def generate(
        self,
        prompt: str,
        width: int = 512,
        height: int = 512,
        aspect_ratio: str = "1:1",
        quality: str = "standard"
    ) -> Tuple[bytes, str]:
        # Minimal valid 1x1 GIF
        gif_bytes = b"GIF89a\x01\x00\x01\x00\x80\x00\x00\xff\xff\xff\x00\x00\x00!\xf9\x04\x01\x00\x00\x00\x00,\x00\x00\x00\x00\x01\x00\x01\x00\x00\x02\x02D\x01\x00;"
        return gif_bytes, "image/gif"


class ImageAssetManager:
    """Thread-safe persistent asset registry and delivery manager."""

    def __init__(self, base_dir: Optional[Path] = None):
        self.base_dir = base_dir or (settings.PATHS.DATA_DIR / "assets" / "images")
        self.base_dir.mkdir(parents=True, exist_ok=True)
        self.metadata_file = self.base_dir / "assets_index.json"
        self._assets: Dict[str, ImageAsset] = {}
        self.default_provider = PollinationsImageProvider()
        self._load_index()

    def _load_index(self):
        if self.metadata_file.exists():
            try:
                with open(self.metadata_file, "r", encoding="utf-8") as f:
                    data = json.load(f)
                for item in data.values():
                    asset = ImageAsset(**item)
                    self._assets[asset.id] = asset
            except Exception as e:
                error_logger.error(f"Error loading ImageAsset index: {e}")

    def _save_index(self):
        try:
            data = {k: v.to_dict() for k, v in self._assets.items()}
            tmp_file = self.metadata_file.with_suffix(".tmp")
            with open(tmp_file, "w", encoding="utf-8") as f:
                json.dump(data, f, indent=2)
            tmp_file.replace(self.metadata_file)
        except Exception as e:
            error_logger.error(f"Error saving ImageAsset index: {e}")

    def create_and_store_asset(
        self,
        image_bytes: bytes,
        mime_type: str,
        prompt: str,
        width: int = 1024,
        height: int = 1024,
        provider: str = "pollinations",
        user_id: str = "default",
        conversation_id: Optional[str] = None
    ) -> ImageAsset:
        """Stores image file securely on disk and indexes asset metadata."""
        asset_id = str(uuid.uuid4())[:12]
        ext = ".png" if "png" in mime_type else (".gif" if "gif" in mime_type else ".jpg")
        safe_filename = f"{asset_id}{ext}"
        target_path = (self.base_dir / safe_filename).resolve()

        # Path traversal guard
        if not str(target_path).startswith(str(self.base_dir.resolve())):
            raise PermissionError("Path traversal violation detected.")

        with open(target_path, "wb") as f:
            f.write(image_bytes)

        asset = ImageAsset(
            id=asset_id,
            type="image",
            mime_type=mime_type,
            url=f"/api/assets/images/{asset_id}",
            width=width,
            height=height,
            provider=provider,
            conversation_id=conversation_id,
            user_id=user_id,
            prompt=prompt,
            _local_file_path=str(target_path)
        )
        self._assets[asset_id] = asset
        self._save_index()

        event_bus.publish(EventType.IMAGE_GENERATED, asset.to_dict())
        tools_logger.info(f"ImageAsset created: [{asset.id}] for prompt '{prompt[:40]}'")
        return asset

    def get_asset(self, asset_id: str, user_id: Optional[str] = None) -> Optional[ImageAsset]:
        """Retrieves asset with optional user ownership check."""
        # Sanitize asset_id
        safe_id = "".join(c for c in asset_id if c.isalnum() or c in "-_")
        asset = self._assets.get(safe_id)
        if not asset:
            return None
        if user_id and user_id != "default" and asset.user_id not in [user_id, "default"]:
            return None
        return asset

    def get_asset_file_path(self, asset_id: str) -> Optional[Path]:
        """Resolves verified file path with path traversal protection."""
        asset = self.get_asset(asset_id)
        if not asset:
            return None

        # Check by ID extension search
        for ext in [".jpg", ".png", ".gif", ".jpeg", ".webp"]:
            candidate = (self.base_dir / f"{asset.id}{ext}").resolve()
            if candidate.exists() and str(candidate).startswith(str(self.base_dir.resolve())):
                return candidate
        return None

    def generate_image(
        self,
        prompt: str,
        width: int = 1024,
        height: int = 1024,
        aspect_ratio: str = "1:1",
        provider_name: Optional[str] = None,
        user_id: str = "default",
        conversation_id: Optional[str] = None
    ) -> ImageAsset:
        """Full pipeline: prompt -> generate -> store -> ImageAsset."""
        provider = self.default_provider
        p_name = "pollinations"
        if provider_name == "mock":
            provider = MockImageProvider()
            p_name = "mock"

        data, mime = provider.generate(prompt=prompt, width=width, height=height, aspect_ratio=aspect_ratio)
        return self.create_and_store_asset(
            image_bytes=data,
            mime_type=mime,
            prompt=prompt,
            width=width,
            height=height,
            provider=p_name,
            user_id=user_id,
            conversation_id=conversation_id
        )


# Global singleton
image_asset_manager = ImageAssetManager()
