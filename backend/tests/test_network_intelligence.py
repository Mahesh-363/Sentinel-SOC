import pytest
from fastapi.testclient import TestClient

def test_network_coverage_and_topology(client: TestClient):
    reg = client.post("/api/v1/auth/register", json={
        "email": "netadmin@defense.org",
        "password": "Password789!",
        "full_name": "Network Administrator",
        "organization_name": "Infrastructure Security"
    })
    token = reg.json()["access_token"]
    org_id = reg.json()["organizations"][0]["id"]
    headers = {"Authorization": f"Bearer {token}", "X-Organization-Id": org_id}

    # 1. Register a network subnet
    net_res = client.post("/api/v1/network/subnets", headers=headers, json={
        "name": "Headquarters Internal LAN",
        "cidr": "10.0.0.0/24",
        "network_type": "Internal",
        "is_authorized": True
    })
    assert net_res.status_code == 200

    # 2. Get network coverage stats
    cov_res = client.get("/api/v1/network/coverage", headers=headers)
    assert cov_res.status_code == 200
    cov = cov_res.json()
    assert "total_subnets" in cov
    assert cov["total_subnets"] >= 1
    assert "subnet_coverage_percent" in cov
    assert "total_devices" in cov

    # 3. Check network topology
    topo_res = client.get("/api/v1/network/topology", headers=headers)
    assert topo_res.status_code == 200
    topo = topo_res.json()
    assert "nodes" in topo
    assert "links" in topo
    # Ensure links explicitly designate link_type as OBSERVED or INFERRED
    for link in topo["links"]:
        assert link["link_type"] in ["OBSERVED", "INFERRED"]

    # 4. Create and Sync a Router/Gateway Integration
    gw_payload = {
        "integration_type": "PFSENSE",
        "name": "Core Gateway 01",
        "target_host": "10.0.0.1",
        "port": 443,
        "is_enabled": True
    }
    gw_res = client.post("/api/v1/network/integrations", headers=headers, json=gw_payload)
    assert gw_res.status_code == 200
    gw_data = gw_res.json()
    gw_id = gw_data["id"]
    assert gw_data["integration_type"] == "PFSENSE"

    # 5. Trigger sync on the router integration
    sync_res = client.post(f"/api/v1/network/integrations/{gw_id}/sync", headers=headers)
    assert sync_res.status_code == 200
    sync_data = sync_res.json()
    assert "devices_synced" in sync_data
    assert sync_data["status"] == "success"
