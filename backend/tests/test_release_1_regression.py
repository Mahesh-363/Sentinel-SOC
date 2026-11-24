import pytest
from fastapi.testclient import TestClient

def test_release_1_core_regression(client: TestClient):
    # Setup test user and organization
    reg = client.post("/api/v1/auth/register", json={
        "email": "regression_tester@defense.org",
        "password": "Password789!",
        "full_name": "Regression Tester",
        "organization_name": "Release 1 Verification Org"
    })
    assert reg.status_code == 200
    token = reg.json()["access_token"]
    org_id = reg.json()["organizations"][0]["id"]
    headers = {"Authorization": f"Bearer {token}", "X-Organization-Id": org_id}

    # 1. Dashboard Stats
    dash_res = client.get("/api/v1/dashboard/stats", headers=headers)
    assert dash_res.status_code == 200
    dash_data = dash_res.json()
    assert "total_assets" in dash_data
    assert "severity_distribution" in dash_data
    assert "event_trend_24h" in dash_data
    assert "integration_health" in dash_data

    # 2. Asset Lifecycle
    create_asset_res = client.post(
        "/api/v1/assets",
        headers=headers,
        json={
            "hostname": "win-dc-test",
            "os_family": "Windows",
            "os_version": "Server 2022",
            "asset_type": "Server",
            "private_ips": ["10.0.0.10"],
            "mac_addresses": ["00:15:5D:01:02:03"],
            "public_ip": "198.51.100.5"
        }
    )
    assert create_asset_res.status_code in [200, 201]
    asset_id = create_asset_res.json()["id"]

    list_assets_res = client.get("/api/v1/assets", headers=headers)
    assert list_assets_res.status_code == 200
    assert any(a["id"] == asset_id for a in list_assets_res.json())

    get_asset_res = client.get(f"/api/v1/assets/{asset_id}", headers=headers)
    assert get_asset_res.status_code == 200
    assert get_asset_res.json()["hostname"] == "win-dc-test"

    # 3. Security Events Ledger
    events_res = client.get("/api/v1/events", headers=headers)
    assert events_res.status_code == 200
    assert "events" in events_res.json() or isinstance(events_res.json(), list)

    # 4. Notifications
    notifs_res = client.get("/api/v1/notifications", headers=headers)
    assert notifs_res.status_code == 200
    mark_all_res = client.post("/api/v1/notifications/mark-all-read", headers=headers)
    assert mark_all_res.status_code == 200

    # 5. Response Automation Playbooks
    playbooks_res = client.get("/api/v1/response/playbooks", headers=headers)
    assert playbooks_res.status_code == 200
    playbooks = playbooks_res.json()
    assert len(playbooks) > 0

    # 6. Admin System Health, AI Quota & Audit Logs
    admin_health_res = client.get("/api/v1/admin/system-health", headers=headers)
    assert admin_health_res.status_code == 200
    assert "database" in admin_health_res.json()

    ai_quota_res = client.get("/api/v1/admin/ai-quota", headers=headers)
    assert ai_quota_res.status_code == 200
    assert "quota_status" in ai_quota_res.json()

    audit_logs_res = client.get("/api/v1/admin/audit-logs", headers=headers)
    assert audit_logs_res.status_code == 200

    # 7. Simulation Reset
    reset_res = client.post("/api/v1/simulation/reset", headers=headers)
    assert reset_res.status_code == 200

    # Cleanup test asset
    del_asset_res = client.delete(f"/api/v1/assets/{asset_id}", headers=headers)
    assert del_asset_res.status_code in [200, 204]

def test_production_health_and_trusted_proxy_security(client: TestClient):
    # 1. Verify Database-Aware Health Endpoint
    health_res = client.get("/health")
    assert health_res.status_code == 200
    health_data = health_res.json()
    assert health_data["status"] == "healthy"
    assert "database" in health_data
    assert health_data["database"]["status"] == "connected"
    assert health_data["database"]["dialect"] in ["sqlite", "postgresql"]

    # 2. Verify Root Metadata Endpoint
    root_res = client.get("/")
    assert root_res.status_code == 200
    root_data = root_res.json()
    assert root_data["health"] == "/health"
    assert root_data["docs"] == "/docs"

    # 3. Verify Trusted Proxy Forwarded Header Handling
    # TestClient default socket is testclient (127.0.0.1)
    proxy_headers = {"X-Forwarded-For": "203.0.113.50, 10.0.0.1", "X-Real-IP": "203.0.113.50"}
    res_proxied = client.get("/health", headers=proxy_headers)
    assert res_proxied.status_code == 200
