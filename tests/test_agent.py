"""
Integration Tests for Agent Runtime, Planner, and Loop Execution
"""

import unittest
from ren.models import set_model_provider, MockProvider
from ren.core.agent import agent_runtime
from ren.core.state import ExecutionContext
from ren.core.planner import TaskPlanner
from ren.sessions.models import Session


class TestAgentRuntime(unittest.TestCase):
    def setUp(self):
        self.mock_provider = MockProvider()
        set_model_provider(self.mock_provider)

    def test_fast_route_command(self):
        spoken = []
        resp = agent_runtime.process_input("who are you", speak_fn=lambda t: spoken.append(t))
        self.assertIn("Ren", resp)
        self.assertEqual(len(spoken), 1)

    def test_task_planner_complexity(self):
        self.assertFalse(TaskPlanner.is_complex_task("hello"))
        self.assertTrue(TaskPlanner.is_complex_task("debug my python script and create a git commit"))

    def test_agent_loop_with_tool_call(self):
        # Queue model response with a tool call followed by final answer
        tool_call_json = '```json\n{"tool": "system_status", "args": {}}\n```'
        final_answer = "System status has been verified. Everything looks healthy! [DONE]"
        self.mock_provider.set_responses([tool_call_json, final_answer])

        spoken = []
        result = agent_runtime.process_input("Check my system status", speak_fn=lambda t: spoken.append(t))
        self.assertIn("healthy", result.lower())

    def test_loop_detection(self):
        context = ExecutionContext(user_query="test loop", session=Session())
        # Record identical action 3 times
        context.record_action("read_file:{'path': 'error.log'}")
        context.record_action("read_file:{'path': 'error.log'}")
        context.record_action("read_file:{'path': 'error.log'}")

        self.assertTrue(context.is_looping(window=3))

    def test_hermes_scratchpad_reasoning(self):
        # Hermes Agent outputs <thought> scratchpad before answer
        model_output = "<thought>The user is asking about the system. I should answer concisely.</thought>All systems are operating at peak efficiency! [DONE]"
        self.mock_provider.set_responses([model_output])

        spoken = []
        result = agent_runtime.process_input("How is the system running?", speak_fn=lambda t: spoken.append(t))
        self.assertIn("peak efficiency", result)
        self.assertNotIn("<thought>", result)
        self.assertNotIn("<thought>", spoken[0] if spoken else "")

    def test_hermes_native_tool_call_xml(self):
        # Hermes native XML <tool_call> format
        tool_call_xml = '<thought>I will check the system status.</thought>\n<tool_call>\n{"name": "system_status", "arguments": {}}\n</tool_call>'
        final_answer = "System status check complete: Healthy. [DONE]"
        self.mock_provider.set_responses([tool_call_xml, final_answer])

        spoken = []
        result = agent_runtime.process_input("Check status please", speak_fn=lambda t: spoken.append(t))
        self.assertIn("Healthy", result)

    def test_hermes_openai_function_format(self):
        # Hermes OpenAI-style function format inside json markdown
        tool_call_json = '```json\n{"name": "system_status", "arguments": {}}\n```'
        final_answer = "Everything is running smoothly! [DONE]"
        self.mock_provider.set_responses([tool_call_json, final_answer])

        result = agent_runtime.process_input("Inspect status")
        self.assertIn("smoothly", result)


if __name__ == "__main__":
    unittest.main()
