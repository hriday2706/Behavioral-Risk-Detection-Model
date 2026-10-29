"""
Unit tests for SentinelFlow Model Inference Pipeline.
"""

from datetime import datetime, timedelta, timezone
import pytest
from config import ALL_RISK_CLASSES, RISK_HIGH, RISK_LOW, RISK_MEDIUM
from src.event_schema import EventType, SessionEvent
from src.inference import RiskInferenceEngine


@pytest.fixture
def engine():
    return RiskInferenceEngine.get_instance()


def test_empty_session_inference(engine):
    res = engine.assess_session([])
    assert res["predicted_class"] == RISK_LOW
    assert "class_probabilities" in res
    assert res["is_simulated_context"] is True


def test_routine_session_inference(engine):
    t0 = datetime(2026, 3, 10, 14, 0, 0, tzinfo=timezone.utc)
    events = [
        SessionEvent.create("sess_r", "u1", EventType.SESSION_STARTED.value, timestamp_utc=t0.isoformat(), device_familiarity="familiar"),
        SessionEvent.create("sess_r", "u1", EventType.LOGIN_SUCCESS.value, timestamp_utc=(t0 + timedelta(seconds=12)).isoformat(), device_familiarity="familiar"),
        SessionEvent.create("sess_r", "u1", EventType.BALANCE_VIEWED.value, timestamp_utc=(t0 + timedelta(seconds=35)).isoformat(), device_familiarity="familiar"),
    ]
    res = engine.assess_session(events)
    assert res["predicted_class"] == RISK_LOW
    assert res["risk_policy"]["action_allowed"] is True
    assert res["risk_policy"]["requires_step_up"] is False


def test_elevated_risk_session_triggers_verification(engine):
    t0 = datetime(2026, 3, 10, 2, 0, 0, tzinfo=timezone.utc)
    events = [
        SessionEvent.create("sess_h", "u2", EventType.SESSION_STARTED.value, timestamp_utc=t0.isoformat(), device_familiarity="unfamiliar"),
        SessionEvent.create("sess_h", "u2", EventType.LOGIN_FAILURE.value, timestamp_utc=(t0 + timedelta(seconds=1.2)).isoformat(), device_familiarity="unfamiliar"),
        SessionEvent.create("sess_h", "u2", EventType.LOGIN_FAILURE.value, timestamp_utc=(t0 + timedelta(seconds=2.4)).isoformat(), device_familiarity="unfamiliar"),
        SessionEvent.create("sess_h", "u2", EventType.LOGIN_FAILURE.value, timestamp_utc=(t0 + timedelta(seconds=3.8)).isoformat(), device_familiarity="unfamiliar"),
        SessionEvent.create("sess_h", "u2", EventType.LOGIN_SUCCESS.value, timestamp_utc=(t0 + timedelta(seconds=5.5)).isoformat(), device_familiarity="unfamiliar"),
        SessionEvent.create("sess_h", "u2", EventType.PASSWORD_CHANGE_REQUESTED.value, timestamp_utc=(t0 + timedelta(seconds=12.0)).isoformat(), device_familiarity="unfamiliar"),
    ]
    res = engine.assess_session(events, target_action=EventType.PASSWORD_CHANGE_REQUESTED.value, is_verified_in_session=False)
    assert res["predicted_class"] == RISK_HIGH
    assert res["risk_policy"]["action_allowed"] is False
    assert res["risk_policy"]["requires_step_up"] is True
    assert res["risk_policy"]["status"] == "verification_required"

    # Now verify that when verified, policy allows action
    res_verified = engine.assess_session(events, target_action=EventType.PASSWORD_CHANGE_REQUESTED.value, is_verified_in_session=True)
    assert res_verified["risk_policy"]["action_allowed"] is True
    assert res_verified["risk_policy"]["requires_step_up"] is False
