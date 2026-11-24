import pytest
from fastapi.testclient import TestClient

def test_detections_and_incident_workflow(client: TestClient):
    # Setup test user and organization
    reg = client.post("/api/v1/auth/register", json={
        "email": "leadanalyst@defense.org",
        "password": "Password789!",
        "full_name": "Lead Analyst",
        "organization_name": "Incident Operations Wing"
    })
    token = reg.json()["access_token"]
    org_id = reg.json()["organizations"][0]["id"]
    headers = {"Authorization": f"Bearer {token}", "X-Organization-Id": org_id}

    # 1. Run controlled brute force simulation
    sim_res = client.post("/api/v1/simulation/run", headers=headers, json={
        "simulation_type": "brute_force_login",
        "target_ip": "127.0.0.1",
        "intensity": 6
    })
    assert sim_res.status_code == 200, sim_res.text
    sim_data = sim_res.json()
    assert sim_data["events_generated"] == 6
    assert sim_data["alerts_triggered"] >= 1
    assert sim_data["incidents_created"] >= 1

    # 2. Verify Alerts listed in Detection Center
    alerts_res = client.get("/api/v1/detections/alerts", headers=headers)
    assert alerts_res.status_code == 200
    alerts = alerts_res.json()
    assert len(alerts) >= 1
    target_alert = alerts[0]
    assert "Brute Force" in target_alert["title"]

    # 3. Verify Incident created in Incident Management
    incidents_res = client.get("/api/v1/incidents", headers=headers)
    assert incidents_res.status_code == 200
    incidents = incidents_res.json()
    assert len(incidents) >= 1
    incident = incidents[0]
    inc_id = incident["id"]
    assert incident["status"] == "New"
    assert incident["severity"] in ["High", "Critical"]

    # 4. Lifecycle update: Acknowledged -> Investigating -> Resolved
    ack_res = client.patch(f"/api/v1/incidents/{inc_id}", headers=headers, json={"status": "Investigating"})
    assert ack_res.status_code == 200
    assert ack_res.json()["status"] == "Investigating"

    # 5. Add Analyst Comment
    comment_res = client.post(f"/api/v1/incidents/{inc_id}/comments", headers=headers, json={
        "comment": "Triage verified brute-force burst from 198.51.100.24. Target port 22 closed."
    })
    assert comment_res.status_code == 200
    assert comment_res.json()["user_name"] == "Lead Analyst"

    # 6. Close incident with resolution notes
    close_res = client.patch(f"/api/v1/incidents/{inc_id}", headers=headers, json={
        "status": "Closed",
        "resolution_notes": "Adversary IP blocked at edge gateway. Authentication logs reviewed."
    })
    assert close_res.status_code == 200
    assert close_res.json()["status"] == "Closed"

    # 7. Safe Simulation Reset: Purge simulated lab data
    reset_res = client.post("/api/v1/simulation/reset", headers=headers)
    assert reset_res.status_code == 200
    assert reset_res.json()["purged_events"] >= 6
