"""
REN Self-Evaluation Engine
Empirical performance monitoring tracking:
- Task success rate
- Tool selection accuracy
- Prediction accuracy & calibration
- Memory retrieval usefulness
- Coding / sandbox execution success
- User correction rate
- Regression failures & skill reliability
Generates targeted improvement objectives from measured weak areas.
"""

import time
from dataclasses import dataclass, field, asdict
from typing import Dict, Any, List, Optional
import threading

from ren.monitoring.logger import agent_logger
from ren.cognitive.curiosity import curiosity_engine


@dataclass
class MetricBucket:
    successes: int = 0
    failures: int = 0
    corrections: int = 0

    @property
    def total(self) -> int:
        return self.successes + self.failures

    @property
    def success_rate(self) -> float:
        return (self.successes / self.total) if self.total > 0 else 1.0


class SelfEvaluationEngine:
    """Monitors performance benchmarks and identifies regression / weak areas."""

    def __init__(self):
        self._lock = threading.Lock()
        self.task_metrics = MetricBucket()
        self.tool_metrics: Dict[str, MetricBucket] = {}
        self.coding_metrics = MetricBucket()
        self.memory_metrics = MetricBucket()
        self.skill_reliability: Dict[str, MetricBucket] = {}

    def record_task_outcome(self, success: bool, had_user_correction: bool = False):
        with self._lock:
            if success:
                self.task_metrics.successes += 1
            else:
                self.task_metrics.failures += 1
            if had_user_correction:
                self.task_metrics.corrections += 1

    def record_tool_call(self, tool_name: str, success: bool):
        with self._lock:
            if tool_name not in self.tool_metrics:
                self.tool_metrics[tool_name] = MetricBucket()
            b = self.tool_metrics[tool_name]
            if success:
                b.successes += 1
            else:
                b.failures += 1

    def record_skill_execution(self, skill_name: str, success: bool):
        with self._lock:
            if skill_name not in self.skill_reliability:
                self.skill_reliability[skill_name] = MetricBucket()
            b = self.skill_reliability[skill_name]
            if success:
                b.successes += 1
            else:
                b.failures += 1

    def record_coding_result(self, compiled_and_tested: bool):
        with self._lock:
            if compiled_and_tested:
                self.coding_metrics.successes += 1
            else:
                self.coding_metrics.failures += 1

    def evaluate_and_generate_improvement_objectives(self) -> List[str]:
        """Scans metrics and generates curiosity objectives for failing areas."""
        generated = []
        with self._lock:
            # Check unreliable tools (< 70% success with >= 3 calls)
            for tool_name, bucket in self.tool_metrics.items():
                if bucket.total >= 3 and bucket.success_rate < 0.70:
                    curiosity_engine.generate_objective(
                        topic=f"Tool Reliability: {tool_name}",
                        reason=f"Tool '{tool_name}' has low empirical success rate ({bucket.success_rate*100:.1f}% across {bucket.total} calls).",
                        category="repeated_failure",
                        priority=0.90,
                        confidence=0.95
                    )
                    generated.append(f"Tool {tool_name} flagged for optimization.")

            # Check unreliable custom skills
            for skill_name, bucket in self.skill_reliability.items():
                if bucket.total >= 2 and bucket.success_rate < 0.60:
                    curiosity_engine.generate_objective(
                        topic=f"Skill Improvement: {skill_name}",
                        reason=f"Skill '{skill_name}' failed in {bucket.failures}/{bucket.total} executions.",
                        category="missing_skill",
                        priority=0.85,
                        confidence=0.90
                    )
                    generated.append(f"Skill {skill_name} flagged for repair.")

        return generated

    def get_summary_report(self) -> Dict[str, Any]:
        """Provides high-level performance metrics dictionary."""
        with self._lock:
            return {
                "overall_task_success_rate": round(self.task_metrics.success_rate, 3),
                "total_tasks": self.task_metrics.total,
                "user_correction_rate": round((self.task_metrics.corrections / max(1, self.task_metrics.total)), 3),
                "coding_success_rate": round(self.coding_metrics.success_rate, 3),
                "tools_tracked": len(self.tool_metrics),
                "skills_tracked": len(self.skill_reliability),
            }


# Global singleton
self_evaluation_engine = SelfEvaluationEngine()
