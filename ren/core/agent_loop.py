"""
Autonomous Bounded Agent Loop
Executes multi-step reasoning, tool dispatch, loop detection, streaming output, and failure recovery.
"""

import re
import json
import time
from typing import Optional, Callable, Dict, Any

from ren.core.state import ExecutionContext, AgentLifecycle
from ren.core.context import ContextBuilder
from ren.core.events import event_bus, EventType
from ren.models import get_model_provider
from ren.tools.registry import tool_registry
from ren.skills.registry import skill_registry
from ren.memory.manager import memory_manager
from ren.config.settings import settings
from ren.monitoring.logger import agent_logger, error_logger


class AgentLoop:
    """Bounded, safe autonomous agent loop with loop prevention and streaming generation."""

    def __init__(self, context: ExecutionContext):
        self.context = context
        self.provider = get_model_provider()

    def run(
        self,
        speak_fn: Optional[Callable[[str], None]] = None,
        ui_callback: Optional[Callable[[str, Any], None]] = None,
        token_callback: Optional[Callable[[str], None]] = None,
    ) -> str:
        """Executes bounded autonomous reasoning loop with immediate streaming output."""
        agent_logger.info(f"Starting Agent Loop for request: '{self.context.user_query}'")
        event_bus.publish(EventType.AGENT_STARTED, {"query": self.context.user_query})

        if ui_callback:
            ui_callback('agent_stage', 'intent')

        observation: Optional[str] = None
        final_answer: str = ""
        already_streamed = False

        while self.context.current_iteration < self.context.max_iterations:
            if self.context.is_cancelled:
                agent_logger.info("Agent execution cancelled by user.")
                msg = "Execution stopped at your request, Sir."
                if speak_fn: speak_fn(msg)
                if token_callback: token_callback(msg)
                return msg

            self.context.current_iteration += 1
            iter_num = self.context.current_iteration
            agent_logger.debug(f"Agent Loop iteration {iter_num}/{self.context.max_iterations}")

            # 1. Build Context
            if ui_callback:
                ui_callback('agent_stage', 'exec')
            event_bus.publish(EventType.AGENT_PLANNING, {"iteration": iter_num})

            prompt = ContextBuilder.build_agent_prompt(
                user_query=self.context.user_query,
                session=self.context.session,
                active_plan=self.context.active_plan,
                observation=observation,
                user_id=self.context.user_id,
            )

            # 2. Query LLM with real-time streaming token callback
            streamed_tokens = []
            def stream_handler(chunk: str):
                streamed_tokens.append(chunk)
                if token_callback and not self.context.is_cancelled:
                    token_callback(chunk)

            llm_response = self.provider.generate(
                prompt,
                max_tokens=settings.MODEL.MAX_TOKENS_AGENT,
                temperature=0.4,
                token_callback=stream_handler if token_callback else None,
                cancel_check=lambda: self.context.is_cancelled,
            )

            if self.context.is_cancelled:
                return "Operation stopped."

            agent_logger.debug(f"LLM Raw Output:\n{llm_response}")

            # 3. Check for Intro Text before Code or Tool Call & speak it immediately
            intro_parts = llm_response.split('```')
            if len(intro_parts) > 1:
                intro_text = intro_parts[0].strip()
                intro_text = re.sub(r'(?i)skill\s*name:\s*.*', '', intro_text).strip()
                intro_clean = re.sub(r'[*#_`-]', '', intro_text).strip()
                if intro_clean and speak_fn and self.context.current_iteration == 1:
                    speak_fn(intro_clean)

            # 4. Check for Skill Generation (`Skill Name:` + Python block)
            skill_match = re.search(r'Skill\s*Name:\s*(.*)', llm_response, re.IGNORECASE)
            python_blocks = re.findall(r'```python\s*(.*?)\s*```', llm_response, re.DOTALL)

            if skill_match and python_blocks:
                friendly_name = skill_match.group(1).strip()
                code_to_install = python_blocks[0]

                if ui_callback:
                    ui_callback('agent_stage', 'tools')
                event_bus.publish(EventType.SKILL_CREATED, {"name": friendly_name})

                success, reg_msg = skill_registry.register_and_install_skill(
                    name=friendly_name,
                    code=code_to_install,
                    source_task=self.context.user_query,
                )

                if success and ui_callback:
                    ui_callback('show_popup', {
                        'title': 'Advancement Unlocked',
                        'message': friendly_name,
                        'type': 'advancement'
                    })
                    ui_callback('skills_list', skill_registry.get_unlocked_skill_names())

                observation = f"[Skill Registration Result]: {reg_msg}"
                continue

            # 5. Check for JSON Tool Call
            json_blocks = re.findall(r'```json\s*(.*?)\s*```', llm_response, re.DOTALL)
            parsed_tool_call = None

            if json_blocks:
                try:
                    parsed_tool_call = json.loads(json_blocks[0])
                except Exception:
                    pass

            if not parsed_tool_call:
                raw_json = re.search(r'\{\s*"tool"\s*:\s*"[^"]+"\s*,\s*"args"\s*:\s*\{.*?\}\s*\}', llm_response, re.DOTALL)
                if raw_json:
                    try:
                        parsed_tool_call = json.loads(raw_json.group(0))
                    except Exception:
                        pass

            if parsed_tool_call and isinstance(parsed_tool_call, dict) and "tool" in parsed_tool_call:
                tool_name = parsed_tool_call.get("tool")
                tool_args = parsed_tool_call.get("args", {})

                action_signature = f"{tool_name}:{json.dumps(tool_args, sort_keys=True)}"
                self.context.record_action(action_signature)

                if self.context.is_looping(window=settings.AGENT.LOOP_DETECTION_WINDOW):
                    agent_logger.warning(f"Loop detected on action: {action_signature}")
                    err_msg = f"I noticed I am repeating the same action ({tool_name}) without progress. Stopping to avoid infinite loop."
                    if speak_fn: speak_fn(err_msg)
                    return err_msg

                if ui_callback:
                    ui_callback('agent_stage', 'exec')

                event_bus.publish(EventType.TOOL_STARTED, {"tool": tool_name, "args": tool_args})

                tool_result = tool_registry.execute_tool(tool_name, tool_args)

                if ui_callback:
                    ui_callback('agent_stage', 'verify')

                if tool_result.success:
                    event_bus.publish(EventType.TOOL_COMPLETED, {"tool": tool_name, "output": tool_result.output})
                    self.context.consecutive_failures = 0
                else:
                    event_bus.publish(EventType.TOOL_FAILED, {"tool": tool_name, "error": tool_result.error})
                    self.context.consecutive_failures += 1

                observation = f"Tool '{tool_name}' result:\nSuccess: {tool_result.success}\nOutput:\n{tool_result.output or tool_result.error}"
                continue

            # 6. Check for standalone Python script execution block
            if python_blocks and not skill_match:
                code_to_exec = python_blocks[0]
                if ui_callback:
                    ui_callback('agent_stage', 'exec')

                # Prepend common helper imports for convenience
                preamble = (
                    "import os, sys, shutil, requests, psutil, json\n"
                    "from ren.core.router import get_downloads_dir\n"
                    "from ren.memory.manager import memory_manager\n"
                )
                full_code = preamble + "\n" + code_to_exec

                tool_result = tool_registry.execute_tool("python_execute", {"code": full_code})
                if ui_callback:
                    ui_callback('agent_stage', 'verify')

                observation = f"Python Execution Result:\nSuccess: {tool_result.success}\nOutput:\n{tool_result.output}"
                if "[DONE]" in tool_result.output:
                    final_answer = tool_result.output.replace("[DONE]", "").strip()
                    break
                continue

            # 7. Final Conversational Response
            clean_text = re.sub(r'```.*?```', '', llm_response, flags=re.DOTALL).strip()
            clean_text = clean_text.replace("[DONE]", "").strip()

            if clean_text:
                final_answer = clean_text
                if streamed_tokens:
                    already_streamed = True
                elif token_callback:
                    token_callback(final_answer)
                break

        if not final_answer:
            final_answer = "Task operations concluded, Sir."
            if token_callback and not already_streamed:
                token_callback(final_answer)

        if speak_fn:
            speak_fn(final_answer)

        self.context.session.add_message(role="user", content=self.context.user_query)
        self.context.session.add_message(role="assistant", content=final_answer)

        memory_manager.record_episode(
            task=self.context.user_query,
            outcome="Success" if self.context.consecutive_failures == 0 else "Partial/Failure",
            actions_taken=", ".join(self.context.executed_actions_history),
            solution=final_answer[:150],
        )

        event_bus.publish(EventType.AGENT_COMPLETED, {
            "query": self.context.user_query,
            "iterations": self.context.current_iteration,
            "response": final_answer,
        })

        if ui_callback:
            ui_callback('agent_stage', 'idle')

        return final_answer
