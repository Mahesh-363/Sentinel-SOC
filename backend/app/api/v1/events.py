from typing import List, Optional
from datetime import datetime, timedelta
from fastapi import APIRouter, Depends, Query, HTTPException, status
from sqlalchemy.orm import Session

from backend.app.database import get_db
from backend.app.core.dependencies import get_current_org, require_role
from backend.app.models.auth import Organization
from backend.app.models.events import SecurityEvent, ThreatIndicator
from backend.app.schemas.events import SecurityEventCreate, SecurityEventOut, ThreatIndicatorOut

router = APIRouter(prefix="/events", tags=["Security Events"])

@router.get("", response_model=List[SecurityEventOut])
def list_events(
    severity: Optional[str] = None,
    event_type: Optional[str] = None,
    source_ip: Optional[str] = None,
    asset_id: Optional[str] = None,
    is_simulated: Optional[bool] = None,
    hours: int = 48,
    limit: int = 100,
    org: Organization = Depends(get_current_org),
    db: Session = Depends(get_db)
):
    since = datetime.utcnow() - timedelta(hours=hours)
    query = db.query(SecurityEvent).filter(
        SecurityEvent.organization_id == org.id,
        SecurityEvent.timestamp >= since
    )
    if severity:
        query = query.filter(SecurityEvent.severity == severity)
    if event_type:
        query = query.filter(SecurityEvent.event_type == event_type)
    if source_ip:
        query = query.filter(SecurityEvent.source_ip == source_ip)
    if asset_id:
        query = query.filter(SecurityEvent.asset_id == asset_id)
    if is_simulated is not None:
        query = query.filter(SecurityEvent.is_simulated == is_simulated)

    return query.order_by(SecurityEvent.timestamp.desc()).limit(limit).all()

@router.get("/{event_id}", response_model=SecurityEventOut)
def get_event(
    event_id: str,
    org: Organization = Depends(get_current_org),
    db: Session = Depends(get_db)
):
    ev = db.query(SecurityEvent).filter(
        SecurityEvent.id == event_id,
        SecurityEvent.organization_id == org.id
    ).first()
    if not ev:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Security event not found")
    return ev

@router.get("/threat/indicators", response_model=List[ThreatIndicatorOut])
def list_threat_indicators(limit: int = 50, db: Session = Depends(get_db)):
    return db.query(ThreatIndicator).order_by(ThreatIndicator.created_at.desc()).limit(limit).all()
