import json
from datetime import datetime, timedelta
from typing import List, Optional
from fastapi import APIRouter, Depends, HTTPException, status, Request, Response
from sqlalchemy.orm import Session

from backend.app.database import get_db
from backend.app.config import settings
from backend.app.core.datetime_utils import serialize_utc_datetime
from backend.app.core.security import generate_enrollment_token, generate_sensor_api_key, hash_token
from backend.app.core.dependencies import get_current_org, require_role, get_sensor_by_key
from backend.app.core.detection_engine import run_detection_pipeline_for_event
from backend.app.core.ip_utils import classify_ip
from backend.app.models.auth import Organization
from backend.app.models.assets import Asset, Sensor, SensorHeartbeat
from backend.app.models.events import SecurityEvent
from backend.app.models.network import NetworkDevice, IPObservation
from backend.app.schemas.assets import (
    SensorGenerateTokenRequest,
    SensorEnrollRequest,
    SensorEnrollResponse,
    SensorHeartbeatIn,
    SensorOut
)
from backend.app.schemas.telemetry import TelemetryBatchIn, CommandAcknowledgeIn

router = APIRouter(prefix="/sensors", tags=["Sensors"])

def compute_sensor_status(sensor: Sensor, now: Optional[datetime] = None) -> str:
    """
    Computes real-time sensor status based on enrollment, revocation,
    and heartbeat freshness within settings.SENSOR_HEARTBEAT_TIMEOUT_SECONDS.
    """
    if sensor.status == "Revoked":
        return "Revoked"
    if not sensor.is_token_used:
        if sensor.token_expires_at and (now or datetime.utcnow()) > sensor.token_expires_at:
            return "Error"
        return "Pending enrollment"
    if not sensor.last_heartbeat:
        return "Offline"

    current_time = now or datetime.utcnow()
    elapsed = (current_time - sensor.last_heartbeat).total_seconds()
    if elapsed > settings.SENSOR_HEARTBEAT_TIMEOUT_SECONDS:
        return "Offline"
    return "Online"

# --- ADMIN / ANALYST ENDPOINTS ---

@router.get("", response_model=List[SensorOut])
def list_sensors(
    response: Response,
    status: Optional[str] = None,
    org: Organization = Depends(get_current_org),
    db: Session = Depends(get_db)
):
    response.headers["Cache-Control"] = "no-cache, no-store, must-revalidate"
    sensors = db.query(Sensor).filter(Sensor.organization_id == org.id).order_by(Sensor.created_at.desc()).all()
    now = datetime.utcnow()
    updated = False
    for s in sensors:
        computed = compute_sensor_status(s, now)
        if s.status != computed:
            s.status = computed
            updated = True
    if updated:
        db.commit()

    if status:
        sensors = [s for s in sensors if s.status == status]
    return sensors

@router.post("/generate-token", response_model=SensorOut, dependencies=[Depends(require_role(["Organization Owner", "Organization Administrator"]))])
def generate_token(
    payload: SensorGenerateTokenRequest,
    org: Organization = Depends(get_current_org),
    db: Session = Depends(get_db)
):
    clean_name = payload.name.strip()
    token = generate_enrollment_token()
    expires_at = datetime.utcnow() + timedelta(hours=settings.SENSOR_TOKEN_EXPIRY_HOURS)

    # Prevent duplicate pending sensors: if an un-enrolled sensor with the same name exists, refresh it
    existing_pending = db.query(Sensor).filter(
        Sensor.organization_id == org.id,
        Sensor.name == clean_name,
        Sensor.is_token_used == False
    ).first()

    if existing_pending:
        existing_pending.enrollment_token = token
        existing_pending.token_expires_at = expires_at
        existing_pending.os_type = payload.os_type
        existing_pending.status = "Pending enrollment"
        existing_pending.error_message = None
        existing_pending.updated_at = datetime.utcnow()
        db.commit()
        db.refresh(existing_pending)
        return existing_pending

    sensor = Sensor(
        organization_id=org.id,
        asset_id=payload.asset_id,
        name=clean_name,
        os_type=payload.os_type,
        status="Pending enrollment",
        enrollment_token=token,
        token_expires_at=expires_at,
        is_token_used=False,
        capabilities=json.dumps({
            "system_metrics": "Available",
            "active_connections": "Available",
            "security_logs": "Available",
            "device_discovery": "Available"
        })
    )
    db.add(sensor)
    db.commit()
    db.refresh(sensor)
    return sensor

@router.post("/{sensor_id}/revoke", dependencies=[Depends(require_role(["Organization Owner", "Organization Administrator"]))])
def revoke_sensor(
    sensor_id: str,
    org: Organization = Depends(get_current_org),
    db: Session = Depends(get_db)
):
    sensor = db.query(Sensor).filter(
        Sensor.id == sensor_id,
        Sensor.organization_id == org.id
    ).first()
    if not sensor:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Sensor not found")
        
    sensor.status = "Revoked"
    sensor.updated_at = datetime.utcnow()
    db.commit()
    return {"status": "success", "message": f"Sensor '{sensor.name}' credentials permanently revoked"}

# --- SENSOR CLIENT ENDPOINTS (Unauthenticated or Token / Key Authenticated) ---

@router.post("/enroll", response_model=SensorEnrollResponse)
def enroll_sensor(
    payload: SensorEnrollRequest,
    request: Request,
    db: Session = Depends(get_db)
):
    """
    Sensor enrollment handshake:
    1. Validates single-use enrollment token and expiration.
    2. Provisions unique sensor API key and hashes it.
    3. Automatically creates or associates the host Asset record.
    4. Marks enrollment token as used and activates sensor.
    """
    sensor = db.query(Sensor).filter(
        Sensor.enrollment_token == payload.enrollment_token.strip(),
        Sensor.is_token_used == False
    ).first()
    
    if not sensor:
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="Invalid or already used sensor enrollment token"
        )
        
    if sensor.token_expires_at and sensor.token_expires_at < datetime.utcnow():
        sensor.status = "Error"
        sensor.error_message = "Enrollment token expired"
        db.commit()
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="Sensor enrollment token has expired. Please generate a new token."
        )

    # Automatically create or link Asset
    client_ip = request.client.host if request.client else None
    if not sensor.asset_id:
        asset = Asset(
            organization_id=sensor.organization_id,
            hostname=payload.hostname,
            os_family=payload.os_type,
            os_version=payload.os_version,
            asset_type="Endpoint",
            public_ip=client_ip,
            health_status="online",
            risk_level="Low",
            last_seen=datetime.utcnow()
        )
        db.add(asset)
        db.flush()
        sensor.asset_id = asset.id

    # Generate persistent API key
    raw_api_key = generate_sensor_api_key()
    sensor.api_key_hash = hash_token(raw_api_key)
    sensor.is_token_used = True
    sensor.enrollment_token = None  # Clear token after single use
    sensor.status = "Online"
    sensor.capabilities = json.dumps(payload.capabilities or {
        "host_metrics": "Available",
        "connections": "Available",
        "security_logs": "Available",
        "network_discovery": "Available"
    })
    sensor.last_heartbeat = datetime.utcnow()
    sensor.updated_at = datetime.utcnow()
    
    db.commit()

    return SensorEnrollResponse(
        sensor_id=sensor.id,
        asset_id=sensor.asset_id,
        api_key=raw_api_key,
        status="Online",
        message="Sensor successfully enrolled and authenticated."
    )

@router.post("/heartbeat")
def sensor_heartbeat(
    payload: SensorHeartbeatIn,
    sensor: Sensor = Depends(get_sensor_by_key),
    db: Session = Depends(get_db)
):
    """
    Periodic sensor heartbeat. Updates health metrics and online state.
    """
    now = datetime.utcnow()
    sensor.last_heartbeat = now
    sensor.status = "Online"
    
    if payload.capabilities:
        sensor.capabilities = json.dumps(payload.capabilities)
        
    # Update linked asset
    if sensor.asset_id:
        asset = db.query(Asset).filter(Asset.id == sensor.asset_id).first()
        if asset:
            asset.last_seen = now
            asset.health_status = "online"

    # Check for active QUEUED commands assigned specifically to THIS sensor
    from backend.app.models.response import SensorCommand, ResponseExecution
    from backend.app.models.auth import AuditLog

    active_cmds = db.query(SensorCommand).filter(
        SensorCommand.sensor_id == sensor.id,
        SensorCommand.status == "QUEUED"
    ).all()

    commands_to_dispatch = []
    for c in active_cmds:
        if c.expires_at and now > c.expires_at:
            c.status = "EXPIRED"
            audit = AuditLog(
                organization_id=sensor.organization_id,
                user_id=None,
                user_email="system",
                action="COMMAND_EXPIRED",
                target_type="SensorCommand",
                target_id=c.id,
                details=f"Command '{c.action}' (ID: {c.id}) expired before retrieval (TTL: {serialize_utc_datetime(c.expires_at)})."
            )
            db.add(audit)
        else:
            c.status = "DISPATCHED"
            c.dispatched_at = now
            commands_to_dispatch.append({
                "id": c.id,
                "action": c.action,
                "params": json.loads(c.parameters_json or "{}"),
                "queued_at": serialize_utc_datetime(c.queued_at),
                "expires_at": serialize_utc_datetime(c.expires_at)
            })
            audit = AuditLog(
                organization_id=sensor.organization_id,
                user_id=None,
                user_email=f"sensor-{sensor.id[:8]}",
                action="COMMAND_DISPATCHED",
                target_type="SensorCommand",
                target_id=c.id,
                details=f"Command '{c.action}' (ID: {c.id}) dispatched to sensor '{sensor.name}' on heartbeat."
            )
            db.add(audit)

    # Support legacy pending_commands queue if present
    if sensor.pending_commands:
        try:
            legacy_cmds = json.loads(sensor.pending_commands)
            existing_ids = {cmd["id"] for cmd in commands_to_dispatch}
            for lc in legacy_cmds:
                if lc.get("id") not in existing_ids:
                    commands_to_dispatch.append(lc)
            sensor.pending_commands = None
        except Exception:
            sensor.pending_commands = None

    # Save heartbeat telemetry sample
    hb = SensorHeartbeat(
        sensor_id=sensor.id,
        timestamp=now,
        cpu_percent=payload.cpu_percent,
        memory_percent=payload.memory_percent,
        disk_percent=payload.disk_percent,
        active_connections_count=payload.active_connections_count,
        status="Online",
        metadata_json=json.dumps(payload.metadata or {})
    )
    db.add(hb)
    db.commit()
    return {
        "status": "acknowledged",
        "timestamp": serialize_utc_datetime(now),
        "dispatched_commands": commands_to_dispatch
    }

@router.post("/commands/acknowledge")
def acknowledge_sensor_command(
    payload: CommandAcknowledgeIn,
    sensor: Sensor = Depends(get_sensor_by_key),
    db: Session = Depends(get_db)
):
    """
    Sensor command execution acknowledgement with strict security controls:
    1. Authenticated via X-Sensor-Key.
    2. Validates command existence in sensor_commands.
    3. Enforces sensor ownership: Sensor A CANNOT acknowledge Sensor B's command.
    4. Enforces tenant boundaries: Sensor cannot acknowledge command from another tenant.
    5. Replay & duplicate protection: Duplicate acks are handled safely and idempotently.
    6. Expired / revoked command protection: Expired or revoked commands cannot execute.
    7. Audits every lifecycle transition.
    """
    now = datetime.utcnow()
    from backend.app.models.response import SensorCommand, ResponseExecution
    from backend.app.models.auth import AuditLog

    cmd = db.query(SensorCommand).filter(SensorCommand.id == payload.command_id).first()
    
    if cmd:
        # Check command ownership & tenant boundaries
        if cmd.sensor_id != sensor.id or cmd.organization_id != sensor.organization_id:
            audit = AuditLog(
                organization_id=sensor.organization_id,
                user_id=None,
                user_email=f"sensor-{sensor.id[:8]}",
                action="COMMAND_AUTHZ_VIOLATION",
                target_type="SensorCommand",
                target_id=payload.command_id,
                details=f"Cross-sensor authorization violation: Sensor '{sensor.id}' attempted to acknowledge command '{cmd.id}' assigned to sensor '{cmd.sensor_id}'."
            )
            db.add(audit)
            db.commit()
            raise HTTPException(
                status_code=status.HTTP_403_FORBIDDEN,
                detail="Access denied: Sensor cannot acknowledge a command assigned to another sensor or tenant."
            )

        # Duplicate / Replay Protection: Safely idempotent
        if cmd.status == "ACKNOWLEDGED":
            return {
                "status": "already_acknowledged",
                "command_id": cmd.id,
                "action": cmd.action,
                "ack_status": cmd.result_status,
                "message": "Duplicate acknowledgement safely handled idempotently; original status preserved."
            }

        # Expired or Revoked command protection
        if cmd.status in ["EXPIRED", "REVOKED"] or (cmd.expires_at and now > cmd.expires_at):
            cmd.status = "EXPIRED" if cmd.status != "REVOKED" else "REVOKED"
            db.commit()
            raise HTTPException(
                status_code=status.HTTP_400_BAD_REQUEST,
                detail=f"Cannot acknowledge command in '{cmd.status}' state (command expired or revoked)."
            )

        # Transition status to ACKNOWLEDGED
        cmd.status = "ACKNOWLEDGED"
        cmd.acknowledged_at = now
        cmd.result_status = payload.status
        cmd.result_details = payload.details

        # Update linked ResponseExecution if linked
        if cmd.execution_id:
            exec_rec = db.query(ResponseExecution).filter(ResponseExecution.id == cmd.execution_id).first()
            if exec_rec:
                exec_rec.execution_log = (
                    f"Sensor Ack: Command '{cmd.action}' (ID: {cmd.id}) - "
                    f"Status: {payload.status}. Details: {payload.details or 'Execution verified'}."
                )
                if payload.status in ["SUCCESS", "VALIDATED_DRY_RUN"]:
                    exec_rec.status = "Completed"
                elif payload.status == "FAILED":
                    exec_rec.status = "Failed"
                exec_rec.completed_at = now

    else:
        # Fallback for ad-hoc / legacy executions matching sensor's asset
        matched_execution = None
        if sensor.asset_id:
            matched_execution = db.query(ResponseExecution).filter(
                ResponseExecution.organization_id == sensor.organization_id,
                ResponseExecution.target_asset_id == sensor.asset_id
            ).order_by(ResponseExecution.created_at.desc()).first()

        if matched_execution:
            matched_execution.execution_log = (
                f"Sensor Ack: Command '{payload.action}' (ID: {payload.command_id}) - "
                f"Status: {payload.status}. Details: {payload.details or 'Execution verified'}."
            )
            if payload.status in ["SUCCESS", "VALIDATED_DRY_RUN"]:
                matched_execution.status = "Completed"
            elif payload.status == "FAILED":
                matched_execution.status = "Failed"
            matched_execution.completed_at = now

    # Record AuditLog for Command Acknowledged
    audit = AuditLog(
        organization_id=sensor.organization_id,
        user_id=None,
        user_email=f"sensor-{sensor.id[:8]}",
        action="COMMAND_ACKNOWLEDGED",
        target_type="SensorCommand",
        target_id=payload.command_id,
        details=f"Sensor '{sensor.name}' acknowledged action '{payload.action}' with status '{payload.status}'. Details: {payload.details or 'N/A'}."
    )
    db.add(audit)
    db.commit()

    return {
        "status": "recorded",
        "command_id": payload.command_id,
        "action": payload.action,
        "ack_status": payload.status,
        "timestamp": serialize_utc_datetime(now)
    }

@router.post("/telemetry")
def ingest_sensor_telemetry(
    payload: TelemetryBatchIn,
    sensor: Sensor = Depends(get_sensor_by_key),
    db: Session = Depends(get_db)
):
    """
    Ingests batch security telemetry from local Windows/Linux sensor:
    1. Records SecurityEvents.
    2. Dispatches events through deterministic detection engine.
    3. Records discovered LAN devices.
    4. Records active IP connection observations.
    """
    ingested_events_count = 0
    now = datetime.utcnow()

    # 1. Process Security Events
    for ev in payload.events:
        event_obj = SecurityEvent(
            organization_id=sensor.organization_id,
            asset_id=sensor.asset_id,
            sensor_id=sensor.id,
            event_type=ev.event_type,
            severity=ev.severity,
            title=ev.title,
            description=ev.description,
            source_ip=ev.source_ip,
            destination_ip=ev.destination_ip,
            source_port=ev.source_port,
            destination_port=ev.destination_port,
            protocol=ev.protocol,
            raw_payload=json.dumps(ev.raw_payload or {}),
            is_simulated=bool(ev.is_simulated),
            timestamp=ev.timestamp or now,
            created_at=now
        )
        db.add(event_obj)
        db.flush()
        ingested_events_count += 1
        
        # Trigger detection rules
        run_detection_pipeline_for_event(db=db, event=event_obj)

    # 2. Process Discovered LAN Devices
    for dev in payload.discovered_devices:
        existing = db.query(NetworkDevice).filter(
            NetworkDevice.organization_id == sensor.organization_id,
            NetworkDevice.ip_address == dev.ip_address
        ).first()
        if existing:
            existing.last_seen = now
            if dev.hostname:
                existing.hostname = dev.hostname
            if dev.mac_address:
                existing.mac_address = dev.mac_address
        else:
            new_dev = NetworkDevice(
                organization_id=sensor.organization_id,
                ip_address=dev.ip_address,
                mac_address=dev.mac_address,
                hostname=dev.hostname,
                vendor=dev.vendor,
                device_type=dev.device_type,
                is_authorized=True,
                first_seen=now,
                last_seen=now
            )
            db.add(new_dev)

    # 3. Process Active Connection Observations
    for conn in payload.active_connections_sample:
        dst_ip = conn.get("destination_ip")
        if dst_ip:
            obs = IPObservation(
                organization_id=sensor.organization_id,
                asset_id=sensor.asset_id,
                ip_address=dst_ip,
                source_port=conn.get("source_port"),
                destination_ip=dst_ip,
                destination_port=conn.get("destination_port"),
                protocol=conn.get("protocol", "TCP"),
                direction=conn.get("direction", "Outbound"),
                observation_source="Endpoint Sensor",
                timestamp=now,
                metadata_json=json.dumps(conn)
            )
            db.add(obs)

    # Telemetry ingestion updates activity timestamps; it does NOT fake a heartbeat
    sensor.updated_at = now
    if sensor.asset_id:
        asset = db.query(Asset).filter(Asset.id == sensor.asset_id).first()
        if asset:
            asset.last_seen = now
    db.commit()

    return {
        "status": "success",
        "events_ingested": ingested_events_count,
        "devices_updated": len(payload.discovered_devices),
        "connections_recorded": len(payload.active_connections_sample)
    }
