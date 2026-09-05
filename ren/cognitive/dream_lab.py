"""
REN Dream Lab
Sandboxed experimentation environment executing:
HYPOTHESIS -> TEMPORARY IMPLEMENTATION -> TEST -> MEASURE -> COMPARE BASELINE -> KEEP/DISCARD.
Experiments run in isolation and never directly alter the live production system unless validated.
"""

import time
import uuid
from dataclasses import dataclass, field, asdict
from typing import Dict, Any, List, Optional, Callable, Tuple
import threading

from ren.monitoring.logger import agent_logger
from ren.security.sandbox import ExecutionSandbox


@dataclass
class ExperimentResult:
    experiment_id: str
    hypothesis: str
    domain: str  # "planning", "tool_selection", "skill", "prompt", "code"
    baseline_score: float
    experiment_score: float
    decision: str  # "KEEP", "DISCARD"
    metrics: Dict[str, Any] = field(default_factory=dict)
    timestamp: float = field(default_factory=time.time)
    details: str = ""

    def to_dict(self) -> Dict[str, Any]:
        return asdict(self)


class DreamLab:
    """Coordinates sandboxed trials and baseline comparisons."""

    def __init__(self):
        self._history: List[ExperimentResult] = []
        self._lock = threading.Lock()

    def run_experiment(
        self,
        hypothesis: str,
        domain: str,
        baseline_fn: Callable[[], Tuple[bool, float]],
        candidate_fn: Callable[[], Tuple[bool, float]],
        min_improvement_margin: float = 0.05
    ) -> ExperimentResult:
        """
        Executes a controlled trial:
        1. Evaluates baseline
        2. Evaluates candidate in sandbox
        3. Measures delta
        4. Decides KEEP if candidate > baseline + margin; else DISCARD
        """
        exp_id = f"exp_{uuid.uuid4().hex[:8]}"
        agent_logger.info(f"DreamLab: Starting trial [{exp_id}] Hypothesis: '{hypothesis}' (Domain: {domain})")

        # 1. Measure baseline
        try:
            base_success, base_score = baseline_fn()
        except Exception as e:
            base_success, base_score = False, 0.0

        # 2. Measure candidate
        try:
            cand_success, cand_score = candidate_fn()
        except Exception as e:
            cand_success, cand_score = False, 0.0

        delta = cand_score - base_score
        kept = cand_success and (delta >= min_improvement_margin)
        decision = "KEEP" if kept else "DISCARD"

        result = ExperimentResult(
            experiment_id=exp_id,
            hypothesis=hypothesis,
            domain=domain,
            baseline_score=base_score,
            experiment_score=cand_score,
            decision=decision,
            metrics={"delta": delta, "candidate_success": cand_success, "baseline_success": base_success},
            details=f"Delta: {delta:+.2f}. Decision: {decision} (Threshold: {min_improvement_margin:.2f})"
        )

        with self._lock:
            self._history.append(result)

        agent_logger.info(f"DreamLab: Trial [{exp_id}] complete -> {decision} (Base: {base_score:.2f}, Cand: {cand_score:.2f})")
        return result

    def get_history(self, limit: int = 10) -> List[Dict[str, Any]]:
        with self._lock:
            return [r.to_dict() for r in reversed(self._history[-limit:])]


# Global singleton
dream_lab = DreamLab()
