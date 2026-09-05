"""
REN Autonomous Initiative Engine
Decides when and how REN should take proactive action without waiting for user prompts.
Enforces strict anti-spam rules: cooldowns, hourly rate limits, importance scoring,
duplicate suppression, quiet hours, and external permission checks.
"""

import time
import threading
from datetime import datetime
from typing import Optional, Dict, Any, List, Tuple

from ren.config.settings import settings
from ren.autonomy.store import autonomous_store, AutonomousMessage
from ren.core.events import event_bus, EventType
from ren.security.permissions import permission_manager, PermissionCategory, PermissionRisk
from ren.monitoring.logger import agent_logger, error_logger


class AutonomyEngine:
    """Evaluates triggers and coordinates proactive autonomous communications."""

    def __init__(self):
        self._lock = threading.Lock()
        self._last_message_time: float = 0.0
        self._hourly_messages: List[float] = []
        self._is_running: bool = False
        self._worker_thread: Optional[threading.Thread] = None

    @property
    def is_enabled(self) -> bool:
        return settings.AUTONOMY.ENABLED

    def set_enabled(self, enabled: bool) -> None:
        settings.AUTONOMY.ENABLED = enabled
        agent_logger.info(f"AutonomyEngine: enabled={enabled}")

    def is_quiet_hours(self) -> bool:
        """Checks if current time falls within configured quiet hours."""
        if not settings.AUTONOMY.QUIET_HOURS_ENABLED:
            return False
        current_hour = datetime.now().hour
        start = settings.AUTONOMY.QUIET_HOURS_START
        end = settings.AUTONOMY.QUIET_HOURS_END
        if start > end:  # Wraps around midnight (e.g. 23:00 to 07:00)
            return current_hour >= start or current_hour < end
        return start <= current_hour < end

    def can_initiate_message(self, importance: float, curiosity: float) -> Tuple[bool, str]:
        """
        Evaluates whether an autonomous proactive message is allowed to proceed.
        Returns: (allowed: bool, reason: str)
        """
        if not self.is_enabled:
            return False, "Autonomous engine is disabled in settings."

        if self.is_quiet_hours():
            return False, "Currently in quiet hours."

        # Threshold checks
        if importance < settings.AUTONOMY.MIN_IMPORTANCE_THRESHOLD:
            return False, f"Importance {importance:.2f} is below threshold {settings.AUTONOMY.MIN_IMPORTANCE_THRESHOLD:.2f}"

        if curiosity < settings.AUTONOMY.MIN_CURIOSITY_THRESHOLD:
            return False, f"Curiosity {curiosity:.2f} is below threshold {settings.AUTONOMY.MIN_CURIOSITY_THRESHOLD:.2f}"

        now = time.time()
        with self._lock:
            # Cooldown check
            elapsed = now - self._last_message_time
            if elapsed < settings.AUTONOMY.COOLDOWN_SECONDS:
                remaining = int(settings.AUTONOMY.COOLDOWN_SECONDS - elapsed)
                return False, f"Autonomous cooldown active ({remaining}s remaining)."

            # Hourly rate limit check
            self._hourly_messages = [t for t in self._hourly_messages if (now - t) < 3600]
            if len(self._hourly_messages) >= settings.AUTONOMY.MAX_MESSAGES_PER_HOUR:
                return False, f"Hourly message limit reached ({settings.AUTONOMY.MAX_MESSAGES_PER_HOUR}/hr)."

        return True, "Approved"

    def propose_initiative(
        self,
        content: str,
        source: str = "dream",
        importance: float = 0.8,
        curiosity_score: float = 0.8,
        reason: str = "Proactive suggestion",
        title: str = "Autonomous Insight",
    ) -> Optional[AutonomousMessage]:
        """
        Complete Autonomous Lifecycle:
        1. Evaluate Policy & Anti-Spam Gate
        2. Duplicate Prevention Check
        3. Permission Policy Gate
        4. Store & Publish to EventBus
        """
        allowed, gate_reason = self.can_initiate_message(importance, curiosity_score)
        if not allowed:
            agent_logger.debug(f"AutonomyEngine: Initiative suppressed: {gate_reason}")
            return None

        # Duplicate check
        if autonomous_store.has_similar_recent_message(content):
            agent_logger.debug("AutonomyEngine: Initiative suppressed due to duplicate content.")
            return None

        # External Permission Policy check (LLM cannot bypass permission manager)
        perm_check = permission_manager.evaluate_permissions(
            required_permissions=[PermissionCategory.NETWORK_REQUEST],
            operation_desc=f"Autonomous message from {source}: '{title}'"
        )
        if not perm_check.allowed:
            agent_logger.warning(f"AutonomyEngine: Permission denied: {perm_check.reason}")
            return None

        now = time.time()
        with self._lock:
            self._last_message_time = now
            self._hourly_messages.append(now)

        # Store in persistent database
        msg = autonomous_store.store_message(
            content=content,
            source=source,
            importance=importance,
            curiosity_score=curiosity_score,
            reason=reason,
            title=title,
        )

        # Publish live event to EventBus for desktop & web subscribers
        event_bus.publish(EventType.POPUP_NOTIFICATION, {
            "type": "autonomous_message",
            "message_id": msg.message_id,
            "title": msg.title,
            "content": msg.content,
            "source": msg.source,
            "importance": msg.importance,
            "reason": msg.reason,
            "created_at": msg.created_at,
        })

        agent_logger.info(f"AutonomyEngine: Dispatched proactive message [{msg.message_id}]: {title}")
        return msg

    def run_inspection_cycle(self):
        """Inspects unresolved work, errors, and project state to evaluate proactive initiatives."""
        if not self.is_enabled:
            return

        # Check for unresolved exceptions
        err_file = settings.PATHS.ERROR_LOG_FILE
        if err_file.exists():
            try:
                import json
                with open(err_file, "r", encoding="utf-8") as f:
                    errors = json.load(f)
                if errors and len(errors) >= 3:
                    self.propose_initiative(
                        content=f"I noticed {len(errors)} unresolved exceptions in the system log. Would you like me to inspect and diagnose the root cause?",
                        source="system_diagnostics",
                        importance=0.85,
                        curiosity_score=0.80,
                        reason="Multiple system exceptions detected in error_log.json",
                        title="System Diagnostics Alert"
                    )
            except Exception:
                pass

    def trigger_task_completed(self, task_id: str, description: str, result: str = "") -> Optional[AutonomousMessage]:
        """Proactive alert when an important background task completes."""
        return self.propose_initiative(
            content=f"Task completed: '{description}'. {result}".strip(),
            source="task_scheduler",
            importance=0.85,
            curiosity_score=0.75,
            reason=f"Task {task_id} completed",
            title="Important Task Completed"
        )

    def trigger_useful_discovery(self, topic: str, summary: str, confidence: float = 0.85) -> Optional[AutonomousMessage]:
        """Proactive alert when a useful discovery or pattern is identified."""
        return self.propose_initiative(
            content=f"Discovery on {topic}: {summary}",
            source="knowledge_discovery",
            importance=confidence,
            curiosity_score=0.90,
            reason="Useful knowledge discovery",
            title=f"Discovery: {topic}"
        )

    def trigger_project_issue(self, project_name: str, issue_desc: str, urgency: float = 0.88) -> Optional[AutonomousMessage]:
        """Proactive alert when a project anomaly or issue is detected."""
        return self.propose_initiative(
            content=f"Issue detected in project '{project_name}': {issue_desc}",
            source="project_monitor",
            importance=urgency,
            curiosity_score=0.80,
            reason="Project issue detected",
            title=f"Project Alert: {project_name}"
        )

    def trigger_dream_result(self, summary: str, insights_count: int = 1) -> Optional[AutonomousMessage]:
        """Proactive alert summarizing key insights from Dream Mode."""
        return self.propose_initiative(
            content=f"Dream cycle concluded with {insights_count} new insights: {summary}",
            source="dream_engine",
            importance=0.82,
            curiosity_score=0.85,
            reason="Dream Mode consolidation result",
            title="Dream Mode Report"
        )

    def trigger_device_issue(self, device_id: str, device_name: str, issue_desc: str) -> Optional[AutonomousMessage]:
        """Proactive alert when a device issue is detected (low battery, disconnected, etc.)."""
        return self.propose_initiative(
            content=f"Device notice for {device_name} ({device_id}): {issue_desc}",
            source="device_monitor",
            importance=0.86,
            curiosity_score=0.70,
            reason="Device state notice",
            title=f"Device Alert: {device_name}"
        )

    def trigger_reminder(self, reminder_text: str) -> Optional[AutonomousMessage]:
        """Proactive alert for configured reminders."""
        return self.propose_initiative(
            content=f"Scheduled reminder: {reminder_text}",
            source="reminder_service",
            importance=0.90,
            curiosity_score=0.70,
            reason="Configured user reminder",
            title="Reminder"
        )


# Global autonomy engine singleton
autonomy_engine = AutonomyEngine()
