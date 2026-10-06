import pytest
from fastapi.testclient import TestClient
from server.app.main import app

client = TestClient(app)


def test_security_summary():
    response = client.get("/security/summary")
    assert response.status_code == 200
    data = response.json()
    assert "status" in data
    assert "security_score" in data
    assert data["status"] == "SHIELD_ACTIVE"


def test_security_audit_logs():
    response = client.get("/security/audit-logs")
    assert response.status_code == 200
    assert isinstance(response.json(), list)


def test_current_risk_assessment():
    response = client.get("/risk/current")
    assert response.status_code == 200
    data = response.json()
    assert "risk_score" in data
    assert "severity" in data
    assert "explainable_ai" in data
    assert "what" in data["explainable_ai"]
    assert "why" in data["explainable_ai"]
    assert "recommended_action" in data["explainable_ai"]


def test_custom_risk_evaluation():
    response = client.post("/risk/evaluate", json={
        "location": "Server Room",
        "detected_people_count": 2,
        "unidentified_faces": 1,
        "unknown_network_devices": 1,
        "anomaly_flag": True
    })
    assert response.status_code == 200
    data = response.json()
    assert data["risk_score"] > 50
    assert data["severity"] in ["HIGH", "CRITICAL"]
