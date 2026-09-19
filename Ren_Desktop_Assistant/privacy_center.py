"""
Privacy & Telemetry Control Center for REN-AI Windows Control Center
Provides:
- Transparent configuration of Windows diagnostic tracking, advertising ID, and telemetry.
- Zero AI-slop: clearly explains what data is sent to Microsoft and why disabling it benefits privacy.
- 100% reversible via registry toggles.
"""

import winreg
from typing import Dict, List, Any, Optional

try:
    from .history import change_history
except ImportError:
    from history import change_history


class PrivacyTweak:
    def __init__(
        self,
        tweak_id: str,
        title: str,
        description: str,
        data_collected: str,
        privacy_benefit: str,
        root_key: int,
        subkey: str,
        value_name: str,
        value_type: int,
        privacy_val: Any,
        default_val: Any,
    ):
        self.id = tweak_id
        self.title = title
        self.description = description
        self.data_collected = data_collected
        self.privacy_benefit = privacy_benefit
        self.root_key = root_key
        self.subkey = subkey
        self.value_name = value_name
        self.value_type = value_type
        self.privacy_val = privacy_val
        self.default_val = default_val

    def is_protected(self) -> bool:
        """Returns True if the privacy-hardened setting is active."""
        try:
            with winreg.OpenKey(self.root_key, self.subkey, 0, winreg.KEY_READ) as key:
                val, _ = winreg.QueryValueEx(key, self.value_name)
                return val == self.privacy_val
        except Exception:
            return False

    def enable_privacy(self) -> Dict[str, Any]:
        """Applies privacy hardening."""
        try:
            with winreg.CreateKey(self.root_key, self.subkey) as key:
                winreg.SetValueEx(key, self.value_name, 0, self.value_type, self.privacy_val)
            return {"success": True, "message": f"Hardened privacy: {self.title}"}
        except Exception as e:
            return {"success": False, "message": f"Requires Administrator: {e}"}

    def revert_privacy(self) -> Dict[str, Any]:
        """Restores standard Windows telemetry default."""
        try:
            with winreg.CreateKey(self.root_key, self.subkey) as key:
                winreg.SetValueEx(key, self.value_name, 0, self.value_type, self.default_val)
            return {"success": True, "message": f"Restored default for: {self.title}"}
        except Exception as e:
            return {"success": False, "message": f"Requires Administrator: {e}"}


class PrivacyCenter:
    """Manages system-wide privacy and telemetry configurations."""

    def __init__(self):
        self._items: Dict[str, PrivacyTweak] = {}
        self._init_items()

    def _init_items(self):
        self._items = {
            "advertising_id": PrivacyTweak(
                tweak_id="advertising_id",
                title="Disable Windows Advertising ID",
                description="Prevents apps from using your advertising ID to deliver targeted ads across Windows apps.",
                data_collected="Unique advertising ID, app usage frequency, interest profiles.",
                privacy_benefit="Eliminates cross-app tracking profile generated for your user account.",
                root_key=winreg.HKEY_CURRENT_USER,
                subkey=r"Software\Microsoft\Windows\CurrentVersion\AdvertisingInfo",
                value_name="Enabled",
                value_type=winreg.REG_DWORD,
                privacy_val=0,
                default_val=1,
            ),
            "tailored_experiences": PrivacyTweak(
                tweak_id="tailored_experiences",
                title="Disable Tailored Experiences with Diagnostic Data",
                description="Stops Microsoft from using diagnostic data to offer personalized recommendations and ads.",
                data_collected="App usage patterns, device hardware configuration, search queries.",
                privacy_benefit="Prevents diagnostic telemetry from being used to serve commercial recommendations.",
                root_key=winreg.HKEY_CURRENT_USER,
                subkey=r"Software\Policies\Microsoft\Windows\CloudContent",
                value_name="DisableTailoredExperiencesWithDiagnosticData",
                value_type=winreg.REG_DWORD,
                privacy_val=1,
                default_val=0,
            ),
            "activity_history": PrivacyTweak(
                tweak_id="activity_history",
                title="Disable Windows Activity History Tracking",
                description="Stops Windows from collecting timeline activities and syncing them to the cloud.",
                data_collected="Browsed websites, opened applications, and accessed documents history.",
                privacy_benefit="Stops continuous logging of opened files and applications on your PC.",
                root_key=winreg.HKEY_LOCAL_MACHINE,
                subkey=r"SOFTWARE\Policies\Microsoft\Windows\System",
                value_name="EnableActivityFeed",
                value_type=winreg.REG_DWORD,
                privacy_val=0,
                default_val=1,
            ),
            "feedback_frequency": PrivacyTweak(
                tweak_id="feedback_frequency",
                title="Set Feedback Request Frequency to Never",
                description="Disables periodic Windows notifications asking for user feedback and ratings.",
                data_collected="Feedback responses, system environment state at time of query.",
                privacy_benefit="Eliminates intrusive feedback popups and related background polling.",
                root_key=winreg.HKEY_CURRENT_USER,
                subkey=r"Software\Microsoft\Siuf\Rules",
                value_name="NumberOfSIUFInPeriod",
                value_type=winreg.REG_DWORD,
                privacy_val=0,
                default_val=1,
            ),
        }

    def get_privacy_settings(self) -> Dict[str, Dict[str, Any]]:
        """Returns all privacy settings and their active hardened status."""
        res = {}
        for k, item in self._items.items():
            res[k] = {
                "id": item.id,
                "title": item.title,
                "description": item.description,
                "data_collected": item.data_collected,
                "privacy_benefit": item.privacy_benefit,
                "is_protected": item.is_protected(),
            }
        return res

    def set_protection(self, tweak_id: str, enable: bool) -> Dict[str, Any]:
        """Toggles a privacy setting and logs to history."""
        item = self._items.get(tweak_id)
        if not item:
            return {"success": False, "message": f"Setting '{tweak_id}' not found."}

        res = item.enable_privacy() if enable else item.revert_privacy()
        if res.get("success") and change_history:
            change_history.record_action(
                action_id=f"privacy_{tweak_id}",
                title=f"{'Hardened' if enable else 'Restored'} {item.title}",
                category="Privacy",
                status="executed",
                verified=item.is_protected() == enable,
                verification_message="Privacy policy updated successfully.",
                reversible=True,
                before_state={"protected": not enable},
                after_state={"protected": enable},
            )
        return res


privacy_center = PrivacyCenter()
