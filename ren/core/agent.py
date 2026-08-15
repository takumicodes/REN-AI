"""
REN Core Autonomous Agent Runtime
Main entrypoint orchestrating intent routing, direct reasoning loops, and telemetry.
"""

from typing import Optional, Callable, Dict, Any

from ren.core.state import ExecutionContext, AgentLifecycle
from ren.core.router import IntentRouter
from ren.core.agent_loop import AgentLoop
from ren.core.events import event_bus, EventType
from ren.sessions.manager import session_manager
from ren.memory.manager import memory_manager
from ren.monitoring.logger import agent_logger


class AgentRuntime:
    """Central agent coordinator for REN."""

    def __init__(self):
        self._current_context: Optional[ExecutionContext] = None

    def process_input(
        self,
        user_input: str,
        speak_fn: Optional[Callable[[str], None]] = None,
        ui_callback: Optional[Callable[[str, Any], None]] = None,
    ) -> str:
        """Processes any user text or speech prompt."""
        query = user_input.strip()
        if not query:
            return ""

        agent_logger.info(f"Processing input: '{query}'")
        event_bus.publish(EventType.USER_MESSAGE, {"text": query})

        # 1. Fast Path Shortcuts (Instant zero-latency execution)
        handled, fast_resp = IntentRouter.try_fast_route(query, speak_fn=speak_fn)
        if handled:
            session = session_manager.active_session
            session.add_message(role="user", content=query)
            session.add_message(role="assistant", content=fast_resp)
            session_manager.save_session(session)
            return fast_resp

        # 2. Autonomous Agent Loop (Direct execution without redundant planner delay)
        session = session_manager.active_session
        self._current_context = ExecutionContext(
            user_query=query,
            session=session,
        )

        loop = AgentLoop(self._current_context)
        response = loop.run(speak_fn=speak_fn, ui_callback=ui_callback)

        # 3. Compact session if needed
        session_manager.compact_session_if_needed(session)

        return response

    def stop_operations(self) -> str:
        """Signals active agent loop to cancel current execution immediately."""
        if self._current_context:
            self._current_context.is_cancelled = True
        agent_logger.info("AgentRuntime: Cancellation requested.")
        return "Operations stopped."


# Global agent runtime singleton
agent_runtime = AgentRuntime()
