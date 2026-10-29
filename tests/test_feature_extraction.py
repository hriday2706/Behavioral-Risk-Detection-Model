"""
Unit tests for SentinelFlow Feature Extraction Module.
"""

from datetime import datetime, timezone, timedelta
import pytest
from src.event_schema import EventType, SessionEvent
from src.feature_extraction import extract_session_features, features_to_vector
from config import FEATURE_COLUMNS


def test_empty_session_features():
    features = extract_session_features([])
    assert features["login_attempt_count"] == 0.0
    assert features["login_failure_rate"] == 0.0
    assert features["session_duration_sec"] == -1.0
    assert features["median_login_interval_sec"] == -1.0


def test_single_login_attempt():
    t0 = datetime(2026, 3, 15, 12, 0, 0, tzinfo=timezone.utc)
    ev = SessionEvent.create(
        session_id="s1",
        user_id="u1",
        event_type=EventType.LOGIN_SUCCESS.value,
        timestamp_utc=t0.isoformat()
    )
    features = extract_session_features([ev])
    assert features["login_attempt_count"] == 1.0
    assert features["login_failure_count"] == 0.0
    assert features["login_failure_rate"] == 0.0
    assert features["median_login_interval_sec"] == -1.0
    assert features["session_duration_sec"] == 0.0


def test_multiple_login_attempts_intervals():
    t0 = datetime(2026, 3, 15, 12, 0, 0, tzinfo=timezone.utc)
    t1 = t0 + timedelta(seconds=2)
    t2 = t1 + timedelta(seconds=8)

    events = [
        SessionEvent.create(session_id="s2", user_id="u1", event_type=EventType.LOGIN_FAILURE.value, timestamp_utc=t0.isoformat()),
        SessionEvent.create(session_id="s2", user_id="u1", event_type=EventType.LOGIN_FAILURE.value, timestamp_utc=t1.isoformat()),
        SessionEvent.create(session_id="s2", user_id="u1", event_type=EventType.LOGIN_SUCCESS.value, timestamp_utc=t2.isoformat()),
    ]
    features = extract_session_features(events)
    assert features["login_attempt_count"] == 3.0
    assert features["login_failure_count"] == 2.0
    assert round(features["login_failure_rate"], 2) == 0.67
    assert features["min_login_interval_sec"] == 2.0
    # intervals are 2.0 and 8.0, median is (2+8)/2 = 5.0
    assert features["median_login_interval_sec"] == 5.0


def test_sensitive_action_and_rapid_security_change():
    t0 = datetime(2026, 3, 15, 12, 0, 0, tzinfo=timezone.utc)
    t_login = t0 + timedelta(seconds=5)
    t_pwd = t_login + timedelta(seconds=25)  # 25 seconds after login (< 120s)

    events = [
        SessionEvent.create(session_id="s3", user_id="u1", event_type=EventType.LOGIN_SUCCESS.value, timestamp_utc=t_login.isoformat()),
        SessionEvent.create(session_id="s3", user_id="u1", event_type=EventType.PASSWORD_CHANGE_REQUESTED.value, timestamp_utc=t_pwd.isoformat()),
    ]
    features = extract_session_features(events)
    assert features["sensitive_action_count"] == 1.0
    assert features["time_to_first_sensitive_action_sec"] == 25.0
    assert features["security_change_after_login_flag"] == 1.0


def test_unsorted_events_handled_deterministically():
    t0 = datetime(2026, 3, 15, 12, 0, 0, tzinfo=timezone.utc)
    t1 = t0 + timedelta(seconds=10)
    t2 = t0 + timedelta(seconds=20)

    e0 = SessionEvent.create(session_id="s4", user_id="u1", event_type=EventType.LOGIN_SUCCESS.value, timestamp_utc=t0.isoformat())
    e1 = SessionEvent.create(session_id="s4", user_id="u1", event_type=EventType.BALANCE_VIEWED.value, timestamp_utc=t1.isoformat())
    e2 = SessionEvent.create(session_id="s4", user_id="u1", event_type=EventType.STATEMENT_DOWNLOADED.value, timestamp_utc=t2.isoformat())

    # Pass in shuffled order
    features = extract_session_features([e2, e0, e1])
    assert features["session_duration_sec"] == 20.0
    assert features["login_attempt_count"] == 1.0


def test_evaluation_cutoff_prevents_leakage():
    t0 = datetime(2026, 3, 15, 12, 0, 0, tzinfo=timezone.utc)
    t1 = t0 + timedelta(seconds=30)
    t2_future = t0 + timedelta(seconds=90)

    e0 = SessionEvent.create(session_id="s5", user_id="u1", event_type=EventType.LOGIN_SUCCESS.value, timestamp_utc=t0.isoformat())
    e1 = SessionEvent.create(session_id="s5", user_id="u1", event_type=EventType.BALANCE_VIEWED.value, timestamp_utc=t1.isoformat())
    e2_future = SessionEvent.create(session_id="s5", user_id="u1", event_type=EventType.PASSWORD_CHANGE_REQUESTED.value, timestamp_utc=t2_future.isoformat())

    # Cutoff at t1 (seconds=30)
    features_at_t1 = extract_session_features([e0, e1, e2_future], evaluation_time=t1)
    assert features_at_t1["sensitive_action_count"] == 0.0
    assert features_at_t1["security_change_after_login_flag"] == 0.0
    assert features_at_t1["session_duration_sec"] == 30.0


def test_features_to_vector_shape():
    features = extract_session_features([])
    vector = features_to_vector(features)
    assert len(vector) == len(FEATURE_COLUMNS)
