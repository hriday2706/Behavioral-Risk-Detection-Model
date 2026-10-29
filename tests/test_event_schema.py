"""
Unit tests for SentinelFlow Event Schema.
Verifies event validation, allowed types, sensitive action flags, and serialization.
"""

import pytest
from src.event_schema import EventType, SessionEvent, SENSITIVE_ACTIONS


def test_valid_event_creation():
    event = SessionEvent.create(
        session_id="sess-001",
        user_id="user-demo",
        event_type=EventType.LOGIN_SUCCESS.value,
        device_familiarity="familiar",
        location_context="home"
    )
    assert event.session_id == "sess-001"
    assert event.user_id == "user-demo"
    assert event.event_type == "login_success"
    assert event.is_sensitive is False
    assert event.success is True
    assert event.device_familiarity == "familiar"


def test_sensitive_action_detection():
    event_pwd = SessionEvent.create(
        session_id="sess-002",
        user_id="user-demo",
        event_type=EventType.PASSWORD_CHANGE_REQUESTED.value
    )
    assert event_pwd.is_sensitive is True
    assert event_pwd.event_type in SENSITIVE_ACTIONS

    event_email = SessionEvent.create(
        session_id="sess-002",
        user_id="user-demo",
        event_type=EventType.EMAIL_UPDATE_REQUESTED.value
    )
    assert event_email.is_sensitive is True

    event_bal = SessionEvent.create(
        session_id="sess-002",
        user_id="user-demo",
        event_type=EventType.BALANCE_VIEWED.value
    )
    assert event_bal.is_sensitive is False


def test_invalid_event_type_rejected():
    with pytest.raises(ValueError, match="Invalid event_type"):
        SessionEvent.create(
            session_id="sess-003",
            user_id="user-demo",
            event_type="hacked_account"
        )


def test_invalid_device_familiarity_rejected():
    with pytest.raises(ValueError, match="Invalid device_familiarity"):
        SessionEvent.create(
            session_id="sess-003",
            user_id="user-demo",
            event_type=EventType.LOGIN_ATTEMPT.value,
            device_familiarity="super_weird"
        )


def test_serialization_roundtrip():
    original = SessionEvent.create(
        session_id="sess-100",
        user_id="user-42",
        event_type=EventType.STATEMENT_DOWNLOADED.value,
        metadata={"file_format": "pdf"}
    )
    data = original.to_dict()
    reconstructed = SessionEvent.from_dict(data)

    assert reconstructed.event_id == original.event_id
    assert reconstructed.session_id == original.session_id
    assert reconstructed.event_type == original.event_type
    assert reconstructed.metadata == {"file_format": "pdf"}
