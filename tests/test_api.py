"""
Integration tests for SentinelFlow REST API endpoints.
"""

import json
import pytest
from app import create_app
from backend.database import init_db
from config import DATABASE_PATH


@pytest.fixture
def client():
    app = create_app({"TESTING": True})
    with app.test_client() as client:
        yield client


def test_api_health(client):
    res = client.get("/api/health")
    assert res.status_code == 200
    data = res.get_json()
    assert data["status"] == "healthy"


def test_demo_login_and_summary(client):
    res = client.post("/api/demo/login", json={
        "username": "alex_demo",
        "device_familiarity": "familiar",
        "location_context": "home"
    })
    assert res.status_code == 200
    data = res.get_json()
    assert "session" in data
    assert "events" in data
    assert "risk_assessment" in data
    assert data["session"]["username"] == "alex_demo"
    assert len(data["events"]) >= 2  # session_started and login_success


def test_non_sensitive_actions(client):
    # View balance
    res_bal = client.post("/api/actions/balance")
    assert res_bal.status_code == 200
    data_bal = res_bal.get_json()
    assert data_bal["status"] == "success"
    assert data_bal["balance"] > 0

    # Download statement
    res_stmt = client.post("/api/actions/statement")
    assert res_stmt.status_code == 200
    data_stmt = res_stmt.get_json()
    assert data_stmt["status"] == "success"


def test_scenario_b_blocks_sensitive_action_and_unlocked_by_verification(client):
    # Load Scenario B (Elevated Risk)
    res_load = client.post("/api/demo/load-scenario", json={"scenario": "B"})
    assert res_load.status_code == 200
    data_load = res_load.get_json()
    assert data_load["summary"]["risk_assessment"]["predicted_class"] == "high"

    # Try sensitive action (Password change)
    res_sec = client.post("/api/actions/security-change", json={"change_type": "password"})
    # Must be blocked by backend policy with 403
    assert res_sec.status_code == 403
    data_sec = res_sec.get_json()
    assert data_sec["status"] == "blocked"
    assert data_sec["requires_step_up"] is True

    # Request step-up challenge
    res_req = client.post("/api/verification/request")
    assert res_req.status_code == 200
    chal = res_req.get_json()
    assert chal["demo_code"] == "123456"

    # Fail verification with wrong code
    res_fail = client.post("/api/verification/complete", json={"code": "000000"})
    assert res_fail.status_code == 400

    # Complete verification with correct code
    res_ok = client.post("/api/verification/complete", json={"code": "123456"})
    assert res_ok.status_code == 200
    assert res_ok.get_json()["success"] is True

    # Retry sensitive action - now allowed!
    res_sec_unlocked = client.post("/api/actions/security-change", json={"change_type": "password"})
    assert res_sec_unlocked.status_code == 200
    assert res_sec_unlocked.get_json()["status"] == "success"


def test_scenario_a_routine_session(client):
    res = client.post("/api/demo/load-scenario", json={"scenario": "A"})
    assert res.status_code == 200
    data = res.get_json()
    assert data["summary"]["risk_assessment"]["predicted_class"] == "low"
    assert data["summary"]["risk_assessment"]["risk_policy"]["action_allowed"] is True


def test_scenario_c_ambiguous_session(client):
    res = client.post("/api/demo/load-scenario", json={"scenario": "C"})
    assert res.status_code == 200
    data = res.get_json()
    # Ambiguous session has unfamiliar device flag, but ordinary action profile
    assert data["summary"]["risk_assessment"]["is_simulated_context"] is True


def test_model_info_endpoint(client):
    res = client.get("/api/model/info")
    assert res.status_code == 200
    meta = res.get_json()
    assert meta["model_name"] == "SentinelFlow Explainable Decision Tree"
    assert "test_metrics" in meta
    assert "classes" in meta
