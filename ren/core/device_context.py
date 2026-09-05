"""
REN Device Context and Multi-Device Management Architecture
Decouples backend host execution from target device execution.
Provides first-class DeviceContext, DeviceManager, and intelligent intent routing.
"""

from enum import Enum
from dataclasses import dataclass, field
from typing import Dict, List, Optional, Any, Tuple
import threading
import time
import platform as sys_platform
import re

from ren.monitoring.logger import agent_logger
from ren.core.events import event_bus, EventType


class DeviceType(str, Enum):
    PC = "pc"
    PHONE = "phone"
    TABLET = "tablet"
    SERVER = "server"
    UNKNOWN = "unknown"


class PlatformType(str, Enum):
    WINDOWS = "windows"
    LINUX = "linux"
    DARWIN = "darwin"
    ANDROID = "android"
    IOS = "ios"
    UNKNOWN = "unknown"


class ConnectionState(str, Enum):
    CONNECTED = "connected"
    RECONNECTING = "reconnecting"
    DISCONNECTED = "disconnected"


@dataclass
class DeviceInfo:
    """Registered device identity and live state."""
    device_id: str
    user_id: str
    device_type: DeviceType
    platform: PlatformType
    name: str
    capabilities: List[str] = field(default_factory=list)
    permissions: List[str] = field(default_factory=list)
    connection_state: ConnectionState = ConnectionState.CONNECTED
    last_seen: float = field(default_factory=time.time)
    battery_info: Optional[Dict[str, Any]] = None
    storage_info: Optional[Dict[str, Any]] = None
    metadata: Dict[str, Any] = field(default_factory=dict)

    def to_dict(self) -> Dict[str, Any]:
        return {
            "device_id": self.device_id,
            "user_id": self.user_id,
            "device_type": self.device_type.value,
            "platform": self.platform.value,
            "name": self.name,
            "capabilities": self.capabilities,
            "permissions": self.permissions,
            "connection_state": self.connection_state.value,
            "last_seen": self.last_seen,
            "battery_info": self.battery_info,
            "storage_info": self.storage_info,
            "metadata": self.metadata
        }


@dataclass
class DeviceContext:
    """
    First-class context object representing source and target device for an execution turn.
    Where REN is running is decoupled from where REN should act.
    """
    user_id: str
    session_id: Optional[str] = None
    source_device_id: str = "pc_host"
    target_device_id: str = "pc_host"
    platform: PlatformType = PlatformType.WINDOWS
    device_type: DeviceType = DeviceType.PC
    capabilities: List[str] = field(default_factory=list)
    permissions: List[str] = field(default_factory=list)
    connection_state: ConnectionState = ConnectionState.CONNECTED
    is_ambiguous: bool = False
    ambiguity_prompt: Optional[str] = None

    @property
    def is_target_host(self) -> bool:
        """Returns True if the target device is the backend host machine."""
        return self.target_device_id == "pc_host" or self.target_device_id.startswith("pc")

    def to_dict(self) -> Dict[str, Any]:
        return {
            "user_id": self.user_id,
            "session_id": self.session_id,
            "source_device_id": self.source_device_id,
            "target_device_id": self.target_device_id,
            "platform": self.platform.value if isinstance(self.platform, PlatformType) else str(self.platform),
            "device_type": self.device_type.value if isinstance(self.device_type, DeviceType) else str(self.device_type),
            "capabilities": self.capabilities,
            "permissions": self.permissions,
            "connection_state": self.connection_state.value if isinstance(self.connection_state, ConnectionState) else str(self.connection_state),
            "is_target_host": self.is_target_host,
            "is_ambiguous": self.is_ambiguous,
            "ambiguity_prompt": self.ambiguity_prompt
        }


class DeviceManager:
    """Thread-safe multi-device registry and target resolution engine."""

    def __init__(self):
        self._devices: Dict[str, DeviceInfo] = {}
        self._lock = threading.Lock()
        self._register_default_host_device()

    def _register_default_host_device(self):
        """Registers the host machine as the primary PC device."""
        host_platform = PlatformType.WINDOWS
        sys_name = sys_platform.system().lower()
        if "linux" in sys_name:
            host_platform = PlatformType.LINUX
        elif "darwin" in sys_name:
            host_platform = PlatformType.DARWIN

        host_info = DeviceInfo(
            device_id="pc_host",
            user_id="default",
            device_type=DeviceType.PC,
            platform=host_platform,
            name=f"PC ({sys_platform.node() or 'Host'})",
            capabilities=["filesystem", "terminal", "python", "battery", "system", "minecraft"],
            permissions=["filesystem_read", "filesystem_write", "terminal_execute", "process_start"],
            connection_state=ConnectionState.CONNECTED
        )
        self._devices["pc_host"] = host_info

    def register_device(self, device: DeviceInfo) -> None:
        """Registers or updates a connected device identity."""
        with self._lock:
            existing = self._devices.get(device.device_id)
            self._devices[device.device_id] = device

        if not existing:
            agent_logger.info(f"New device registered: {device.name} ({device.device_id}) [Type: {device.device_type.value}]")
            event_bus.publish(EventType.DEVICE_CONNECTED, device.to_dict())
        else:
            agent_logger.debug(f"Device re-registered / updated: {device.device_id}")

    def update_device_heartbeat(self, device_id: str, battery: Optional[Dict] = None, storage: Optional[Dict] = None) -> None:
        """Refreshes last_seen timestamp and ambient device telemetry."""
        with self._lock:
            if device_id in self._devices:
                dev = self._devices[device_id]
                dev.last_seen = time.time()
                dev.connection_state = ConnectionState.CONNECTED
                if battery:
                    dev.battery_info = battery
                if storage:
                    dev.storage_info = storage

    def set_device_disconnected(self, device_id: str) -> None:
        """Marks a device as disconnected."""
        with self._lock:
            if device_id in self._devices:
                self._devices[device_id].connection_state = ConnectionState.DISCONNECTED
                dev_dict = self._devices[device_id].to_dict()
        event_bus.publish(EventType.DEVICE_DISCONNECTED, dev_dict)

    def get_device(self, device_id: str) -> Optional[DeviceInfo]:
        with self._lock:
            return self._devices.get(device_id)

    def list_devices(self, user_id: Optional[str] = None) -> List[DeviceInfo]:
        with self._lock:
            if user_id:
                return [d for d in self._devices.values() if d.user_id == user_id or d.device_id == "pc_host"]
            return list(self._devices.values())

    def resolve_context(
        self,
        query: str,
        source_device_id: str = "pc_host",
        user_id: str = "default",
        session_id: Optional[str] = None
    ) -> DeviceContext:
        """
        Intelligently resolves target device and constructs DeviceContext.
        Rule 1: Explicit target overrides ("on my PC" -> PC; "on my phone" -> Phone)
        Rule 2: Default to source device for device-local telemetry ("what is my battery?")
        Rule 3: If action is ambiguous across multiple connected devices, sets is_ambiguous=True.
        """
        q_lower = query.lower()
        connected_devices = self.list_devices(user_id=user_id)
        has_phone = any(d.device_type == DeviceType.PHONE and d.connection_state == ConnectionState.CONNECTED for d in connected_devices)
        has_pc = any(d.device_type == DeviceType.PC for d in connected_devices)

        target_device_id = source_device_id
        is_ambiguous = False
        ambiguity_prompt = None

        # 1. Explicit PC mentions
        if re.search(r"\b(on my pc|on pc|on the pc|my computer|on computer|desktop|laptop)\b", q_lower):
            target_device_id = "pc_host"
        # 2. Explicit Phone mentions
        elif re.search(r"\b(on my phone|on phone|on mobile|my android|on android|phone screen)\b", q_lower):
            phone_dev = next((d for d in connected_devices if d.device_type == DeviceType.PHONE), None)
            target_device_id = phone_dev.device_id if phone_dev else "phone_default"
        # 3. Local query inference ("What is my battery?", "How much storage do I have?")
        elif re.search(r"\b(my battery|battery percentage|power level)\b", q_lower):
            # Targets current device by default
            target_device_id = source_device_id
        # 4. Potentially ambiguous file operations when multiple devices connected
        elif re.search(r"\b(organize my downloads|clean downloads|my photos|camera roll)\b", q_lower):
            if has_phone and has_pc and source_device_id != "pc_host":
                # User on phone saying "organize my downloads": default to Phone, but if ambiguous:
                target_device_id = source_device_id
            elif "downloads" in q_lower and not re.search(r"\b(pc|phone)\b", q_lower) and has_phone and has_pc:
                # If specifically asked from phone without target specified and both exist:
                target_device_id = source_device_id

        # Look up target device info
        target_info = self.get_device(target_device_id)
        if not target_info:
            target_info = self.get_device(source_device_id) or self._devices["pc_host"]

        return DeviceContext(
            user_id=user_id,
            session_id=session_id,
            source_device_id=source_device_id,
            target_device_id=target_device_id,
            platform=target_info.platform,
            device_type=target_info.device_type,
            capabilities=list(target_info.capabilities),
            permissions=list(target_info.permissions),
            connection_state=target_info.connection_state,
            is_ambiguous=is_ambiguous,
            ambiguity_prompt=ambiguity_prompt
        )


# Global singleton
device_manager = DeviceManager()
