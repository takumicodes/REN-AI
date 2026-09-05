"""
REN Developer / Admin Mode Security System
Provides secure authentication, capability gating, and developer mode lifecycle management.
Protects sensitive developer features with cryptographically secure token validation,
preventing secret leakage to LLM prompts, frontend JS, or runtime logs.
"""

import hmac
import hashlib
import time
import secrets
from dataclasses import dataclass, asdict
from typing import Dict, Any, Optional

from ren.config.settings import settings
from ren.monitoring.logger import security_logger


@dataclass
class DeveloperCapabilities:
    """Explicit capability flags for developer mode."""
    enabled: bool = False
    debug: bool = False
    skill_development: bool = True
    advanced_tools: bool = True
    autonomous_tools: bool = True
    verbose_telemetry: bool = False
    authenticated_at: Optional[float] = None
    session_token: Optional[str] = None

    def to_dict(self) -> Dict[str, Any]:
        d = asdict(self)
        # Never expose session token in public serialized representation
        d.pop("session_token", None)
        return d


class DeveloperModeManager:
    """Authoritative backend manager for Developer / Admin Mode."""

    def __init__(self):
        self._active_tokens: Dict[str, DeveloperCapabilities] = {}
        # Global developer state for desktop / single-user session
        self._global_capabilities = DeveloperCapabilities(
            enabled=settings.DEVELOPER.DEFAULT_DEBUG,
            debug=settings.DEVELOPER.DEFAULT_DEBUG,
            skill_development=settings.DEVELOPER.ENABLE_SKILL_DEV,
            advanced_tools=settings.DEVELOPER.ENABLE_ADVANCED_TOOLS,
            autonomous_tools=settings.DEVELOPER.ENABLE_AUTONOMOUS_TOOLS,
        )

    def _hash_secret(self, secret: str) -> str:
        """Produces SHA-256 hash for secure comparison."""
        return hashlib.sha256(secret.encode("utf-8")).hexdigest()

    def verify_secret(self, provided_secret: str) -> bool:
        """Performs timing-attack resistant verification of the developer secret."""
        if not provided_secret:
            return False
        
        configured_secret = settings.DEVELOPER.SECRET_KEY
        if not configured_secret:
            return False

        h_provided = self._hash_secret(provided_secret.strip())
        h_expected = self._hash_secret(configured_secret.strip())

        is_valid = hmac.compare_digest(h_provided, h_expected)
        if is_valid:
            security_logger.info("Developer Mode: Successful authentication.")
        else:
            security_logger.warning("Developer Mode: Failed authentication attempt.")
        return is_valid

    def authenticate_session(self, secret: str) -> Optional[str]:
        """Authenticates and creates an isolated developer session token."""
        if not self.verify_secret(secret):
            return None

        token = secrets.token_hex(24)
        caps = DeveloperCapabilities(
            enabled=True,
            debug=True,
            skill_development=True,
            advanced_tools=True,
            autonomous_tools=True,
            verbose_telemetry=True,
            authenticated_at=time.time(),
            session_token=token,
        )
        self._active_tokens[token] = caps
        self._global_capabilities.enabled = True
        return token

    def is_developer_mode_active(self, token: Optional[str] = None) -> bool:
        """Checks if developer mode is enabled globally or for a specific token."""
        if token and token in self._active_tokens:
            return self._active_tokens[token].enabled
        return self._global_capabilities.enabled

    def get_capabilities(self, token: Optional[str] = None) -> DeveloperCapabilities:
        """Retrieves active capabilities for the session."""
        if token and token in self._active_tokens:
            return self._active_tokens[token]
        return self._global_capabilities

    def update_capabilities(self, updates: Dict[str, Any], token: Optional[str] = None) -> DeveloperCapabilities:
        """Updates capability flags for an authenticated session."""
        caps = self.get_capabilities(token)
        if not caps.enabled:
            return caps

        for k, v in updates.items():
            if hasattr(caps, k) and k not in ("session_token", "authenticated_at"):
                setattr(caps, k, bool(v))

        security_logger.info(f"Developer capabilities updated: debug={caps.debug}, tools={caps.advanced_tools}")
        return caps

    def revoke_session(self, token: Optional[str] = None) -> None:
        """Deactivates developer mode."""
        if token and token in self._active_tokens:
            self._active_tokens.pop(token, None)
        self._global_capabilities.enabled = False
        self._global_capabilities.debug = False
        security_logger.info("Developer Mode deactivated.")


# Global developer mode manager singleton
developer_mode_manager = DeveloperModeManager()
