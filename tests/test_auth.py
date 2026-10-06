import pytest
from fastapi.testclient import TestClient
from server.app.main import app

client = TestClient(app)


def test_health_check():
    response = client.get("/api/health")
    assert response.status_code == 200
    data = response.json()
    assert data["status"] == "online"
    assert "EDITH AI" in data["system"]


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
