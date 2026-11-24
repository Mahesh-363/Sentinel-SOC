import pytest
from fastapi.testclient import TestClient

def test_ip_investigation_and_grounding(client: TestClient):
    # Register analyst
    reg = client.post("/api/v1/auth/register", json={
        "email": "investigator@defense.org",
        "password": "Password789!",
        "full_name": "Senior Investigator",
        "organization_name": "Threat Intel Cell"
    })
    assert reg.status_code == 200
    token = reg.json()["access_token"]
    org_id = reg.json()["organizations"][0]["id"]
    headers = {"Authorization": f"Bearer {token}", "X-Organization-Id": org_id}

    # 1. Investigate a Public IPv4 (e.g. 198.51.100.1 or 8.8.8.8)
    res_pub = client.get("/api/v1/ip-intelligence/investigate?ip=8.8.8.8", headers=headers)
    assert res_pub.status_code == 200
    data_pub = res_pub.json()
    assert data_pub["ip_address"] == "8.8.8.8"
    assert data_pub["ip_version"] == "IPv4"
    assert data_pub["address_type"] == "Public"
    assert "grounding_breakdown" in data_pub
    assert "Directly Observed" in data_pub["grounding_breakdown"]
    assert "Imported Threat Intel" in data_pub["grounding_breakdown"]
    assert "Third-Party Enrichment" in data_pub["grounding_breakdown"]
    assert "Inferred Context" in data_pub["grounding_breakdown"]
    assert "Unavailable" in data_pub["grounding_breakdown"]
    assert "threat_providers" in data_pub
    assert "investigation_timeline" in data_pub

    # 2. Investigate an IPv6 address
    res_v6 = client.get("/api/v1/ip-intelligence/investigate?ip=2001:4860:4860::8888", headers=headers)
    assert res_v6.status_code == 200
    data_v6 = res_v6.json()
    assert data_v6["ip_version"] == "IPv6"
    assert data_v6["address_type"] == "Public"

    # 3. Investigate a Private IPv4 address
    res_priv = client.get("/api/v1/ip-intelligence/investigate?ip=192.168.1.50", headers=headers)
    assert res_priv.status_code == 200
    data_priv = res_priv.json()
    assert data_priv["address_type"] == "Private"
    assert data_priv["reputation"] in ["Benign", "Neutral / Internal"]

    # 4. Create an Analyst Investigation Case Note
    case_payload = {
        "ip_address": "8.8.8.8",
        "verdict": "Suspicious",
        "notes": "Target observed querying high-risk dynamic DNS domains during off-hours.",
        "tags": ["reconnaissance", "c2-suspect"],
        "confidence": 75
    }
    case_res = client.post("/api/v1/ip-intelligence/investigations", headers=headers, json=case_payload)
    assert case_res.status_code == 200
    case_data = case_res.json()
    assert case_data["verdict"] == "Suspicious"
    assert "reconnaissance" in case_data["tags"]

    # 5. List Investigations for organization
    list_cases = client.get("/api/v1/ip-intelligence/investigations", headers=headers)
    assert list_cases.status_code == 200
    cases = list_cases.json()
    assert len(cases) >= 1
    assert any(c["ip_address"] == "8.8.8.8" for c in cases)

    # 6. Verify Investigation details are reflected in subsequent IP investigate call
    recheck = client.get("/api/v1/ip-intelligence/investigate?ip=8.8.8.8", headers=headers)
    assert recheck.status_code == 200
    recheck_data = recheck.json()
    assert recheck_data["investigation_notes"] == "Target observed querying high-risk dynamic DNS domains during off-hours."
    assert "reconnaissance" in recheck_data["tags"]
