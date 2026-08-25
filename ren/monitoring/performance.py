"""
REN Resource and Performance Monitor
Monitors host CPU, RAM, disk usage, model inference latencies, and provides adaptive context budgeting.
"""

import os
import sys
import time
import threading
from contextlib import contextmanager
from dataclasses import dataclass, field
from typing import Dict, Any, Optional, List
import psutil

from ren.monitoring.logger import perf_logger


@dataclass
class PerformanceMetrics:
    cpu_percent: float = 0.0
    ram_percent: float = 0.0
    ram_available_mb: float = 0.0
    disk_percent: float = 0.0
    active_threads: int = 0
    last_llm_latency: float = 0.0
    avg_llm_latency: float = 0.0
    total_llm_calls: int = 0
    total_tokens_generated: int = 0
    estimated_tokens_per_sec: float = 0.0


class PerformanceMonitor:
    """Thread-safe performance and resource tracker."""

    def __init__(self):
        self._lock = threading.Lock()
        self._inference_lock = threading.Lock()  # Single primary LLM inference gate
        self._metrics = PerformanceMetrics()
        self._llm_latencies: List[float] = []
        self._tool_durations: Dict[str, List[float]] = {}

    @property
    def inference_lock(self) -> threading.Lock:
        """Lock to ensure only one primary local LLM generation runs simultaneously."""
        return self._inference_lock

    def get_system_snapshot(self) -> Dict[str, Any]:
        """Captures immediate OS and hardware resource metrics."""
        try:
            cpu = psutil.cpu_percent(interval=None)
            ram = psutil.virtual_memory()
            disk = psutil.disk_usage(os.path.abspath(os.sep))

            with self._lock:
                self._metrics.cpu_percent = cpu
                self._metrics.ram_percent = ram.percent
                self._metrics.ram_available_mb = ram.available / (1024 * 1024)
                self._metrics.disk_percent = disk.percent
                self._metrics.active_threads = threading.active_count()

            return {
                "cpu_percent": cpu,
                "ram_percent": ram.percent,
                "ram_available_mb": round(ram.available / (1024 * 1024), 1),
                "disk_percent": disk.percent,
                "active_threads": threading.active_count(),
                "last_llm_latency": round(self._metrics.last_llm_latency, 2),
                "avg_llm_latency": round(self._metrics.avg_llm_latency, 2),
                "total_llm_calls": self._metrics.total_llm_calls,
                "total_tokens": self._metrics.total_tokens_generated,
            }
        except Exception as e:
            perf_logger.error(f"Failed to capture system snapshot: {e}")
            return {
                "cpu_percent": 0.0,
                "ram_percent": 0.0,
                "ram_available_mb": 0.0,
                "disk_percent": 0.0,
                "active_threads": 0,
            }

    def is_resource_strained(self, cpu_thresh: float = 85.0, ram_thresh: float = 85.0) -> bool:
        """Checks whether system is under heavy CPU or RAM memory pressure."""
        snapshot = self.get_system_snapshot()
        return snapshot["cpu_percent"] > cpu_thresh or snapshot["ram_percent"] > ram_thresh

    def get_adaptive_context_budget(self, base_budget: int = 3000) -> int:
        """Dynamically shrinks context window budget if RAM is heavily consumed."""
        snapshot = self.get_system_snapshot()
        ram_pct = snapshot.get("ram_percent", 50.0)

        if ram_pct > 85.0:
            return min(base_budget, 3024)
        elif ram_pct > 70.0:
            return min(base_budget, 3042)
        return min(base_budget, 3030)

    def record_llm_call(self, latency: float, tokens_generated: int = 0, model: str = "") -> None:
        """Records telemetry for an LLM generation call."""
        with self._lock:
            self._metrics.total_llm_calls += 1
            self._metrics.last_llm_latency = latency
            self._llm_latencies.append(latency)
            if len(self._llm_latencies) > 50:
                self._llm_latencies.pop(0)

            self._metrics.avg_llm_latency = sum(self._llm_latencies) / len(self._llm_latencies)
            self._metrics.total_tokens_generated += tokens_generated

            if latency > 0 and tokens_generated > 0:
                self._metrics.estimated_tokens_per_sec = tokens_generated / latency

        perf_logger.info(
            f"LLM Call: model={model} latency={latency:.2f}s "
            f"tokens={tokens_generated} speed={self._metrics.estimated_tokens_per_sec:.1f} t/s"
        )

    def record_tool_call(self, tool_name: str, duration: float, success: bool) -> None:
        """Records execution telemetry for a tool invocation."""
        with self._lock:
            if tool_name not in self._tool_durations:
                self._tool_durations[tool_name] = []
            self._tool_durations[tool_name].append(duration)
            if len(self._tool_durations[tool_name]) > 30:
                self._tool_durations[tool_name].pop(0)

        perf_logger.info(f"Tool Executed: {tool_name} duration={duration:.3f}s success={success}")

    @contextmanager
    def measure_time(self, label: str):
        """Context manager to measure execution time of any arbitrary block."""
        start = time.perf_counter()
        try:
            yield
        finally:
            elapsed = time.perf_counter() - start
            perf_logger.debug(f"Block '{label}' took {elapsed:.4f}s")


# Global monitor singleton
perf_monitor = PerformanceMonitor()
