"""
Unit tests for SentinelFlow Decision-Path Explanation Module.
"""

import pytest
import joblib
from config import MODEL_PATH
from src.explanations import explain_decision_path


@pytest.fixture
def model():
    return joblib.load(MODEL_PATH)


def test_decision_path_explanation_structure(model):
    # Dummy feature vector with high failures
    features = {
        "login_attempt_count": 5.0,
        "login_failure_count": 4.0,
        "login_failure_rate": 0.8,
        "median_login_interval_sec": 1.5,
        "min_login_interval_sec": 1.0,
        "session_duration_sec": 15.0,
        "sensitive_action_count": 1.0,
        "time_to_first_sensitive_action_sec": 8.0,
        "actions_last_60_sec": 6.0,
        "unfamiliar_device_flag": 1.0,
        "unusual_time_flag": 1.0,
        "location_anomaly_flag": 1.0,
        "security_change_after_login_flag": 1.0,
        "action_burst_count": 6.0,
    }
    explanation = explain_decision_path(model, features, predicted_class="high")
    assert explanation["predicted_class"] == "high"
    assert len(explanation["path_steps"]) > 0
    assert len(explanation["path_summary"]) > 0

    # Ensure every path step has required fields
    for step in explanation["path_steps"]:
        assert "feature" in step
        assert "threshold" in step
        assert "observed_value" in step
        assert "branch" in step
        assert "description" in step


def test_contextual_observations_separation(model):
    features = {
        "login_attempt_count": 1.0,
        "login_failure_count": 0.0,
        "login_failure_rate": 0.0,
        "median_login_interval_sec": -1.0,
        "min_login_interval_sec": -1.0,
        "session_duration_sec": 45.0,
        "sensitive_action_count": 0.0,
        "time_to_first_sensitive_action_sec": -1.0,
        "actions_last_60_sec": 2.0,
        "unfamiliar_device_flag": 0.0,
        "unusual_time_flag": 0.0,
        "location_anomaly_flag": 0.0,
        "security_change_after_login_flag": 0.0,
        "action_burst_count": 2.0,
    }
    explanation = explain_decision_path(model, features, predicted_class="low")
    assert explanation["predicted_class"] == "low"
    assert any("The model did not identify a high-risk pattern" in s for s in explanation["path_summary"])
    assert len(explanation["contextual_observations"]) > 0
