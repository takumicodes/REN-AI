"""
REN Voice Pipeline Architecture
Implements: Microphone -> VAD (Voice Activity Detection) -> Streaming STT -> Reasoning -> Streaming TTS.
Includes barge-in / speech interruption handling and offline/online fallback engines.
"""

import os
import sys
import time
import queue
import threading
import asyncio
from pathlib import Path
from typing import Optional, Callable, Dict, Any, Generator, Tuple

from ren.config.settings import settings
from ren.monitoring.logger import agent_logger, error_logger
import voice


class SimpleVAD:
    """Voice Activity Detector based on RMS energy threshold and silence duration."""

    def __init__(self, energy_threshold: float = 500.0, silence_duration: float = 1.2):
        self.energy_threshold = energy_threshold
        self.silence_duration = silence_duration
        self._last_speech_time = 0.0
        self._is_speaking = False

    def process_chunk(self, audio_data: bytes) -> Tuple[bool, bool]:
        """
        Returns (is_speech_present, is_utterance_complete).
        """
        import audioop
        try:
            rms = audioop.rms(audio_data, 2)
        except Exception:
            rms = 0

        now = time.time()
        is_speech = rms > self.energy_threshold

        if is_speech:
            self._is_speaking = True
            self._last_speech_time = now
            return True, False

        if self._is_speaking and (now - self._last_speech_time > self.silence_duration):
            self._is_speaking = False
            return False, True  # Utterance concluded

        return False, False


class VoicePipelineManager:
    """Coordinates Microphone -> VAD -> STT -> AgentRuntime -> TTS with barge-in interruption."""

    def __init__(self):
        self.is_listening = False
        self.is_speaking = False
        self._interrupted = False
        self._lock = threading.Lock()
        self.vad = SimpleVAD()

    def barge_in(self):
        """Interrupts ongoing speech playback immediately when user starts speaking."""
        with self._lock:
            if self.is_speaking:
                agent_logger.info("Barge-in triggered: interrupting active TTS speech playback.")
                self._interrupted = True
                voice.stop_speaking()
                self.is_speaking = False

    def speak(self, text: str, callback: Optional[Callable[[], None]] = None):
        """Speaks text using edge-tts or offline SAPI5 with interruption awareness."""
        with self._lock:
            self.is_speaking = True
            self._interrupted = False

        try:
            voice.speak(text)
        finally:
            with self._lock:
                self.is_speaking = False
            if callback:
                callback()

    def stop(self):
        """Immediately silences output and stops active voice listeners."""
        self.barge_in()
        self.is_listening = False


# Global singleton
voice_pipeline = VoicePipelineManager()
