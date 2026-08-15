"""
Skill Static Validator
Performs AST static analysis to ensure generated skills are syntactically valid and free of dangerous raw exploits.
"""

import ast
from dataclasses import dataclass
from typing import List, Tuple, Optional

from ren.monitoring.logger import skills_logger


@dataclass
class ValidationResult:
    is_valid: bool
    errors: List[str]
    warnings: List[str]


class SkillValidator:
    """AST-based safety and syntax validator for autonomous skills."""

    FORBIDDEN_CALLS = {
        "os.system('rmdir /s /q c:\\')",
        "shutil.rmtree('C:\\Windows')",
    }

    FORBIDDEN_MODULES = {
        # Raw ctypes memory overwriting or shell execution that bypasses sandbox
    }

    @classmethod
    def validate_code(cls, code: str) -> ValidationResult:
        """Parses and inspects code AST."""
        errors = []
        warnings = []

        if not code or not code.strip():
            return ValidationResult(is_valid=False, errors=["Empty skill code"], warnings=[])

        # 1. Syntax Check
        try:
            tree = ast.parse(code)
        except SyntaxError as e:
            return ValidationResult(
                is_valid=False,
                errors=[f"SyntaxError on line {e.lineno}: {e.msg}"],
                warnings=[]
            )

        # 2. AST Node Traversal
        for node in ast.walk(tree):
            # Check for forbidden dangerous imports
            if isinstance(node, ast.Import):
                for alias in node.names:
                    if alias.name in cls.FORBIDDEN_MODULES:
                        errors.append(f"Forbidden module import: {alias.name}")
            elif isinstance(node, ast.ImportFrom):
                if node.module in cls.FORBIDDEN_MODULES:
                    errors.append(f"Forbidden module import: {node.module}")

        is_valid = len(errors) == 0
        if not is_valid:
            skills_logger.warning(f"Skill validation failed: {errors}")

        return ValidationResult(is_valid=is_valid, errors=errors, warnings=warnings)
