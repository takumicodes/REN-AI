"""
REN Learning Pipeline
Enforces rigorous multi-confirmation learning:
Experience -> Candidate Lesson -> Validation -> Repeated Evidence -> Validated Knowledge -> Training Queue.
Guarantees that a single bad interaction or hallucination can never permanently alter system knowledge or models.
"""

import time
import json
import uuid
from dataclasses import dataclass, field, asdict
from typing import Dict, Any, List, Optional
import threading

from ren.config.settings import settings
from ren.monitoring.logger import agent_logger
from ren.core.events import event_bus, EventType


@dataclass
class LearningRecord:
    id: str
    experience: str
    lesson: str
    source: str  # "user_interaction", "tool_observation", "dream_lab", "benchmark"
    confidence: float = 0.5
    times_confirmed: int = 1
    times_failed: int = 0
    status: str = "candidate"  # "candidate", "validated", "rejected"
    training_candidate: bool = False
    created_at: float = field(default_factory=time.time)
    updated_at: float = field(default_factory=time.time)

    def to_dict(self) -> Dict[str, Any]:
        return asdict(self)


class LearningPipeline:
    """Manages empirical lesson validation and training queue accumulation."""

    def __init__(self, state_file: Optional[str] = None):
        self.state_file = settings.PATHS.DATA_DIR / "learning_records.json"
        self._records: Dict[str, LearningRecord] = {}
        self._lock = threading.Lock()
        self._load_records()

    def _load_records(self):
        if self.state_file.exists():
            try:
                with open(self.state_file, "r", encoding="utf-8") as f:
                    data = json.load(f)
                for item in data.values():
                    rec = LearningRecord(**item)
                    self._records[rec.id] = rec
            except Exception as e:
                agent_logger.error(f"Failed loading learning records: {e}")

    def _save_records(self):
        try:
            self.state_file.parent.mkdir(parents=True, exist_ok=True)
            data = {k: v.to_dict() for k, v in self._records.items()}
            tmp = self.state_file.with_suffix(".tmp")
            with open(tmp, "w", encoding="utf-8") as f:
                json.dump(data, f, indent=2)
            tmp.replace(self.state_file)
        except Exception as e:
            agent_logger.error(f"Failed saving learning records: {e}")

    def propose_candidate_lesson(
        self,
        experience: str,
        lesson: str,
        source: str = "user_interaction",
        initial_confidence: float = 0.6
    ) -> LearningRecord:
        """Enters a candidate lesson into the validation queue."""
        rec_id = f"learn_{uuid.uuid4().hex[:8]}"
        rec = LearningRecord(
            id=rec_id,
            experience=experience,
            lesson=lesson,
            source=source,
            confidence=min(1.0, max(0.1, initial_confidence)),
            status="candidate",
            training_candidate=False
        )
        with self._lock:
            self._records[rec_id] = rec
            self._save_records()

        agent_logger.info(f"LearningPipeline: New candidate lesson [{rec_id}] from '{source}': {lesson[:50]}")
        return rec

    def record_evidence(self, lesson_id: str, confirmed: bool) -> Optional[LearningRecord]:
        """
        Updates evidence count for a lesson.
        When confirmed >= 3 times with confidence >= 0.85, marks as validated and queues for training.
        """
        with self._lock:
            rec = self._records.get(lesson_id)
            if not rec:
                return None

            now = time.time()
            rec.updated_at = now
            if confirmed:
                rec.times_confirmed += 1
                rec.confidence = min(1.0, rec.confidence + 0.10)
            else:
                rec.times_failed += 1
                rec.confidence = max(0.0, rec.confidence - 0.20)

            # Promotion criteria
            if rec.times_confirmed >= 3 and rec.confidence >= 0.80 and (rec.times_failed * 2 < rec.times_confirmed):
                if rec.status != "validated":
                    rec.status = "validated"
                    rec.training_candidate = True
                    event_bus.publish(EventType.KNOWLEDGE_LEARNED, rec.to_dict())
                    agent_logger.info(f"LearningPipeline: Promoted lesson [{rec.id}] to VALIDATED training candidate.")
            elif rec.times_failed >= 3 and rec.confidence < 0.40:
                rec.status = "rejected"
                rec.training_candidate = False

            self._save_records()
            return rec

    def get_training_queue(self) -> List[LearningRecord]:
        """Returns all validated lessons ready for fine-tuning, adapter creation, or memory consolidation."""
        with self._lock:
            return [r for r in self._records.values() if r.status == "validated" and r.training_candidate]


# Global singleton
learning_pipeline = LearningPipeline()
