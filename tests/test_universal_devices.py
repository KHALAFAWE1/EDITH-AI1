import pytest
from fastapi.testclient import TestClient
from server.app.main import app

client = TestClient(app)


def test_host_telemetry_and_processes():
    # 1. Host Telemetry
    res = client.get("/devices/telemetry")
    assert res.status_code == 200
    data = res.json()
    assert "cpu" in data
    assert "ram" in data
    assert "storage" in data
    assert "hostname" in data
    assert data["status"] == "Online"

    # 2. Host Processes
    proc_res = client.get("/devices/processes?limit=10&sort_by=cpu")
    assert proc_res.status_code == 200
    proc_data = proc_res.json()
    assert "processes" in proc_data
    assert "total_active_processes" in proc_data
    assert len(proc_data["processes"]) <= 10


def test_universal_device_registration():
    # Direct Device Registration
    reg_payload = {
        "device_name": "Test Engineering Laptop",
        "device_type": "LAPTOP",
        "platform": "Linux",
        "operating_system": "Ubuntu 22.04",
        "browser": "Firefox 122",
        "client_version": "2.5.0",
        "capabilities": {
            "camera": True,
            "microphone": True,
            "speaker": True,
            "battery": False,
            "touch": False,
            "websocket": True
        }
    }
    res = client.post("/devices/register", json=reg_payload)
    assert res.status_code == 200
    data = res.json()
    assert data["success"] is True
    assert "device_id" in data
    assert "auth_token" in data
    assert data["status"] == "ENROLLED"
    device_id = data["device_id"]
    auth_token = data["auth_token"]

    # Query device by ID
    get_res = client.get(f"/devices/{device_id}")
    assert get_res.status_code == 200
    dev_data = get_res.json()
    assert dev_data["device_name"] == "Test Engineering Laptop"
    assert dev_data["platform"] == "Linux"
    assert dev_data["capabilities"]["camera"] is True

    # Send Heartbeat
    hb_res = client.post(
        f"/devices/{device_id}/heartbeat",
        json={"auth_token": auth_token, "battery_level": 85, "battery_charging": True}
    )
    assert hb_res.status_code == 200
    assert hb_res.json()["status"] == "ONLINE"

    # Check capabilities endpoint
    cap_res = client.get(f"/devices/{device_id}/capabilities")
    assert cap_res.status_code == 200
    assert cap_res.json()["capabilities"]["microphone"] is True


def test_pairing_flow_and_claim():
    # 1. Generate Ephemeral Pairing QR / Token
    gen_res = client.post("/devices/pairing/generate", json={"device_type": "PHONE"})
    assert gen_res.status_code == 200
    gen_data = gen_res.json()
    assert "pairing_token" in gen_data
    assert "pairing_url" in gen_data
    assert gen_data["expires_in_seconds"] == 300
    token = gen_data["pairing_token"]

    # 2. Claim Pairing Token from Mobile Client
    claim_payload = {
        "pairing_token": token,
        "device_name": "Field iPhone Companion",
        "device_type": "PHONE",
        "platform": "iOS",
        "operating_system": "iOS 17.4",
        "browser": "Mobile Safari",
        "capabilities": {
            "camera": True,
            "microphone": True,
            "hud": True,
            "battery": True
        },
        "battery_level": 92,
        "battery_charging": False
    }
    claim_res = client.post("/devices/pairing/claim", json=claim_payload)
    assert claim_res.status_code == 200
    claim_data = claim_res.json()
    assert claim_data["success"] is True
    assert "device_id" in claim_data
    assert "auth_token" in claim_data
    assert claim_data["device_name"] == "Field iPhone Companion"
    device_id = claim_data["device_id"]

    # 3. Attempting to claim the same token again must fail (Single-use security)
    replay_res = client.post("/devices/pairing/claim", json=claim_payload)
    assert replay_res.status_code == 400


def test_command_allowlist_and_revocation():
    # Register temporary device
    reg_res = client.post("/devices/register", json={
        "device_name": "Temporary Target Node",
        "device_type": "SMART_GLASSES",
        "platform": "Universal"
    })
    assert reg_res.status_code == 200
    device_id = reg_res.json()["device_id"]

    # Test Allowlisted Command (PING)
    cmd_res = client.post(f"/devices/{device_id}/command", json={"command": "PING"})
    assert cmd_res.status_code == 200
    # Returns offline if no active WS connection is established yet
    assert "message" in cmd_res.json()

    # Test Unauthorized Command Rejection
    bad_cmd_res = client.post(f"/devices/{device_id}/command", json={"command": "EXECUTE_ARBITRARY_CODE"})
    assert bad_cmd_res.status_code == 400

    # Test Device Revocation / Deletion
    del_res = client.delete(f"/devices/{device_id}")
    assert del_res.status_code == 200
    assert del_res.json()["success"] is True

    # Verify device is no longer found
    check_res = client.get(f"/devices/{device_id}")
    assert check_res.status_code == 404
