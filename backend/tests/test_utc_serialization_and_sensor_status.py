import re
import uuid
from datetime import datetime, timedelta, timezone

from fastapi.testclient import TestClient
from pydantic import BaseModel

from backend.app.api.v1.sensors import compute_sensor_status
from backend.app.config import settings
from backend.app.core.datetime_utils import (
    UTCDatetime,
    ensure_utc,
    serialize_utc_datetime,
)
from backend.app.core.risk_engine import calculate_asset_risk_score
from backend.app.models.assets import Asset, Sensor


ISO_UTC_Z_RE = re.compile(r"^\d{4}-\d{2}-\d{2}T\d{2}:\d{2}:\d{2}(?:\.\d+)?Z$")


class _SampleTimestampModel(BaseModel):
    ts: UTCDatetime
    optional_ts: UTCDatetime | None = None


def test_utc_datetime_helpers_and_pydantic_serializer():
    naive_dt = datetime(2026, 11, 25, 7, 37, 35)
    naive_micro_dt = datetime(2026, 11, 25, 7, 37, 35, 123456)
    aware_utc_dt = datetime(2026, 11, 25, 7, 37, 35, tzinfo=timezone.utc)
    ist_tz = timezone(timedelta(hours=5, minutes=30))
    aware_ist_dt = datetime(2026, 11, 25, 13, 7, 35, tzinfo=ist_tz)

    assert ensure_utc(naive_dt) == aware_utc_dt
    assert ensure_utc(aware_ist_dt) == aware_utc_dt

    assert serialize_utc_datetime(naive_dt) == "2026-11-25T07:37:35Z"
    assert serialize_utc_datetime(naive_micro_dt) == "2026-11-25T07:37:35.123456Z"
    assert serialize_utc_datetime(aware_utc_dt) == "2026-11-25T07:37:35Z"
    assert serialize_utc_datetime(aware_ist_dt) == "2026-11-25T07:37:35Z"
    assert serialize_utc_datetime(None) is None

    model = _SampleTimestampModel(ts=naive_dt, optional_ts=aware_ist_dt)
    dumped = model.model_dump(mode="json")
    assert dumped["ts"] == "2026-11-25T07:37:35Z"
    assert dumped["optional_ts"] == "2026-11-25T07:37:35Z"

    model_none = _SampleTimestampModel(ts=aware_utc_dt, optional_ts=None)
    dumped_none = model_none.model_dump(mode="json")
    assert dumped_none["ts"] == "2026-11-25T07:37:35Z"
    assert dumped_none["optional_ts"] is None


def test_compute_sensor_status_preserves_online_offline_logic():
    now = datetime(2026, 11, 25, 12, 0, 0)  # naive UTC matching DB storage
    timeout = settings.SENSOR_HEARTBEAT_TIMEOUT_SECONDS

    revoked = Sensor(
        name="revoked-host",
        os_type="Windows",
        status="Revoked",
        api_key_hash="test-hash",
        is_token_used=True,
        last_heartbeat=now,
    )
    assert compute_sensor_status(revoked, now=now) == "Revoked"

    pending = Sensor(
        name="pending-host",
        os_type="Windows",
        status="Pending enrollment",
        api_key_hash=None,
        is_token_used=False,
        token_expires_at=now + timedelta(minutes=10),
        last_heartbeat=None,
    )
    assert compute_sensor_status(pending, now=now) == "Pending enrollment"

    never_seen = Sensor(
        name="never-seen-host",
        os_type="Windows",
        status="Online",
        api_key_hash="test-hash",
        is_token_used=True,
        last_heartbeat=None,
    )
    assert compute_sensor_status(never_seen, now=now) == "Offline"

    online_recent = Sensor(
        name="online-host",
        os_type="Windows",
        status="Online",
        api_key_hash="test-hash",
        is_token_used=True,
        last_heartbeat=now - timedelta(seconds=30),
    )
    assert compute_sensor_status(online_recent, now=now) == "Online"

    boundary_online = Sensor(
        name="boundary-host",
        os_type="Windows",
        status="Online",
        api_key_hash="test-hash",
        is_token_used=True,
        last_heartbeat=now - timedelta(seconds=timeout),
    )
    assert compute_sensor_status(boundary_online, now=now) == "Online"

    stale_offline = Sensor(
        name="stale-host",
        os_type="Windows",
        status="Online",
        api_key_hash="test-hash",
        is_token_used=True,
        last_heartbeat=now - timedelta(seconds=timeout + 1),
    )
    assert compute_sensor_status(stale_offline, now=now) == "Offline"


def test_api_endpoints_serialize_utc_z_timestamps(client: TestClient, db_session):
    suffix = uuid.uuid4().hex[:6]
    email = f"utc_tester_{suffix}@defense.org"
    reg = client.post(
        "/api/v1/auth/register",
        json={
            "email": email,
            "password": "StrongPassword123!",
            "full_name": "UTC Verifier",
            "organization_name": f"UTC Test Org {suffix}",
        },
    )
    assert reg.status_code == 200, reg.text
    token = reg.json()["access_token"]
    org_id = reg.json()["organizations"][0]["id"]
    headers = {"Authorization": f"Bearer {token}", "X-Organization-Id": org_id}

    # 1. Asset creation & risk breakdown calculated_at
    asset_res = client.post(
        "/api/v1/assets",
        headers=headers,
        json={"hostname": f"win-host-{suffix}", "os_family": "Windows", "asset_type": "Endpoint"},
    )
    assert asset_res.status_code == 200, asset_res.text
    asset_data = asset_res.json()
    assert ISO_UTC_Z_RE.match(asset_data["last_seen"])
    assert ISO_UTC_Z_RE.match(asset_data["created_at"])

    asset_row = db_session.query(Asset).filter(Asset.id == asset_data["id"]).first()
    assert asset_row is not None
    _, _, risk_breakdown = calculate_asset_risk_score(db_session, asset_row)
    assert ISO_UTC_Z_RE.match(risk_breakdown["calculated_at"])

    # 2. Sensor generate-token -> enroll -> heartbeat -> GET /sensors
    gen_res = client.post(
        "/api/v1/sensors/generate-token",
        headers=headers,
        json={"name": f"Mahesh-{suffix}", "os_type": "Windows"},
    )
    assert gen_res.status_code == 200, gen_res.text
    gen_data = gen_res.json()
    assert ISO_UTC_Z_RE.match(gen_data["token_expires_at"])
    assert ISO_UTC_Z_RE.match(gen_data["created_at"])

    enroll_res = client.post(
        "/api/v1/sensors/enroll",
        json={
            "enrollment_token": gen_data["enrollment_token"],
            "hostname": f"Mahesh-{suffix}",
            "os_type": "Windows",
            "os_version": "Windows 11",
            "capabilities": {"host_metrics": "Available"},
        },
    )
    assert enroll_res.status_code == 200, enroll_res.text
    api_key = enroll_res.json()["api_key"]

    hb_res = client.post(
        "/api/v1/sensors/heartbeat",
        headers={"X-Sensor-Key": api_key},
        json={"cpu_percent": 12.5, "memory_percent": 40.0, "disk_percent": 55.0},
    )
    assert hb_res.status_code == 200, hb_res.text

    sensors_res = client.get("/api/v1/sensors", headers=headers)
    assert sensors_res.status_code == 200, sensors_res.text
    matched = [s for s in sensors_res.json() if s["id"] == gen_data["id"]]
    assert len(matched) == 1
    sensor_out = matched[0]
    assert sensor_out["status"] == "Online"
    assert ISO_UTC_Z_RE.match(sensor_out["last_heartbeat"])
    assert ISO_UTC_Z_RE.match(sensor_out["created_at"])

    # 3. Admin endpoints & audit logs
    health_res = client.get("/api/v1/admin/system-health", headers=headers)
    assert health_res.status_code == 200, health_res.text
    assert ISO_UTC_Z_RE.match(health_res.json()["timestamp"])

    audit_res = client.get("/api/v1/admin/audit-logs", headers=headers)
    assert audit_res.status_code == 200, audit_res.text
    logs = audit_res.json()
    assert len(logs) >= 1
    assert ISO_UTC_Z_RE.match(logs[0]["created_at"])
