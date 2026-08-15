"""
Unit Tests for Skill Validation, Discovery, Lifecycle, and Router
"""

import unittest
import tempfile
import shutil
from pathlib import Path

from ren.skills.validator import SkillValidator
from ren.skills.registry import SkillRegistry, SkillMetadata
from ren.skills.router import SkillRouter


class TestSkillSystem(unittest.TestCase):
    def test_skill_ast_validation(self):
        valid_code = "def get_battery():\n    print('Battery 100%')\nget_battery()\n"
        res = SkillValidator.validate_code(valid_code)
        self.assertTrue(res.is_valid)

        syntax_error_code = "def bad_func(:\n    pass\n"
        res_bad = SkillValidator.validate_code(syntax_error_code)
        self.assertFalse(res_bad.is_valid)
        self.assertGreater(len(res_bad.errors), 0)

    def test_skill_routing(self):
        # Test keyword matching
        selected = SkillRouter.select_skills("Check battery status of laptop")
        self.assertTrue(isinstance(selected, list))

    def test_skill_registration_lifecycle(self):
        code = "print('Hello from test skill')\n"
        from ren.skills.registry import skill_registry
        success, msg = skill_registry.register_and_install_skill(
            name="Test Greeter",
            code=code,
            description="Greets user in testing"
        )
        self.assertTrue(success)
        skill = skill_registry.get_skill("Test Greeter")
        self.assertIsNotNone(skill)


if __name__ == "__main__":
    unittest.main()
