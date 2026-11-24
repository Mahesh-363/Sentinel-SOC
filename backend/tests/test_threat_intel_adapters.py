import pytest
from fastapi.testclient import TestClient
from backend.app.core.threat_intel.adapters import (
    query_abuseipdb,
    query_greynoise,
    query_alienvault_otx,
    query_spamhaus,
    enrich_ip_all_providers,
    get_threat_provider_health,
    get_normalized_indicator
)

def test_threat_provider_health_endpoint(client: TestClient):
    reg = client.post("/api/v1/auth/register", json={
        "email": "threatadmin@defense.org",
        "password": "Password789!",
        "full_name": "Threat Intel Admin",
        "organization_name": "Cyber Defense Unit"
    })
    token = reg.json()["access_token"]
    org_id = reg.json()["organizations"][0]["id"]
    headers = {"Authorization": f"Bearer {token}", "X-Organization-Id": org_id}

    res = client.get("/api/v1/ip-intelligence/providers", headers=headers)
    assert res.status_code == 200
    providers = res.json()
    assert len(providers) >= 4
    names = [p["provider_name"] for p in providers]
    assert "AbuseIPDB" in names
    assert "GreyNoise" in names
    assert "AlienVault OTX" in names
    assert "Spamhaus" in names
    for p in providers:
        assert "status" in p
        assert p["status"] in ["CONFIGURED", "ACTIVE", "NOT CONFIGURED", "ERROR", "RATE LIMITED"]

@pytest.mark.asyncio
async def test_unconfigured_adapters_handle_gracefully():
    # When API keys are not provided in settings, querying returns normalized indicator with NOT CONFIGURED
    res_abuse = await query_abuseipdb("198.51.100.25")
    assert res_abuse["provider"] == "AbuseIPDB"
    assert res_abuse["status"] in ["NOT CONFIGURED", "SUCCESS"]
    assert "attribution" in res_abuse

    res_noise = await query_greynoise("198.51.100.25")
    assert res_noise["provider"] == "GreyNoise"
    assert res_noise["status"] in ["NOT CONFIGURED", "SUCCESS"]

    res_otx = await query_alienvault_otx("198.51.100.25")
    assert res_otx["provider"] == "AlienVault OTX"
    assert res_otx["status"] in ["NOT CONFIGURED", "SUCCESS"]

    res_spamhaus = await query_spamhaus("198.51.100.25")
    assert res_spamhaus["provider"] == "Spamhaus"
    assert res_spamhaus["status"] in ["NOT CONFIGURED", "SUCCESS", "ERROR"]

def test_normalized_threat_indicator_schema():
    indicator = get_normalized_indicator(
        indicator_value="198.51.100.25",
        indicator_type="IPv4",
        provider="AbuseIPDB",
        reputation="Malicious",
        confidence=85,
        status="SUCCESS",
        attribution="Threat data provided by AbuseIPDB",
        reference="https://www.abuseipdb.com/check/198.51.100.25"
    )
    assert indicator["indicator_value"] == "198.51.100.25"
    assert indicator["indicator_type"] == "IPv4"
    assert indicator["provider"] == "AbuseIPDB"
    assert indicator["reputation"] == "Malicious"
    assert indicator["confidence"] == 85
    assert indicator["reference"] == "https://www.abuseipdb.com/check/198.51.100.25"
    assert indicator["expires_at"] is not None
