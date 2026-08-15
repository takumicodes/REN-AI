"""
Unit Tests for Tool Registry and Built-in Tools
"""

import unittest
import tempfile
import shutil
from pathlib import Path

from ren.tools.registry import tool_registry
from ren.tools.filesystem import ReadFileTool, WriteFileTool, ListDirectoryTool
from ren.tools.python_runner import PythonRunnerTool


class TestTools(unittest.TestCase):
    def setUp(self):
        self.temp_dir = tempfile.mkdtemp()

    def tearDown(self):
        shutil.rmtree(self.temp_dir, ignore_errors=True)

    def test_write_and_read_file_tool(self):
        test_file = Path(self.temp_dir) / "test.txt"
        res_write = tool_registry.execute_tool("write_file", {"path": str(test_file), "content": "Hello World REN"})
        self.assertTrue(res_write.success)

        res_read = tool_registry.execute_tool("read_file", {"path": str(test_file)})
        self.assertTrue(res_read.success)
        self.assertIn("Hello World REN", res_read.output)

    def test_missing_required_args(self):
        res = tool_registry.execute_tool("read_file", {})
        self.assertFalse(res.success)
        self.assertIn("Missing required parameter", res.error)

    def test_python_runner_tool(self):
        code = "a = 15\nb = 25\nprint(f'Sum: {a + b}')\n"
        res = tool_registry.execute_tool("python_execute", {"code": code})
        self.assertTrue(res.success)
        self.assertIn("Sum: 40", res.output)

    def test_system_status_tool(self):
        res = tool_registry.execute_tool("system_status", {})
        self.assertTrue(res.success)
        self.assertIn("Operating System", res.output)


if __name__ == "__main__":
    unittest.main()
