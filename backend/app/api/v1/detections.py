import json
from typing import List, Optional, Dict, Any
from datetime import datetime
from fastapi import APIRouter, Depends, HTTPException, status, Query
from sqlalchemy.orm import Session

from backend.app.database import get_db
from backend.app.core.dependencies import get_current_org, require_role
from backend.app.core.detection_engine import seed_default_detection_rules, run_event_correlation
from backend.app.models.auth import Organization
from backend.app.models.detections import DetectionRule, DetectionResult, CorrelatedEventGroup
from backend.app.schemas.detections import (
    DetectionRuleOut,
    DetectionResultOut,
    CorrelatedEventGroupOut,
    RuleParametersUpdate
)

router = APIRouter(prefix="/detections", tags=["Detection Center"])

@router.get("/rules", response_model=List[DetectionRuleOut])
def list_detection_rules(org: Organization = Depends(get_current_org), db: Session = Depends(get_db)):
    """
    Returns the complete catalog of all 13 detection and correlation rules.
    """
    seed_default_detection_rules(db)
    return db.query(DetectionRule).order_by(DetectionRule.is_correlation_rule.desc(), DetectionRule.name.asc()).all()

@router.patch("/rules/{rule_id}/toggle", dependencies=[Depends(require_role(["Organization Owner", "Organization Administrator"]))])
def toggle_detection_rule(
    rule_id: str,
    enabled: bool,
    db: Session = Depends(get_db)
):
    rule = db.query(DetectionRule).filter(DetectionRule.id == rule_id).first()
    if not rule:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Detection rule not found")
    rule.is_enabled = enabled
    rule.updated_at = datetime.utcnow()
    db.commit()
    return {"status": "success", "rule_id": rule.id, "is_enabled": rule.is_enabled}

@router.put("/rules/{rule_id}/parameters", dependencies=[Depends(require_role(["Organization Owner", "Organization Administrator"]))])
@router.patch("/rules/{rule_id}/parameters", dependencies=[Depends(require_role(["Organization Owner", "Organization Administrator"]))])
def update_rule_parameters(
    rule_id: str,
    payload: RuleParametersUpdate,
    db: Session = Depends(get_db)
):
    rule = db.query(DetectionRule).filter(DetectionRule.id == rule_id).first()
    if not rule:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Detection rule not found")
    if payload.threshold is not None:
        rule.threshold = payload.threshold
    if payload.time_window_seconds is not None:
        rule.time_window_seconds = payload.time_window_seconds
    if payload.severity is not None:
        rule.severity = payload.severity
    if payload.is_enabled is not None:
        rule.is_enabled = payload.is_enabled
    rule.updated_at = datetime.utcnow()
    db.commit()
    db.refresh(rule)
    return {
        "status": "success",
        "rule_id": rule.id,
        "threshold": rule.threshold,
        "time_window_seconds": rule.time_window_seconds,
        "severity": rule.severity,
        "is_enabled": rule.is_enabled
    }

@router.get("/alerts", response_model=List[DetectionResultOut])
def list_detection_alerts(
    severity: Optional[str] = None,
    status_filter: Optional[str] = None,
    is_simulated: Optional[bool] = None,
    limit: int = 100,
    org: Organization = Depends(get_current_org),
    db: Session = Depends(get_db)
):
    query = db.query(DetectionResult).filter(DetectionResult.organization_id == org.id)
    if severity:
        query = query.filter(DetectionResult.severity == severity)
    if status_filter:
        query = query.filter(DetectionResult.status == status_filter)
    if is_simulated is not None:
        query = query.filter(DetectionResult.is_simulated == is_simulated)
    return query.order_by(DetectionResult.timestamp.desc()).limit(limit).all()

@router.patch("/alerts/{alert_id}/status", dependencies=[Depends(require_role(["Organization Owner", "Organization Administrator", "Security Analyst"]))])
def update_alert_status(
    alert_id: str,
    new_status: str,
    org: Organization = Depends(get_current_org),
    db: Session = Depends(get_db)
):
    alert = db.query(DetectionResult).filter(
        DetectionResult.id == alert_id,
        DetectionResult.organization_id == org.id
    ).first()
    if not alert:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Alert not found")
        
    alert.status = new_status
    db.commit()
    return {"status": "success", "alert_id": alert.id, "new_status": alert.status}

@router.post("/correlate", dependencies=[Depends(require_role(["Organization Owner", "Organization Administrator", "Security Analyst"]))])
def trigger_correlation(
    window_seconds: int = Query(default=900, description="Time window in seconds to correlate"),
    org: Organization = Depends(get_current_org),
    db: Session = Depends(get_db)
):
    """
    Executes the multi-stage event correlation engine across recent security telemetry.
    """
    groups = run_event_correlation(db=db, org_id=org.id, time_window_seconds=window_seconds)
    return {
        "status": "success",
        "correlated_groups_created": len(groups),
        "message": f"Successfully evaluated attack chain correlation across {window_seconds}s window."
    }

@router.get("/correlations", response_model=List[CorrelatedEventGroupOut])
def list_correlated_groups(
    org: Organization = Depends(get_current_org),
    db: Session = Depends(get_db)
):
    """
    Lists correlated attack progression groups with underlying evidence and rationale.
    """
    records = db.query(CorrelatedEventGroup).filter(
        CorrelatedEventGroup.organization_id == org.id
    ).order_by(CorrelatedEventGroup.created_at.desc()).all()

    return [
        CorrelatedEventGroupOut(
            id=r.id,
            organization_id=r.organization_id,
            rule_code=r.rule_code,
            title=r.title,
            description=r.description,
            severity=r.severity,
            confidence=r.confidence,
            time_window_start=r.time_window_start,
            time_window_end=r.time_window_end,
            event_ids=json.loads(r.event_ids_json or "[]"),
            asset_ids=json.loads(r.asset_ids_json or "[]"),
            ip_addresses=json.loads(r.ip_addresses_json or "[]"),
            explanation=r.explanation,
            status=r.status,
            created_at=r.created_at
        )
        for r in records
    ]
