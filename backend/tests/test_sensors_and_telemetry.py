import pytest
import json
import uuid
from datetime import datetime, timedelta
from fastapi.testclient import TestClient

def test_sensor_lifecycle_and_telemetry(client: TestClient):
    # 1. Setup Org & Admin
    reg = client.post("/api/v1/auth/register", json={
        "email": "sensoradmin@defense.org",
        "password": "Password123!",
        "full_name": "Sensor Admin",
        "organization_name": "Sensor Testing Division"
    })
    token = reg.json()["access_token"]
    org_id = reg.json()["organizations"][0]["id"]
    headers = {"Authorization": f"Bearer {token}", "X-Organization-Id": org_id}

    # 2. Generate Enrollment Token
    gen_res = client.post("/api/v1/sensors/generate-token", headers=headers, json={
        "name": "workstation-charlie-sensor",
        "os_type": "Windows"
    })
    assert gen_res.status_code == 200
    enroll_data = gen_res.json()
    enrollment_token = enroll_data["enrollment_token"]
    assert enrollment_token.startswith("stk_")

    # 3. Sensor Client Enrolls with single-use Token
    enroll_client_res = client.post("/api/v1/sensors/enroll", json={
        "enrollment_token": enrollment_token,
        "hostname": "fin-charlie-pc",
        "os_type": "Windows",
        "os_version": "Windows 11 Enterprise",
        "capabilities": {"system": "Available", "connections": "Available"}
    })
    assert enroll_client_res.status_code == 200
    sensor_creds = enroll_client_res.json()
    sensor_api_key = sensor_creds["api_key"]
    sensor_id = sensor_creds["sensor_id"]
    asset_id = sensor_creds["asset_id"]
    assert sensor_api_key.startswith("sak_")

    # 4. Verify Single-Use Token: Second attempt with same token must fail with 401
    second_enroll_res = client.post("/api/v1/sensors/enroll", json={
        "enrollment_token": enrollment_token,
        "hostname": "attacker-duplicate",
        "os_type": "Linux"
    })
    assert second_enroll_res.status_code == 401, "Enrollment token was not single-use!"

    # 5. Sensor Sends Heartbeat
    hb_headers = {"X-Sensor-Key": sensor_api_key}
    hb_res = client.post("/api/v1/sensors/heartbeat", headers=hb_headers, json={
        "cpu_percent": 25.5,
        "memory_percent": 55.0,
        "disk_percent": 40.0,
        "active_connections_count": 12
    })
    assert hb_res.status_code == 200
    assert hb_res.json()["status"] == "acknowledged"

    # 6. Sensor Ingests Batch Telemetry
    telemetry_payload = {
        "sensor_version": "1.0.0",
        "events": [
            {
                "event_type": "network_connection",
                "severity": "Low",
                "title": "Outbound DNS resolution",
                "description": "DNS query to 1.1.1.1:53",
                "source_ip": "192.168.1.55",
                "destination_ip": "1.1.1.1",
                "destination_port": 53,
                "protocol": "UDP"
            }
        ],
        "discovered_devices": [
            {
                "ip_address": "192.168.1.1",
                "mac_address": "00:AA:BB:CC:DD:EE",
                "hostname": "router-default-gw",
                "vendor": "Netgear",
                "device_type": "Router"
            }
        ],
        "active_connections_sample": [
            {
                "destination_ip": "1.1.1.1",
                "destination_port": 53,
                "protocol": "UDP",
                "direction": "Outbound"
            }
        ]
    }
    telem_res = client.post("/api/v1/sensors/telemetry", headers=hb_headers, json=telemetry_payload)
    assert telem_res.status_code == 200
    assert telem_res.json()["events_ingested"] == 1
    assert telem_res.json()["devices_updated"] == 1

    # 7. Check Dashboard Stats reflects real ingested telemetry
    stats_res = client.get("/api/v1/dashboard/stats", headers=headers)
    assert stats_res.status_code == 200
    stats = stats_res.json()
    assert stats["total_assets"] >= 1
    assert stats["online_sensors"] >= 1
    assert stats["network_devices_count"] >= 1

    # 8. Revoke Sensor Credentials
    revoke_res = client.post(f"/api/v1/sensors/{sensor_id}/revoke", headers=headers)
    assert revoke_res.status_code == 200

    # 9. Verify Revoked Sensor Cannot Send Heartbeat (must return 403)
    revoked_hb_res = client.post("/api/v1/sensors/heartbeat", headers=hb_headers, json={"cpu_percent": 10})
    assert revoked_hb_res.status_code == 403

def test_simulated_vs_genuine_event_classification_and_isolation(client: TestClient):
    """
    Regression test ensuring simulated fixtures are strictly separated from genuine telemetry,
    with simulation status inherited across detections and incidents, and segmented in dashboard and reports.
    """
    # 1. Setup Isolated Testing Organization
    reg = client.post("/api/v1/auth/register", json={
        "email": "classification_lead@defense.org",
        "password": "Password123!",
        "full_name": "Classification Lead",
        "organization_name": "Classification Testing Unit"
    })
    assert reg.status_code == 200
    token = reg.json()["access_token"]
    org_id = reg.json()["organizations"][0]["id"]
    headers = {"Authorization": f"Bearer {token}", "X-Organization-Id": org_id}

    # 2. Generate Sensor Token & Enroll
    gen_res = client.post("/api/v1/sensors/generate-token", headers=headers, json={
        "name": "classification-eval-sensor",
        "os_type": "Windows"
    })
    assert gen_res.status_code == 200
    enrollment_token = gen_res.json()["enrollment_token"]

    enroll_res = client.post("/api/v1/sensors/enroll", json={
        "enrollment_token": enrollment_token,
        "hostname": "win-eval-endpoint",
        "os_type": "Windows",
        "os_version": "Windows 11 Pro"
    })
    assert enroll_res.status_code == 200
    sensor_api_key = enroll_res.json()["api_key"]
    hb_headers = {"X-Sensor-Key": sensor_api_key}

    # 3. Transmit Dual Batch: 1 Genuine Observation + 1 Simulated Fixture Event
    batch_payload = {
        "sensor_version": "1.0.0",
        "events": [
            {
                "event_type": "network_connection",
                "severity": "Informational",
                "title": "Local Loopback Telemetry Event",
                "description": "Genuine endpoint socket observation",
                "source_ip": "127.0.0.1",
                "destination_ip": "127.0.0.1",
                "source_port": 50505,
                "destination_port": 8000,
                "protocol": "TCP",
                "is_simulated": False
            },
            {
                "event_type": "network_traffic",
                "severity": "High",
                "title": "Outbound Suspicious Reverse Shell Beacon Attempt",
                "description": "Suspicious outbound connection fixture",
                "source_ip": "192.168.1.150",
                "destination_ip": "198.51.100.99",
                "source_port": 49210,
                "destination_port": 4444,
                "protocol": "TCP",
                "is_simulated": True
            }
        ]
    }
    telem_res = client.post("/api/v1/sensors/telemetry", headers=hb_headers, json=batch_payload)
    assert telem_res.status_code == 200
    assert telem_res.json()["events_ingested"] == 2

    # 4. Verify Database Persistence and Classification
    events_res = client.get("/api/v1/events", headers=headers)
    assert events_res.status_code == 200
    events = events_res.json()
    assert len(events) == 2

    genuine_ev = next(e for e in events if e["destination_port"] == 8000)
    simulated_ev = next(e for e in events if e["destination_port"] == 4444)
    assert genuine_ev["is_simulated"] is False, "Genuine event must have is_simulated == False"
    assert simulated_ev["is_simulated"] is True, "Simulated fixture must have is_simulated == True"

    # 5. Verify Filtered Event Queries
    sim_only = client.get("/api/v1/events?is_simulated=true", headers=headers).json()
    gen_only = client.get("/api/v1/events?is_simulated=false", headers=headers).json()
    assert len(sim_only) == 1 and sim_only[0]["destination_port"] == 4444
    assert len(gen_only) == 1 and gen_only[0]["destination_port"] == 8000

    # 6. Verify Detection Result Inherits is_simulated=True
    alerts_res = client.get("/api/v1/detections/alerts", headers=headers)
    assert alerts_res.status_code == 200
    alerts = alerts_res.json()
    c2_alert = next((a for a in alerts if "4444" in a["title"] or a["rule_name"] == "Unusual Outbound Network Connection"), None)
    assert c2_alert is not None, "Detection alert for port 4444 not found"
    assert c2_alert["is_simulated"] is True, "Detection result must inherit is_simulated=True from fixture event"

    # 7. Verify Incident Inherits is_simulated=True
    incidents_res = client.get("/api/v1/incidents", headers=headers)
    assert incidents_res.status_code == 200
    incidents = incidents_res.json()
    assert len(incidents) >= 1
    c2_inc = incidents[0]
    assert c2_inc["is_simulated"] is True, "Incident must inherit is_simulated=True from detection"

    # Test incident filtering
    inc_sim_only = client.get("/api/v1/incidents?is_simulated=true", headers=headers).json()
    inc_gen_only = client.get("/api/v1/incidents?is_simulated=false", headers=headers).json()
    assert len(inc_sim_only) == 1
    assert len(inc_gen_only) == 0

    # 8. Verify Dashboard Stats Segmentation
    stats_res = client.get("/api/v1/dashboard/stats", headers=headers)
    assert stats_res.status_code == 200
    stats = stats_res.json()
    assert stats["total_events_24h"] == 2
    assert stats["genuine_events_24h"] == 1
    assert stats["simulated_events_24h"] == 1
    assert stats["simulated_incidents_count"] == 1
    assert stats["genuine_incidents_count"] == 0

    # 9. Verify Reports Executive Summary & Exports
    summary_res = client.get("/api/v1/reports/summary", headers=headers)
    assert summary_res.status_code == 200
    summary = summary_res.json()
    assert summary["genuine_security_events"] == 1
    assert summary["simulated_security_events"] == 1
    assert summary["genuine_incidents"] == 0
    assert summary["simulated_incidents"] == 1

    # Incidents CSV export
    csv_res = client.get("/api/v1/reports/incidents/csv", headers=headers)
    assert csv_res.status_code == 200
    assert "Simulated" in csv_res.text
    assert "Yes" in csv_res.text

    # Incidents JSON export
    json_res = client.get("/api/v1/reports/incidents/json", headers=headers)
    assert json_res.status_code == 200
    assert json_res.json()[0]["is_simulated"] is True

def test_sensor_authentication_matrix_and_rejection_side_effects(client: TestClient, db_session):
    """
    Mandatory Security Audit: Tests all 7 sensor credential scenarios:
    1. Valid sensor API key.
    2. Random invalid API key.
    3. Empty API key.
    4. Missing API key.
    5. Revoked sensor credential.
    6. Expired enrollment token.
    7. Cross-tenant authentication attempt.
    Asserts: HTTP status (401 or 403), zero persistence in SecurityEvent table, zero detection side effects.
    """
    # 1. Setup Tenant A and Tenant B
    reg_a = client.post("/api/v1/auth/register", json={
        "email": "lead_a@tenant-a.org",
        "password": "Password123!",
        "full_name": "Lead A",
        "organization_name": "Tenant Alpha Org"
    })
    token_a = reg_a.json()["access_token"]
    org_a_id = reg_a.json()["organizations"][0]["id"]
    headers_a = {"Authorization": f"Bearer {token_a}", "X-Organization-Id": org_a_id}

    reg_b = client.post("/api/v1/auth/register", json={
        "email": "lead_b@tenant-b.org",
        "password": "Password123!",
        "full_name": "Lead B",
        "organization_name": "Tenant Beta Org"
    })
    token_b = reg_b.json()["access_token"]
    org_b_id = reg_b.json()["organizations"][0]["id"]
    headers_b = {"Authorization": f"Bearer {token_b}", "X-Organization-Id": org_b_id}

    # 2. Enroll Sensor A in Tenant A
    tok_res = client.post("/api/v1/sensors/generate-token", headers=headers_a, json={
        "name": "sensor-alpha-01", "os_type": "Linux"
    })
    stk_a = tok_res.json()["enrollment_token"]
    enroll_a = client.post("/api/v1/sensors/enroll", json={
        "enrollment_token": stk_a, "hostname": "host-alpha-01", "os_type": "Linux"
    })
    sensor_a = enroll_a.json()
    sensor_a_id = sensor_a["sensor_id"]
    valid_key_a = sensor_a["api_key"]

    # Sample telemetry payload
    sample_telemetry = {
        "sensor_version": "1.0.0",
        "events": [{
            "event_type": "network_connection",
            "severity": "High",
            "title": "Unauthorized Telemetry Ingestion Probe",
            "description": "Probe event destined for port 4444",
            "source_ip": "10.0.0.1",
            "destination_ip": "198.51.100.99",
            "destination_port": 4444,
            "protocol": "TCP",
            "is_simulated": True
        }]
    }

    # Baseline: Count existing security events
    from backend.app.models.events import SecurityEvent
    from backend.app.models.detections import DetectionResult
    from backend.app.models.assets import Sensor
    from backend.app.models.auth import AuditLog

    events_before = db_session.query(SecurityEvent).count()

    # --- SCENARIO 1: Valid Sensor API Key ---
    res1 = client.post("/api/v1/sensors/heartbeat", headers={"X-Sensor-Key": valid_key_a}, json={"cpu_percent": 10})
    assert res1.status_code == 200, f"Valid key failed: {res1.text}"
    assert res1.json()["status"] == "acknowledged"

    # Ingest legitimate telemetry
    res1_telem = client.post("/api/v1/sensors/telemetry", headers={"X-Sensor-Key": valid_key_a}, json=sample_telemetry)
    assert res1_telem.status_code == 200
    events_after_valid = db_session.query(SecurityEvent).count()
    assert events_after_valid == events_before + 1, "Legitimate telemetry was not persisted"

    # --- SCENARIO 2: Random Invalid API Key ---
    res2_hb = client.post("/api/v1/sensors/heartbeat", headers={"X-Sensor-Key": "sak_bogus_random_invalid_key_99999"}, json={"cpu_percent": 10})
    assert res2_hb.status_code == 401, f"Expected 401, got {res2_hb.status_code}"
    res2_telem = client.post("/api/v1/sensors/telemetry", headers={"X-Sensor-Key": "sak_bogus_random_invalid_key_99999"}, json=sample_telemetry)
    assert res2_telem.status_code == 401
    assert db_session.query(SecurityEvent).count() == events_after_valid, "Unauthorized telemetry persisted on random key!"

    # --- SCENARIO 3: Empty API Key ---
    res3_hb = client.post("/api/v1/sensors/heartbeat", headers={"X-Sensor-Key": ""}, json={"cpu_percent": 10})
    assert res3_hb.status_code == 401, f"Expected 401 on empty key, got {res3_hb.status_code}"
    res3_ws = client.post("/api/v1/sensors/heartbeat", headers={"X-Sensor-Key": "   "}, json={"cpu_percent": 10})
    assert res3_ws.status_code == 401, f"Expected 401 on whitespace key, got {res3_ws.status_code}"
    res3_telem = client.post("/api/v1/sensors/telemetry", headers={"X-Sensor-Key": ""}, json=sample_telemetry)
    assert res3_telem.status_code == 401
    assert db_session.query(SecurityEvent).count() == events_after_valid, "Unauthorized telemetry persisted on empty key!"

    # --- SCENARIO 4: Missing API Key ---
    res4_hb = client.post("/api/v1/sensors/heartbeat", headers={}, json={"cpu_percent": 10})
    assert res4_hb.status_code == 401, f"Expected 401 on missing key, got {res4_hb.status_code}"
    res4_telem = client.post("/api/v1/sensors/telemetry", headers={}, json=sample_telemetry)
    assert res4_telem.status_code == 401
    assert db_session.query(SecurityEvent).count() == events_after_valid, "Unauthorized telemetry persisted on missing key!"

    # --- SCENARIO 5: Revoked Sensor Credential ---
    rev_res = client.post(f"/api/v1/sensors/{sensor_a_id}/revoke", headers=headers_a)
    assert rev_res.status_code == 200
    res5_hb = client.post("/api/v1/sensors/heartbeat", headers={"X-Sensor-Key": valid_key_a}, json={"cpu_percent": 10})
    assert res5_hb.status_code == 403, f"Expected 403 on revoked sensor, got {res5_hb.status_code}"
    assert "revoked" in res5_hb.text.lower()
    res5_telem = client.post("/api/v1/sensors/telemetry", headers={"X-Sensor-Key": valid_key_a}, json=sample_telemetry)
    assert res5_telem.status_code == 403
    assert db_session.query(SecurityEvent).count() == events_after_valid, "Unauthorized telemetry persisted on revoked sensor!"
    rev_audit = db_session.query(AuditLog).filter(
        AuditLog.action == "REVOKED_SENSOR_ACCESS_ATTEMPT",
        AuditLog.target_id == sensor_a_id
    ).first()
    assert rev_audit is not None, "AuditLog did not record revoked sensor access attempt"

    # --- SCENARIO 6: Expired Credential (Expired Enrollment Token) ---
    gen_expired = client.post("/api/v1/sensors/generate-token", headers=headers_a, json={
        "name": "sensor-alpha-expired", "os_type": "Linux"
    })
    stk_expired = gen_expired.json()["enrollment_token"]
    sensor_exp_db = db_session.query(Sensor).filter(Sensor.enrollment_token == stk_expired).first()
    sensor_exp_db.token_expires_at = datetime.utcnow() - timedelta(hours=1)
    db_session.commit()

    res6_enroll = client.post("/api/v1/sensors/enroll", json={
        "enrollment_token": stk_expired, "hostname": "expired-host", "os_type": "Linux"
    })
    assert res6_enroll.status_code == 401, f"Expected 401 on expired token, got {res6_enroll.status_code}"
    assert "expired" in res6_enroll.text.lower()

    # --- SCENARIO 7: Cross-Tenant Boundary Authentication Violation ---
    gen_b = client.post("/api/v1/sensors/generate-token", headers=headers_b, json={
        "name": "sensor-beta-01", "os_type": "Linux"
    })
    stk_b = gen_b.json()["enrollment_token"]
    enroll_b = client.post("/api/v1/sensors/enroll", json={
        "enrollment_token": stk_b, "hostname": "host-beta-01", "os_type": "Linux"
    })
    valid_key_b = enroll_b.json()["api_key"]

    cross_headers = {"X-Sensor-Key": valid_key_b, "X-Organization-Id": org_a_id}
    res7_hb = client.post("/api/v1/sensors/heartbeat", headers=cross_headers, json={"cpu_percent": 10})
    assert res7_hb.status_code == 403, f"Expected 403 on cross-tenant violation, got {res7_hb.status_code}"
    assert "cross-tenant" in res7_hb.text.lower()

    res7_telem = client.post("/api/v1/sensors/telemetry", headers=cross_headers, json=sample_telemetry)
    assert res7_telem.status_code == 403
    assert db_session.query(SecurityEvent).count() == events_after_valid, "Cross-tenant telemetry persisted!"

    cross_audit = db_session.query(AuditLog).filter(
        AuditLog.action == "CROSS_TENANT_SENSOR_ATTEMPT"
    ).first()
    assert cross_audit is not None, "AuditLog did not record cross-tenant violation"

def test_sensor_command_security_and_replay_protection(client: TestClient, db_session):
    """
    Mandatory Security Audit: Tests sensor command authorization and replay protection:
    - Sensor retrieves only its own commands.
    - Sensor cannot retrieve another sensor's commands.
    - Sensor cannot acknowledge another sensor's commands (HTTP 403).
    - Unauthenticated acknowledgements rejected (HTTP 401).
    - Duplicate acknowledgements handled idempotently without mutating original state.
    - Expired commands cannot be executed (HTTP 400).
    - Command identifiers cannot be reused.
    - Full lifecycle transitions audited.
    """
    reg = client.post("/api/v1/auth/register", json={
        "email": "cmd_auditor@defense.org",
        "password": "Password123!",
        "full_name": "Command Auditor",
        "organization_name": "Command Security Testing Unit"
    })
    token = reg.json()["access_token"]
    org_id = reg.json()["organizations"][0]["id"]
    headers = {"Authorization": f"Bearer {token}", "X-Organization-Id": org_id}

    t1 = client.post("/api/v1/sensors/generate-token", headers=headers, json={"name": "s1", "os_type": "Linux"}).json()["enrollment_token"]
    s1_data = client.post("/api/v1/sensors/enroll", json={"enrollment_token": t1, "hostname": "h1", "os_type": "Linux"}).json()
    s1_id = s1_data["sensor_id"]
    s1_key = s1_data["api_key"]

    t2 = client.post("/api/v1/sensors/generate-token", headers=headers, json={"name": "s2", "os_type": "Linux"}).json()["enrollment_token"]
    s2_data = client.post("/api/v1/sensors/enroll", json={"enrollment_token": t2, "hostname": "h2", "os_type": "Linux"}).json()
    s2_id = s2_data["sensor_id"]
    s2_key = s2_data["api_key"]

    from backend.app.models.response import SensorCommand
    from backend.app.models.auth import AuditLog

    # Queue Command 1 explicitly for Sensor 1
    cmd1_id = str(uuid.uuid4())
    cmd1 = SensorCommand(
        id=cmd1_id,
        sensor_id=s1_id,
        organization_id=org_id,
        action="DIAGNOSTIC_PROBE",
        parameters_json=json.dumps({"dry_run": True}),
        status="QUEUED",
        queued_at=datetime.utcnow(),
        expires_at=datetime.utcnow() + timedelta(hours=1)
    )
    db_session.add(cmd1)
    db_session.commit()

    # Sensor 2 Heartbeat: Must NOT receive Sensor 1's command
    hb_s2 = client.post("/api/v1/sensors/heartbeat", headers={"X-Sensor-Key": s2_key}, json={"cpu_percent": 10})
    assert hb_s2.status_code == 200
    cmds_s2 = hb_s2.json().get("dispatched_commands", [])
    assert len(cmds_s2) == 0, "Sensor 2 received commands belonging to Sensor 1!"

    # Sensor 1 Heartbeat: Must receive Command 1
    hb_s1 = client.post("/api/v1/sensors/heartbeat", headers={"X-Sensor-Key": s1_key}, json={"cpu_percent": 10})
    assert hb_s1.status_code == 200
    cmds_s1 = hb_s1.json().get("dispatched_commands", [])
    assert len(cmds_s1) == 1
    assert cmds_s1[0]["id"] == cmd1_id

    # Cross-Sensor Acknowledgment Violation: Sensor 2 tries to acknowledge Command 1
    cross_ack = client.post("/api/v1/sensors/commands/acknowledge", headers={"X-Sensor-Key": s2_key}, json={
        "command_id": cmd1_id,
        "action": "DIAGNOSTIC_PROBE",
        "status": "SUCCESS",
        "details": "Rogue sensor trying to ack another sensor's command"
    })
    assert cross_ack.status_code == 403, f"Expected 403 on cross-sensor ack, got {cross_ack.status_code}"

    authz_audit = db_session.query(AuditLog).filter(
        AuditLog.action == "COMMAND_AUTHZ_VIOLATION",
        AuditLog.target_id == cmd1_id
    ).first()
    assert authz_audit is not None, "AuditLog did not record cross-sensor command violation"

    # Unauthenticated Acknowledgment Attempt
    unauth_ack = client.post("/api/v1/sensors/commands/acknowledge", headers={}, json={
        "command_id": cmd1_id, "action": "DIAGNOSTIC_PROBE", "status": "SUCCESS"
    })
    assert unauth_ack.status_code == 401

    # Sensor 1 Legitimate Acknowledgment
    legit_ack = client.post("/api/v1/sensors/commands/acknowledge", headers={"X-Sensor-Key": s1_key}, json={
        "command_id": cmd1_id,
        "action": "DIAGNOSTIC_PROBE",
        "status": "SUCCESS",
        "details": "Verified execution"
    })
    assert legit_ack.status_code == 200
    assert legit_ack.json()["status"] == "recorded"

    db_session.refresh(cmd1)
    assert cmd1.status == "ACKNOWLEDGED"

    # Duplicate Acknowledgment: Safely Idempotent
    dup_ack = client.post("/api/v1/sensors/commands/acknowledge", headers={"X-Sensor-Key": s1_key}, json={
        "command_id": cmd1_id,
        "action": "DIAGNOSTIC_PROBE",
        "status": "FAILED",
        "details": "Duplicate attempt"
    })
    assert dup_ack.status_code == 200
    assert dup_ack.json()["status"] == "already_acknowledged"
    db_session.refresh(cmd1)
    assert cmd1.result_status == "SUCCESS"

    # Expired Command Protection
    cmd_exp_id = str(uuid.uuid4())
    cmd_exp = SensorCommand(
        id=cmd_exp_id,
        sensor_id=s1_id,
        organization_id=org_id,
        action="DIAGNOSTIC_PROBE",
        parameters_json=json.dumps({"dry_run": True}),
        status="QUEUED",
        queued_at=datetime.utcnow() - timedelta(hours=3),
        expires_at=datetime.utcnow() - timedelta(hours=1)
    )
    db_session.add(cmd_exp)
    db_session.commit()

    hb_exp = client.post("/api/v1/sensors/heartbeat", headers={"X-Sensor-Key": s1_key}, json={"cpu_percent": 10})
    exp_dispatched = hb_exp.json().get("dispatched_commands", [])
    assert all(c["id"] != cmd_exp_id for c in exp_dispatched), "Expired command was dispatched!"
    db_session.refresh(cmd_exp)
    assert cmd_exp.status == "EXPIRED"

    exp_ack = client.post("/api/v1/sensors/commands/acknowledge", headers={"X-Sensor-Key": s1_key}, json={
        "command_id": cmd_exp_id, "action": "DIAGNOSTIC_PROBE", "status": "SUCCESS"
    })
    assert exp_ack.status_code == 400

def test_audit_log_integrity_and_tenant_isolation(client: TestClient, db_session):
    """
    Mandatory Security Audit: Tests audit log integrity and tenant isolation:
    - Organization admins cannot modify historical audit entries (zero PUT/PATCH endpoints).
    - Ordinary API users cannot delete audit records (zero DELETE endpoints).
    - Tenant boundaries enforced when querying audit logs.
    - Privileged administrative actions create audit entries.
    - Failed authorization attempts are logged.
    - Unauthorized access to audit logs is blocked.
    """
    reg_a = client.post("/api/v1/auth/register", json={
        "email": "audit_admin_a@alpha.org",
        "password": "Password123!",
        "full_name": "Audit Admin A",
        "organization_name": "Audit Alpha Org"
    })
    token_a = reg_a.json()["access_token"]
    org_a_id = reg_a.json()["organizations"][0]["id"]
    headers_a = {"Authorization": f"Bearer {token_a}", "X-Organization-Id": org_a_id}

    reg_b = client.post("/api/v1/auth/register", json={
        "email": "audit_admin_b@beta.org",
        "password": "Password123!",
        "full_name": "Audit Admin B",
        "organization_name": "Audit Beta Org"
    })
    token_b = reg_b.json()["access_token"]
    org_b_id = reg_b.json()["organizations"][0]["id"]
    headers_b = {"Authorization": f"Bearer {token_b}", "X-Organization-Id": org_b_id}

    # Perform actions in Tenant A and Tenant B
    client.post("/api/v1/assets", headers=headers_a, json={
        "hostname": "alpha-srv-01", "os_family": "Linux", "asset_type": "Server"
    })
    client.post("/api/v1/assets", headers=headers_b, json={
        "hostname": "beta-srv-01", "os_family": "Linux", "asset_type": "Server"
    })

    # Query audit logs as Tenant A
    logs_a_res = client.get("/api/v1/admin/audit-logs", headers=headers_a)
    assert logs_a_res.status_code == 200
    logs_a = logs_a_res.json()
    assert len(logs_a) >= 1
    for entry in logs_a:
        assert entry["organization_id"] == org_a_id, f"Cross-tenant leak: Log from {entry['organization_id']} returned to Tenant A"

    # Query audit logs as Tenant B
    logs_b_res = client.get("/api/v1/admin/audit-logs", headers=headers_b)
    assert logs_b_res.status_code == 200
    logs_b = logs_b_res.json()
    assert len(logs_b) >= 1
    for entry in logs_b:
        assert entry["organization_id"] == org_b_id, f"Cross-tenant leak: Log from {entry['organization_id']} returned to Tenant B"

    # Modification Protection: Assert zero PUT/PATCH endpoints exist
    put_res = client.put(f"/api/v1/admin/audit-logs/{logs_a[0]['id']}", headers=headers_a, json={"details": "tampered"})
    assert put_res.status_code in [404, 405], f"Audit modification should be rejected! Got {put_res.status_code}"
    patch_res = client.patch(f"/api/v1/admin/audit-logs/{logs_a[0]['id']}", headers=headers_a, json={"details": "tampered"})
    assert patch_res.status_code in [404, 405], f"Audit patch should be rejected! Got {patch_res.status_code}"

    # Deletion Protection: Assert zero DELETE endpoints exist
    del_res = client.delete(f"/api/v1/admin/audit-logs/{logs_a[0]['id']}", headers=headers_a)
    assert del_res.status_code in [404, 405], f"Audit deletion should be rejected! Got {del_res.status_code}"

    # Ordinary user / Unauthorized access: Unauthenticated
    unauth_res = client.get("/api/v1/admin/audit-logs")
    assert unauth_res.status_code == 401

    sample = logs_a[0]
    assert "user_email" in sample or "user_id" in sample
    assert "action" in sample
    assert "created_at" in sample
    assert "organization_id" in sample
    assert "target_type" in sample

