"""
REN Skill Registry 2.0
Robust lifecycle manager: CREATE -> VALIDATE -> TEST -> SAVE -> REGISTER -> LOAD -> EXPOSE TO MODEL -> EXECUTE.
Maintains active registry, dynamic tool bridging, metadata persistence, and error handling.
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
from ren.skills.loader import SkillLoader
from ren.security.sandbox import ExecutionSandbox
from ren.security.permissions import PermissionCategory, PermissionRisk
from ren.tools.base import BaseTool, ToolResult
from ren.monitoring.logger import skills_logger, error_logger


@dataclass
class SkillMetadata:
    name: str
    description: str
    version: str = "1.0.0"
    triggers: List[str] = field(default_factory=list)
    capabilities: List[str] = field(default_factory=list)
    dependencies: List[str] = field(default_factory=list)
    supported_devices: List[str] = field(default_factory=lambda: ["pc_host", "phone"])
    entrypoint: str = "main"
    parameters: Dict[str, Any] = field(default_factory=dict)
    input_schema: Dict[str, Any] = field(default_factory=dict)
    output_schema: Dict[str, Any] = field(default_factory=dict)
    permissions: List[str] = field(default_factory=list)
    risk_level: str = "LOW"
    enabled: bool = True
    created_at: str = field(default_factory=lambda: datetime.utcnow().isoformat())
    source_task: str = ""
    tests: List[str] = field(default_factory=list)
    provenance: str = "llm_generated"
    confidence: float = 0.8
    tested: bool = False

    def to_dict(self) -> Dict[str, Any]:
        return asdict(self)

    @classmethod
    def from_dict(cls, data: Dict[str, Any]) -> "SkillMetadata":
        # Handle backward compatibility for older JSON without new fields
        valid_keys = cls.__dataclass_fields__.keys()
        filtered = {k: v for k, v in data.items() if k in valid_keys}
        return cls(**filtered)


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

    @property
    def risk_level(self) -> str:
        return self.metadata.risk_level

    @property
    def enabled(self) -> bool:
        return self.metadata.enabled


class DynamicSkillToolWrapper(BaseTool):
    """Wraps a registered skill as a callable BaseTool for the ToolRegistry."""

    def __init__(self, skill: Skill):
        self.skill = skill
        self.name = f"skill_{re.sub(r'[^a-z0-9_]', '_', skill.name.lower().strip()).strip('_')}"
        self.description = f"[Custom Skill] {skill.description}"
        
        # Determine required permissions based on risk level
        if skill.risk_level == "HIGH":
            self.required_permissions = [PermissionCategory.SYSTEM_MODIFY]
        elif skill.risk_level == "MEDIUM":
            self.required_permissions = [PermissionCategory.TERMINAL_EXECUTE]
        else:
            self.required_permissions = [PermissionCategory.FILESYSTEM_READ]

        self.parameters_schema = {
            "type": "object",
            "properties": skill.metadata.parameters or {
                "input": {"type": "string", "description": "Optional input string or arguments"}
            },
            "required": []
        }

    def run(self, **kwargs) -> ToolResult:
        start_t = time.perf_counter()
        success, stdout, stderr, exit_code = SkillLoader.execute_skill(self.skill, args=kwargs)
        duration = time.perf_counter() - start_t
        output = stdout.strip() if stdout else ""
        if not success and stderr:
            error_msg = f"Skill execution error: {stderr.strip()}"
            return ToolResult(success=False, output=output, error=error_msg, exit_code=exit_code, duration=duration)
        return ToolResult(success=True, output=output or "Skill executed successfully with no stdout.", exit_code=0, duration=duration)


class SkillRegistry:
    """Discovers, validates, registers, tests, loads, and executes skills."""

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
        """Scans and loads all valid active and legacy skill files into registry."""
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
                    skill = Skill(
                        metadata=metadata,
                        file_path=py_file,
                        code_content=code
                    )
                    self._skills[metadata.name.lower()] = skill
                    self._sync_tool_wrapper(skill)
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

                    metadata = SkillMetadata(
                        name=friendly_name,
                        description=f"Automated skill: {friendly_name}",
                        triggers=[w.lower() for w in friendly_name.split()],
                        capabilities=[friendly_name.lower()],
                        enabled=True,
                        tested=True,
                    )
                    skill = Skill(
                        metadata=metadata,
                        file_path=py_file,
                        code_content=code
                    )
                    self._skills[key] = skill
                    self._sync_tool_wrapper(skill)
                except Exception as e:
                    skills_logger.error(f"Failed reading legacy skill {py_file}: {e}")

        skills_logger.info(f"Loaded {len(self._skills)} registered skills.")

    def _sync_tool_wrapper(self, skill: Skill):
        """Registers or updates a dynamic tool in the global ToolRegistry."""
        try:
            from ren.tools.registry import tool_registry
            wrapper = DynamicSkillToolWrapper(skill)
            tool_registry.register_tool(wrapper)
        except Exception as e:
            skills_logger.debug(f"Tool registry bridge sync: {e}")

    def get_skill(self, name: str) -> Optional[Skill]:
        """Retrieves skill by name or slug."""
        clean = name.lower().strip().replace("skill_", "").replace("_", " ")
        for k, s in self._skills.items():
            if k == clean or s.name.lower() == clean:
                return s
        return self._skills.get(name.lower())

    def get_active_skills(self) -> List[Skill]:
        return [s for s in self._skills.values() if s.metadata.enabled]

    def get_unlocked_skill_names(self) -> List[str]:
        names = [s.metadata.name for s in self.get_active_skills()]
        names.sort()
        return names

    def register_and_install_skill(
        self,
        name: str,
        code: str,
        description: str = "",
        source_task: str = "",
        parameters: Optional[Dict[str, Any]] = None,
        risk_level: str = "LOW",
    ) -> Tuple[bool, str]:
        """
        Full lifecycle:
        1. Static AST Validation (Syntax & safety analysis)
        2. Quarantine placement
        3. Sandbox test execution
        4. Promotion to Active directory + legacy sync
        5. Dynamic registration into ToolRegistry without restart
        """
        # Step 1: Static AST Validation
        val = SkillValidator.validate_code(code)
        if not val.is_valid:
            err = f"Skill static validation failed: {'; '.join(val.errors)}"
            skills_logger.warning(err)
            return False, err

        clean_name = name.strip()
        slug = re.sub(r'[^a-z0-9_]', '_', clean_name.lower().replace(' ', '_'))
        slug = re.sub(r'_+', '_', slug).strip('_')

        metadata = SkillMetadata(
            name=clean_name.title(),
            description=description or f"Skill to {clean_name}",
            triggers=[w.lower() for w in clean_name.split()],
            capabilities=[slug.replace('_', ' ')],
            source_task=source_task,
            parameters=parameters or {},
            risk_level=risk_level.upper() if risk_level.upper() in ("LOW", "MEDIUM", "HIGH") else "LOW",
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
        skills_logger.info(f"Testing new skill '{clean_name}' in execution sandbox...")
        test_success, stdout, stderr, exit_code = ExecutionSandbox.execute_python_code(
            code=code,
            timeout=15
        )

        metadata.tested = test_success
        if not test_success and exit_code != 0:
            skills_logger.warning(f"Skill '{clean_name}' failed sandbox execution test (exit={exit_code}): {stderr}")

        # Step 4: Promote to Active directory
        active_py = self.active_dir / f"{slug}.py"
        active_json = self.active_dir / f"{slug}.json"
        shutil.copy2(quarantine_py, active_py)
        with open(active_json, "w", encoding="utf-8") as f:
            json.dump(metadata.to_dict(), f, indent=2)

        # Step 5: Legacy root skills/ folder sync
        legacy_py = self.skills_dir / f"skill_{slug}.py"
        shutil.copy2(quarantine_py, legacy_py)

        # Step 6: Load into active memory registry & expose dynamically to ToolRegistry
        skill_obj = Skill(metadata=metadata, file_path=active_py, code_content=code)
        self._skills[metadata.name.lower()] = skill_obj
        self._sync_tool_wrapper(skill_obj)

        skills_logger.info(f"Successfully registered and dynamically loaded skill: {metadata.name}")
        return True, f"Skill '{metadata.name}' registered, validated, and ready for immediate execution."

    def execute_skill(self, name: str, args: Optional[Dict[str, Any]] = None) -> ToolResult:
        """Executes a registered skill safely and returns a structured ToolResult."""
        skill = self.get_skill(name)
        if not skill:
            return ToolResult(
                success=False,
                error=f"Skill '{name}' not found in registry.",
                exit_code=1
            )
        if not skill.enabled:
            return ToolResult(
                success=False,
                error=f"Skill '{name}' is currently disabled.",
                exit_code=1
            )

        start_t = time.perf_counter()
        success, stdout, stderr, exit_code = SkillLoader.execute_skill(skill, args=args or {})
        duration = time.perf_counter() - start_t

        if not success and stderr:
            return ToolResult(
                success=False,
                output=stdout.strip() if stdout else "",
                error=f"Execution error: {stderr.strip()}",
                exit_code=exit_code,
                duration=duration
            )

        output_text = stdout.strip() if stdout else "Skill executed successfully."
        return ToolResult(
            success=True,
            output=output_text,
            exit_code=0,
            duration=duration
        )

    def improve_skill(
        self,
        name: str,
        improved_code: str,
        rationale: str = ""
    ) -> Tuple[bool, str]:
        """
        Executes the IMPROVE step in skill lifecycle:
        1. Finds existing skill
        2. Validates new code via AST
        3. Tests new code in sandbox
        4. Increments version (e.g. 1.0.0 -> 1.0.1)
        5. Saves updated code & metadata
        6. Updates ToolRegistry and broadcasts SKILL_UPDATED event
        """
        existing = self.get_skill(name)
        if not existing:
            return False, f"Skill '{name}' not found for improvement."

        # Validate
        val = SkillValidator.validate_code(improved_code)
        if not val.is_valid:
            return False, f"Improvement rejected: {'; '.join(val.errors)}"

        # Sandbox test
        success, stdout, stderr, exit_code = ExecutionSandbox.execute_python_code(
            code=improved_code,
            timeout=15
        )
        if not success and exit_code != 0:
            return False, f"Sandbox test failed for improved code: {stderr}"

        # Increment patch version
        ver_parts = existing.metadata.version.split(".")
        try:
            ver_parts[-1] = str(int(ver_parts[-1]) + 1)
            new_version = ".".join(ver_parts)
        except Exception:
            new_version = f"{existing.metadata.version}.1"

        existing.metadata.version = new_version
        existing.metadata.tested = True
        existing.metadata.confidence = min(1.0, existing.metadata.confidence + 0.05)
        existing.code_content = improved_code

        # Write updated files
        slug = re.sub(r'[^a-z0-9_]', '_', existing.name.lower().replace(' ', '_'))
        slug = re.sub(r'_+', '_', slug).strip('_')

        active_py = self.active_dir / f"{slug}.py"
        active_json = self.active_dir / f"{slug}.json"
        with open(active_py, "w", encoding="utf-8") as f:
            f.write(improved_code)
        with open(active_json, "w", encoding="utf-8") as f:
            json.dump(existing.metadata.to_dict(), f, indent=2)

        self._sync_tool_wrapper(existing)
        from ren.core.events import event_bus, EventType
        event_bus.publish(EventType.SKILL_UPDATED, {
            "name": existing.name,
            "version": new_version,
            "rationale": rationale
        })
        skills_logger.info(f"Skill '{existing.name}' improved to v{new_version}.")
        return True, f"Successfully improved {existing.name} to v{new_version}."

    def build_compact_skill_index(self) -> str:
        """Builds a compact schema index of active skills for LLM context."""
        skills = self.get_active_skills()
        if not skills:
            return "No custom skills currently active."

        lines = []
        for s in skills[:20]:
            lines.append(f"- `{s.name}` ({s.risk_level} risk): {s.description}")
        return "\n".join(lines)


# Global registry singleton
skill_registry = SkillRegistry()
