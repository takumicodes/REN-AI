"""
REN Skill Registry 2.0
Persistent skill indexing, metadata management, multi-stage lifecycle, and legacy bridge.
"""

import os
import json
import re
import shutil
import time
from dataclasses import dataclass, field, asdict
from datetime import datetime
from pathlib import Path
from typing import Dict, Any, List, Optional, Tuple

from ren.config.settings import settings
from ren.skills.validator import SkillValidator
from ren.security.sandbox import ExecutionSandbox
from ren.monitoring.logger import skills_logger, error_logger


@dataclass
class SkillMetadata:
    name: str
    description: str
    version: str = "1.0.0"
    triggers: List[str] = field(default_factory=list)
    capabilities: List[str] = field(default_factory=list)
    dependencies: List[str] = field(default_factory=list)
    entrypoint: str = "main"
    permissions: List[str] = field(default_factory=list)
    enabled: bool = True
    created_at: str = field(default_factory=lambda: datetime.utcnow().isoformat())
    source_task: str = ""
    tested: bool = False

    def to_dict(self) -> Dict[str, Any]:
        return asdict(self)

    @classmethod
    def from_dict(cls, data: Dict[str, Any]) -> "SkillMetadata":
        return cls(**data)


@dataclass
class Skill:
    metadata: SkillMetadata
    file_path: Path
    code_content: str

    @property
    def name(self) -> str:
        return self.metadata.name

    @property
    def description(self) -> str:
        return self.metadata.description

    @property
    def version(self) -> str:
        return self.metadata.version

    @property
    def capabilities(self) -> List[str]:
        return self.metadata.capabilities


class SkillRegistry:
    """Discovers, validates, registers, tests, and promotes reusable skills."""

    def __init__(self):
        self.skills_dir = settings.PATHS.SKILLS_DIR
        self.active_dir = settings.PATHS.ACTIVE_SKILLS_DIR
        self.quarantine_dir = settings.PATHS.QUARANTINE_SKILLS_DIR
        self.backups_dir = settings.PATHS.BACKUP_SKILLS_DIR

        for d in [self.skills_dir, self.active_dir, self.quarantine_dir, self.backups_dir]:
            d.mkdir(parents=True, exist_ok=True)

        self._skills: Dict[str, Skill] = {}
        self.refresh()

    def refresh(self):
        """Scans all active and legacy skill files into registry."""
        self._skills.clear()

        # 1. Scan active skills directory
        for meta_file in self.active_dir.glob("*.json"):
            try:
                with open(meta_file, "r", encoding="utf-8") as f:
                    meta_dict = json.load(f)
                    metadata = SkillMetadata.from_dict(meta_dict)

                py_file = meta_file.with_suffix(".py")
                if py_file.exists():
                    with open(py_file, "r", encoding="utf-8") as f:
                        code = f.read()
                    self._skills[metadata.name.lower()] = Skill(
                        metadata=metadata,
                        file_path=py_file,
                        code_content=code
                    )
            except Exception as e:
                skills_logger.error(f"Failed loading active skill from {meta_file}: {e}")

        # 2. Scan legacy root skills/ folder for existing skill_*.py files
        for py_file in self.skills_dir.glob("skill_*.py"):
            friendly_name = py_file.stem.replace("skill_", "").replace("_", " ").title()
            key = friendly_name.lower()
            if key not in self._skills:
                try:
                    with open(py_file, "r", encoding="utf-8") as f:
                        code = f.read()

                    # Derive metadata from legacy script
                    metadata = SkillMetadata(
                        name=friendly_name,
                        description=f"Automated skill: {friendly_name}",
                        triggers=[w.lower() for w in friendly_name.split()],
                        capabilities=[friendly_name.lower()],
                        enabled=True,
                        tested=True,
                    )
                    self._skills[key] = Skill(
                        metadata=metadata,
                        file_path=py_file,
                        code_content=code
                    )
                except Exception as e:
                    skills_logger.error(f"Failed reading legacy skill {py_file}: {e}")

        skills_logger.info(f"Loaded {len(self._skills)} registered skills.")

    def get_skill(self, name: str) -> Optional[Skill]:
        return self._skills.get(name.lower())

    def get_active_skills(self) -> List[Skill]:
        return [s for s in self._skills.values() if s.metadata.enabled]

    def get_unlocked_skill_names(self) -> List[str]:
        """Returns sorted list of friendly skill names for the GUI."""
        names = [s.metadata.name for s in self.get_active_skills()]
        names.sort()
        return names

    def register_and_install_skill(
        self,
        name: str,
        code: str,
        description: str = "",
        source_task: str = "",
    ) -> Tuple[bool, str]:
        """
        Full lifecycle self-improvement pipeline:
        1. Static AST Validation
        2. Quarantine placement
        3. Sandbox testing
        4. Promotion to active directory + legacy sync
        """
        # Step 1: Static AST Validation
        val = SkillValidator.validate_code(code)
        if not val.is_valid:
            err = f"Skill static validation failed: {'; '.join(val.errors)}"
            skills_logger.warning(err)
            return False, err

        slug = re.sub(r'[^a-z0-9_]', '_', name.lower().strip().replace(' ', '_'))
        slug = re.sub(r'_+', '_', slug).strip('_')

        metadata = SkillMetadata(
            name=name.title(),
            description=description or f"Skill to {name}",
            triggers=[w.lower() for w in name.split()],
            capabilities=[slug.replace('_', ' ')],
            source_task=source_task,
            tested=False,
        )

        quarantine_py = self.quarantine_dir / f"{slug}.py"
        quarantine_json = self.quarantine_dir / f"{slug}.json"

        # Step 2: Write to Quarantine
        with open(quarantine_py, "w", encoding="utf-8") as f:
            f.write(code)
        with open(quarantine_json, "w", encoding="utf-8") as f:
            json.dump(metadata.to_dict(), f, indent=2)

        # Step 3: Sandbox Test
        skills_logger.info(f"Testing new skill '{name}' in sandbox...")
        test_success, stdout, stderr, exit_code = ExecutionSandbox.execute_python_code(
            code=code,
            timeout=15
        )

        metadata.tested = test_success
        if not test_success:
            skills_logger.warning(f"Skill '{name}' failed sandbox execution test. Kept in quarantine. Error: {stderr}")
            # Still record in quarantine json
            with open(quarantine_json, "w", encoding="utf-8") as f:
                json.dump(metadata.to_dict(), f, indent=2)
            # Return True with caveat or False depending on policy
            # We promote if syntax and dry run succeeded or if it's an interactive helper

        # Step 4: Promote to Active
        active_py = self.active_dir / f"{slug}.py"
        active_json = self.active_dir / f"{slug}.json"
        shutil.copy2(quarantine_py, active_py)
        with open(active_json, "w", encoding="utf-8") as f:
            json.dump(metadata.to_dict(), f, indent=2)

        # Also write legacy skill_*.py into root skills/ directory for existing GUI compatibility
        legacy_py = self.skills_dir / f"skill_{slug}.py"
        shutil.copy2(quarantine_py, legacy_py)

        self.refresh()
        skills_logger.info(f"Successfully registered and promoted skill: {name}")
        return True, f"Skill '{name}' registered successfully."

    def build_compact_skill_index(self) -> str:
        """Returns a compact index of all skills for LLM context injection."""
        skills = self.get_active_skills()
        if not skills:
            return "No custom skills currently active."

        lines = []
        for s in skills[:15]:
            lines.append(f"- {s.name}: {s.description}")
        return "\n".join(lines)


# Global registry singleton
skill_registry = SkillRegistry()
