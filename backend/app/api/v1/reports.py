import csv
import io
import json
from datetime import datetime
from fastapi import APIRouter, Depends, Response
from sqlalchemy.orm import Session

from backend.app.database import get_db
from backend.app.core.dependencies import get_current_org, require_role
from backend.app.models.auth import Organization
from backend.app.models.incidents import Incident
from backend.app.models.events import SecurityEvent, ThreatIndicator
from backend.app.models.assets import Asset
from backend.app.models.network import NetworkDevice, Network
from backend.app.models.aws import AWSFinding

router = APIRouter(prefix="/reports", tags=["Reports & Analytics"])

@router.get("/incidents/csv", dependencies=[Depends(require_role(["Organization Owner", "Organization Administrator", "Security Analyst"]))])
def export_incidents_csv(org: Organization = Depends(get_current_org), db: Session = Depends(get_db)):
    incidents = db.query(Incident).filter(Incident.organization_id == org.id).order_by(Incident.created_at.desc()).all()
    
    output = io.StringIO()
    writer = csv.writer(output)
    writer.writerow(["Incident ID", "Title", "Severity", "Status", "Simulated", "Created At", "Closed At", "Description"])
    for inc in incidents:
        writer.writerow([
            inc.id,
            inc.title,
            inc.severity,
            inc.status,
            "Yes" if inc.is_simulated else "No",
            inc.created_at.isoformat(),
            inc.closed_at.isoformat() if inc.closed_at else "",
            inc.description
        ])
        
    return Response(
        content=output.getvalue(),
        media_type="text/csv",
        headers={"Content-Disposition": f"attachment; filename=sentinel_incidents_{datetime.utcnow().strftime('%Y%m%d')}.csv"}
    )

@router.get("/incidents/json", dependencies=[Depends(require_role(["Organization Owner", "Organization Administrator", "Security Analyst"]))])
def export_incidents_json(org: Organization = Depends(get_current_org), db: Session = Depends(get_db)):
    incidents = db.query(Incident).filter(Incident.organization_id == org.id).order_by(Incident.created_at.desc()).all()
    data = [
        {
            "id": inc.id,
            "title": inc.title,
            "severity": inc.severity,
            "status": inc.status,
            "is_simulated": inc.is_simulated,
            "created_at": inc.created_at.isoformat(),
            "closed_at": inc.closed_at.isoformat() if inc.closed_at else None,
            "description": inc.description,
            "resolution_notes": inc.resolution_notes
        }
        for inc in incidents
    ]
    return Response(
        content=json.dumps(data, indent=2),
        media_type="application/json",
        headers={"Content-Disposition": f"attachment; filename=sentinel_incidents_{datetime.utcnow().strftime('%Y%m%d')}.json"}
    )

@router.get("/events/csv", dependencies=[Depends(require_role(["Organization Owner", "Organization Administrator", "Security Analyst"]))])
def export_events_csv(org: Organization = Depends(get_current_org), db: Session = Depends(get_db)):
    events = db.query(SecurityEvent).filter(SecurityEvent.organization_id == org.id).order_by(SecurityEvent.timestamp.desc()).limit(1000).all()
    
    output = io.StringIO()
    writer = csv.writer(output)
    writer.writerow(["Event ID", "Timestamp", "Type", "Severity", "Title", "Source IP", "Destination IP", "Destination Port", "Protocol", "Simulated"])
    for e in events:
        writer.writerow([
            e.id,
            e.timestamp.isoformat(),
            e.event_type,
            e.severity,
            e.title,
            e.source_ip or "",
            e.destination_ip or "",
            e.destination_port or "",
            e.protocol or "",
            e.is_simulated
        ])
        
    return Response(
        content=output.getvalue(),
        media_type="text/csv",
        headers={"Content-Disposition": f"attachment; filename=sentinel_events_{datetime.utcnow().strftime('%Y%m%d')}.csv"}
    )

@router.get("/events/json", dependencies=[Depends(require_role(["Organization Owner", "Organization Administrator", "Security Analyst"]))])
def export_events_json(org: Organization = Depends(get_current_org), db: Session = Depends(get_db)):
    events = db.query(SecurityEvent).filter(SecurityEvent.organization_id == org.id).order_by(SecurityEvent.timestamp.desc()).limit(1000).all()
    data = [
        {
            "id": e.id,
            "timestamp": e.timestamp.isoformat(),
            "event_type": e.event_type,
            "severity": e.severity,
            "title": e.title,
            "source_ip": e.source_ip,
            "destination_ip": e.destination_ip,
            "destination_port": e.destination_port,
            "protocol": e.protocol,
            "is_simulated": e.is_simulated
        }
        for e in events
    ]
    return Response(
        content=json.dumps(data, indent=2),
        media_type="application/json",
        headers={"Content-Disposition": f"attachment; filename=sentinel_events_{datetime.utcnow().strftime('%Y%m%d')}.json"}
    )

@router.get("/threat-intel/csv", dependencies=[Depends(require_role(["Organization Owner", "Organization Administrator", "Security Analyst"]))])
def export_threat_intel_csv(db: Session = Depends(get_db)):
    indicators = db.query(ThreatIndicator).order_by(ThreatIndicator.created_at.desc()).all()
    output = io.StringIO()
    writer = csv.writer(output)
    writer.writerow(["Indicator Value", "Type", "Threat Category", "Severity", "Source", "Confidence", "First Seen", "Last Seen"])
    for ind in indicators:
        writer.writerow([
            ind.indicator_value,
            ind.indicator_type,
            ind.threat_type,
            ind.severity,
            ind.source,
            ind.confidence,
            ind.first_seen.isoformat() if ind.first_seen else "",
            ind.last_seen.isoformat() if ind.last_seen else ""
        ])
    return Response(
        content=output.getvalue(),
        media_type="text/csv",
        headers={"Content-Disposition": f"attachment; filename=sentinel_threat_indicators_{datetime.utcnow().strftime('%Y%m%d')}.csv"}
    )

@router.get("/network/csv", dependencies=[Depends(require_role(["Organization Owner", "Organization Administrator", "Security Analyst"]))])
def export_network_inventory_csv(org: Organization = Depends(get_current_org), db: Session = Depends(get_db)):
    devices = db.query(NetworkDevice).filter(NetworkDevice.organization_id == org.id).order_by(NetworkDevice.last_seen.desc()).all()
    output = io.StringIO()
    writer = csv.writer(output)
    writer.writerow(["IP Address", "MAC Address", "Hostname", "Vendor", "Device Type", "Discovery Method", "Authorized", "First Seen", "Last Seen"])
    for d in devices:
        writer.writerow([
            d.ip_address,
            d.mac_address or "N/A",
            d.hostname or "N/A",
            d.vendor or "N/A",
            d.device_type,
            d.discovery_method,
            "Yes" if d.is_authorized else "No",
            d.first_seen.isoformat(),
            d.last_seen.isoformat()
        ])
    return Response(
        content=output.getvalue(),
        media_type="text/csv",
        headers={"Content-Disposition": f"attachment; filename=sentinel_network_devices_{datetime.utcnow().strftime('%Y%m%d')}.csv"}
    )

@router.get("/aws/csv", dependencies=[Depends(require_role(["Organization Owner", "Organization Administrator", "Security Analyst"]))])
def export_aws_findings_csv(org: Organization = Depends(get_current_org), db: Session = Depends(get_db)):
    findings = db.query(AWSFinding).filter(AWSFinding.organization_id == org.id).order_by(AWSFinding.created_at.desc()).all()
    output = io.StringIO()
    writer = csv.writer(output)
    writer.writerow(["Service", "Finding Type", "Severity", "Resource ID", "Description", "Remediation", "Simulated", "Created At"])
    for f in findings:
        writer.writerow([
            f.service,
            f.finding_type,
            f.severity,
            f.resource_id or "N/A",
            f.description,
            f.remediation_guidance or "N/A",
            "Yes" if f.is_simulated else "No",
            f.created_at.isoformat()
        ])
    return Response(
        content=output.getvalue(),
        media_type="text/csv",
        headers={"Content-Disposition": f"attachment; filename=sentinel_aws_findings_{datetime.utcnow().strftime('%Y%m%d')}.csv"}
    )

@router.get("/summary")
def get_executive_summary(org: Organization = Depends(get_current_org), db: Session = Depends(get_db)):
    total_assets = db.query(Asset).filter(Asset.organization_id == org.id).count()
    total_events = db.query(SecurityEvent).filter(SecurityEvent.organization_id == org.id).count()
    simulated_events = db.query(SecurityEvent).filter(SecurityEvent.organization_id == org.id, SecurityEvent.is_simulated == True).count()
    genuine_events = total_events - simulated_events
    
    total_incidents = db.query(Incident).filter(Incident.organization_id == org.id).count()
    simulated_incidents = db.query(Incident).filter(Incident.organization_id == org.id, Incident.is_simulated == True).count()
    genuine_incidents = total_incidents - simulated_incidents
    
    resolved_incidents = db.query(Incident).filter(Incident.organization_id == org.id, Incident.status.in_(["Resolved", "Closed"])).count()
    total_devices = db.query(NetworkDevice).filter(NetworkDevice.organization_id == org.id).count()
    total_aws = db.query(AWSFinding).filter(AWSFinding.organization_id == org.id).count()
    
    return {
        "organization_id": org.id,
        "organization_name": org.name,
        "generated_at": datetime.utcnow().isoformat(),
        "total_assets_monitored": total_assets,
        "total_network_devices_discovered": total_devices,
        "total_security_events_recorded": total_events,
        "genuine_security_events": genuine_events,
        "simulated_security_events": simulated_events,
        "total_incidents": total_incidents,
        "genuine_incidents": genuine_incidents,
        "simulated_incidents": simulated_incidents,
        "resolved_incidents": resolved_incidents,
        "active_aws_findings": total_aws,
        "incident_resolution_rate": f"{(resolved_incidents / total_incidents * 100):.1f}%" if total_incidents > 0 else "100%"
    }
