import pytest
from fastapi.testclient import TestClient

def test_incident_timeline_and_multi_format_reports(client: TestClient):
    reg = client.post("/api/v1/auth/register", json={
        "email": "reportanalyst@defense.org",
        "password": "Password789!",
        "full_name": "Reporting Specialist",
        "organization_name": "SOC Compliance Office"
    })
    token = reg.json()["access_token"]
    org_id = reg.json()["organizations"][0]["id"]
    headers = {"Authorization": f"Bearer {token}", "X-Organization-Id": org_id}

    # 1. Create an incident
    inc_res = client.post("/api/v1/incidents", headers=headers, json={
        "title": "Suspected Lateral Movement in DMZ",
        "description": "Anomalous SMB connections from staging bastion",
        "severity": "High",
        "related_ip_addresses": ["10.0.10.45", "198.51.100.99"]
    })
    assert inc_res.status_code == 200
    inc_data = inc_res.json()
    inc_id = inc_data["id"]

    # 2. Add an investigation note to the incident
    note_res = client.post(f"/api/v1/incidents/{inc_id}/comments", headers=headers, json={
        "comment": "Bastion host isolated; memory dump captured for volatility analysis."
    })
    assert note_res.status_code == 200

    # 3. Update status to Investigating
    patch_res = client.patch(f"/api/v1/incidents/{inc_id}", headers=headers, json={
        "status": "Investigating"
    })
    assert patch_res.status_code == 200

    # 4. Fetch the incident timeline
    tl_res = client.get(f"/api/v1/incidents/{inc_id}/timeline", headers=headers)
    assert tl_res.status_code == 200
    timeline = tl_res.json()
    assert len(timeline) >= 2
    types = [t["entry_type"] for t in timeline]
    assert "CREATED" in types
    assert "NOTE_ADDED" in types or "STATUS_CHANGE" in types

    # 5. Export Incident Timeline as CSV
    csv_tl_res = client.get(f"/api/v1/incidents/{inc_id}/export/csv", headers=headers)
    assert csv_tl_res.status_code == 200
    assert "text/csv" in csv_tl_res.headers.get("content-type", "")
    assert "Timestamp" in csv_tl_res.text
    assert "Entry Type" in csv_tl_res.text
    assert "Title" in csv_tl_res.text

    # 6. Export Reports
    # A) Incidents CSV
    exp_inc_csv = client.get("/api/v1/reports/incidents/csv", headers=headers)
    assert exp_inc_csv.status_code == 200
    assert "Incident ID,Title,Severity,Status" in exp_inc_csv.text

    # B) Incidents JSON
    exp_inc_json = client.get("/api/v1/reports/incidents/json", headers=headers)
    assert exp_inc_json.status_code == 200
    assert isinstance(exp_inc_json.json(), list)

    # C) Threat Intel CSV
    exp_intel_csv = client.get("/api/v1/reports/threat-intel/csv", headers=headers)
    assert exp_intel_csv.status_code == 200

    # D) Network Inventory CSV
    exp_net_csv = client.get("/api/v1/reports/network/csv", headers=headers)
    assert exp_net_csv.status_code == 200

    # E) AWS Findings CSV
    exp_aws_csv = client.get("/api/v1/reports/aws/csv", headers=headers)
    assert exp_aws_csv.status_code == 200

    # F) Executive Summary
    summary_res = client.get("/api/v1/reports/summary", headers=headers)
    assert summary_res.status_code == 200
    assert "total_incidents" in summary_res.json()
