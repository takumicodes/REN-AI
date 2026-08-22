"""
TTS API Endpoints
Provides high-fidelity cloud text-to-speech audio streaming.
"""

from fastapi import APIRouter, HTTPException
from fastapi.responses import StreamingResponse
from pydantic import BaseModel
from typing import Optional
import edge_tts
import io

from ren.monitoring.logger import agent_logger, error_logger

router = APIRouter(prefix="/tts", tags=["Voice & TTS"])


class TTSRequest(BaseModel):
    text: str
    voice: Optional[str] = "en-IN-PrabhatNeural"


@router.post("")
async def generate_speech(req: TTSRequest):
    """Generates audio for text using Edge TTS and streams MP3 bytes directly."""
    text = req.text.strip()
    if not text:
        raise HTTPException(status_code=400, detail="Text cannot be empty.")

    # Clean markdown / code blocks from spoken text for natural voice synthesis
    import re
    cleaned_text = re.sub(r'```.*?```', 'code block omitted', text, flags=re.DOTALL)
    cleaned_text = re.sub(r'[*#_`~]', '', cleaned_text).strip()
    if not cleaned_text:
        cleaned_text = "Code output received."

    # Limit maximum spoken characters per request to avoid huge payloads
    if len(cleaned_text) > 2000:
        cleaned_text = cleaned_text[:2000] + "... and so on."

    try:
        communicate = edge_tts.Communicate(cleaned_text, voice=req.voice or "en-IN-PrabhatNeural")

        async def audio_stream_generator():
            async for chunk in communicate.stream():
                if chunk.get("type") == "audio" and "data" in chunk:
                    yield chunk["data"]

        return StreamingResponse(
            audio_stream_generator(),
            media_type="audio/mpeg",
            headers={
                "Cache-Control": "no-cache",
                "Content-Disposition": "inline; filename=speech.mp3",
            }
        )
    except Exception as e:
        error_logger.warning(f"Edge TTS API generation failed: {e}")
        raise HTTPException(
            status_code=503,
            detail="Cloud TTS unavailable. Browser fallback synthesis recommended."
        )
