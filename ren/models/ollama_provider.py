"""
Ollama & Cloud Model Provider
Direct, unthrottled high-performance inference for Hermes Agent / Gemma 31B on Cloud
with multimodal vision support, full token potential, and zero fallbacks.
"""

import time
import json
import re
import requests
from typing import Dict, Any, Optional, List, Tuple, Callable

from ren.models.provider import ModelProvider
from ren.config.settings import settings
from ren.monitoring.logger import agent_logger, error_logger
from ren.monitoring.performance import perf_monitor


class OllamaProvider(ModelProvider):
    """Direct unthrottled client with multimodal image support and zero fallbacks."""

    VISION_PATTERNS = ["vision", "llava", "bakllava", "moondream", "minicpm-v", "gemini", "gpt-4", "claude"]

    def __init__(
        self,
        host: Optional[str] = None,
        model_name: Optional[str] = None,
        timeout: Optional[int] = None,
    ):
        self.host = (host or settings.MODEL.OLLAMA_HOST).rstrip("/")
        self.generate_url = f"{self.host}/api/generate"
        self.tags_url = f"{self.host}/api/tags"
        self.model_name = model_name or settings.MODEL.MODEL_NAME
        self.timeout = timeout or settings.MODEL.TIMEOUT_SECONDS
        self._installed_models_cache: List[str] = []
        self._last_tags_check: float = 0.0

    def supports_vision(self) -> bool:
        """Determines if the configured model supports vision/images."""
        m_lower = self.model_name.lower()
        return any(pattern in m_lower for pattern in self.VISION_PATTERNS)

    def get_installed_models(self) -> List[str]:
        """Queries and caches installed models."""
        now = time.time()
        if self._installed_models_cache and (now - self._last_tags_check < 30.0):
            return self._installed_models_cache
        try:
            r = requests.get(self.tags_url, timeout=3)
            if r.status_code == 200:
                data = r.json()
                self._installed_models_cache = [m.get("name") for m in data.get("models", [])]
                self._last_tags_check = now
                return self._installed_models_cache
        except Exception:
            pass
        return self._installed_models_cache

    def is_available(self) -> bool:
        """Checks if model endpoint is reachable and responding."""
        try:
            r = requests.get(self.tags_url, timeout=3)
            return r.status_code == 200
        except Exception:
            return False

    def health_check(self) -> Dict[str, Any]:
        """Queries model host for available models and server status."""
        try:
            start_t = time.perf_counter()
            r = requests.get(self.tags_url, timeout=4)
            latency = time.perf_counter() - start_t
            if r.status_code == 200:
                data = r.json()
                models = [m.get("name") for m in data.get("models", [])]
                model_present = any(self.model_name in m for m in models) if models else True
                return {
                    "online": True,
                    "latency": round(latency, 3),
                    "available_models": models,
                    "target_model_installed": model_present,
                    "active_model": self.model_name,
                    "supports_vision": self.supports_vision(),
                }
        except Exception as e:
            return {"online": False, "error": str(e), "active_model": self.model_name, "supports_vision": self.supports_vision()}
        return {"online": False, "error": "Unknown status", "active_model": self.model_name, "supports_vision": self.supports_vision()}

    def _execute_request(
        self,
        model: str,
        prompt: str,
        ctx: int,
        num_predict: int,
        temp: float,
        images: Optional[List[str]] = None,
    ) -> Tuple[bool, str, int, str]:
        """Sends raw generation request to model host with retry."""
        clean_images = [img for img in (images or []) if img]
        # Clean any data URI headers (e.g. data:image/png;base64,...)
        formatted_images = []
        for img in clean_images:
            if "," in img and "base64" in img:
                formatted_images.append(img.split(",", 1)[1].strip())
            else:
                formatted_images.append(img.strip())

        payload: Dict[str, Any] = {
            "model": model,
            "prompt": prompt,
            "stream": False,
            "options": {
                "num_predict": num_predict,
                "num_ctx": ctx,
                "temperature": temp,
                "top_p": 0.9,
                "top_k": 40,
                "repeat_penalty": 1.1,
            },
        }

        if formatted_images:
            payload["images"] = formatted_images

        for attempt in range(2):
            try:
                response = requests.post(self.generate_url, json=payload, timeout=self.timeout)
                if response.status_code == 200:
                    data = response.json()
                    text = data.get("response", "").strip()
                    tokens_count = data.get("eval_count", len(text.split()))
                    return True, text, tokens_count, ""
                if attempt == 0 and ("forcibly closed" in response.text or "encountered while running" in response.text):
                    time.sleep(0.5)
                    continue
                return False, f"HTTP {response.status_code}", 0, response.text
            except requests.Timeout:
                return False, "Timeout", 0, "Inference timed out"
            except Exception as e:
                if attempt == 0:
                    time.sleep(0.5)
                    continue
                return False, str(e), 0, str(e)

        return False, "Unknown inference failure", 0, ""

    def _execute_stream_request(
        self,
        model: str,
        prompt: str,
        ctx: int,
        num_predict: int,
        temp: float,
        images: Optional[List[str]] = None,
        token_callback: Optional[Callable[[str], None]] = None,
        cancel_check: Optional[Callable[[], bool]] = None,
    ) -> Tuple[bool, str, int, str]:
        """Sends streaming generation request to model host with retry."""
        clean_images = [img for img in (images or []) if img]
        formatted_images = []
        for img in clean_images:
            if "," in img and "base64" in img:
                formatted_images.append(img.split(",", 1)[1].strip())
            else:
                formatted_images.append(img.strip())

        payload: Dict[str, Any] = {
            "model": model,
            "prompt": prompt,
            "stream": True,
            "options": {
                "num_predict": num_predict,
                "num_ctx": ctx,
                "temperature": temp,
                "top_p": 0.9,
                "top_k": 40,
                "repeat_penalty": 1.1,
            },
        }

        if formatted_images:
            payload["images"] = formatted_images

        for attempt in range(2):
            try:
                response = requests.post(self.generate_url, json=payload, stream=True, timeout=self.timeout)
                if response.status_code != 200:
                    if attempt == 0 and ("forcibly closed" in response.text or "encountered while running" in response.text):
                        time.sleep(0.5)
                        continue
                    return False, f"HTTP {response.status_code}", 0, response.text

                accumulated_tokens = []
                token_count = 0
                for line in response.iter_lines():
                    if cancel_check and cancel_check():
                        response.close()
                        return True, "".join(accumulated_tokens).strip(), token_count, "Cancelled"
                    if line:
                        try:
                            chunk_json = json.loads(line.decode("utf-8"))
                            text_part = chunk_json.get("response", "")
                            if text_part:
                                accumulated_tokens.append(text_part)
                                token_count += 1
                                if token_callback:
                                    token_callback(text_part)
                            if chunk_json.get("done", False):
                                eval_count = chunk_json.get("eval_count", token_count)
                                return True, "".join(accumulated_tokens).strip(), eval_count, ""
                        except json.JSONDecodeError:
                            continue

                full_text = "".join(accumulated_tokens).strip()
                return True, full_text, token_count, ""
            except requests.Timeout:
                return False, "Timeout", 0, "Inference timed out"
            except Exception as e:
                if attempt == 0:
                    time.sleep(0.5)
                    continue
                return False, str(e), 0, str(e)

        return False, "Unknown inference failure", 0, ""

    def generate(
        self,
        prompt: str,
        images: Optional[List[str]] = None,
        max_tokens: Optional[int] = None,
        temperature: Optional[float] = None,
        num_ctx: Optional[int] = None,
        token_callback: Optional[Callable[[str], None]] = None,
        cancel_check: Optional[Callable[[], bool]] = None,
        **kwargs,
    ) -> str:
        """Sends prompt directly to model with optional image inputs and zero fallbacks."""
        num_predict = max_tokens or settings.MODEL.MAX_TOKENS_AGENT
        temp = temperature if temperature is not None else settings.MODEL.DEFAULT_TEMPERATURE
        ctx = num_ctx or settings.MODEL.NUM_CTX
        target_model = self.model_name

        start_time = time.perf_counter()
        agent_logger.debug(f"Generating ({target_model}) ctx={ctx} predict={num_predict} images={len(images or [])}...")

        if token_callback or cancel_check:
            success, result_text, tokens_count, raw_err = self._execute_stream_request(
                model=target_model,
                prompt=prompt,
                ctx=ctx,
                num_predict=num_predict,
                temp=temp,
                images=images,
                token_callback=token_callback,
                cancel_check=cancel_check,
            )
        else:
            success, result_text, tokens_count, raw_err = self._execute_request(
                model=target_model,
                prompt=prompt,
                ctx=ctx,
                num_predict=num_predict,
                temp=temp,
                images=images,
            )

        if success:
            latency = time.perf_counter() - start_time
            perf_monitor.record_llm_call(
                latency=latency,
                tokens_generated=tokens_count,
                model=target_model
            )
            return result_text

        if "not found" in raw_err.lower():
            agent_logger.warning(f"Model '{target_model}' not found on {self.host}.")
            return (
                f"Model '{target_model}' was not found on host {self.host}.\n\n"
                f"To resolve this:\n"
                f"1. If running locally: run `ollama pull {target_model}` in your terminal.\n"
                f"2. If running on Cloud (e.g. Gemma 31B / Hermes): set your cloud host and model in your `.env` file:\n"
                f"   REN_OLLAMA_HOST=http://<YOUR_CLOUD_IP>:11434\n"
                f"   REN_MODEL_NAME=<YOUR_MODEL_TAG>"
            )

        error_logger.error(f"Inference error on '{target_model}': {raw_err}")
        return f"Error: Inference failed on {target_model}: {raw_err}"

    def chat(self, messages: List[Dict[str, Any]], images: Optional[List[str]] = None, **kwargs) -> str:
        """Converts structured messages into ChatML prompt string for Hermes Agent and generates response."""
        prompt_parts = []
        for msg in messages:
            role = str(msg.get("role", "user")).lower()
            content = str(msg.get("content", ""))
            prompt_parts.append(f"<|im_start|>{role}\n{content}<|im_end|>")
        prompt_parts.append("<|im_start|>assistant\n")
        full_prompt = "\n".join(prompt_parts)
        return self.generate(full_prompt, images=images, **kwargs)
