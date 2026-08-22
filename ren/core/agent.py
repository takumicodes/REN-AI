"""
REN Core Autonomous Agent Runtime
Main entrypoint orchestrating intent routing, direct reasoning loops, and multi-user telemetry.
"""

import threading
from typing import Optional, Callable, Dict, Any

from ren.core.state import ExecutionContext, AgentLifecycle
from ren.core.router import IntentRouter
from ren.core.agent_loop import AgentLoop
from ren.core.events import event_bus, EventType
from ren.sessions.manager import session_manager
from ren.memory.manager import memory_manager
from ren.monitoring.logger import agent_logger


class AgentRuntime:
    """Central agent coordinator for REN with per-user/per-session concurrency support."""

    def __init__(self):
        self._lock = threading.Lock()
        self._active_contexts: Dict[str, ExecutionContext] = {}

    def process_input(
        self,
        user_input: str,
        speak_fn: Optional[Callable[[str], None]] = None,
        ui_callback: Optional[Callable[[str, Any], None]] = None,
        token_callback: Optional[Callable[[str], None]] = None,
        session_id: Optional[str] = None,
        user_id: str = "default",
    ) -> str:
        """Processes user text or speech prompt with isolated session and memory scoping."""
        query = user_input.strip()
        if not query:
            return ""

        agent_logger.info(f"Processing input (user='{user_id}', session='{session_id}'): '{query}'")
        event_bus.publish(EventType.USER_MESSAGE, {"text": query, "user_id": user_id})

        # Resolve session strictly for this user
        if session_id:
            session = session_manager.resume_session(session_id, user_id=user_id)
            if not session:
                session = session_manager.create_session(
                    user_id=user_id,
                    title=query[:30] if len(query) > 30 else query
                )
        else:
            session = session_manager.get_active_session_for_user(user_id=user_id)

        target_session_id = session.session_id

        # Auto-update session title if it's default
        if session and (session.title in ["New Session", "New Conversation", "Fresh Session"] or not session.messages):
            first_words = " ".join(query.split()[:5])
            if first_words:
                session.title = first_words[:30]

        # 1. Fast Path Shortcuts (Instant zero-latency execution)
        handled, fast_resp = IntentRouter.try_fast_route(query, speak_fn=speak_fn)
        if handled:
            session.add_message(role="user", content=query)
            session.add_message(role="assistant", content=fast_resp)
            session_manager.save_session(session)
            if token_callback:
                token_callback(fast_resp)
            return fast_resp

        # 2. Autonomous Agent Loop with isolated execution context
        context = ExecutionContext(
            user_query=query,
            session=session,
            user_id=user_id,
        )

        with self._lock:
            self._active_contexts[target_session_id] = context

        try:
            loop = AgentLoop(context)
            response = loop.run(speak_fn=speak_fn, ui_callback=ui_callback, token_callback=token_callback)

            # 3. Compact session if needed
            session_manager.compact_session_if_needed(session)
            session_manager.save_session(session)
            return response
        finally:
            with self._lock:
                self._active_contexts.pop(target_session_id, None)

    def stop_operations(self, session_id: Optional[str] = None, user_id: Optional[str] = None) -> str:
        """Signals active agent loop to cancel execution with granular session/user isolation."""
        with self._lock:
            if session_id and session_id in self._active_contexts:
                self._active_contexts[session_id].is_cancelled = True
                agent_logger.info(f"AgentRuntime: Cancellation requested for session '{session_id}'.")
                return f"Session '{session_id}' stopped."
            elif user_id:
                count = 0
                for sid, ctx in self._active_contexts.items():
                    if ctx.user_id == user_id:
                        ctx.is_cancelled = True
                        count += 1
                agent_logger.info(f"AgentRuntime: Cancellation requested for user '{user_id}' ({count} active).")
                return f"Stopped {count} active sessions for user."
            else:
                # Desktop master stop or global stop
                for sid, ctx in self._active_contexts.items():
                    ctx.is_cancelled = True
                agent_logger.info("AgentRuntime: Global cancellation requested.")
                return "All operations stopped."


# Global agent runtime singleton
agent_runtime = AgentRuntime()
