import pytest
from fastapi.testclient import TestClient

def test_register_and_login(client: TestClient):
    # 1. Register User A
    reg_res = client.post("/api/v1/auth/register", json={
        "email": "analyst1@defense.org",
        "password": "StrongPassword123!",
        "full_name": "Analyst One",
        "organization_name": "Alpha Security Org"
    })
    assert reg_res.status_code == 200, reg_res.text
    data = reg_res.json()
    assert "access_token" in data
    assert data["email"] == "analyst1@defense.org"
    assert len(data["organizations"]) == 1
    org_a_id = data["organizations"][0]["id"]

    # 2. Login User A
    login_res = client.post("/api/v1/auth/login", json={
        "email": "analyst1@defense.org",
        "password": "StrongPassword123!"
    })
    assert login_res.status_code == 200
    token_a = login_res.json()["access_token"]

    # 3. Register User B in a different Organization
    reg_b = client.post("/api/v1/auth/register", json={
        "email": "analyst2@other.org",
        "password": "StrongPassword456!",
        "full_name": "Analyst Two",
        "organization_name": "Beta Defense Org"
    })
    assert reg_b.status_code == 200
    token_b = reg_b.json()["access_token"]
    org_b_id = reg_b.json()["organizations"][0]["id"]

    # 4. User A creates an asset in Org A
    headers_a = {"Authorization": f"Bearer {token_a}", "X-Organization-Id": org_a_id}
    asset_res = client.post("/api/v1/assets", headers=headers_a, json={
        "hostname": "alpha-server-01",
        "os_family": "Linux",
        "asset_type": "Server"
    })
    assert asset_res.status_code == 200
    asset_a_id = asset_res.json()["id"]

    # 5. Strict Multi-Tenant Isolation Check:
    # User B (member of Org B) attempts to access Org A with header X-Organization-Id = org_a_id
    headers_b_impersonate = {"Authorization": f"Bearer {token_b}", "X-Organization-Id": org_a_id}
    cross_tenant_res = client.get("/api/v1/assets", headers=headers_b_impersonate)
    # Must be 403 Forbidden!
    assert cross_tenant_res.status_code == 403, "Tenant boundary breached!"

    # 6. User B querying their own Org B sees empty assets
    headers_b = {"Authorization": f"Bearer {token_b}", "X-Organization-Id": org_b_id}
    org_b_assets = client.get("/api/v1/assets", headers=headers_b).json()
    assert len(org_b_assets) == 0
