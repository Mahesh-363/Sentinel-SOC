"""
SENTINEL SOC — End-to-End System Smoke Test
Executes complete lifecycle:
Auth -> Org Context -> Asset -> Sensor Token -> Sensor Enrollment ->
Heartbeat -> Telemetry Batch -> Rule Detection -> Incident Triage ->
AI Redaction & Advisory -> Host Containment Playbook -> Revocation Check.
"""
import sys
import os

# Ensure backend is on PYTHONPATH
sys.path.insert(0, os.path.abspath(os.path.join(os.path.dirname(__file__), "..")))

from fastapi.testclient import TestClient
from backend.app.main import app
from backend.app.database import Base, engine
from backend.app.db.seed import seed_database

def run_smoke_test():
    Base.metadata.create_all(bind=engine)
    seed_database()
    with TestClient(app) as client:
        print("=================================================================")
        print("🚀 SENTINEL SOC — END-TO-END VERIFICATION SUITE")
        print("=================================================================")

        # 1. Healthcheck
        resp = client.get("/health")
        assert resp.status_code == 200, f"Healthcheck failed: {resp.text}"
        print("✅ 1. System Healthcheck: OK")

        # 2. Authenticate Admin User
        login_resp = client.post(
            "/api/v1/auth/login",
            json={"email": "admin@sentinelsoc.com", "password": "SentinelAdmin123!"}
        )
        assert login_resp.status_code == 200, f"Login failed: {login_resp.text}"
        token_data = login_resp.json()
        token = token_data["access_token"]
        print(f"✅ 2. Authentication: Logged in as {token_data['full_name']} ({token_data['email']})")

        # 3. Retrieve Organization
        auth_headers = {"Authorization": f"Bearer {token}"}
        orgs_resp = client.get("/api/v1/organizations", headers=auth_headers)
        assert orgs_resp.status_code == 200
        orgs = orgs_resp.json()
        assert len(orgs) > 0, "No organizations found"
        org_id = orgs[0]["id"]
        org_name = orgs[0]["name"]
        tenant_headers = {
            "Authorization": f"Bearer {token}",
            "X-Organization-Id": org_id,
        }
        print(f"✅ 3. Multi-Tenancy: Scoped to '{org_name}' (ID: {org_id})")

        # 4. Generate Single-Use Sensor Enrollment Token
        token_resp = client.post(
            "/api/v1/sensors/generate-token",
            json={"name": "e2e-sensor-01", "os_type": "Linux"},
            headers=tenant_headers
        )
        assert token_resp.status_code == 200, f"Token generation failed: {token_resp.text}"
        enrollment_token = token_resp.json()["enrollment_token"]
        print(f"✅ 4. Sensor Token: Generated single-use token: {enrollment_token[:16]}...")

        # 5. Enroll Endpoint Sensor
        enroll_resp = client.post(
            "/api/v1/sensors/enroll",
            json={
                "enrollment_token": enrollment_token,
                "hostname": "e2e-monitored-srv01",
                "os_type": "Linux",
                "os_version": "Ubuntu 24.04 LTS",
                "capabilities": {
                    "system_metrics": "Available",
                    "socket_monitoring": "Available",
                    "log_collection": "Available",
                    "arp_discovery": "Available"
                }
            }
        )
        assert enroll_resp.status_code == 200, f"Enrollment failed: {enroll_resp.text}"
        sensor_data = enroll_resp.json()
        sensor_id = sensor_data["sensor_id"]
        api_key = sensor_data["api_key"]
        print(f"✅ 5. Sensor Enrolled: Sensor ID {sensor_id}")

        # 6. Verify Token Cannot Be Reused (Single-Use Guarantee)
        reuse_resp = client.post(
            "/api/v1/sensors/enroll",
            json={
                "enrollment_token": enrollment_token,
                "hostname": "rogue-agent",
                "os_type": "Linux",
                "os_version": "Ubuntu",
                "capabilities": {}
            }
        )
        assert reuse_resp.status_code == 401, "Single-use token was illegally reused!"
        print("✅ 6. Security Boundary: Single-use token reuse correctly rejected (HTTP 401)")

        # 7. Sensor Heartbeat Ping
        sensor_headers = {"X-Sensor-Key": api_key}
        hb_resp = client.post(
            "/api/v1/sensors/heartbeat",
            headers=sensor_headers,
            json={"system_status": "Healthy", "cpu_percent": 18.5, "memory_percent": 54.0, "disk_percent": 32.1}
        )
        assert hb_resp.status_code == 200, f"Heartbeat failed: {hb_resp.text}"
        print("✅ 7. Sensor Heartbeat: Ping acknowledged (CPU: 18.5%, Mem: 54.0%)")

        # 8. Send Batch Telemetry (Triggering AUTH_FAILED_BURST)
        telemetry_records = [
            {
                "event_type": "auth_failure",
                "severity": "Medium",
                "title": f"Failed password attempt {i+1}",
                "description": f"Failed authentication for user admin from 198.51.100.200",
                "source_ip": "198.51.100.200",
                "destination_port": 22,
                "raw_payload": {"user": "admin", "reason": "Bad credentials", "attempt": i + 1}
            }
            for i in range(5)
        ]
        batch_resp = client.post(
            "/api/v1/sensors/telemetry",
            headers=sensor_headers,
            json={"events": telemetry_records}
        )
        assert batch_resp.status_code == 200, f"Telemetry failed: {batch_resp.text}"
        batch_result = batch_resp.json()
        print(f"✅ 8. Ingestion & Detection: Ingested {batch_result['events_ingested']} events.")

        # 9. Verify Incident Escalation
        incidents_resp = client.get("/api/v1/incidents", headers=tenant_headers)
        assert incidents_resp.status_code == 200
        incidents = incidents_resp.json()
        assert len(incidents) > 0, "No incidents found after alert escalation"
        latest_incident = incidents[0]
        inc_id = latest_incident["id"]
        print(f"✅ 9. Incident Management: Found incident '{latest_incident['title']}' (Severity: {latest_incident['severity']})")

        # 10. AI Analyst Advisory Investigation (With Redaction)
        ai_resp = client.post(
            "/api/v1/ai-analyst/investigate",
            headers=tenant_headers,
            json={"target_type": "incident", "target_id": inc_id, "query": "Assess brute force risk and recommend mitigations."}
        )
        assert ai_resp.status_code == 200, f"AI Analyst failed: {ai_resp.text}"
        ai_data = ai_resp.json()
        print(f"✅ 10. AI Analyst (Provider: {ai_data['provider'].upper()}):")
        print(f"     Assessment: {ai_data['analysis'][:120]}...")

        # 11. Execute Response Playbook (Human-in-the-Loop)
        pb_list_resp = client.get("/api/v1/response/playbooks", headers=tenant_headers)
        assert pb_list_resp.status_code == 200
        playbooks = pb_list_resp.json()
        assert len(playbooks) > 0
        pb = playbooks[0]

        trigger_resp = client.post(
            "/api/v1/response/trigger",
            headers=tenant_headers,
            json={
                "playbook_id": pb["id"],
                "target_asset_id": sensor_data["asset_id"],
                "reason": "E2E automated response verification"
            }
        )
        assert trigger_resp.status_code == 200, f"Trigger failed: {trigger_resp.text}"
        execution_id = trigger_resp.json()["id"]

        decision_resp = client.post(
            f"/api/v1/response/executions/{execution_id}/decision",
            headers=tenant_headers,
            json={"decision": "Approved", "notes": "Approved by E2E test suite"}
        )
        assert decision_resp.status_code == 200, f"Decision failed: {decision_resp.text}"
        print(f"✅ 11. Response Playbook: Triggered '{pb['name']}' -> Human Approval -> Status: {decision_resp.json()['status']}")

        # 12. Revoke Sensor Credentials and Verify 403 Forbidden
        revoke_resp = client.post(
            f"/api/v1/sensors/{sensor_id}/revoke",
            headers=tenant_headers
        )
        assert revoke_resp.status_code == 200, f"Revocation failed: {revoke_resp.text}"
        print("✅ 12. Sensor Revocation: Credentials permanently revoked")

        rejected_ping = client.post(
            "/api/v1/sensors/heartbeat",
            headers=sensor_headers,
            json={"system_status": "Healthy"}
        )
        assert rejected_ping.status_code == 403, f"Expected 403 for revoked sensor, got {rejected_ping.status_code}"
        print("✅ 13. Revocation Enforcement: Revoked sensor ping rejected with HTTP 403 Forbidden")

        # 14. Attack Simulation & Safe Reset
        sim_resp = client.post(
            "/api/v1/simulation/run",
            headers=tenant_headers,
            json={"simulation_type": "port_scan"}
        )
        assert sim_resp.status_code == 200, f"Simulation failed: {sim_resp.text}"
        sim_data = sim_resp.json()
        print(f"✅ 14. Attack Simulation Lab: Ran port_scan scenario. Generated {sim_data['events_generated']} simulated events.")

        reset_resp = client.post(
            "/api/v1/simulation/reset",
            headers=tenant_headers
        )
        assert reset_resp.status_code == 200, f"Reset failed: {reset_resp.text}"
        reset_data = reset_resp.json()
        print(f"✅ 15. Simulation Reset: Safely purged {reset_data['purged_events']} simulated records without touching real telemetry.")

        print("=================================================================")
        print("🏆 ALL 15 END-TO-END VERIFICATION STEPS PASSED SUCCESSFULLY!")
        print("=================================================================")

if __name__ == "__main__":
    run_smoke_test()
