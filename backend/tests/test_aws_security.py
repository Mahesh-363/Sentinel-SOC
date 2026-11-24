import pytest
from fastapi.testclient import TestClient

def test_aws_security_expansion(client: TestClient):
    reg = client.post("/api/v1/auth/register", json={
        "email": "cloudsec@defense.org",
        "password": "Password789!",
        "full_name": "Cloud Security Architect",
        "organization_name": "Cloud Operations Wing"
    })
    token = reg.json()["access_token"]
    org_id = reg.json()["organizations"][0]["id"]
    headers = {"Authorization": f"Bearer {token}", "X-Organization-Id": org_id}

    # 1. Fetch Least-Privilege IAM Policy Template
    policy_res = client.get("/api/v1/aws/iam-policy-template", headers=headers)
    assert policy_res.status_code == 200
    pdata = policy_res.json()
    assert "policy_json" in pdata
    assert "trust_relationship" in pdata
    assert "policy_name" in pdata

    # 2. Register AWS Account (AssumeRole configuration)
    acct_payload = {
        "account_id": "123456789012",
        "account_name": "Production Core AWS",
        "role_arn": "arn:aws:iam::123456789012:role/SentinelSOCReadOnlyRole",
        "external_id": "sentinel-soc-auth-uuid-test",
        "region": "us-east-1"
    }
    acct_res = client.post("/api/v1/aws/accounts", headers=headers, json=acct_payload)
    assert acct_res.status_code == 200
    acct_data = acct_res.json()
    acct_id = acct_data["id"]
    assert acct_data["account_id"] == "123456789012"
    assert acct_data["role_arn"] == "arn:aws:iam::123456789012:role/SentinelSOCReadOnlyRole"

    # 3. Load Offline Zero-Cost Simulation Fixtures
    load_res = client.post("/api/v1/aws/fixtures/load-all-fixtures", headers=headers)
    assert load_res.status_code == 200
    fixtures_loaded = load_res.json()
    assert fixtures_loaded["fixtures_loaded"] >= 4

    # 4. List AWS Findings
    findings_res = client.get("/api/v1/aws/findings", headers=headers)
    assert findings_res.status_code == 200
    findings = findings_res.json()
    assert len(findings) >= 4
    finding_types = [f["finding_type"] for f in findings]
    assert any("S3" in ft or "Public" in ft for ft in finding_types)
    assert any("CryptoCurrency" in ft or "Bitcoin" in ft or "SSH" in ft for ft in finding_types)

    # 5. List AWS Resources
    resources_res = client.get("/api/v1/aws/resources", headers=headers)
    assert resources_res.status_code == 200
    resources = resources_res.json()
    assert len(resources) >= 4

    # 6. Disconnect AWS Account
    del_res = client.delete(f"/api/v1/aws/accounts/{acct_id}", headers=headers)
    assert del_res.status_code == 200
    assert del_res.json()["status"] == "success"
