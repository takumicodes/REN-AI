"""
Ollama Local Model Provider
Integrates with local Ollama daemon (Qwen, DeepSeek, Llama) with resource locks,
adaptive context window scaling, and automated memory-fallback model selection.
"""

import time
import json
import requests
from typing import Dict, Any, Optional, List, Tuple

from ren.models.provider import ModelProvider
from ren.config.settings import settings
from ren.monitoring.logger import agent_logger, error_logger
from ren.monitoring.performance import perf_monitor


class OllamaProvider(ModelProvider):
    """Local Ollama client with concurrency gates and adaptive parameters."""

    FALLBACK_MODELS = [
        "qwen2.5-coder:1.5b",
        "qwen2.5:1.5b",
        "qwen2.5:0.5b",
        "qwen2.5-coder:0.5b",
        "llama3.2:1b",
    ]

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

    def get_installed_models(self) -> List[str]:
        """Queries and caches installed Ollama models."""
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
        """Checks if Ollama daemon is reachable and responding."""
        try:
            r = requests.get(self.tags_url, timeout=3)
            return r.status_code == 200
        except Exception:
            return False

    def health_check(self) -> Dict[str, Any]:
        """Queries Ollama for loaded models and server status."""
        try:
            start_t = time.perf_counter()
            r = requests.get(self.tags_url, timeout=4)
            latency = time.perf_counter() - start_t
            if r.status_code == 200:
                data = r.json()
                models = [m.get("name") for m in data.get("models", [])]
                model_present = any(self.model_name in m for m in models)
                return {
                    "online": True,
                    "latency": round(latency, 3),
                    "available_models": models,
                    "target_model_installed": model_present,
                    "active_model": self.model_name,
                }
        except Exception as e:
            return {"online": False, "error": str(e), "active_model": self.model_name}
        return {"online": False, "error": "Unknown status", "active_model": self.model_name}

    def _execute_request(self, model: str, prompt: str, ctx: int, num_predict: int, temp: float) -> Tuple[bool, str, int, str]:
        """
        Sends raw generation request to Ollama.
        Returns: (success: bool, text_or_error: str, tokens_count: int, raw_error_text: str)
        """
        payload = {
            "model": model,
            "prompt": prompt,
            "stream": False,
            "options": {
                "num_predict": num_predict,
                "num_ctx": ctx,
                "temperature": temp,
            },
        }

        try:
            response = requests.post(self.generate_url, json=payload, timeout=self.timeout)
            if response.status_code == 200:
                data = response.json()
                text = data.get("response", "").strip()
                tokens_count = data.get("eval_count", len(text.split()))
                return True, text, tokens_count, ""
            return False, f"HTTP {response.status_code}", 0, response.text
        except requests.Timeout:
            return False, "Timeout", 0, "Inference timed out"
        except Exception as e:
            return False, str(e), 0, str(e)

    def generate(
        self,
        prompt: str,
        max_tokens: Optional[int] = None,
        temperature: Optional[float] = None,
        num_ctx: Optional[int] = None,
        **kwargs,
    ) -> str:
        """Sends prompt to Ollama with single-inference concurrency and auto-fallback."""
        num_predict = max_tokens or settings.MODEL.MAX_TOKENS_AGENT
        temp = temperature if temperature is not None else settings.MODEL.DEFAULT_TEMPERATURE
        ctx = num_ctx or settings.MODEL.NUM_CTX

        # Adjust context budget based on system pressure
        ctx = perf_monitor.get_adaptive_context_budget(ctx)

        # Enforce single primary inference to avoid thrashing CPU/RAM
        with perf_monitor.inference_lock:
            start_time = time.perf_counter()

            # Context size steps to try
            ctx_steps = [ctx]
            if ctx > 1024:
                ctx_steps.append(1024)
            if ctx > 512:
                ctx_steps.append(512)

            # Candidate models (primary target first, followed by installed fallbacks)
            installed = self.get_installed_models()
            candidate_models = [self.model_name]
            for fb in self.FALLBACK_MODELS:
                if fb not in candidate_models and any(fb in m for m in installed):
                    candidate_models.append(fb)

            for target_model in candidate_models:
                for attempt_ctx in ctx_steps:
                    agent_logger.debug(f"Ollama generating ({target_model}) ctx={attempt_ctx} predict={num_predict}...")
                    success, result_text, tokens_count, raw_err = self._execute_request(
                        model=target_model,
                        prompt=prompt,
                        ctx=attempt_ctx,
                        num_predict=num_predict,
                        temp=temp,
                    )

                    if success:
                        latency = time.perf_counter() - start_time
                        perf_monitor.record_llm_call(
                            latency=latency,
                            tokens_generated=tokens_count,
                            model=target_model
                        )
                        if target_model != self.model_name:
                            agent_logger.info(f"Ollama memory adaptation: Answered using lighter model '{target_model}'")
                            self.model_name = target_model
                        return result_text

                    # If memory allocation failure, try next context step or lighter model
                    if "failed to allocate" in raw_err or "alloc_tensor_range" in raw_err or "unable to allocate" in raw_err:
                        agent_logger.warning(
                            f"Ollama buffer allocation failed for '{target_model}' at ctx={attempt_ctx}. Stepping down..."
                        )
                        time.sleep(0.5)
                        continue

                    # If model not found or other non-memory error, log and break ctx loop to try next model
                    if "not found" in raw_err.lower():
                        agent_logger.warning(f"Model '{target_model}' not found in Ollama.")
                        break

                    error_logger.error(f"Ollama error on '{target_model}': {raw_err}")
                    break

            return "Error: Unable to allocate model buffer in local RAM. Consider running with a lighter model like qwen2.5-coder:1.5b."

    def chat(self, messages: List[Dict[str, str]], **kwargs) -> str:
        """Converts structured messages into prompt string and generates response."""
        prompt_parts = []
        for msg in messages:
            role = msg.get("role", "user").upper()
            content = msg.get("content", "")
            prompt_parts.append(f"{role}:\n{content}\n")
        prompt_parts.append("REN:\n")
        full_prompt = "\n".join(prompt_parts)
        return self.generate(full_prompt, **kwargs)
