"""
REN Transfer Engine
Extracts domain abstractions from project experiences and searches for cross-project application opportunities.
Stores validated abstractions separately from raw experiences with explicit confidence thresholds.
"""

import time
import uuid
from dataclasses import dataclass, field, asdict
from typing import List, Dict, Any, Optional
import threading

from ren.monitoring.logger import agent_logger
from ren.core.world_model import world_model


@dataclass
class DomainAbstraction:
    id: str
    concept: str
    source_context: str
    abstraction_rule: str
    confidence: float
    evidence: List[str] = field(default_factory=list)
    applicable_domains: List[str] = field(default_factory=list)
    created_at: float = field(default_factory=time.time)

    def to_dict(self) -> Dict[str, Any]:
        return asdict(self)


class TransferEngine:
    """Detects and transfers reusable procedural patterns across projects."""

    def __init__(self):
        self._abstractions: Dict[str, DomainAbstraction] = {}
        self._lock = threading.Lock()

    def extract_abstraction(
        self,
        concept: str,
        source_context: str,
        rule: str,
        confidence: float = 0.85,
        evidence: Optional[List[str]] = None,
        target_domains: Optional[List[str]] = None
    ) -> DomainAbstraction:
        """Stores a generalized procedural or design abstraction."""
        abs_id = f"abs_{uuid.uuid4().hex[:8]}"
        ab = DomainAbstraction(
            id=abs_id,
            concept=concept,
            source_context=source_context,
            abstraction_rule=rule,
            confidence=min(1.0, max(0.0, confidence)),
            evidence=evidence or [],
            applicable_domains=target_domains or []
        )
        with self._lock:
            self._abstractions[abs_id] = ab

        agent_logger.info(f"TransferEngine: Extracted abstraction [{concept}] from '{source_context}' (Confidence: {confidence:.2f})")
        return ab

    def search_transfer_opportunities(self, target_project_name: str) -> List[DomainAbstraction]:
        """Identifies reusable abstractions applicable to a given target project."""
        proj = world_model.get_project(target_project_name)
        if not proj:
            return []

        matched = []
        with self._lock:
            for ab in self._abstractions.values():
                if ab.confidence >= 0.70:
                    # Check domain or dependency relevance
                    if any(d.lower() in str(proj.dependencies).lower() or d.lower() in target_project_name.lower() for d in ab.applicable_domains):
                        matched.append(ab)
        return matched

    def list_abstractions(self) -> List[Dict[str, Any]]:
        with self._lock:
            return [a.to_dict() for a in self._abstractions.values()]


# Global singleton
transfer_engine = TransferEngine()
