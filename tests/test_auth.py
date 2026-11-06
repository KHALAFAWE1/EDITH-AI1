import pytest
from fastapi.testclient import TestClient
from server.app.main import app

client = TestClient(app)


def test_health_check():
    response = client.get("/api/health")
    assert response.status_code == 200
    data = response.json()
    assert data["status"] == "online"
    assert "TARS AI" in data["system"]
    assert data["assistant"] == "TARS"
    assert "database_connected" in data
    assert "recognition_service" in data


def test_auth_login_failed():
    response = client.post("/auth/login", json={"username": "nonexistent_user", "password": "wrongpassword"})
    assert response.status_code == 401
    assert "detail" in response.json()


def test_auth_get_me():
    response = client.get("/auth/me")
    assert response.status_code == 200
    data = response.json()
    assert "username" in data
    assert "role" in data


def test_tars_personality_matrix():
    # 1. Read default/current personality
    get_res = client.get("/ai/personality")
    assert get_res.status_code == 200
    p_data = get_res.json()
    assert "humor" in p_data
    assert "honesty" in p_data
    assert "directness" in p_data
    assert "professionalism" in p_data

    # 2. Update personality sliders
    update_res = client.post(
        "/ai/personality",
        json={"humor": 75, "honesty": 90, "directness": 85, "professionalism": 90}
    )
    assert update_res.status_code == 200
    updated = update_res.json()
    assert updated["success"] is True
    assert updated["personality"]["humor"] == 75
    assert updated["personality"]["honesty"] == 90


def test_tars_chat_response():
    res = client.post(
        "/ai/chat",
        json={
            "prompt": "Report system status and telemetry",
            "history": [],
            "personality": {"humor": 75, "honesty": 90, "directness": 85, "professionalism": 90}
        }
    )
    assert res.status_code == 200
    data = res.json()
    assert "reply" in data
    assert len(data["reply"]) > 0
