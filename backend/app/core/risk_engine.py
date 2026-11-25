from datetime import datetime, timedelta
from typing import Dict, Any, Tuple
from sqlalchemy.orm import Session
from sqlalchemy import func

from backend.app.core.datetime_utils import serialize_utc_datetime
from backend.app.models.assets import Asset
from backend.app.models.detections import DetectionResult
from backend.app.models.events import SecurityEvent
from backend.app.models.incidents import Incident

def calculate_asset_risk_score(db: Session, asset: Asset) -> Tuple[int, str, Dict[str, Any]]:
    """
    Computes a deterministic, auditable risk score (0-100) and risk level for an asset.
    Factors considered:
    1. Active Detection Alerts (Critical: +25, High: +15, Medium: +5)
    2. Open Incidents linked to asset (+20 each)
    3. Failed Authentication Bursts in past 24h (+10 to +15)
    4. Asset Health & Connectivity Status (+15 for offline, +25 for critical)
    """
    factors = []
    score = 10  # Baseline asset operational score

    now = datetime.utcnow()
    past_24h = now - timedelta(hours=24)

    # 1. Active Detection Alerts linked to this asset
    open_alerts = db.query(DetectionResult).filter(
        DetectionResult.organization_id == asset.organization_id,
        DetectionResult.related_asset_id == asset.id,
        DetectionResult.status.in_(["Open", "In Review"])
    ).all()

    crit_count = sum(1 for a in open_alerts if a.severity == "Critical")
    high_count = sum(1 for a in open_alerts if a.severity == "High")
    med_count = sum(1 for a in open_alerts if a.severity == "Medium")

    if crit_count > 0:
        alert_pts = min(50, crit_count * 25)
        score += alert_pts
        factors.append(f"{crit_count} active Critical alert(s) (+{alert_pts})")

    if high_count > 0:
        alert_pts = min(30, high_count * 15)
        score += alert_pts
        factors.append(f"{high_count} active High alert(s) (+{alert_pts})")

    if med_count > 0:
        alert_pts = min(15, med_count * 5)
        score += alert_pts
        factors.append(f"{med_count} active Medium alert(s) (+{alert_pts})")

    # 2. Associated Open Incidents
    open_incidents = db.query(Incident).filter(
        Incident.organization_id == asset.organization_id,
        Incident.status.in_(["New", "Acknowledged", "Investigating"]),
        Incident.related_asset_ids_json.like(f"%{asset.id}%")
    ).count()

    if open_incidents > 0:
        inc_pts = min(30, open_incidents * 20)
        score += inc_pts
        factors.append(f"{open_incidents} active case incident(s) (+{inc_pts})")

    # 3. Failed Authentication Events in 24h
    failed_logins = db.query(SecurityEvent).filter(
        SecurityEvent.organization_id == asset.organization_id,
        SecurityEvent.asset_id == asset.id,
        SecurityEvent.event_type.in_(["auth_failure", "failed_login"]),
        SecurityEvent.timestamp >= past_24h
    ).count()

    if failed_logins >= 10:
        score += 15
        factors.append(f"{failed_logins} failed login attempts in 24h (+15)")
    elif failed_logins >= 5:
        score += 10
        factors.append(f"{failed_logins} failed login attempts in 24h (+10)")

    # 4. Asset Health Status
    if asset.health_status == "critical":
        score += 25
        factors.append("Asset health flagged as Critical (+25)")
    elif asset.health_status == "warning":
        score += 10
        factors.append("Asset health flagged as Warning (+10)")
    elif asset.health_status == "offline":
        score += 15
        factors.append("Asset agent sensor currently Offline (+15)")

    # Normalize final score between 0 and 100
    final_score = min(100, max(0, score))

    if final_score >= 80:
        level = "Critical"
    elif final_score >= 60:
        level = "High"
    elif final_score >= 30:
        level = "Medium"
    else:
        level = "Low"

    breakdown = {
        "asset_id": asset.id,
        "hostname": asset.hostname,
        "score": final_score,
        "level": level,
        "factors": factors or ["Nominal operational baseline"],
        "calculated_at": serialize_utc_datetime(now)
    }

    return final_score, level, breakdown

def update_asset_risk_score(db: Session, asset: Asset) -> Asset:
    """Calculates and updates risk score directly on asset entity."""
    score, level, _ = calculate_asset_risk_score(db, asset)
    asset.risk_score = score
    asset.risk_level = level
    db.commit()
    db.refresh(asset)
    return asset
