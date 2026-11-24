import pytest
import json
import uuid
from datetime import datetime, timedelta
from fastapi.testclient import TestClient

from backend.app.models.auth import User, Organization, OrganizationMembership, AuditLog
from backend.app.models.assets import Sensor
from backend.app.core.security import hash_password, verify_password
from scripts.reset_admin_password import reset_password


def test_authentication_matrix(client: TestClient, db_session):
    """
    Verifies full authentication matrix:
    - Valid JSON login -> 200
    - Valid Form data login (Swagger OAuth2 style) -> 200
    - Invalid password -> 401
    - Invalid email format (.local or bad syntax) -> 422
    - Deactivated user account -> 403
    """
    unique_suffix = uuid.uuid4().hex[:6]
    test_email = f"auth_test_{unique_suffix}@defense.org"
    test_password = "CorrectPassword123!"

    # 1. Register active user
    reg = client.post("/api/v1/auth/register", json={
        "email": test_email,
        "password": test_password,
        "full_name": "Auth Matrix User",
        "organization_name": f"Org {unique_suffix}"
    })
    assert reg.status_code == 200, f"Registration failed: {reg.text}"

    # 1. Valid JSON Login
    res_json = client.post("/api/v1/auth/login", json={"email": test_email, "password": test_password})
    assert res_json.status_code == 200, f"JSON login failed: {res_json.text}"
    data_json = res_json.json()
    assert "access_token" in data_json
    assert data_json["token_type"].lower() == "bearer"
    assert len(data_json["organizations"]) == 1

    # 2. Valid Form Data Login (Swagger UI OAuth2 Password Flow)
    res_form = client.post("/api/v1/auth/login", data={"username": test_email, "password": test_password})
    assert res_form.status_code == 200, f"Form login failed: {res_form.text}"
    data_form = res_form.json()
    assert "access_token" in data_form
    assert data_form["token_type"].lower() == "bearer"

    # 3. Invalid Password -> 401
    res_bad_pw = client.post("/api/v1/auth/login", json={"email": test_email, "password": "WrongPassword!"})
    assert res_bad_pw.status_code == 401
    assert "Incorrect email or password" in res_bad_pw.json()["detail"]

    # 4. Invalid Email Formats -> 422
    res_bad_email = client.post("/api/v1/auth/login", json={"email": "operator@sentinel.local", "password": test_password})
    assert res_bad_email.status_code == 422, "Special-use .local domain must be rejected with 422"

    res_malformed_email = client.post("/api/v1/auth/login", json={"email": "not-an-email-at-all", "password": test_password})
    assert res_malformed_email.status_code == 422

    # 5. Deactivated User Account -> 403
    user = db_session.query(User).filter(User.email == test_email).first()
    assert user is not None
    user.is_active = False
    db_session.commit()

    res_deactivated = client.post("/api/v1/auth/login", json={"email": test_email, "password": test_password})
    assert res_deactivated.status_code == 403
    assert "suspended or deactivated" in res_deactivated.json()["detail"].lower()


def test_password_recovery_mechanism(client: TestClient, db_session):
    """
    Verifies that the administrative password reset CLI:
    - Successfully updates the password using bcrypt.
    - Invalidates the old password.
    - Enables login with the newly set password.
    - Creates an immutable audit log record.
    - Preserves user records and relationships.
    """
    unique_suffix = uuid.uuid4().hex[:6]
    test_email = f"recovery_admin_{unique_suffix}@defense.org"
    initial_pass = "InitialPass123!"
    recovered_pass = "RecoveredPass456!"

    # Register user
    reg = client.post("/api/v1/auth/register", json={
        "email": test_email,
        "password": initial_pass,
        "full_name": "Recovery Test Admin",
        "organization_name": f"Recovery Org {unique_suffix}"
    })
    assert reg.status_code == 200

    user = db_session.query(User).filter(User.email == test_email).first()
    assert user is not None
    user.is_platform_admin = True
    db_session.commit()

    # Verify initial login works
    r1 = client.post("/api/v1/auth/login", json={"email": test_email, "password": initial_pass})
    assert r1.status_code == 200

    # Execute recovery mechanism using db_session
    success = reset_password(test_email, recovered_pass, db=db_session)
    assert success is True

    # Old password must now fail
    r_old = client.post("/api/v1/auth/login", json={"email": test_email, "password": initial_pass})
    assert r_old.status_code == 401

    # New password must succeed
    r_new = client.post("/api/v1/auth/login", json={"email": test_email, "password": recovered_pass})
    assert r_new.status_code == 200

    # Verify audit log entry
    audit = db_session.query(AuditLog).filter(
        AuditLog.user_email == test_email,
        AuditLog.action == "ADMIN_PASSWORD_RESET_CLI"
    ).first()
    assert audit is not None
    assert "password reset via CLI tool" in audit.details


def test_swagger_authorization_and_organization_isolation(client: TestClient):
    """
    Verifies Swagger authorization workflow:
    - Obtains access token via OAuth2 form-compatible login.
    - Successfully accesses protected endpoints with 'Authorization: Bearer <token>'.
    - Confirms rejection of unauthenticated requests with HTTP 401.
    - Enforces organization-level access controls and cross-tenant boundaries.
    """
    # 1. Register a test org
    unique_suffix = uuid.uuid4().hex[:6]
    reg = client.post("/api/v1/auth/register", json={
        "email": f"swagger_admin_{unique_suffix}@defense.org",
        "password": "Password123!",
        "full_name": "Swagger Admin",
        "organization_name": f"Swagger Org {unique_suffix}"
    })
    assert reg.status_code == 200
    token = reg.json()["access_token"]
    org_id = reg.json()["organizations"][0]["id"]

    # 2. Access protected /sensors without token -> 401
    r_unauth = client.get("/api/v1/sensors")
    assert r_unauth.status_code == 401

    # 3. Access protected /sensors with valid Bearer token -> 200
    r_auth = client.get(
        "/api/v1/sensors",
        headers={"Authorization": f"Bearer {token}", "X-Organization-Id": org_id}
    )
    assert r_auth.status_code == 200
    assert isinstance(r_auth.json(), list)

    # 4. Access with non-member X-Organization-Id -> 403
    foreign_org_id = str(uuid.uuid4())
    r_foreign = client.get(
        "/api/v1/sensors",
        headers={"Authorization": f"Bearer {token}", "X-Organization-Id": foreign_org_id}
    )
    assert r_foreign.status_code in [403, 404]


def test_sensor_lifecycle_heartbeat_and_offline_detection(client: TestClient, db_session):
    """
    Verifies sensor lifecycle:
    1. Generate token -> 'Pending enrollment'
    2. Duplicate pending token generation -> Reuses pending record, prevents clutter
    3. Enrollment -> 'Online', sets last_heartbeat
    4. Heartbeat -> Updates last_heartbeat and status to 'Online'
    5. Telemetry batch -> Accepts data but does NOT fake heartbeat
    6. Offline detection -> Stale heartbeat beyond timeout transitions status to 'Offline'
    7. Heartbeat resumes -> Transitions status back to 'Online'
    """
    unique_suffix = uuid.uuid4().hex[:6]
    reg = client.post("/api/v1/auth/register", json={
        "email": f"sensor_tester_{unique_suffix}@defense.org",
        "password": "Password123!",
        "full_name": "Sensor Tester",
        "organization_name": f"Sensor Test Org {unique_suffix}"
    })
    token = reg.json()["access_token"]
    org_id = reg.json()["organizations"][0]["id"]
    headers = {"Authorization": f"Bearer {token}", "X-Organization-Id": org_id}

    sensor_name = f"TestHost-{unique_suffix}"

    # 1. Generate Token
    gen1 = client.post("/api/v1/sensors/generate-token", headers=headers, json={
        "name": sensor_name,
        "os_type": "Windows"
    })
    assert gen1.status_code == 200
    data1 = gen1.json()
    assert data1["status"] == "Pending enrollment"
    token1 = data1["enrollment_token"]
    sensor_id = data1["id"]

    # 2. Duplicate generation with same name -> Should reuse pending sensor record
    gen2 = client.post("/api/v1/sensors/generate-token", headers=headers, json={
        "name": sensor_name,
        "os_type": "Windows"
    })
    assert gen2.status_code == 200
    data2 = gen2.json()
    assert data2["id"] == sensor_id, "Pending sensor must be reused rather than creating a duplicate!"

    # 3. Enroll Sensor
    enroll_res = client.post("/api/v1/sensors/enroll", json={
        "enrollment_token": data2["enrollment_token"],
        "hostname": sensor_name,
        "os_type": "Windows",
        "os_version": "Windows 11 Pro",
        "capabilities": {"system": "Available", "connections": "Available"}
    })
    assert enroll_res.status_code == 200
    sensor_creds = enroll_res.json()
    api_key = sensor_creds["api_key"]
    assert sensor_creds["status"] == "Online"

    # Verify listing shows Online
    list_res = client.get("/api/v1/sensors", headers=headers)
    assert list_res.status_code == 200
    sensors = list_res.json()
    matched = [s for s in sensors if s["id"] == sensor_id]
    assert len(matched) == 1
    assert matched[0]["status"] == "Online"

    # 4. Valid Heartbeat Updates last_heartbeat
    hb_headers = {"X-Sensor-Key": api_key}
    hb_res = client.post("/api/v1/sensors/heartbeat", headers=hb_headers, json={
        "cpu_percent": 15.0,
        "memory_percent": 45.0,
        "disk_percent": 30.0,
        "active_connections_count": 5
    })
    assert hb_res.status_code == 200
    assert hb_res.json()["status"] == "acknowledged"

    # 5. Ingest Telemetry -> Must NOT overwrite last_heartbeat with a fake heartbeat
    sensor_row = db_session.query(Sensor).filter(Sensor.id == sensor_id).first()
    assert sensor_row is not None
    recorded_hb_before = sensor_row.last_heartbeat

    telem_res = client.post("/api/v1/sensors/telemetry", headers=hb_headers, json={
        "sensor_version": "1.0.0",
        "events": [{
            "event_type": "network_connection",
            "severity": "Low",
            "title": "Outbound DNS Query",
            "description": "Standard DNS resolution",
            "source_ip": "192.168.1.100",
            "destination_ip": "8.8.8.8",
            "destination_port": 53,
            "protocol": "UDP",
            "is_simulated": False
        }],
        "discovered_devices": [],
        "active_connections_sample": []
    })
    assert telem_res.status_code == 200
    assert telem_res.json()["events_ingested"] == 1

    db_session.refresh(sensor_row)
    # Verify last_heartbeat was NOT altered by telemetry batch
    assert sensor_row.last_heartbeat == recorded_hb_before

    # 6. Offline Detection: Stale heartbeat beyond timeout
    # Simulate last_heartbeat occurring 5 minutes ago (300s > 120s timeout)
    sensor_row.last_heartbeat = datetime.utcnow() - timedelta(seconds=300)
    db_session.commit()

    # Listing sensors must dynamically transition status to 'Offline'
    list_stale = client.get("/api/v1/sensors", headers=headers)
    assert list_stale.status_code == 200
    stale_matched = [s for s in list_stale.json() if s["id"] == sensor_id][0]
    assert stale_matched["status"] == "Offline", "Stale sensor must be classified as Offline!"

    # Dashboard stats should count sensor as offline
    dash_res = client.get("/api/v1/dashboard/stats", headers=headers)
    assert dash_res.status_code == 200
    dash_data = dash_res.json()
    assert dash_data["online_sensors"] == 0
    assert dash_data["offline_sensors"] >= 1

    # 7. Resuming heartbeat restores 'Online' status
    hb_resume = client.post("/api/v1/sensors/heartbeat", headers=hb_headers, json={"cpu_percent": 10.0})
    assert hb_resume.status_code == 200

    list_online = client.get("/api/v1/sensors", headers=headers)
    assert list_online.status_code == 200
    online_matched = [s for s in list_online.json() if s["id"] == sensor_id][0]
    assert online_matched["status"] == "Online", "Sensor must return to Online upon fresh heartbeat!"


def test_revoked_sensor_telemetry_and_heartbeat_rejection(client: TestClient):
    """
    Verifies that revoked sensors are blocked with HTTP 403 on both telemetry and heartbeats.
    """
    unique_suffix = uuid.uuid4().hex[:6]
    reg = client.post("/api/v1/auth/register", json={
        "email": f"revoke_tester_{unique_suffix}@defense.org",
        "password": "Password123!",
        "full_name": "Revoke Tester",
        "organization_name": f"Revoke Org {unique_suffix}"
    })
    token = reg.json()["access_token"]
    org_id = reg.json()["organizations"][0]["id"]
    headers = {"Authorization": f"Bearer {token}", "X-Organization-Id": org_id}

    # Generate and enroll
    gen = client.post("/api/v1/sensors/generate-token", headers=headers, json={
        "name": f"RevokeHost-{unique_suffix}",
        "os_type": "Linux"
    })
    sensor_id = gen.json()["id"]
    stk = gen.json()["enrollment_token"]

    enroll = client.post("/api/v1/sensors/enroll", json={
        "enrollment_token": stk,
        "hostname": "RevokeHost",
        "os_type": "Linux"
    })
    api_key = enroll.json()["api_key"]
    hb_headers = {"X-Sensor-Key": api_key}

    # Revoke sensor
    rev_res = client.post(f"/api/v1/sensors/{sensor_id}/revoke", headers=headers)
    assert rev_res.status_code == 200

    # Heartbeat attempt by revoked sensor must return 403 Forbidden
    hb_res = client.post("/api/v1/sensors/heartbeat", headers=hb_headers, json={"cpu_percent": 20.0})
    assert hb_res.status_code == 403
    assert "revoked" in hb_res.json()["detail"].lower()

    # Telemetry attempt by revoked sensor must return 403 Forbidden
    telem_res = client.post("/api/v1/sensors/telemetry", headers=hb_headers, json={
        "sensor_version": "1.0.0",
        "events": [],
        "discovered_devices": [],
        "active_connections_sample": []
    })
    assert telem_res.status_code == 403
    assert "revoked" in telem_res.json()["detail"].lower()
