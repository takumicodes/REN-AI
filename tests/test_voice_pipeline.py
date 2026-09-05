"""
Tests for Phase 6: Voice Pipeline and Barge-in.
"""

import unittest
import time
from ren.voice.pipeline import SimpleVAD, VoicePipelineManager


class TestVoicePipeline(unittest.TestCase):

    def test_vad_speech_detection(self):
        vad = SimpleVAD(energy_threshold=100.0, silence_duration=0.5)

        # High energy chunk (simulated speech audio)
        speech_chunk = b"\xff\x7f" * 100
        is_speech, is_done = vad.process_chunk(speech_chunk)
        self.assertTrue(is_speech)
        self.assertFalse(is_done)

        # Low energy chunk (silence)
        silence_chunk = b"\x00\x00" * 100
        is_speech2, is_done2 = vad.process_chunk(silence_chunk)
        self.assertFalse(is_speech2)

        # After silence duration expires
        time.sleep(0.6)
        is_speech3, is_done3 = vad.process_chunk(silence_chunk)
        self.assertFalse(is_speech3)
        self.assertTrue(is_done3)

    def test_barge_in_interruption(self):
        mgr = VoicePipelineManager()
        mgr.is_speaking = True

        # Trigger barge-in
        mgr.barge_in()
        self.assertFalse(mgr.is_speaking)
        self.assertTrue(mgr._interrupted)


if __name__ == "__main__":
    unittest.main()
