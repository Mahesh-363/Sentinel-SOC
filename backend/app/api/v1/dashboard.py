from datetime import datetime, timedelta
from typing import Dict, Any, List
from fastapi import APIRouter, Depends, Response
from sqlalchemy.orm import Session
from sqlalchemy import func

from backend.app.database import get_db
from backend.app.config import settings
from backend.app.core.datetime_utils import serialize_utc_datetime
from backend.app.core.dependencies import get_current_org
from backend.app.core.ai.provider import get_ai_provider
from backend.app.models.auth import Organization
from backend.app.models.assets import Asset, Sensor
from backend.app.models.events import SecurityEvent
from backend.app.models.detections import DetectionResult
from backend.app.models.incidents import Incident
from backend.app.models.network import NetworkDevice, IPObservation
from backend.app.models.aws import AWSFinding
from backend.app.schemas.dashboard import DashboardStatsOut
from backend.app.api.v1.sensors import compute_sensor_status

router = APIRouter(prefix="/dashboard", tags=["Dashboard"])

@router.get("/stats", response_model=DashboardStatsOut)
def get_dashboard_stats(
    response: Response,
    org: Organization = Depends(get_current_org),
    db: Session = Depends(get_db)
):
    response.headers["Cache-Control"] = "no-cache, no-store, must-revalidate"
    now = datetime.utcnow()
    past_24h = now - timedelta(hours=24)

    # 1. Assets count and fleet risk metrics
    assets = db.query(Asset).filter(Asset.organization_id == org.id).all()
    total_assets = len(assets)
    fleet_average_risk_score = int(sum(getattr(a, 'risk_score', 15) for a in assets) / total_assets) if total_assets > 0 else 15
    high_risk_assets_count = sum(1 for a in assets if getattr(a, 'risk_score', 15) >= 60)

    # 2. Sensors count dynamically evaluated against heartbeat timeout
    all_sensors = db.query(Sensor).filter(Sensor.organization_id == org.id).all()
    online_sensors = 0
    offline_sensors = 0
    pending_sensors = 0
    sensor_status_updated = False
    for s in all_sensors:
        computed = compute_sensor_status(s, now)
        if s.status != computed:
            s.status = computed
            sensor_status_updated = True
        if computed == "Online":
            online_sensors += 1
        elif computed == "Pending enrollment":
            pending_sensors += 1
        else:
            offline_sensors += 1
    if sensor_status_updated:
        db.commit()

    # 3. Security events in 24h (total, genuine, simulated)
    total_events_24h = db.query(SecurityEvent).filter(
        SecurityEvent.organization_id == org.id,
        SecurityEvent.timestamp >= past_24h
    ).count()
    simulated_events_24h = db.query(SecurityEvent).filter(
        SecurityEvent.organization_id == org.id,
        SecurityEvent.is_simulated == True,
        SecurityEvent.timestamp >= past_24h
    ).count()
    genuine_events_24h = total_events_24h - simulated_events_24h

    # 4. Critical & High Alerts
    critical_high_alerts = db.query(DetectionResult).filter(
        DetectionResult.organization_id == org.id,
        DetectionResult.severity.in_(["Critical", "High"]),
        DetectionResult.status.in_(["Open", "In Review"])
    ).count()

    # 5. Open Incidents (total, genuine, simulated)
    open_incidents = db.query(Incident).filter(
        Incident.organization_id == org.id,
        Incident.status.in_(["New", "Acknowledged", "Investigating", "Contained"])
    ).count()
    simulated_incidents_count = db.query(Incident).filter(
        Incident.organization_id == org.id,
        Incident.is_simulated == True
    ).count()
    genuine_incidents_count = db.query(Incident).filter(
        Incident.organization_id == org.id,
        Incident.is_simulated == False
    ).count()

    # 6. Network devices & AWS findings
    network_devices_count = db.query(NetworkDevice).filter(NetworkDevice.organization_id == org.id).count()
    aws_findings_count = db.query(AWSFinding).filter(AWSFinding.organization_id == org.id).count()

    # 7. Severity distribution of recent events
    severities = ["Critical", "High", "Medium", "Low", "Informational"]
    severity_distribution = {}
    for sev in severities:
        count = db.query(SecurityEvent).filter(
            SecurityEvent.organization_id == org.id,
            SecurityEvent.severity == sev,
            SecurityEvent.timestamp >= past_24h
        ).count()
        severity_distribution[sev] = count

    # 8. Event trend for past 24 hours (hourly buckets)
    event_trend = []
    for h in range(23, -1, -1):
        bucket_start = now - timedelta(hours=h+1)
        bucket_end = now - timedelta(hours=h)
        cnt = db.query(SecurityEvent).filter(
            SecurityEvent.organization_id == org.id,
            SecurityEvent.timestamp >= bucket_start,
            SecurityEvent.timestamp < bucket_end
        ).count()
        event_trend.append({
            "time": bucket_end.strftime("%H:00"),
            "events": cnt
        })

    # 9. Recent suspicious IPs observed
    recent_suspicious = db.query(DetectionResult).filter(
        DetectionResult.organization_id == org.id,
        DetectionResult.related_ip != None
    ).order_by(DetectionResult.timestamp.desc()).limit(6).all()
    
    suspicious_ips = []
    for d in recent_suspicious:
        suspicious_ips.append({
            "ip": d.related_ip,
            "severity": d.severity,
            "rule": d.rule_name,
            "timestamp": serialize_utc_datetime(d.timestamp),
            "is_simulated": d.is_simulated
        })

    # 10. Recent security activity feed
    recent_events = db.query(SecurityEvent).filter(
        SecurityEvent.organization_id == org.id
    ).order_by(SecurityEvent.timestamp.desc()).limit(8).all()
    
    activity = []
    for e in recent_events:
        activity.append({
            "id": e.id,
            "type": e.event_type,
            "title": e.title,
            "severity": e.severity,
            "source_ip": e.source_ip,
            "destination_ip": e.destination_ip,
            "timestamp": serialize_utc_datetime(e.timestamp),
            "is_simulated": e.is_simulated
        })

    # 11. Sensor health breakdown
    sensor_health = {
        "Online": online_sensors,
        "Offline": offline_sensors,
        "Pending": pending_sensors
    }

    # 12. Integration health
    ai_provider = get_ai_provider()
    integration_health = {
        "ai_provider": ai_provider.health_check(),
        "database": {"status": "ONLINE", "dialect": db.bind.dialect.name},
        "redis": {"status": "ONLINE" if settings.REDIS_ENABLED else "LOCAL_FALLBACK", "enabled": settings.REDIS_ENABLED},
        "abuseipdb": {"status": "ONLINE" if settings.ABUSEIPDB_API_KEY else "NOT CONFIGURED"},
        "email_delivery": {"status": "ONLINE" if settings.EMAIL_ENABLED else "NOT CONFIGURED (DEV MOCK)"},
        "aws_cloud": {"status": "ONLINE" if settings.AWS_ENABLED else "NOT CONFIGURED"}
    }

    return DashboardStatsOut(
        total_assets=total_assets,
        online_sensors=online_sensors,
        offline_sensors=offline_sensors,
        total_events_24h=total_events_24h,
        critical_high_alerts=critical_high_alerts,
        open_incidents=open_incidents,
        network_devices_count=network_devices_count,
        aws_findings_count=aws_findings_count,
        simulated_events_24h=simulated_events_24h,
        genuine_events_24h=genuine_events_24h,
        simulated_incidents_count=simulated_incidents_count,
        genuine_incidents_count=genuine_incidents_count,
        fleet_average_risk_score=fleet_average_risk_score,
        high_risk_assets_count=high_risk_assets_count,
        severity_distribution=severity_distribution,
        event_trend_24h=event_trend,
        recent_suspicious_ips=suspicious_ips,
        recent_activity=activity,
        sensor_health_summary=sensor_health,
        integration_health=integration_health
    )
