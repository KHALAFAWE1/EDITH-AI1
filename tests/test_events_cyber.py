import pytest
from fastapi.testclient import TestClient
from server.app.main import app

client = TestClient(app)


def test_timeline_events_and_stats():
    # Test Stats
    stats_res = client.get("/events/stats")
    assert stats_res.status_code == 200
    assert "total_events" in stats_res.json()
    assert "baseline_conformity_percent" in stats_res.json()

    # Test Logging an Event
    log_res = client.post("/events", json={
        "event_type": "TEST_OPTICAL_TRIGGER",
        "source": "OPTICAL_SENSOR",
        "location_name": "Sector B",
        "summary": "Automated QA Test Event",
        "severity": "INFO"
    })
    assert log_res.status_code == 200
    assert log_res.json()["success"] is True

    # Test Timeline Query
    timeline_res = client.get("/events?limit=10")
    assert timeline_res.status_code == 200
    events = timeline_res.json()
    assert isinstance(events, list)
    assert len(events) >= 1


def test_cyber_nodes_and_correlation():
    # Test Nodes
    nodes_res = client.get("/cyber/nodes")
    assert nodes_res.status_code == 200
    nodes = nodes_res.json()
    assert isinstance(nodes, list)

    # Test Correlation Engine
    corr_res = client.get("/cyber/correlate")
    assert corr_res.status_code == 200
    assert "correlation_active" in corr_res.json()
