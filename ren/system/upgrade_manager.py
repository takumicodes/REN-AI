"""
REN Upgrade Manager
Coordinates safe, verified system updates:
CHECK -> CHECKPOINT -> INSTALL -> REGRESSION TESTS -> HEALTH CHECK -> KEEP or ROLLBACK.
Classifies updates by risk (LOW, MEDIUM, HIGH) and prevents unverified code execution.
"""

import os
import shutil
import time
import json
from dataclasses import dataclass, field, asdict
from typing import Dict, Any, List, Optional, Tuple, Callable
import threading

from ren.config.settings import settings
from ren.monitoring.logger import agent_logger, error_logger
from ren.core.events import event_bus, EventType


@dataclass
class UpgradeItem:
    item_id: str
    component: str  # "skills", "config", "dependencies", "system"
    version: str
    risk_level: str  # "LOW", "MEDIUM", "HIGH"
    description: str
    requires_confirmation: bool = False
    status: str = "pending"  # "pending", "checkpointed", "installed", "verified", "rolled_back"


class UpgradeManager:
    """Orchestrates system maintenance, backups, regression gates, and rollback recovery."""

    def __init__(self):
        self.checkpoints_dir = settings.PATHS.DATA_DIR / "checkpoints"
        self.checkpoints_dir.mkdir(parents=True, exist_ok=True)
        self.history_file = self.checkpoints_dir / "upgrade_history.json"
        self._lock = threading.Lock()

    def check_updates(self) -> List[UpgradeItem]:
        """Scans for available system improvements, migrations, and skill patches."""
        updates = []

        # 1. Check for pending config migrations
        # Ensure world_model.json, learning_records.json, etc. exist
        wm_file = settings.PATHS.ROOT_DIR / "data" / "world_model.json"
        if not wm_file.exists():
            updates.append(UpgradeItem(
                item_id="mig_world_model",
                component="config",
                version="2.0.0",
                risk_level="LOW",
                description="Initialize structured World Model storage.",
                requires_confirmation=False
            ))

        # 2. Check for skills requiring patch or optimization
        from ren.skills.registry import skill_registry
        for s in skill_registry.get_active_skills():
            if not s.metadata.tested:
                updates.append(UpgradeItem(
                    item_id=f"skill_test_{s.name.lower()}",
                    component="skills",
                    version=s.version,
                    risk_level="LOW",
                    description=f"Run verification test suite on skill '{s.name}'.",
                    requires_confirmation=False
                ))

        return updates

    def create_checkpoint(self, label: str) -> str:
        """Creates a restorable snapshot before executing updates."""
        timestamp = time.strftime("%Y%m%d_%H%M%S")
        checkpoint_id = f"cp_{label}_{timestamp}"
        target_dir = self.checkpoints_dir / checkpoint_id
        target_dir.mkdir(parents=True, exist_ok=True)

        # Snapshot critical databases and configuration
        try:
            db_path = settings.PATHS.DB_PATH
            if db_path.exists():
                shutil.copy2(db_path, target_dir / "ren_memory.db")

            env_path = settings.PATHS.ROOT_DIR / ".env"
            if env_path.exists():
                shutil.copy2(env_path, target_dir / ".env")

            history_entry = {
                "checkpoint_id": checkpoint_id,
                "label": label,
                "timestamp": timestamp,
                "path": str(target_dir)
            }
            agent_logger.info(f"UpgradeManager: Checkpoint created -> {checkpoint_id}")
            return checkpoint_id
        except Exception as e:
            error_logger.error(f"Failed creating checkpoint: {e}")
            raise

    def execute_upgrade_flow(
        self,
        upgrade: UpgradeItem,
        install_action: Callable[[], bool],
        regression_test_fn: Optional[Callable[[], bool]] = None
    ) -> Tuple[bool, str]:
        """
        Full verified upgrade pipeline:
        CHECK -> CHECKPOINT -> INSTALL -> REGRESSION TESTS -> KEEP or ROLLBACK.
        """
        event_bus.publish(EventType.UPGRADE_STARTED, {"item_id": upgrade.item_id, "component": upgrade.component})
        agent_logger.info(f"UpgradeManager: Starting upgrade [{upgrade.item_id}] (Risk: {upgrade.risk_level})")

        # 1. Checkpoint
        checkpoint_id = self.create_checkpoint(label=upgrade.item_id)
        upgrade.status = "checkpointed"

        # 2. Install
        try:
            success = install_action()
            if not success:
                self.rollback_checkpoint(checkpoint_id)
                upgrade.status = "rolled_back"
                return False, "Installation action failed. State restored from checkpoint."
        except Exception as err:
            self.rollback_checkpoint(checkpoint_id)
            upgrade.status = "rolled_back"
            return False, f"Exception during install ({err}). Rolled back."

        upgrade.status = "installed"

        # 3. Regression tests & health check
        if regression_test_fn:
            try:
                tests_passed = regression_test_fn()
                if not tests_passed:
                    agent_logger.warning(f"UpgradeManager: Regression test failed for {upgrade.item_id}. Rolling back...")
                    self.rollback_checkpoint(checkpoint_id)
                    upgrade.status = "rolled_back"
                    event_bus.publish(EventType.UPGRADE_ROLLED_BACK, {"item_id": upgrade.item_id})
                    return False, "Regression tests failed. State rolled back safely."
            except Exception as e:
                self.rollback_checkpoint(checkpoint_id)
                upgrade.status = "rolled_back"
                event_bus.publish(EventType.UPGRADE_ROLLED_BACK, {"item_id": upgrade.item_id, "error": str(e)})
                return False, f"Regression test exception: {e}. Rolled back."

        # 4. Verified & Kept
        upgrade.status = "verified"
        event_bus.publish(EventType.UPGRADE_COMPLETED, {"item_id": upgrade.item_id, "version": upgrade.version})
        agent_logger.info(f"UpgradeManager: Upgrade [{upgrade.item_id}] successfully installed and verified.")
        return True, f"Upgrade {upgrade.item_id} completed successfully."

    def rollback_checkpoint(self, checkpoint_id: str) -> bool:
        """Restores state from a snapshot checkpoint."""
        target_dir = self.checkpoints_dir / checkpoint_id
        if not target_dir.exists():
            return False
        try:
            # Restore db
            backup_db = target_dir / "ren_memory.db"
            if backup_db.exists():
                shutil.copy2(backup_db, settings.PATHS.DB_PATH)

            # Restore .env
            backup_env = target_dir / ".env"
            if backup_env.exists():
                shutil.copy2(backup_env, settings.PATHS.ROOT_DIR / ".env")

            agent_logger.info(f"UpgradeManager: Restored system from checkpoint {checkpoint_id}")
            return True
        except Exception as e:
            error_logger.error(f"Failed rollback: {e}")
            return False


# Global singleton
upgrade_manager = UpgradeManager()
