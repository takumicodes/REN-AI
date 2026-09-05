"""
System-Wide Live Event Bus API Endpoint
Streams real-time events (agent status, dream logs, autonomous messages, tools, skills)
to connected desktop and web clients via Server-Sent Events (SSE).
"""

import json
import asyncio
import queue
from typing import Dict, Any
from fastapi import APIRouter, Request, Depends
from fastapi.responses import StreamingResponse

from ren.core.events import event_bus
from api.user_session import get_current_user_id

router = APIRouter(prefix="/events", tags=["Live Events"])


@router.get("")
async def system_events_stream(
    request: Request,
    user_id: str = Depends(get_current_user_id)
):
    """Subscribes client to global live events via SSE."""
    client_queue = queue.Queue(maxsize=100)

    def event_listener(event_type: str, data: Any):
        try:
            client_queue.put_nowait({
                "event": event_type,
                "data": data
            })
        except queue.Full:
            pass

    event_bus.subscribe("*", event_listener)

    async def sse_event_generator():
        try:
            while True:
                if await request.is_disconnected():
                    break

                try:
                    msg = client_queue.get_nowait()
                    yield f"event: {msg['event']}\ndata: {json.dumps(msg['data'])}\n\n"
                except queue.Empty:
                    await asyncio.sleep(0.1)

        except asyncio.CancelledError:
            pass

    return StreamingResponse(
        sse_event_generator(),
        media_type="text/event-stream",
        headers={
            "Cache-Control": "no-cache, no-transform",
            "Connection": "keep-alive",
            "X-Accel-Buffering": "no",
        }
    )
