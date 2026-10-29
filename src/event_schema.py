"""
SentinelFlow Event Schema and Validation Module.
Defines canonical event types, sensitive actions, and schema validation
for server-recorded session events.
"""

from dataclasses import dataclass, field
from datetime import datetime, timezone
from enum import Enum
from typing import Any, Dict, List, Optional
import uuid


class EventType(str, Enum):
    LOGIN_ATTEMPT = "login_attempt"
    LOGIN_SUCCESS = "login_success"
    LOGIN_FAILURE = "login_failure"
    SESSION_STARTED = "session_started"
    BALANCE_VIEWED = "balance_viewed"
    STATEMENT_DOWNLOADED = "statement_downloaded"
    PASSWORD_CHANGE_REQUESTED = "password_change_requested"
    EMAIL_UPDATE_REQUESTED = "email_update_requested"
    STEP_UP_REQUESTED = "step_up_requested"
    STEP_UP_SUCCEEDED = "step_up_succeeded"
    STEP_UP_FAILED = "step_up_failed"
    LOGOUT = "logout"


# Set of actions considered sensitive and requiring strict evaluation
SENSITIVE_ACTIONS = frozenset({
    EventType.PASSWORD_CHANGE_REQUESTED.value,
    EventType.EMAIL_UPDATE_REQUESTED.value,
})

# Allowed device familiarity values
DEVICE_FAMILIARITY_VALUES = frozenset({"familiar", "unfamiliar", "unknown"})


@dataclass(frozen=True)
class SessionEvent:
    event_id: str
    session_id: str
    user_id: str
    event_type: str
    timestamp_utc: str
    success: bool = True
    device_familiarity: str = "familiar"
    location_context: str = "home"
    metadata: Dict[str, Any] = field(default_factory=dict)

    @classmethod
    def create(
        cls,
        session_id: str,
        user_id: str,
        event_type: str,
        timestamp_utc: Optional[str] = None,
        success: bool = True,
        device_familiarity: str = "familiar",
        location_context: str = "home",
        metadata: Optional[Dict[str, Any]] = None,
        event_id: Optional[str] = None,
    ) -> "SessionEvent":
        """Factory method with automatic validation and UTC timestamp generation."""
        if not event_id:
            event_id = str(uuid.uuid4())

        if not timestamp_utc:
            timestamp_utc = datetime.now(timezone.utc).isoformat()

        instance = cls(
            event_id=str(event_id),
            session_id=str(session_id),
            user_id=str(user_id),
            event_type=str(event_type),
            timestamp_utc=str(timestamp_utc),
            success=bool(success),
            device_familiarity=str(device_familiarity).lower(),
            location_context=str(location_context),
            metadata=metadata or {},
        )
        instance.validate()
        return instance

    def validate(self) -> None:
        """Validate integrity constraints and allowed enum types."""
        if not self.event_id or not self.event_id.strip():
            raise ValueError("event_id must not be empty.")
        if not self.session_id or not self.session_id.strip():
            raise ValueError("session_id must not be empty.")
        if not self.user_id or not self.user_id.strip():
            raise ValueError("user_id must not be empty.")

        allowed_events = {e.value for e in EventType}
        if self.event_type not in allowed_events:
            raise ValueError(f"Invalid event_type '{self.event_type}'. Allowed types: {sorted(allowed_events)}")

        if self.device_familiarity not in DEVICE_FAMILIARITY_VALUES:
            raise ValueError(
                f"Invalid device_familiarity '{self.device_familiarity}'. Allowed: {sorted(DEVICE_FAMILIARITY_VALUES)}"
            )

        # Validate timestamp format (ISO 8601 UTC)
        try:
            cleaned = self.timestamp_utc.replace("Z", "+00:00")
            datetime.fromisoformat(cleaned)
        except Exception as exc:
            raise ValueError(f"Invalid timestamp_utc format '{self.timestamp_utc}': must be ISO 8601.") from exc

    def to_dict(self) -> Dict[str, Any]:
        """Convert event to serializable dictionary."""
        return {
            "event_id": self.event_id,
            "session_id": self.session_id,
            "user_id": self.user_id,
            "event_type": self.event_type,
            "timestamp_utc": self.timestamp_utc,
            "success": self.success,
            "device_familiarity": self.device_familiarity,
            "location_context": self.location_context,
            "metadata": self.metadata,
        }

    @classmethod
    def from_dict(cls, data: Dict[str, Any]) -> "SessionEvent":
        """Reconstruct a SessionEvent from dictionary data."""
        return cls.create(
            event_id=data.get("event_id"),
            session_id=data["session_id"],
            user_id=data["user_id"],
            event_type=data["event_type"],
            timestamp_utc=data.get("timestamp_utc"),
            success=data.get("success", True),
            device_familiarity=data.get("device_familiarity", "familiar"),
            location_context=data.get("location_context", "home"),
            metadata=data.get("metadata", {}),
        )

    @property
    def is_sensitive(self) -> bool:
        """Returns True if the event represents a sensitive action request."""
        return self.event_type in SENSITIVE_ACTIONS
