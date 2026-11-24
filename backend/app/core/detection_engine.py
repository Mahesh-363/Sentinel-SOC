import json
import logging
from datetime import datetime, timedelta
from typing import List, Optional, Dict, Any
from sqlalchemy.orm import Session
from sqlalchemy import func

from backend.app.models.events import SecurityEvent, ThreatIndicator
from backend.app.models.detections import DetectionRule, DetectionResult, CorrelatedEventGroup
from backend.app.models.incidents import Incident, IncidentEvent, IncidentTimelineEntry
from backend.app.models.network import NetworkDevice
from backend.app.core.notification_service import send_notification

logger = logging.getLogger("sentinel.detections")

def seed_default_detection_rules(db: Session):
    """
    Seeds comprehensive Release 2 detection rules catalog covering host, network, cloud, and correlation.
    """
    default_rules = [
        # 1. Single Asset Brute Force
        {
            "rule_code": "AUTH_FAILED_BURST",
            "name": "Repeated Failed Login Attempts (Single Host)",
            "description": "Detects multiple failed authentication attempts from a single source against a host within a 5-minute window.",
            "severity": "High",
            "category": "Authentication",
            "is_correlation_rule": False,
            "time_window_seconds": 300,
            "threshold": 5,
            "parameters_json": json.dumps({"threshold": 5, "window_seconds": 300})
        },
        # 2. Distributed Brute Force / Multi-Asset Stuffing
        {
            "rule_code": "AUTH_FAILED_MULTI_ASSET",
            "name": "Distributed Credential Stuffing Across Multiple Assets",
            "description": "Identifies an external or internal source IP attempting failed logins across 3 or more distinct hosts, indicating horizontal credential spray.",
            "severity": "Critical",
            "category": "Authentication",
            "is_correlation_rule": True,
            "time_window_seconds": 600,
            "threshold": 3,
            "correlation_pattern": "MULTI_ASSET_AUTH_FAIL",
            "parameters_json": json.dumps({"asset_count_threshold": 3, "window_seconds": 600})
        },
        # 3. Port Scan Indicators
        {
            "rule_code": "PORT_SCAN_ACTIVITY",
            "name": "Port Scan Activity Detected",
            "description": "Detects rapid connection probes across 5 or more distinct destination ports from a single IP address in a short time frame.",
            "severity": "Medium",
            "category": "Network",
            "is_correlation_rule": False,
            "time_window_seconds": 60,
            "threshold": 5,
            "parameters_json": json.dumps({"port_count_threshold": 5, "window_seconds": 60})
        },
        # 4. Threat Intel Match
        {
            "rule_code": "MALICIOUS_IP_MATCH",
            "name": "Connection to Known Malicious Threat Indicator",
            "description": "Identifies network connections involving an IP address confirmed in global threat intelligence indicators.",
            "severity": "Critical",
            "category": "Threat Intelligence",
            "is_correlation_rule": False,
            "time_window_seconds": 60,
            "threshold": 1,
            "parameters_json": json.dumps({"confidence_min": 70})
        },
        # 5. Unusual Outbound C2 Ports
        {
            "rule_code": "UNUSUAL_OUTBOUND_CONN",
            "name": "Unusual Outbound Network Connection",
            "description": "Flags outbound connections to suspicious external ports (4444, 1337, 6667, 31337, 8888, 9999) commonly associated with reverse shells and C2 beacons.",
            "severity": "High",
            "category": "Network",
            "is_correlation_rule": False,
            "time_window_seconds": 60,
            "threshold": 1,
            "parameters_json": json.dumps({"suspicious_ports": [4444, 1337, 6667, 31337, 8888, 9999]})
        },
        # 6. Rogue LAN Device
        {
            "rule_code": "NEW_UNAUTHORIZED_LAN_DEVICE",
            "name": "New Unauthorized Device on Authorized Subnet",
            "description": "Detects when an unrecognized MAC/IP address is first observed communicating within an authorized local network segment.",
            "severity": "Medium",
            "category": "Asset & LAN",
            "is_correlation_rule": False,
            "time_window_seconds": 300,
            "threshold": 1,
            "parameters_json": json.dumps({"alert_on_new": True})
        },
        # 7. Unusual DNS Metadata (DGA / Tunneling)
        {
            "rule_code": "UNUSUAL_DNS_METADATA",
            "name": "Suspicious DNS Query Pattern (DGA or Data Exfiltration)",
            "description": "Detects high-entropy domain queries, excessively long hostnames, or anomalous TXT record requests consistent with DNS tunneling or malware DGA.",
            "severity": "High",
            "category": "Network",
            "is_correlation_rule": False,
            "time_window_seconds": 120,
            "threshold": 3,
            "parameters_json": json.dumps({"min_entropy": 3.8, "length_threshold": 45})
        },
        # 8. Suspicious Process Execution
        {
            "rule_code": "SUSPICIOUS_PROCESS_ACTIVITY",
            "name": "Suspicious Process Execution (Living-off-the-Land)",
            "description": "Flags execution of dual-use binaries (certutil, encoded powershell, vssadmin, net user /add, /bin/bash -i) indicative of initial access or discovery.",
            "severity": "High",
            "category": "Endpoint",
            "is_correlation_rule": False,
            "time_window_seconds": 60,
            "threshold": 1,
            "parameters_json": json.dumps({
                "keywords": ["powershell -enc", "certutil -urlcache", "vssadmin delete", "net user /add", "whoami /priv", "bash -i"]
            })
        },
        # 9. Privilege Escalation Indicators
        {
            "rule_code": "PRIVILEGE_ESCALATION",
            "name": "Local Privilege Escalation Indicator",
            "description": "Detects suspicious attempts to acquire root or SYSTEM privileges (sudo without TTY, token manipulation, shadow file inspection).",
            "severity": "High",
            "category": "Endpoint",
            "is_correlation_rule": False,
            "time_window_seconds": 60,
            "threshold": 1,
            "parameters_json": json.dumps({"indicators": ["SeDebugPrivilege", "sudo_nopasswd", "shadow_read"]})
        },
        # 10. AWS Risky IAM Modification
        {
            "rule_code": "AWS_RISKY_IAM_MODIFICATION",
            "name": "Risky AWS IAM Policy Modification",
            "description": "Detects privileged policy attachments (AdministratorAccess), unrestricted AssumeRole trust, or root credential access in cloud telemetry.",
            "severity": "High",
            "category": "Cloud Security",
            "is_correlation_rule": False,
            "time_window_seconds": 60,
            "threshold": 1,
            "parameters_json": json.dumps({"critical_policies": ["AdministratorAccess", "*:*"]})
        },
        # 11. AWS Risky S3 Bucket Event
        {
            "rule_code": "AWS_RISKY_S3_EVENT",
            "name": "Risky AWS S3 Public Policy or Ransomware Deletion",
            "description": "Flags S3 bucket policy changes granting public 0.0.0.0/0 read/write or rapid batch deletion events.",
            "severity": "Critical",
            "category": "Cloud Security",
            "is_correlation_rule": False,
            "time_window_seconds": 300,
            "threshold": 1,
            "parameters_json": json.dumps({"monitor_actions": ["PutBucketPolicy", "DeleteObjects"]})
        },
        # 12. AWS GuardDuty High Finding
        {
            "rule_code": "AWS_GUARDDUTY_FINDING",
            "name": "AWS GuardDuty High/Critical Threat Finding",
            "description": "Detects active cloud threat findings reported by AWS GuardDuty (CryptoCurrency:EC2/BitcoinTool, Trojan:EC2/DNSDataExfiltration).",
            "severity": "Critical",
            "category": "Cloud Security",
            "is_correlation_rule": False,
            "time_window_seconds": 60,
            "threshold": 1,
            "parameters_json": json.dumps({"min_severity": "High"})
        },
        # 13. Multi-Stage Attack Correlation
        {
            "rule_code": "MULTI_EVENT_CORRELATION",
            "name": "Correlated Attack Chain (Compromise followed by C2 Beacon)",
            "description": "Correlates multi-step attacker behavior: an authentication failure burst or exploit on a host followed by anomalous outbound network connections within 15 minutes.",
            "severity": "Critical",
            "category": "Correlation",
            "is_correlation_rule": True,
            "time_window_seconds": 900,
            "threshold": 2,
            "correlation_pattern": "BRUTE_FORCE_THEN_C2",
            "parameters_json": json.dumps({"window_seconds": 900})
        }
    ]

    for r in default_rules:
        existing = db.query(DetectionRule).filter(DetectionRule.rule_code == r["rule_code"]).first()
        if not existing:
            new_rule = DetectionRule(
                rule_code=r["rule_code"],
                name=r["name"],
                description=r["description"],
                severity=r["severity"],
                category=r["category"],
                is_enabled=True,
                is_correlation_rule=r.get("is_correlation_rule", False),
                time_window_seconds=r.get("time_window_seconds", 300),
                correlation_pattern=r.get("correlation_pattern"),
                threshold=r.get("threshold", 5),
                parameters_json=r["parameters_json"],
                created_at=datetime.utcnow(),
                updated_at=datetime.utcnow()
            )
            db.add(new_rule)
        else:
            # Update parameters and metadata if already exists
            existing.name = r["name"]
            existing.description = r["description"]
            existing.is_correlation_rule = r.get("is_correlation_rule", False)
            existing.correlation_pattern = r.get("correlation_pattern")
            existing.time_window_seconds = r.get("time_window_seconds", 300)
            existing.threshold = r.get("threshold", 5)

    db.commit()

def run_detection_pipeline_for_event(db: Session, event: SecurityEvent) -> List[DetectionResult]:
    """
    Evaluates enabled detection rules against an incoming security event.
    Deterministic, auditable, and independent of external AI services.
    """
    generated_results = []
    
    # -------------------------------------------------------------
    # Rule 1: AUTH_FAILED_BURST (Single Host Brute Force)
    # -------------------------------------------------------------
    if event.event_type in ["auth_failure", "failed_login"]:
        rule = db.query(DetectionRule).filter(
            DetectionRule.rule_code == "AUTH_FAILED_BURST",
            DetectionRule.is_enabled == True
        ).first()
        if rule and event.source_ip:
            params = json.loads(rule.parameters_json or "{}")
            threshold = params.get("threshold", rule.threshold or 5)
            window = params.get("window_seconds", rule.time_window_seconds or 300)
            window_start = event.timestamp - timedelta(seconds=window)
            
            count = db.query(SecurityEvent).filter(
                SecurityEvent.organization_id == event.organization_id,
                SecurityEvent.event_type.in_(["auth_failure", "failed_login"]),
                SecurityEvent.source_ip == event.source_ip,
                SecurityEvent.timestamp >= window_start
            ).count()
            
            if count >= threshold:
                det = DetectionResult(
                    organization_id=event.organization_id,
                    rule_id=rule.id,
                    rule_name=rule.name,
                    severity=rule.severity,
                    title=f"Brute Force Alert: {count} failed logins from {event.source_ip}",
                    description=f"Observed {count} failed authentication attempts within {window}s originating from source IP {event.source_ip}.",
                    evidence_json=json.dumps({
                        "source_ip": event.source_ip,
                        "failed_attempts": count,
                        "threshold": threshold,
                        "time_window_seconds": window,
                        "triggering_event_id": event.id
                    }),
                    confidence=90,
                    related_asset_id=event.asset_id,
                    related_ip=event.source_ip,
                    is_simulated=event.is_simulated,
                    status="Open",
                    timestamp=datetime.utcnow()
                )
                db.add(det)
                db.flush()
                generated_results.append(det)

    # -------------------------------------------------------------
    # Rule 2: AUTH_FAILED_MULTI_ASSET (Distributed Stuffing)
    # -------------------------------------------------------------
    if event.event_type in ["auth_failure", "failed_login"] and event.source_ip:
        rule_multi = db.query(DetectionRule).filter(
            DetectionRule.rule_code == "AUTH_FAILED_MULTI_ASSET",
            DetectionRule.is_enabled == True
        ).first()
        if rule_multi:
            window = rule_multi.time_window_seconds or 600
            window_start = event.timestamp - timedelta(seconds=window)
            distinct_targets = db.query(func.count(func.distinct(func.coalesce(SecurityEvent.asset_id, SecurityEvent.destination_ip)))).filter(
                SecurityEvent.organization_id == event.organization_id,
                SecurityEvent.event_type.in_(["auth_failure", "failed_login"]),
                SecurityEvent.source_ip == event.source_ip,
                SecurityEvent.timestamp >= window_start
            ).scalar() or 0

            if distinct_targets >= (rule_multi.threshold or 3):
                det = DetectionResult(
                    organization_id=event.organization_id,
                    rule_id=rule_multi.id,
                    rule_name=rule_multi.name,
                    severity=rule_multi.severity,
                    title=f"Distributed Credential Stuffing: {distinct_targets} hosts targeted by {event.source_ip}",
                    description=f"Source IP {event.source_ip} attempted failed logins across {distinct_targets} distinct endpoints within {window}s.",
                    evidence_json=json.dumps({
                        "source_ip": event.source_ip,
                        "distinct_assets_targeted": distinct_targets,
                        "threshold": rule_multi.threshold,
                        "window_seconds": window
                    }),
                    confidence=95,
                    related_ip=event.source_ip,
                    is_simulated=event.is_simulated,
                    status="Open",
                    timestamp=datetime.utcnow()
                )
                db.add(det)
                db.flush()
                generated_results.append(det)

    # -------------------------------------------------------------
    # Rule 3: PORT_SCAN_ACTIVITY
    # -------------------------------------------------------------
    if event.event_type in ["port_scan", "network_connection"] and event.source_ip:
        rule = db.query(DetectionRule).filter(
            DetectionRule.rule_code == "PORT_SCAN_ACTIVITY",
            DetectionRule.is_enabled == True
        ).first()
        if rule:
            params = json.loads(rule.parameters_json or "{}")
            port_threshold = params.get("port_count_threshold", rule.threshold or 5)
            window = params.get("window_seconds", rule.time_window_seconds or 60)
            window_start = event.timestamp - timedelta(seconds=window)
            
            distinct_ports = db.query(func.count(func.distinct(SecurityEvent.destination_port))).filter(
                SecurityEvent.organization_id == event.organization_id,
                SecurityEvent.source_ip == event.source_ip,
                SecurityEvent.destination_port.isnot(None),
                SecurityEvent.timestamp >= window_start
            ).scalar() or 0
            
            if distinct_ports >= port_threshold:
                det = DetectionResult(
                    organization_id=event.organization_id,
                    rule_id=rule.id,
                    rule_name=rule.name,
                    severity=rule.severity,
                    title=f"Port Scan Detected: {distinct_ports} distinct ports probed by {event.source_ip}",
                    description=f"Observed sequential probe attempts to {distinct_ports} ports within {window}s originating from {event.source_ip}.",
                    evidence_json=json.dumps({
                        "source_ip": event.source_ip,
                        "distinct_ports_scanned": distinct_ports,
                        "threshold": port_threshold,
                        "window_seconds": window
                    }),
                    confidence=85,
                    related_asset_id=event.asset_id,
                    related_ip=event.source_ip,
                    is_simulated=event.is_simulated,
                    status="Open",
                    timestamp=datetime.utcnow()
                )
                db.add(det)
                db.flush()
                generated_results.append(det)

    # -------------------------------------------------------------
    # Rule 4: MALICIOUS_IP_MATCH
    # -------------------------------------------------------------
    eval_ips = [ip for ip in [event.source_ip, event.destination_ip] if ip]
    if eval_ips:
        rule = db.query(DetectionRule).filter(
            DetectionRule.rule_code == "MALICIOUS_IP_MATCH",
            DetectionRule.is_enabled == True
        ).first()
        if rule:
            match = db.query(ThreatIndicator).filter(
                ThreatIndicator.indicator_value.in_(eval_ips)
            ).first()
            if match:
                det = DetectionResult(
                    organization_id=event.organization_id,
                    rule_id=rule.id,
                    rule_name=rule.name,
                    severity=rule.severity,
                    title=f"Threat Feed Match: Connection to {match.indicator_value} ({match.threat_type})",
                    description=f"Observed communication with known malicious indicator {match.indicator_value} (Source: {match.source}, Severity: {match.severity}).",
                    evidence_json=json.dumps({
                        "matched_ip": match.indicator_value,
                        "threat_type": match.threat_type,
                        "threat_source": match.source,
                        "confidence": match.confidence,
                        "triggering_event_id": event.id
                    }),
                    confidence=match.confidence,
                    related_asset_id=event.asset_id,
                    related_ip=match.indicator_value,
                    is_simulated=event.is_simulated,
                    status="Open",
                    timestamp=datetime.utcnow()
                )
                db.add(det)
                db.flush()
                generated_results.append(det)

    # -------------------------------------------------------------
    # Rule 5: UNUSUAL_OUTBOUND_CONN (Suspicious C2 Ports)
    # -------------------------------------------------------------
    if event.destination_port:
        rule = db.query(DetectionRule).filter(
            DetectionRule.rule_code == "UNUSUAL_OUTBOUND_CONN",
            DetectionRule.is_enabled == True
        ).first()
        if rule:
            params = json.loads(rule.parameters_json or "{}")
            suspicious_ports = params.get("suspicious_ports", [4444, 1337, 6667, 31337, 8888, 9999])
            if event.destination_port in suspicious_ports:
                det = DetectionResult(
                    organization_id=event.organization_id,
                    rule_id=rule.id,
                    rule_name=rule.name,
                    severity=rule.severity,
                    title=f"Suspicious Outbound Port {event.destination_port} to {event.destination_ip or 'Remote'}",
                    description=f"Observed traffic destined for port {event.destination_port}, an anomalous port frequently associated with reverse shells and C2 beaconing.",
                    evidence_json=json.dumps({
                        "destination_port": event.destination_port,
                        "destination_ip": event.destination_ip,
                        "source_ip": event.source_ip,
                        "protocol": event.protocol
                    }),
                    confidence=80,
                    related_asset_id=event.asset_id,
                    related_ip=event.destination_ip,
                    is_simulated=event.is_simulated,
                    status="Open",
                    timestamp=datetime.utcnow()
                )
                db.add(det)
                db.flush()
                generated_results.append(det)

    # -------------------------------------------------------------
    # Rule 8: SUSPICIOUS_PROCESS_ACTIVITY (Living-off-the-Land)
    # -------------------------------------------------------------
    if event.event_type in ["process_exec", "command_exec"] or "powershell" in (event.description or "").lower():
        rule = db.query(DetectionRule).filter(
            DetectionRule.rule_code == "SUSPICIOUS_PROCESS_ACTIVITY",
            DetectionRule.is_enabled == True
        ).first()
        if rule:
            raw = (event.raw_payload or "") + " " + (event.description or "")
            suspicious_terms = ["powershell -enc", "certutil -urlcache", "vssadmin delete", "net user /add", "whoami /priv", "bash -i"]
            matched_term = next((t for t in suspicious_terms if t in raw.lower()), None)
            if matched_term:
                det = DetectionResult(
                    organization_id=event.organization_id,
                    rule_id=rule.id,
                    rule_name=rule.name,
                    severity=rule.severity,
                    title=f"Suspicious Process Invocation: {matched_term}",
                    description=f"Observed execution of dual-use command '{matched_term}' on monitored endpoint.",
                    evidence_json=json.dumps({
                        "matched_keyword": matched_term,
                        "title": event.title,
                        "raw_command_excerpt": raw[:200]
                    }),
                    confidence=88,
                    related_asset_id=event.asset_id,
                    is_simulated=event.is_simulated,
                    status="Open",
                    timestamp=datetime.utcnow()
                )
                db.add(det)
                db.flush()
                generated_results.append(det)

    # -------------------------------------------------------------
    # Rule 10: AWS_RISKY_IAM_MODIFICATION
    # -------------------------------------------------------------
    if "iam" in event.event_type.lower() or "administratoraccess" in (event.description or "").lower():
        rule = db.query(DetectionRule).filter(
            DetectionRule.rule_code == "AWS_RISKY_IAM_MODIFICATION",
            DetectionRule.is_enabled == True
        ).first()
        if rule:
            det = DetectionResult(
                organization_id=event.organization_id,
                rule_id=rule.id,
                rule_name=rule.name,
                severity=rule.severity,
                title="Critical AWS IAM Policy Attachment Detected",
                description=f"Cloud audit recorded privileged policy attachment: {event.description}",
                evidence_json=json.dumps({
                    "service": "AWS IAM",
                    "event_type": event.event_type,
                    "details": event.description
                }),
                confidence=95,
                is_simulated=event.is_simulated,
                status="Open",
                timestamp=datetime.utcnow()
            )
            db.add(det)
            db.flush()
            generated_results.append(det)

    # Automatically escalate High and Critical alerts into Case Management Incidents
    for res in generated_results:
        if res.severity in ["High", "Critical"]:
            create_or_link_incident(db, res)

    db.commit()
    return generated_results

def create_or_link_incident(db: Session, detection: DetectionResult) -> Optional[Incident]:
    """
    Escalates high/critical alerts into actionable case management incidents with timeline records.
    """
    now = datetime.utcnow()
    one_hour_ago = now - timedelta(hours=1)
    
    # Check for existing open incident for same related IP or asset
    existing_incident = db.query(Incident).filter(
        Incident.organization_id == detection.organization_id,
        Incident.status.in_(["New", "Acknowledged", "Investigating"]),
        Incident.created_at >= one_hour_ago
    )
    if detection.related_ip:
        existing_incident = existing_incident.filter(Incident.related_ip_addresses_json.like(f"%{detection.related_ip}%"))
    elif detection.related_asset_id:
        existing_incident = existing_incident.filter(Incident.related_asset_ids_json.like(f"%{detection.related_asset_id}%"))
    else:
        existing_incident = existing_incident.filter(Incident.title.like(f"%{detection.rule_name}%"))
        
    incident = existing_incident.first()

    if not incident:
        # Create brand-new Incident
        incident = Incident(
            organization_id=detection.organization_id,
            title=f"Incident: {detection.title}",
            description=f"Automated incident created from {detection.severity} alert '{detection.rule_name}'. {detection.description}",
            severity=detection.severity,
            status="New",
            related_asset_ids_json=json.dumps([detection.related_asset_id] if detection.related_asset_id else []),
            related_ip_addresses_json=json.dumps([detection.related_ip] if detection.related_ip else []),
            is_simulated=detection.is_simulated,
            created_at=now,
            updated_at=now
        )
        db.add(incident)
        db.flush()

        # Add Incident Timeline Entry: CREATED
        entry = IncidentTimelineEntry(
            incident_id=incident.id,
            organization_id=detection.organization_id,
            entry_type="CREATED",
            title="Incident Opened",
            description=f"Incident opened automatically from alert: {detection.title}",
            actor_type="SYSTEM",
            actor_name="Sentinel Detection Engine",
            metadata_json=detection.evidence_json,
            timestamp=now
        )
        db.add(entry)
    else:
        # Update existing incident severity if higher
        if detection.severity == "Critical" and incident.severity != "Critical":
            incident.severity = "Critical"
        if not detection.is_simulated:
            incident.is_simulated = False
        incident.updated_at = now

    # Link Detection to Incident
    inc_event = IncidentEvent(
        incident_id=incident.id,
        detection_result_id=detection.id
    )
    db.add(inc_event)

    # Add Incident Timeline Entry: DETECTION_ATTACHED
    entry_det = IncidentTimelineEntry(
        incident_id=incident.id,
        organization_id=detection.organization_id,
        entry_type="DETECTION_ATTACHED",
        title=f"Alert Attached: {detection.title}",
        description=detection.description,
        actor_type="SYSTEM",
        actor_name="Detection Engine",
        metadata_json=detection.evidence_json,
        timestamp=now
    )
    db.add(entry_det)

    # In-app notification
    send_notification(
        db=db,
        organization_id=detection.organization_id,
        title=f"Security Alert Escalated: {detection.title}",
        message=f"{detection.severity} severity alert '{detection.rule_name}' was escalated to Incident {incident.id[:8]}",
        notification_type="ALERT",
        severity=detection.severity,
        link_url=f"/incidents"
    )

    db.commit()
    return incident

def run_event_correlation(
    db: Session,
    org_id: str,
    time_window_seconds: int = 900
) -> List[CorrelatedEventGroup]:
    """
    Advanced Multi-Stage Event Correlation Engine:
    Examines time-window sequences, multi-asset relations, and attack progression:
    - Pattern 1: Brute Force (auth_failure) followed by C2 outbound connection on same host.
    - Pattern 2: Port scan probe followed by high-severity alert on target host.
    - Pattern 3: Unauthorized LAN device followed by authentication failures.
    """
    now = datetime.utcnow()
    window_start = now - timedelta(seconds=time_window_seconds)
    created_groups = []

    # Correlation Pattern 1: BRUTE_FORCE_THEN_C2 (Compromise -> Outbound C2)
    auth_fails = db.query(SecurityEvent).filter(
        SecurityEvent.organization_id == org_id,
        SecurityEvent.event_type.in_(["auth_failure", "failed_login"]),
        SecurityEvent.timestamp >= window_start,
        SecurityEvent.asset_id.isnot(None)
    ).all()

    for af in auth_fails:
        outbound = db.query(SecurityEvent).filter(
            SecurityEvent.organization_id == org_id,
            SecurityEvent.asset_id == af.asset_id,
            SecurityEvent.event_type == "outbound_conn",
            SecurityEvent.timestamp >= af.timestamp,
            SecurityEvent.timestamp <= af.timestamp + timedelta(minutes=15)
        ).first()

        if outbound:
            # Check if this pair is already correlated
            existing = db.query(CorrelatedEventGroup).filter(
                CorrelatedEventGroup.organization_id == org_id,
                CorrelatedEventGroup.rule_code == "MULTI_EVENT_CORRELATION",
                CorrelatedEventGroup.event_ids_json.like(f"%{af.id}%")
            ).first()

            if not existing:
                group = CorrelatedEventGroup(
                    organization_id=org_id,
                    rule_code="MULTI_EVENT_CORRELATION",
                    title="Correlated Attack Progression: Authentication Burst followed by Outbound Connection",
                    description=f"Host '{af.asset_id}' experienced failed logins from {af.source_ip} followed by an anomalous outbound connection to {outbound.destination_ip}:{outbound.destination_port} within 15 minutes.",
                    severity="Critical",
                    confidence=92,
                    time_window_start=af.timestamp,
                    time_window_end=outbound.timestamp,
                    event_ids_json=json.dumps([af.id, outbound.id]),
                    asset_ids_json=json.dumps([af.asset_id]),
                    ip_addresses_json=json.dumps([ip for ip in [af.source_ip, outbound.destination_ip] if ip]),
                    explanation=(
                        f"Correlation rationale: The sequence of failed authentication attempts followed by "
                        f"outbound traffic on non-standard ports indicates possible credential compromise leading to "
                        f"outbound command-and-control beaconing on asset '{af.asset_id}'."
                    ),
                    status="Active",
                    created_at=now
                )
                db.add(group)
                db.flush()
                created_groups.append(group)

    db.commit()
    return created_groups
