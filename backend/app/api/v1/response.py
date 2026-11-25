import json
import uuid
from datetime import datetime, timedelta
from typing import List, Optional
from fastapi import APIRouter, Depends, HTTPException, status
from pydantic import BaseModel
from sqlalchemy.orm import Session

from backend.app.database import get_db
from backend.app.core.datetime_utils import serialize_utc_datetime
from backend.app.core.dependencies import get_current_org, get_current_user, require_role
from backend.app.models.auth import Organization, User, AuditLog
from backend.app.models.response import ResponsePlaybook, ResponseExecution, SensorCommand
from backend.app.models.assets import Asset, Sensor
from backend.app.models.incidents import Incident, IncidentTimelineEntry
from backend.app.schemas.response import ResponsePlaybookOut, ResponseExecutionOut

router = APIRouter(prefix="/response", tags=["Response Automation"])

class TriggerPlaybookRequest(BaseModel):
    playbook_id: str
    target_asset_id: Optional[str] = None
    target_ip: Optional[str] = None
    incident_id: Optional[str] = None
    reason: Optional[str] = None

class ApproveExecutionRequest(BaseModel):
    decision: str  # "Approved" or "Rejected"
    notes: Optional[str] = None

def seed_default_playbooks(db: Session, org_id: str):
    playbooks = [
        {
            "name": "Isolate Host from Network",
            "description": "Requests endpoint containment by instructing the local sensor to restrict network adapters to Sentinel SOC communication only.",
            "action_type": "isolate_endpoint",
            "requires_approval": True
        },
        {
            "name": "Revoke Compromised Sensor Credential",
            "description": "Revokes active sensor API key and terminates ingestion privileges for a suspect endpoint.",
            "action_type": "revoke_sensor_credential",
            "requires_approval": True
        },
        {
            "name": "Advisory Perimeter IP Block",
            "description": "Generates edge firewall rule syntax (iptables, pfSense, AWS Network ACL) to block verified adversary C2 or scanner IP.",
            "action_type": "block_ip_advisory",
            "requires_approval": True
        },
        {
            "name": "Generate Rapid Triage Investigation Checklist",
            "description": "Generates structured SOC analyst investigation tasks, memory triage prompts, and artifact collection steps attached directly to incident timeline.",
            "action_type": "investigation_checklist",
            "requires_approval": False
        },
        {
            "name": "AWS IAM Least-Privilege Remediation Guidance",
            "description": "Generates AWS CLI and CloudFormation remediation scripts to isolate compromised IAM roles and detach administrative policies.",
            "action_type": "aws_iam_remediation",
            "requires_approval": True
        },
        {
            "name": "Non-Destructive Diagnostic Verification Probe",
            "description": "Dispatches a safe, non-destructive probe to verify endpoint sensor queue dispatch and execution acknowledgement without altering network state.",
            "action_type": "safe_diagnostic_probe",
            "requires_approval": True
        }
    ]
    for pb in playbooks:
        existing = db.query(ResponsePlaybook).filter(
            ResponsePlaybook.organization_id == org_id,
            ResponsePlaybook.action_type == pb["action_type"]
        ).first()
        if not existing:
            new_pb = ResponsePlaybook(
                organization_id=org_id,
                name=pb["name"],
                description=pb["description"],
                action_type=pb["action_type"],
                requires_approval=pb["requires_approval"],
                is_enabled=True,
                created_at=datetime.utcnow()
            )
            db.add(new_pb)
    db.commit()

@router.get("/playbooks", response_model=List[ResponsePlaybookOut])
def list_playbooks(org: Organization = Depends(get_current_org), db: Session = Depends(get_db)):
    seed_default_playbooks(db, org.id)
    return db.query(ResponsePlaybook).filter(ResponsePlaybook.organization_id == org.id).all()

@router.get("/executions", response_model=List[ResponseExecutionOut])
def list_executions(org: Organization = Depends(get_current_org), db: Session = Depends(get_db)):
    return db.query(ResponseExecution).filter(ResponseExecution.organization_id == org.id).order_by(ResponseExecution.created_at.desc()).all()

@router.post("/trigger", response_model=ResponseExecutionOut, dependencies=[Depends(require_role(["Organization Owner", "Organization Administrator", "Security Analyst"]))])
def trigger_playbook(
    payload: TriggerPlaybookRequest,
    user: User = Depends(get_current_user),
    org: Organization = Depends(get_current_org),
    db: Session = Depends(get_db)
):
    playbook = db.query(ResponsePlaybook).filter(
        ResponsePlaybook.id == payload.playbook_id,
        ResponsePlaybook.organization_id == org.id
    ).first()
    if not playbook:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Playbook not found")

    preview = f"Action: {playbook.name} on Target Asset={payload.target_asset_id or 'N/A'}, Target IP={payload.target_ip or 'N/A'}. Reason: {payload.reason or 'Analyst manual invocation'}"
    
    execution = ResponseExecution(
        playbook_id=playbook.id,
        organization_id=org.id,
        triggered_by_user_id=user.id,
        target_asset_id=payload.target_asset_id,
        target_ip=payload.target_ip,
        action_preview=preview,
        status="Pending Approval" if playbook.requires_approval else "Completed",
        created_at=datetime.utcnow()
    )
    db.add(execution)
    db.flush()

    # Record Audit Log for playbook invocation
    audit = AuditLog(
        organization_id=org.id,
        user_id=user.id,
        user_email=user.email,
        action="PLAYBOOK_TRIGGERED",
        target_type="ResponsePlaybook",
        target_id=playbook.id,
        details=f"User {user.email} triggered playbook '{playbook.name}'. Status: {execution.status}."
    )
    db.add(audit)

    # If requires no approval (e.g. non-destructive investigation checklist), execute immediately
    if not playbook.requires_approval:
        execution.completed_at = datetime.utcnow()
        execution.execution_log = "Checklist generated automatically without destructive authorization requirement."
        
        # Attach to incident timeline if provided
        if payload.incident_id:
            entry = IncidentTimelineEntry(
                incident_id=payload.incident_id,
                organization_id=org.id,
                entry_type="ANALYST_ACTION",
                title="Triage Checklist Generated",
                description="1. Verify process tree and parent PID.\n2. Collect active network sockets.\n3. Check persistence mechanisms (Registry Run keys / Cron).\n4. Pull hash reputation from Threat Intel.\n5. Review user session auth history.",
                actor_type="USER",
                actor_name=user.full_name,
                timestamp=datetime.utcnow()
            )
            db.add(entry)

    db.commit()
    db.refresh(execution)
    return execution

@router.post("/executions/{execution_id}/decision", response_model=ResponseExecutionOut, dependencies=[Depends(require_role(["Organization Owner", "Organization Administrator"]))])
def approve_or_reject_execution(
    execution_id: str,
    payload: ApproveExecutionRequest,
    user: User = Depends(get_current_user),
    org: Organization = Depends(get_current_org),
    db: Session = Depends(get_db)
):
    execution = db.query(ResponseExecution).filter(
        ResponseExecution.id == execution_id,
        ResponseExecution.organization_id == org.id
    ).first()
    if not execution:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Execution not found")

    playbook = db.query(ResponsePlaybook).filter(ResponsePlaybook.id == execution.playbook_id).first()

    now = datetime.utcnow()
    if payload.decision == "Approved":
        execution.status = "Completed"
        execution.approved_by_user_id = user.id
        execution.approved_at = now
        execution.completed_at = now
        
        log_notes = []

        # Action 1: Isolate Endpoint (Queue command to sensor and mark asset health)
        if playbook and playbook.action_type == "isolate_endpoint" and execution.target_asset_id:
            asset = db.query(Asset).filter(Asset.id == execution.target_asset_id).first()
            if asset:
                asset.health_status = "isolated"
                log_notes.append(f"Asset '{asset.hostname}' health status marked as 'isolated'.")

            sensor = db.query(Sensor).filter(Sensor.asset_id == execution.target_asset_id).first()
            if sensor:
                cmd_id = str(uuid.uuid4())
                sensor_cmd = SensorCommand(
                    id=cmd_id,
                    sensor_id=sensor.id,
                    organization_id=org.id,
                    execution_id=execution.id,
                    action="ISOLATE_HOST",
                    parameters_json=json.dumps({"allow_backend_only": True}),
                    status="QUEUED",
                    queued_at=now,
                    expires_at=now + timedelta(hours=2)
                )
                db.add(sensor_cmd)
                
                # Also log command queued audit
                cmd_audit = AuditLog(
                    organization_id=org.id,
                    user_id=user.id,
                    user_email=user.email,
                    action="COMMAND_QUEUED",
                    target_type="SensorCommand",
                    target_id=cmd_id,
                    details=f"Command 'ISOLATE_HOST' (ID: {cmd_id}) queued for Sensor '{sensor.name}'."
                )
                db.add(cmd_audit)

                # Keep legacy pending_commands in sync
                cmds = []
                if sensor.pending_commands:
                    try:
                        cmds = json.loads(sensor.pending_commands)
                    except Exception:
                        cmds = []
                cmds.append({
                    "id": cmd_id,
                    "action": "ISOLATE_HOST",
                    "params": {"allow_backend_only": True},
                    "queued_at": serialize_utc_datetime(now)
                })
                sensor.pending_commands = json.dumps(cmds)
                log_notes.append(f"Network isolation command queued for Sensor '{sensor.name}' (ID: {sensor.id}).")

        # Action 2: Revoke Sensor Credential
        elif playbook and playbook.action_type == "revoke_sensor_credential" and execution.target_asset_id:
            sensor = db.query(Sensor).filter(Sensor.asset_id == execution.target_asset_id).first()
            if sensor:
                sensor.status = "Revoked"
                sensor.api_key_hash = None
                log_notes.append(f"Sensor '{sensor.name}' credentials revoked. Ingestion access terminated.")

        # Action 3: Advisory Perimeter IP Block
        elif playbook and playbook.action_type == "block_ip_advisory" and execution.target_ip:
            log_notes.append(f"Firewall drop rules generated for IP {execution.target_ip}: `iptables -A INPUT -s {execution.target_ip} -j DROP`")

        # Action 4: AWS IAM Least-Privilege Remediation
        elif playbook and playbook.action_type == "aws_iam_remediation":
            log_notes.append("Remediation generated: `aws iam detach-role-policy --role-name SuspectRole --policy-arn arn:aws:iam::aws:policy/AdministratorAccess`")

        # Action 5: Safe Diagnostic Verification Probe
        elif playbook and playbook.action_type == "safe_diagnostic_probe" and execution.target_asset_id:
            sensor = db.query(Sensor).filter(Sensor.asset_id == execution.target_asset_id).first()
            if sensor:
                cmd_id = str(uuid.uuid4())
                sensor_cmd = SensorCommand(
                    id=cmd_id,
                    sensor_id=sensor.id,
                    organization_id=org.id,
                    execution_id=execution.id,
                    action="DIAGNOSTIC_PROBE",
                    parameters_json=json.dumps({"dry_run": True, "message": "Non-destructive verification probe"}),
                    status="QUEUED",
                    queued_at=now,
                    expires_at=now + timedelta(hours=2)
                )
                db.add(sensor_cmd)

                cmd_audit = AuditLog(
                    organization_id=org.id,
                    user_id=user.id,
                    user_email=user.email,
                    action="COMMAND_QUEUED",
                    target_type="SensorCommand",
                    target_id=cmd_id,
                    details=f"Command 'DIAGNOSTIC_PROBE' (ID: {cmd_id}) queued for Sensor '{sensor.name}'."
                )
                db.add(cmd_audit)

                cmds = []
                if sensor.pending_commands:
                    try:
                        cmds = json.loads(sensor.pending_commands)
                    except Exception:
                        cmds = []
                cmds.append({
                    "id": cmd_id,
                    "action": "DIAGNOSTIC_PROBE",
                    "params": {"dry_run": True, "message": "Non-destructive verification probe"},
                    "queued_at": serialize_utc_datetime(now)
                })
                sensor.pending_commands = json.dumps(cmds)
                log_notes.append(f"Safe diagnostic probe command queued for Sensor '{sensor.name}' (ID: {sensor.id}).")

        execution.execution_log = f"Approved by {user.full_name}. " + " ".join(log_notes)

        # Audit Log
        audit = AuditLog(
            organization_id=org.id,
            user_id=user.id,
            user_email=user.email,
            action="PLAYBOOK_APPROVED",
            target_type="ResponsePlaybook",
            target_id=playbook.id if playbook else execution.playbook_id,
            details=f"Approved execution of '{playbook.name if playbook else 'Unknown'}' on Target={execution.target_asset_id or execution.target_ip}. Execution completed."
        )
        db.add(audit)

    else:
        execution.status = "Rejected"
        execution.approved_by_user_id = user.id
        execution.approved_at = now
        execution.completed_at = now
        execution.execution_log = f"Rejected by {user.full_name}. Reason: {payload.notes or 'No reason provided'}"

        audit = AuditLog(
            organization_id=org.id,
            user_id=user.id,
            user_email=user.email,
            action="PLAYBOOK_REJECTED",
            target_type="ResponsePlaybook",
            target_id=playbook.id if playbook else execution.playbook_id,
            details=f"Rejected execution of '{playbook.name if playbook else 'Unknown'}'. Reason: {payload.notes or 'N/A'}"
        )
        db.add(audit)

    db.commit()
    db.refresh(execution)
    return execution
