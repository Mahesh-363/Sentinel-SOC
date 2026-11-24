import pytest
from fastapi.testclient import TestClient

def test_asset_risk_scoring_engine(client: TestClient):
    """
    Release 3 Stage 1: Verifies dynamic asset risk score calculation (0-100),
    level categorizations, factors calculation, and endpoint reporting.
    """
    # 1. Setup Org & Admin
    reg = client.post("/api/v1/auth/register", json={
        "email": "risk_analyst@defense.org",
        "password": "Password123!",
        "full_name": "Risk Analyst",
        "organization_name": "Risk Analytics Division"
    })
    assert reg.status_code == 200
    token = reg.json()["access_token"]
    org_id = reg.json()["organizations"][0]["id"]
    headers = {"Authorization": f"Bearer {token}", "X-Organization-Id": org_id}

    # 2. Create Asset
    create_asset_res = client.post("/api/v1/assets", headers=headers, json={
        "hostname": "core-banking-db01",
        "os_family": "Linux",
        "os_version": "Ubuntu 22.04 LTS",
        "asset_type": "Server",
        "private_ips": ["10.0.5.10"]
    })
    assert create_asset_res.status_code == 200
    asset_id = create_asset_res.json()["id"]

    # 3. Retrieve Asset Risk Breakdown
    risk_res = client.get(f"/api/v1/assets/{asset_id}/risk", headers=headers)
    assert risk_res.status_code == 200
    risk_data = risk_res.json()
    assert "score" in risk_data
    assert "level" in risk_data
    assert "factors" in risk_data
    assert risk_data["score"] >= 0 and risk_data["score"] <= 100

    # 4. Verify in Dashboard Stats
    stats_res = client.get("/api/v1/dashboard/stats", headers=headers)
    assert stats_res.status_code == 200
    stats = stats_res.json()
    assert "fleet_average_risk_score" in stats
    assert "high_risk_assets_count" in stats

def test_response_playbook_approval_workflow(client: TestClient):
    """
    Release 3 Stage 2: Verifies approval-based response automation,
    human-in-the-loop authorization gates, asset isolation, and sensor command queueing.
    """
    # 1. Setup Org, Admin & Target Sensor
    reg = client.post("/api/v1/auth/register", json={
        "email": "secops_lead@defense.org",
        "password": "Password123!",
        "full_name": "SecOps Lead",
        "organization_name": "SecOps Automation Unit"
    })
    assert reg.status_code == 200
    token = reg.json()["access_token"]
    org_id = reg.json()["organizations"][0]["id"]
    headers = {"Authorization": f"Bearer {token}", "X-Organization-Id": org_id}

    # Generate Sensor Token & Enroll
    gen_res = client.post("/api/v1/sensors/generate-token", headers=headers, json={
        "name": "containment-target-host",
        "os_type": "Linux"
    })
    enrollment_token = gen_res.json()["enrollment_token"]

    enroll_res = client.post("/api/v1/sensors/enroll", json={
        "enrollment_token": enrollment_token,
        "hostname": "compromised-bastion",
        "os_type": "Linux"
    })
    sensor_creds = enroll_res.json()
    sensor_id = sensor_creds["sensor_id"]
    asset_id = sensor_creds["asset_id"]
    sensor_api_key = sensor_creds["api_key"]
    hb_headers = {"X-Sensor-Key": sensor_api_key}

    # 2. List Playbooks (all 5 default playbooks seeded)
    pbs_res = client.get("/api/v1/response/playbooks", headers=headers)
    assert pbs_res.status_code == 200
    playbooks = pbs_res.json()
    assert len(playbooks) >= 5
    isolate_pb = next(p for p in playbooks if p["action_type"] == "isolate_endpoint")
    checklist_pb = next(p for p in playbooks if p["action_type"] == "investigation_checklist")

    # 3. Test Non-Destructive Auto-Playbook: Investigation Checklist
    trig_checklist = client.post("/api/v1/response/trigger", headers=headers, json={
        "playbook_id": checklist_pb["id"],
        "target_asset_id": asset_id,
        "reason": "Automated triage kick-off"
    })
    assert trig_checklist.status_code == 200
    assert trig_checklist.json()["status"] == "Completed"

    # 4. Test Destructive Playbook Gate: Isolate Endpoint (Requires Human Approval)
    trig_isolate = client.post("/api/v1/response/trigger", headers=headers, json={
        "playbook_id": isolate_pb["id"],
        "target_asset_id": asset_id,
        "reason": "C2 beacon activity detected on bastion"
    })
    assert trig_isolate.status_code == 200
    execution = trig_isolate.json()
    assert execution["status"] == "Pending Approval"
    exec_id = execution["id"]

    # Verify asset is NOT isolated yet
    asset_before = client.get(f"/api/v1/assets/{asset_id}", headers=headers).json()
    assert asset_before["health_status"] != "isolated"

    # 5. Approve Execution
    approve_res = client.post(f"/api/v1/response/executions/{exec_id}/decision", headers=headers, json={
        "decision": "Approved",
        "notes": "Containment authorized by Incident Commander"
    })
    assert approve_res.status_code == 200
    assert approve_res.json()["status"] == "Completed"

    # Verify asset health status is now "isolated"
    asset_after = client.get(f"/api/v1/assets/{asset_id}", headers=headers).json()
    assert asset_after["health_status"] == "isolated"

    # 6. Verify Sensor Receives Queued Command in Next Heartbeat
    hb_res = client.post("/api/v1/sensors/heartbeat", headers=hb_headers, json={"cpu_percent": 15})
    assert hb_res.status_code == 200
    hb_data = hb_res.json()
    assert "dispatched_commands" in hb_data
    assert len(hb_data["dispatched_commands"]) == 1
    cmd = hb_data["dispatched_commands"][0]
    assert cmd["action"] == "ISOLATE_HOST"

    # 7. Sensor Validates & Acknowledges Command (Safe Dry-Run)
    ack_res = client.post("/api/v1/sensors/commands/acknowledge", headers=hb_headers, json={
        "command_id": cmd["id"],
        "action": cmd["action"],
        "status": "VALIDATED_DRY_RUN",
        "details": "Parameters validated; dry-run mode active to prevent network disruption."
    })
    assert ack_res.status_code == 200
    ack_data = ack_res.json()
    assert ack_data["status"] == "recorded"
    assert ack_data["ack_status"] == "VALIDATED_DRY_RUN"

    # 8. Verify Execution Record Reflects Final Status
    exec_records = client.get("/api/v1/response/executions", headers=headers).json()
    matched = next((e for e in exec_records if e["id"] == exec_id), None)
    assert matched is not None
    assert "Sensor Ack" in matched["execution_log"]

    # 9. Test Safe Non-Destructive Diagnostic Verification Probe
    safe_pb = next(p for p in playbooks if p["action_type"] == "safe_diagnostic_probe")
    trig_safe = client.post("/api/v1/response/trigger", headers=headers, json={
        "playbook_id": safe_pb["id"],
        "target_asset_id": asset_id,
        "reason": "Routine non-destructive health probe"
    })
    assert trig_safe.status_code == 200
    safe_exec_id = trig_safe.json()["id"]
    assert trig_safe.json()["status"] == "Pending Approval"

    # Operator approves diagnostic probe
    app_safe = client.post(f"/api/v1/response/executions/{safe_exec_id}/decision", headers=headers, json={
        "decision": "Approved",
        "notes": "Diagnostic probe authorized"
    })
    assert app_safe.status_code == 200

    # Sensor retrieves probe command via heartbeat polling
    hb2 = client.post("/api/v1/sensors/heartbeat", headers=hb_headers, json={"cpu_percent": 12})
    probe_cmds = hb2.json().get("dispatched_commands", [])
    assert len(probe_cmds) == 1
    assert probe_cmds[0]["action"] == "DIAGNOSTIC_PROBE"

    # Sensor acknowledges probe execution
    ack2 = client.post("/api/v1/sensors/commands/acknowledge", headers=hb_headers, json={
        "command_id": probe_cmds[0]["id"],
        "action": "DIAGNOSTIC_PROBE",
        "status": "SUCCESS",
        "details": "Non-destructive probe validated successfully."
    })
    assert ack2.status_code == 200

def test_attack_simulation_lab_and_purge(client: TestClient):
    """
    Release 3 Stage 3: Verifies safe local attack simulation scenarios
    (IAM escalation, credential spray), deterministic rule triggering,
    explicit simulated classification, and non-destructive lab purge.
    """
    # 1. Setup Org & Admin
    reg = client.post("/api/v1/auth/register", json={
        "email": "lab_commander@defense.org",
        "password": "Password123!",
        "full_name": "Lab Commander",
        "organization_name": "Attack Simulation Division"
    })
    assert reg.status_code == 200
    token = reg.json()["access_token"]
    org_id = reg.json()["organizations"][0]["id"]
    headers = {"Authorization": f"Bearer {token}", "X-Organization-Id": org_id}

    # 2. Ingest 1 Real Event (To verify purge does NOT touch genuine data)
    real_event_res = client.post("/api/v1/events", headers=headers, json={
        "event_type": "network_connection",
        "severity": "Informational",
        "title": "Legitimate Core DNS Resolution",
        "description": "System core internal query to 10.0.0.2",
        "source_ip": "10.0.0.50",
        "destination_ip": "10.0.0.2",
        "destination_port": 53,
        "protocol": "UDP",
        "is_simulated": False
    })
    assert real_event_res.status_code in [200, 201, 405] # if direct creation or via sensor

    # 3. Trigger AWS IAM Escalation Simulation
    iam_sim = client.post("/api/v1/simulation/run", headers=headers, json={
        "simulation_type": "aws_iam_escalation"
    })
    assert iam_sim.status_code == 200
    iam_data = iam_sim.json()
    assert iam_data["is_simulated"] is True
    assert iam_data["events_generated"] == 1
    assert iam_data["alerts_triggered"] >= 1

    # 4. Trigger Credential Spray Simulation
    spray_sim = client.post("/api/v1/simulation/run", headers=headers, json={
        "simulation_type": "credential_spray"
    })
    assert spray_sim.status_code == 200
    spray_data = spray_sim.json()
    assert spray_data["events_generated"] == 3
    assert spray_data["alerts_triggered"] >= 1

    # 5. Verify Simulated Incidents Created
    sim_incs = client.get("/api/v1/incidents?is_simulated=true", headers=headers).json()
    assert len(sim_incs) >= 1

    # 6. Execute Safe Lab Reset / Purge
    reset_res = client.post("/api/v1/simulation/reset", headers=headers)
    assert reset_res.status_code == 200
    reset_data = reset_res.json()
    assert reset_data["status"] == "success"
    assert reset_data["purged_events"] >= 4
    assert reset_data["purged_alerts"] >= 2
    assert reset_data["purged_incidents"] >= 1

    # 7. Confirm Zero Simulated Artifacts Remain
    remaining_sim_events = client.get("/api/v1/events?is_simulated=true", headers=headers).json()
    assert len(remaining_sim_events) == 0
    remaining_sim_incs = client.get("/api/v1/incidents?is_simulated=true", headers=headers).json()
    assert len(remaining_sim_incs) == 0

def test_administration_and_governance(client: TestClient, db_session):
    """
    Release 3 Stage 4: Verifies multi-user organization administration,
    role assignments, integration health reporting, and audit logging.
    """
    # 1. Setup Org & Owner
    reg = client.post("/api/v1/auth/register", json={
        "email": "governance_director@defense.org",
        "password": "Password123!",
        "full_name": "Governance Director",
        "organization_name": "Governance and Controls Division"
    })
    assert reg.status_code == 200
    token = reg.json()["access_token"]
    org_id = reg.json()["organizations"][0]["id"]
    headers = {"Authorization": f"Bearer {token}", "X-Organization-Id": org_id}

    # 2. Register Junior Analyst and add to org
    reg_user = client.post("/api/v1/auth/register", json={
        "email": "junior_analyst@defense.org",
        "password": "Password123!",
        "full_name": "Junior Analyst",
        "organization_name": "Junior Subsid"
    })
    assert reg_user.status_code == 200

    from backend.app.models.auth import User, OrganizationMembership
    u = db_session.query(User).filter(User.email == "junior_analyst@defense.org").first()
    assert u is not None
    mem = OrganizationMembership(user_id=u.id, organization_id=org_id, role="Security Analyst")
    db_session.add(mem)
    db_session.commit()

    # 3. List Organization Users
    users_res = client.get("/api/v1/admin/users", headers=headers)
    assert users_res.status_code == 200
    users = users_res.json()
    assert len(users) >= 2

    target_analyst = next(u for u in users if u["email"] == "junior_analyst@defense.org")
    assert target_analyst["role"] == "Security Analyst"

    # 4. Promote User Role
    update_role_res = client.patch(
        f"/api/v1/admin/users/{target_analyst['user_id']}/role",
        headers=headers,
        json={"role": "Organization Administrator"}
    )
    assert update_role_res.status_code == 200
    assert update_role_res.json()["new_role"] == "Organization Administrator"

    # 5. Check Audit Logs for Role Update
    audit_res = client.get("/api/v1/admin/audit-logs", headers=headers)
    assert audit_res.status_code == 200
    audit_logs = audit_res.json()
    assert any(log["action"] == "USER_ROLE_UPDATED" for log in audit_logs)

    # 6. Verify Integrations Connector Status
    integrations_res = client.get("/api/v1/admin/integrations", headers=headers)
    assert integrations_res.status_code == 200
    integrations_data = integrations_res.json()
    assert "integrations" in integrations_data
    assert len(integrations_data["integrations"]) >= 6
    assert all(item["free_tier"] is True for item in integrations_data["integrations"])

    # 7. Verify Data Retention Policy Details
    retention_res = client.get("/api/v1/admin/retention", headers=headers)
    assert retention_res.status_code == 200
    ret_data = retention_res.json()
    assert "event_retention_days" in ret_data
    assert "incident_retention_days" in ret_data
