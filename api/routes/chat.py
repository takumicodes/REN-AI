"""
Chat API Endpoints
Provides real-time streaming (SSE) and JSON chat interactions with multi-user isolation,
multimodal image input support, thinking modes (FAST, MEDIUM, HIGH), and think-hard toggle.
"""

import json
import asyncio
import queue
import threading
from typing import Optional, Dict, Any, List
from pydantic import BaseModel
from fastapi import APIRouter, HTTPException, Request, Depends
from fastapi.responses import StreamingResponse

from ren.core.agent import agent_runtime
from ren.core.thinking import ThinkingMode, thinking_manager
from ren.sessions.manager import session_manager
from ren.monitoring.logger import agent_logger, error_logger
from api.user_session import get_current_user_id
import back_end

router = APIRouter(prefix="/chat", tags=["Chat"])


class ChatRequest(BaseModel):
    message: str
    session_id: Optional[str] = None
    stream: Optional[bool] = True
    image_base64: Optional[str] = None
    images: Optional[List[str]] = None
    thinking_mode: Optional[str] = "MEDIUM"
    think_hard: Optional[bool] = False
    developer_token: Optional[str] = None
    source_device_id: Optional[str] = None
    target_device_id: Optional[str] = None


class StopRequest(BaseModel):
    session_id: Optional[str] = None


@router.post("/stop")
async def stop_generation(
    req: Optional[StopRequest] = None,
    user_id: str = Depends(get_current_user_id)
):
    """Immediately stops active agent generation for the requesting session or user."""
    target_session_id = req.session_id if req else None
    result = agent_runtime.stop_operations(session_id=target_session_id, user_id=user_id)
    return {"status": "stopped", "message": result, "session_id": target_session_id}


@router.post("")
async def chat_endpoint(
    req: ChatRequest,
    request: Request,
    user_id: str = Depends(get_current_user_id)
):
    """
    Main chat interaction endpoint with strict multi-user isolation.
    Supports multimodal images, thinking modes (Fast/Medium/High), Think Hard override, and SSE streaming.
    """
    user_message = req.message.strip()
    images = list(req.images or [])
    if req.image_base64 and req.image_base64 not in images:
        images.insert(0, req.image_base64)

    if not user_message and not images:
        raise HTTPException(status_code=400, detail="Message or image must be provided.")

    if not user_message and images:
        user_message = "Analyze this image and describe what you see."

    # Resolve or create session strictly for this user
    target_session = None
    if req.session_id:
        target_session = session_manager.resume_session(req.session_id, user_id=user_id)
        if not target_session:
            target_session = session_manager.create_session(
                user_id=user_id,
                title=user_message[:30] if len(user_message) > 30 else user_message
            )
    else:
        target_session = session_manager.get_active_session_for_user(user_id=user_id)

    session_id = target_session.session_id

    # Extract source and target device identities from request or headers
    source_device_id = req.source_device_id or request.headers.get("X-Source-Device-ID") or request.headers.get("X-Device-ID") or "pc_host"
    target_device_id = req.target_device_id or request.headers.get("X-Target-Device-ID") or None

    # If streaming is NOT requested, process synchronously in thread pool
    if not req.stream:
        try:
            response_text = await asyncio.to_thread(
                agent_runtime.process_input,
                user_message,
                images=images if images else None,
                thinking_mode=req.thinking_mode,
                think_hard=bool(req.think_hard),
                developer_token=req.developer_token,
                session_id=session_id,
                user_id=user_id,
                source_device_id=source_device_id,
                target_device_id=target_device_id,
            )
            updated_session = session_manager.resume_session(session_id, user_id=user_id)
            title = updated_session.title if updated_session else target_session.title

            return {
                "response": response_text,
                "session_id": session_id,
                "user_id": user_id,
                "title": title,
                "source_device_id": source_device_id,
                "target_device_id": target_device_id,
                "thinking_mode": req.thinking_mode,
                "think_hard": req.think_hard,
                "status": "completed"
            }
        except Exception as e:
            error_logger.error(f"Error in non-stream chat: {e}", exc_info=True)
            raise HTTPException(status_code=500, detail=str(e))

    # Streaming via Server-Sent Events (SSE)
    event_queue = queue.Queue()

    def token_callback(token: str):
        event_queue.put({"type": "token", "token": token})

    def ui_callback(event_type: str, data: Any):
        if event_type == "agent_stage":
            event_queue.put({"type": "status", "stage": data, "message": f"Stage: {data}"})
        elif event_type == "status":
            event_queue.put({"type": "status", "stage": data, "message": f"{data}"})
        elif event_type == "module_status":
            module_name, status_text, _ = data
            event_queue.put({"type": "tool", "tool": module_name, "message": f"Tool '{module_name}': {status_text}"})
        elif event_type == "show_popup" and isinstance(data, dict):
            if data.get("type") == "advancement":
                event_queue.put({"type": "skill_created", "name": data.get("message", "")})

    def run_agent_worker():
        try:
            mode_cfg = thinking_manager.get_config(
                ThinkingMode.from_string(req.thinking_mode),
                think_hard=bool(req.think_hard)
            )
            event_queue.put({
                "type": "start",
                "session_id": session_id,
                "user_id": user_id,
                "source_device_id": source_device_id,
                "target_device_id": target_device_id,
                "thinking_mode": mode_cfg.mode.value,
                "status_label": mode_cfg.status_label,
            })
            
            final_res = agent_runtime.process_input(
                user_message,
                images=images if images else None,
                thinking_mode=req.thinking_mode,
                think_hard=bool(req.think_hard),
                developer_token=req.developer_token,
                ui_callback=ui_callback,
                token_callback=token_callback,
                session_id=session_id,
                user_id=user_id,
                source_device_id=source_device_id,
                target_device_id=target_device_id,
            )

            updated_session = session_manager.resume_session(session_id, user_id=user_id)
            title = updated_session.title if updated_session else target_session.title

            event_queue.put({
                "type": "done",
                "response": final_res,
                "session_id": session_id,
                "user_id": user_id,
                "source_device_id": source_device_id,
                "target_device_id": target_device_id,
                "title": title
            })
        except Exception as err:
            error_logger.error(f"Agent worker error: {err}", exc_info=True)
            event_queue.put({"type": "error", "error": str(err)})
        finally:
            event_queue.put(None)  # Sentinel to end stream

    # Launch agent loop in background OS thread
    worker_thread = threading.Thread(target=run_agent_worker, daemon=True)
    worker_thread.start()

    async def sse_stream_generator():
        try:
            while True:
                # Check for client disconnect
                if await request.is_disconnected():
                    agent_logger.info(f"Client disconnected for session '{session_id}'. Halting generation...")
                    agent_runtime.stop_operations(session_id=session_id)
                    break

                # Non-blocking poll from thread queue with async sleep
                try:
                    event = event_queue.get_nowait()
                except queue.Empty:
                    await asyncio.sleep(0.02)
                    continue

                if event is None:
                    break

                # Send SSE formatted chunk
                yield f"data: {json.dumps(event)}\n\n"

        except asyncio.CancelledError:
            agent_logger.info(f"SSE Stream cancelled by client for session '{session_id}'.")
            agent_runtime.stop_operations(session_id=session_id)
        except Exception as e:
            error_logger.error(f"Error in SSE generator: {e}")
            yield f"data: {json.dumps({'type': 'error', 'error': str(e)})}\n\n"

    return StreamingResponse(
        sse_stream_generator(),
        media_type="text/event-stream",
        headers={
            "Cache-Control": "no-cache, no-transform",
            "Connection": "keep-alive",
            "X-Accel-Buffering": "no",
        }
    )
