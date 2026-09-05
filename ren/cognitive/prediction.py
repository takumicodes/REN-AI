"""
REN Prediction & Calibration Engine
Tracks: PREDICT -> ACT -> OBSERVE -> COMPARE -> UPDATE CONFIDENCE.
Maintains empirical calibration logs across tool calls, plans, and cognitive decisions.
"""

import time
import uuid
from dataclasses import dataclass, field, asdict
from typing import Dict, Any, List, Optional
import threading

from ren.monitoring.logger import agent_logger


@dataclass
class PredictionRecord:
    id: str
    domain: str  # "tool_execution", "plan_completion", "retrieval_relevance"
    prediction_statement: str
    expected_outcome: str
    confidence: float  # 0.0 to 1.0
    actual_outcome: Optional[str] = None
    was_accurate: Optional[bool] = None
    error_delta: Optional[float] = None
    timestamp: float = field(default_factory=time.time)

    def to_dict(self) -> Dict[str, Any]:
        return asdict(self)


class PredictionEngine:
    """Manages empirical action predictions and Bayesian calibration scoring."""

    def __init__(self):
        self._records: Dict[str, PredictionRecord] = {}
        self._lock = threading.Lock()

    def record_prediction(
        self,
        domain: str,
        statement: str,
        expected_outcome: str,
        confidence: float
    ) -> str:
        """Registers an explicit prediction prior to action."""
        pred_id = f"pred_{uuid.uuid4().hex[:8]}"
        rec = PredictionRecord(
            id=pred_id,
            domain=domain,
            prediction_statement=statement,
            expected_outcome=expected_outcome,
            confidence=min(1.0, max(0.0, confidence))
        )
        with self._lock:
            self._records[pred_id] = rec
        return pred_id

    def record_observation(
        self,
        pred_id: str,
        actual_outcome: str,
        was_accurate: bool
    ) -> Optional[PredictionRecord]:
        """Compares actual observation against prediction and records calibration delta."""
        with self._lock:
            rec = self._records.get(pred_id)
            if not rec:
                return None

            rec.actual_outcome = actual_outcome
            rec.was_accurate = was_accurate
            # Error delta: difference between confidence and actual binary outcome (1.0 or 0.0)
            target = 1.0 if was_accurate else 0.0
            rec.error_delta = abs(rec.confidence - target)

        agent_logger.debug(
            f"PredictionEngine: Evaluated [{pred_id}] Domain={rec.domain}, Accurate={was_accurate}, "
            f"Conf={rec.confidence:.2f}, Error={rec.error_delta:.2f}"
        )
        return rec

    def get_calibration_stats(self, domain: Optional[str] = None) -> Dict[str, Any]:
        """Computes empirical accuracy and Brier calibration score."""
        with self._lock:
            evaluated = [r for r in self._records.values() if r.was_accurate is not None]
            if domain:
                evaluated = [r for r in evaluated if r.domain == domain]

        if not evaluated:
            return {"total": 0, "accuracy": 1.0, "average_confidence": 1.0, "brier_score": 0.0}

        total = len(evaluated)
        correct = sum(1 for r in evaluated if r.was_accurate)
        avg_conf = sum(r.confidence for r in evaluated) / total
        brier = sum((r.error_delta ** 2) for r in evaluated if r.error_delta is not None) / total

        return {
            "total": total,
            "accuracy": correct / total,
            "average_confidence": avg_conf,
            "brier_score": brier,
            "is_well_calibrated": abs((correct / total) - avg_conf) < 0.15
        }


# Global singleton
prediction_engine = PredictionEngine()
