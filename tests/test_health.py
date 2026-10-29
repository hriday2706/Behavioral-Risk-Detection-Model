"""
Unit tests for SentinelFlow API health endpoint (M1 acceptance check).
"""

import pytest
from app import create_app


@pytest.fixture
def client():
    app = create_app({"TESTING": True})
    with app.test_client() as client:
        yield client


def test_health_endpoint(client):
    response = client.get("/api/health")
    assert response.status_code == 200
    json_data = response.get_json()
    assert json_data["status"] == "healthy"
    assert "service" in json_data
    assert json_data["policy_version"] == "demo-policy-v1"
