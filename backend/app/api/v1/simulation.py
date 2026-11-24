import json
from datetime import datetime, timedelta
from typing import List, Optional
from fastapi import APIRouter, Depends, HTTPException, status
from sqlalchemy.orm import Session

from backend.app.database import get_db
from backend.app.core.dependencies import get_current_org, require_role
from backend.app.core.detection_engine import run_detection_pipeline_for_event
from backend.app.models.auth import Organization
from backend.app.models.events import SecurityEvent
from backend.app.models.detections import DetectionResult
from backend.app.models.incidents import Incident, IncidentEvent
from backend.app.models.network import NetworkDevice
from backend.app.schemas.simulation import AttackSimulationRequest, AttackSimulationResult

router = APIRouter(prefix="/simulation", tags=["Attack Simulation Lab"])

@router.post("/run", response_model=AttackSimulationResult, dependencies=[Depends(require_role(["Organization Owner", "Organization Administrator", "Security Analyst"]))])
def run_attack_simulation(
    payload: AttackSimulationRequest,
    org: Organization = Depends(get_current_org),
    db: Session = Depends(get_db)
):
    """
    Executes safe, localized, explicitly labeled simulation fixtures to verify detection rules and alerts.
    Does NOT execute real destructive attacks or scan unauthorized external ranges.
    """
    now = datetime.utcnow()
    events_generated = []
    alerts_triggered = 0
    incidents_before = db.query(Incident).filter(Incident.organization_id == org.id).count()

    sim_type = payload.simulation_type.lower()
    target_ip = payload.target_ip or "127.0.0.1"

    if sim_type == "brute_force_login":
        # Generate N failed login attempts from a lab source IP (e.g., 198.51.100.24)
        source_ip = "198.51.100.24"
        count = payload.intensity or 6
        for i in range(count):
            ev = SecurityEvent(
                organization_id=org.id,
                event_type="auth_failure",
                severity="Medium" if i < count - 1 else "High",
                title="SSH Failed Authentication Attempt (SIMULATED)",
                description=f"Simulated repeated failed password for user 'root' from lab IP {source_ip}",
                source_ip=source_ip,
                destination_ip=target_ip,
                destination_port=22,
                protocol="TCP",
                raw_payload=json.dumps({"attempt": i+1, "method": "password", "service": "sshd"}),
                is_simulated=True,
                timestamp=now - timedelta(seconds=(count - i) * 10),
                created_at=now
            )
            db.add(ev)
            db.flush()
            events_generated.append(ev.id)
            results = run_detection_pipeline_for_event(db=db, event=ev)
            alerts_triggered += len(results)

        summary = f"Simulated {count} rapid failed logins from {source_ip} against port 22. Detection rule 'AUTH_FAILED_BURST' evaluated."

    elif sim_type == "port_scan":
        source_ip = "192.168.1.199"
        ports = [21, 22, 23, 80, 443, 445, 3389, 8080]
        for p in ports:
            ev = SecurityEvent(
                organization_id=org.id,
                event_type="port_scan",
                severity="Low",
                title=f"TCP SYN probe to port {p} (SIMULATED)",
                description=f"Simulated sequential TCP connect probe to target {target_ip}:{p}",
                source_ip=source_ip,
                destination_ip=target_ip,
                destination_port=p,
                protocol="TCP",
                raw_payload=json.dumps({"flags": "SYN", "target": f"{target_ip}:{p}"}),
                is_simulated=True,
                timestamp=now,
                created_at=now
            )
            db.add(ev)
            db.flush()
            events_generated.append(ev.id)
            results = run_detection_pipeline_for_event(db=db, event=ev)
            alerts_triggered += len(results)

        summary = f"Simulated multi-port scan touching {len(ports)} ports on target {target_ip}. Evaluated 'PORT_SCAN_ACTIVITY' rule."

    elif sim_type == "malicious_c2_outbound":
        # Known threat indicator IP: 185.220.101.5 (Tor Exit / Malicious scanner)
        source_ip = "192.168.1.45"
        dest_ip = "185.220.101.5"
        ev = SecurityEvent(
            organization_id=org.id,
            event_type="outbound_conn",
            severity="Critical",
            title="Outbound Network Connection to Suspected C2 (SIMULATED)",
            description=f"Simulated outbound beacon session established to known threat indicator {dest_ip}:4444",
            source_ip=source_ip,
            destination_ip=dest_ip,
            destination_port=4444,
            protocol="TCP",
            raw_payload=json.dumps({"beacon_interval": 30, "destination": dest_ip}),
            is_simulated=True,
            timestamp=now,
            created_at=now
        )
        db.add(ev)
        db.flush()
        events_generated.append(ev.id)
        results = run_detection_pipeline_for_event(db=db, event=ev)
        alerts_triggered += len(results)

        summary = f"Simulated outbound command-and-control connection to {dest_ip}:4444. Evaluated 'MALICIOUS_IP_MATCH' and 'UNUSUAL_OUTBOUND_CONN'."

    elif sim_type == "new_lan_device":
        rogue_ip = "192.168.1.188"
        rogue_mac = "00:1A:2B:3C:4D:EE"
        new_dev = NetworkDevice(
            organization_id=org.id,
            ip_address=rogue_ip,
            mac_address=rogue_mac,
            hostname="unknown-rogue-lab-device",
            vendor="Raspberry Pi Foundation",
            device_type="Unknown",
            is_authorized=False,
            first_seen=now,
            last_seen=now
        )
        db.add(new_dev)
        db.flush()
        
        ev = SecurityEvent(
            organization_id=org.id,
            event_type="lan_device",
            severity="Medium",
            title="New Unauthorized Device Detected on Subnet (SIMULATED)",
            description=f"Device {rogue_ip} ({rogue_mac}) discovered with unauthorized policy flag.",
            source_ip=rogue_ip,
            raw_payload=json.dumps({"mac": rogue_mac, "vendor": "Raspberry Pi Foundation"}),
            is_simulated=True,
            timestamp=now,
            created_at=now
        )
        db.add(ev)
        db.flush()
        events_generated.append(ev.id)
        results = run_detection_pipeline_for_event(db=db, event=ev)
        alerts_triggered += len(results)
        summary = f"Simulated rogue device {rogue_ip} appearing on LAN. Evaluated 'NEW_UNAUTHORIZED_LAN_DEVICE'."

    elif sim_type == "aws_iam_escalation":
        ev = SecurityEvent(
            organization_id=org.id,
            event_type="iam_policy_change",
            severity="Critical",
            title="AdministratorAccess Policy Attached to Sandbox Role (SIMULATED)",
            description="Cloud audit recorded privileged policy attachment: AdministratorAccess attached to role 'developer-sandbox' by user 'intern-dev'.",
            source_ip="203.0.113.88",
            raw_payload=json.dumps({"service": "AWS IAM", "event": "AttachRolePolicy", "policy": "AdministratorAccess"}),
            is_simulated=True,
            timestamp=now,
            created_at=now
        )
        db.add(ev)
        db.flush()
        events_generated.append(ev.id)
        results = run_detection_pipeline_for_event(db=db, event=ev)
        alerts_triggered += len(results)
        summary = "Simulated high-risk AWS IAM escalation attachment of AdministratorAccess. Evaluated 'AWS_RISKY_IAM_MODIFICATION'."

    elif sim_type == "credential_spray":
        source_ip = "198.51.100.77"
        targets = [("10.0.1.10", "ad-dc01"), ("10.0.1.20", "mail-srv01"), ("10.0.1.30", "hr-portal01")]
        for ip, host in targets:
            ev = SecurityEvent(
                organization_id=org.id,
                event_type="auth_failure",
                severity="High",
                title=f"Failed Domain Authentication on {host} (SIMULATED)",
                description=f"Horizontal spray probe: failed login for 'administrator' against {host} ({ip}) from {source_ip}.",
                source_ip=source_ip,
                destination_ip=ip,
                destination_port=445,
                protocol="TCP",
                raw_payload=json.dumps({"target_host": host, "source": source_ip}),
                is_simulated=True,
                timestamp=now,
                created_at=now
            )
            db.add(ev)
            db.flush()
            events_generated.append(ev.id)
            results = run_detection_pipeline_for_event(db=db, event=ev)
            alerts_triggered += len(results)
        summary = f"Simulated multi-asset credential spray across 3 distinct hosts from {source_ip}. Evaluated 'AUTH_FAILED_MULTI_ASSET'."

    else:
        raise HTTPException(status_code=status.HTTP_400_BAD_REQUEST, detail=f"Unknown simulation type: {sim_type}")

    db.commit()
    incidents_after = db.query(Incident).filter(Incident.organization_id == org.id).count()

    return AttackSimulationResult(
        simulation_type=sim_type,
        is_simulated=True,
        events_generated=len(events_generated),
        alerts_triggered=alerts_triggered,
        incidents_created=max(0, incidents_after - incidents_before),
        summary=summary,
        generated_event_ids=events_generated
    )

@router.post("/reset", dependencies=[Depends(require_role(["Organization Owner", "Organization Administrator"]))])
def reset_simulation_lab(
    org: Organization = Depends(get_current_org),
    db: Session = Depends(get_db)
):
    """
    Safely purges simulated security events, alerts, and incidents from the lab,
    without touching genuine production telemetry.
    """
    from backend.app.models.incidents import IncidentEvent, IncidentTimelineEntry

    # Find simulated incidents
    sim_incidents = db.query(Incident.id).filter(
        Incident.organization_id == org.id,
        Incident.is_simulated == True
    ).all()
    sim_inc_ids = [i.id for i in sim_incidents]

    if sim_inc_ids:
        db.query(IncidentTimelineEntry).filter(IncidentTimelineEntry.incident_id.in_(sim_inc_ids)).delete(synchronize_session=False)
        db.query(IncidentEvent).filter(IncidentEvent.incident_id.in_(sim_inc_ids)).delete(synchronize_session=False)

    deleted_incidents = db.query(Incident).filter(
        Incident.organization_id == org.id,
        Incident.is_simulated == True
    ).delete(synchronize_session=False)

    deleted_alerts = db.query(DetectionResult).filter(
        DetectionResult.organization_id == org.id,
        DetectionResult.is_simulated == True
    ).delete(synchronize_session=False)

    deleted_events = db.query(SecurityEvent).filter(
        SecurityEvent.organization_id == org.id,
        SecurityEvent.is_simulated == True
    ).delete(synchronize_session=False)

    db.commit()
    return {
        "status": "success",
        "purged_events": deleted_events,
        "purged_alerts": deleted_alerts,
        "purged_incidents": deleted_incidents,
        "message": "Simulation lab reset complete. Real production telemetry was untouched."
    }
