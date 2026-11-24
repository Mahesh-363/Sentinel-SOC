import pytest
from fastapi.testclient import TestClient

def test_advanced_correlation_and_rules(client: TestClient):
    reg = client.post("/api/v1/auth/register", json={
        "email": "correlator@defense.org",
        "password": "Password789!",
        "full_name": "Correlation Specialist",
        "organization_name": "Advanced Detection Bureau"
    })
    token = reg.json()["access_token"]
    org_id = reg.json()["organizations"][0]["id"]
    headers = {"Authorization": f"Bearer {token}", "X-Organization-Id": org_id}

    # 1. Fetch detection rules and ensure 13 rules exist, with correlation flags
    rules_res = client.get("/api/v1/detections/rules", headers=headers)
    assert rules_res.status_code == 200
    rules = rules_res.json()
    assert len(rules) >= 13
    correlation_rules = [r for r in rules if r.get("is_correlation_rule") is True]
    assert len(correlation_rules) >= 2

    # Check for specific correlation rules
    rule_names = [r["name"] for r in rules]
    assert "Distributed Credential Stuffing Across Multiple Assets" in rule_names
    assert "Correlated Attack Chain (Compromise followed by C2 Beacon)" in rule_names
    assert "Unusual Outbound Network Connection" in rule_names
    assert "Repeated Failed Login Attempts (Single Host)" in rule_names

    # 2. Update a rule threshold/time window parameter
    target_rule = next(r for r in rules if r["name"] == "Repeated Failed Login Attempts (Single Host)")
    rule_id = target_rule["id"]
    update_res = client.put(f"/api/v1/detections/rules/{rule_id}/parameters", headers=headers, json={
        "threshold": 4,
        "time_window_seconds": 600,
        "is_enabled": True
    })
    assert update_res.status_code == 200
    updated_rule = update_res.json()
    assert updated_rule["threshold"] == 4
    assert updated_rule["time_window_seconds"] == 600

    # 3. Trigger correlation engine
    corr_trigger = client.post("/api/v1/detections/correlate?window_seconds=1800", headers=headers)
    assert corr_trigger.status_code == 200
    corr_data = corr_trigger.json()
    assert "correlated_groups_created" in corr_data

    # 4. List correlated groups
    corr_list = client.get("/api/v1/detections/correlations", headers=headers)
    assert corr_list.status_code == 200
    assert isinstance(corr_list.json(), list)
