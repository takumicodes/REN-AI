"""
REN Core Autonomous Agent Runtime
Main entrypoint orchestrating intent routing, thinking mode selection, multimodal image forwarding,
direct reasoning loops, and multi-user telemetry.
"""

import threading
from typing import Optional, Callable, Dict, Any, List, Union

from ren.core.state import ExecutionContext, AgentLifecycle
from ren.core.thinking import ThinkingMode
from ren.core.device_context import DeviceContext, device_manager
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
        images: Optional[List[str]] = None,
        thinking_mode: Optional[Union[str, ThinkingMode]] = None,
        think_hard: bool = False,
        developer_token: Optional[str] = None,
        speak_fn: Optional[Callable[[str], None]] = None,
        ui_callback: Optional[Callable[[str, Any], None]] = None,
        token_callback: Optional[Callable[[str], None]] = None,
        session_id: Optional[str] = None,
        user_id: str = "default",
        source_device_id: str = "pc_host",
        target_device_id: Optional[str] = None,
        device_context: Optional[DeviceContext] = None,
    ) -> str:
        """Processes user text/image prompt with thinking mode adaptation, device context resolution, and isolated session scoping."""
        query = user_input.strip()
        if not query and not images:
            return ""

        resolved_mode = ThinkingMode.from_string(thinking_mode) if isinstance(thinking_mode, str) else (thinking_mode or ThinkingMode.MEDIUM)

        # Resolve Device Context (Decouple host from target)
        resolved_device_ctx = device_context
        if not resolved_device_ctx:
            resolved_device_ctx = device_manager.resolve_context(
                query=query,
                source_device_id=source_device_id,
                user_id=user_id,
                session_id=session_id
            )
            if target_device_id:
                resolved_device_ctx.target_device_id = target_device_id

        agent_logger.info(
            f"Processing input (user='{user_id}', session='{session_id}', source='{resolved_device_ctx.source_device_id}', "
            f"target='{resolved_device_ctx.target_device_id}', mode='{resolved_mode.value}', think_hard={think_hard}): '{query[:50]}'"
        )
        event_bus.publish(EventType.USER_MESSAGE, {
            "text": query,
            "user_id": user_id,
            "source_device_id": resolved_device_ctx.source_device_id,
            "target_device_id": resolved_device_ctx.target_device_id,
            "thinking_mode": resolved_mode.value,
            "think_hard": think_hard,
            "has_images": bool(images and len(images) > 0)
        })

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

        # 1. Fast Path Shortcuts (Instant zero-latency execution - only if no image attached and not Think Hard)
        if not images and not think_hard and resolved_mode == ThinkingMode.FAST:
            handled, fast_resp = IntentRouter.try_fast_route(query, speak_fn=speak_fn, device_context=resolved_device_ctx)
            if handled:
                session.add_message(role="user", content=query)
                session.add_message(role="assistant", content=fast_resp)
                session_manager.save_session(session)
                if token_callback:
                    token_callback(fast_resp)
                return fast_resp
        elif not images and not think_hard:
            handled, fast_resp = IntentRouter.try_fast_route(query, speak_fn=speak_fn, device_context=resolved_device_ctx)
            # Only handle safety / identity fast routes
            if handled and any(kw in query.lower() for kw in ["who are you", "what is your name", "who made you", "nuclear", "bomb", "hack"]):
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
            images=images,
            thinking_mode=resolved_mode,
            think_hard=think_hard,
            developer_token=developer_token,
            device_context=resolved_device_ctx,
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
                for sid, ctx in self._active_contexts.items():
                    ctx.is_cancelled = True
                agent_logger.info("AgentRuntime: Global cancellation requested.")
                return "All operations stopped."


# Global agent runtime singleton
agent_runtime = AgentRuntime()
