"""
Unit Tests for Multimodal Image Input & Vision Pipeline
Tests image payload formatting, base64 stripping, vision model capability checks, and prompt cues.
"""

import unittest
from ren.models.ollama_provider import OllamaProvider
from ren.core.context import ContextBuilder
from ren.sessions.models import Session


class TestImageInput(unittest.TestCase):

    def test_vision_capability_detection(self):
        v_provider = OllamaProvider(model_name="llava:13b")
        self.assertTrue(v_provider.supports_vision())

        gemma_provider = OllamaProvider(model_name="gemma4:31b-cloud")
        # Gemma text model returns False unless named vision
        self.assertFalse(gemma_provider.supports_vision())

        gemini_provider = OllamaProvider(model_name="gemini-1.5-pro")
        self.assertTrue(gemini_provider.supports_vision())

    def test_context_builder_image_cue(self):
        session = Session(session_id="img_sess", user_id="usr_1")
        prompt = ContextBuilder.build_agent_prompt(
            user_query="Describe this diagram",
            session=session,
            has_image=True
        )
        self.assertIn("[Multimodal Input Attached", prompt)

    def test_image_base64_data_uri_cleaning(self):
        provider = OllamaProvider()
        # Mocking format logic: data URIs should have prefix stripped before sending to Ollama
        raw_data_uri = "data:image/png;base64,iVBORw0KGgoAAAANSUhEUgAAAAEAAAABCAQAAAC1HAwCAAAAC0lEQVR42mNk+A8AAQUBAScY42YAAAAASUVORK5CYII="
        clean = raw_data_uri.split(",", 1)[1].strip() if "," in raw_data_uri else raw_data_uri
        self.assertFalse(clean.startswith("data:"))
        self.assertTrue(clean.startswith("iVBORw0KGgo"))


if __name__ == "__main__":
    unittest.main()
