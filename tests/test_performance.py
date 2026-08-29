"""
Unit Tests for Performance Monitoring and Concurrency Lock
"""

import unittest
from ren.monitoring.performance import perf_monitor, PerformanceMonitor


class TestPerformance(unittest.TestCase):
    def test_telemetry_recording(self):
        perf_monitor.record_llm_call(latency=1.25, tokens_generated=50, model="hermes3:3b")
        snapshot = perf_monitor.get_system_snapshot()
        self.assertGreaterEqual(snapshot["total_llm_calls"], 1)
        self.assertGreaterEqual(snapshot["total_tokens"], 50)

    def test_single_inference_lock(self):
        lock = perf_monitor.inference_lock
        self.assertTrue(lock.acquire(blocking=False))
        # Second acquire without release should fail
        self.assertFalse(lock.acquire(blocking=False))
        lock.release()

    def test_adaptive_context_budget(self):
        budget = perf_monitor.get_adaptive_context_budget(base_budget=3000)
        self.assertGreater(budget, 1000)
        self.assertLessEqual(budget, 3000)


if __name__ == "__main__":
    unittest.main()
