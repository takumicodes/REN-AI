"""
Unit Tests for REN 2.0 Skill Lifecycle:
CREATE -> VALIDATE -> TEST -> SAVE -> REGISTER -> LOAD -> EXPOSE TO MODEL -> EXECUTE
"""

import unittest
from ren.skills.validator import SkillValidator
from ren.skills.registry import skill_registry, SkillMetadata
from ren.tools.registry import tool_registry


class TestSkillsLifecycle(unittest.TestCase):

    def test_full_skill_lifecycle(self):
        skill_name = "Speedrun Math Calculator"
        skill_code = (
            "import sys\n"
            "a = 15\n"
            "b = 27\n"
            "print(f'Sum: {a + b}')\n"
        )

        # 1. Validation & Installation
        success, msg = skill_registry.register_and_install_skill(
            name=skill_name,
            code=skill_code,
            description="Calculates sum of numbers",
            risk_level="LOW",
            parameters={"a": {"type": "integer"}, "b": {"type": "integer"}}
        )
        self.assertTrue(success, msg)

        # 2. Retrieval from registry
        skill = skill_registry.get_skill(skill_name)
        self.assertIsNotNone(skill)
        self.assertEqual(skill.name, skill_name)
        self.assertEqual(skill.risk_level, "LOW")
        self.assertTrue(skill.enabled)

        # 3. Dynamic Tool Registry Bridge
        tool = tool_registry.get_tool("skill_speedrun_math_calculator")
        self.assertIsNotNone(tool, "Dynamic tool wrapper was not created in tool_registry")

        # 4. Immediate Execution
        exec_res = skill_registry.execute_skill(skill_name)
        self.assertTrue(exec_res.success)
        self.assertIn("Sum: 42", exec_res.output)

        # 5. Direct Tool Execution via Tool Registry
        tool_res = tool_registry.execute_tool("skill_speedrun_math_calculator", {})
        self.assertTrue(tool_res.success)
        self.assertIn("Sum: 42", tool_res.output)

        # 6. Generic execute_skill tool
        generic_tool_res = tool_registry.execute_tool("execute_skill", {"skill_name": skill_name})
        self.assertTrue(generic_tool_res.success)
        self.assertIn("Sum: 42", generic_tool_res.output)

    def test_invalid_syntax_rejected(self):
        bad_code = "def invalid_syntax(:\n    pass\n"
        success, msg = skill_registry.register_and_install_skill(
            name="Broken Skill",
            code=bad_code,
        )
        self.assertFalse(success)
        self.assertIn("validation failed", msg.lower())

    def test_disabled_skill_execution(self):
        code = "print('Active')\n"
        skill_registry.register_and_install_skill(name="Toggleable Skill", code=code)
        skill = skill_registry.get_skill("Toggleable Skill")
        skill.metadata.enabled = False
        res = skill_registry.execute_skill("Toggleable Skill")
        self.assertFalse(res.success)
        self.assertIn("disabled", res.error.lower())
        skill.metadata.enabled = True


if __name__ == "__main__":
    unittest.main()
