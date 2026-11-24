import json
import csv
import io
from datetime import datetime
from typing import List, Optional, Dict, Any
from fastapi import APIRouter, Depends, HTTPException, status, Response
from sqlalchemy.orm import Session

from backend.app.database import get_db
from backend.app.core.dependencies import get_current_org, get_current_user, require_role
from backend.app.models.auth import Organization, User
from backend.app.models.incidents import Incident, IncidentEvent, IncidentComment, IncidentTimelineEntry
from backend.app.schemas.incidents import (
    IncidentCreate,
    IncidentUpdate,
    IncidentOut,
    IncidentCommentIn,
    IncidentCommentOut,
    IncidentTimelineEntryCreate,
    IncidentTimelineEntryOut
)

router = APIRouter(prefix="/incidents", tags=["Incident Management"])

@router.get("", response_model=List[IncidentOut])
def list_incidents(
    status: Optional[str] = None,
    severity: Optional[str] = None,
    is_simulated: Optional[bool] = None,
    limit: int = 100,
    org: Organization = Depends(get_current_org),
    db: Session = Depends(get_db)
):
    query = db.query(Incident).filter(Incident.organization_id == org.id)
    if status:
        query = query.filter(Incident.status == status)
    if severity:
        query = query.filter(Incident.severity == severity)
    if is_simulated is not None:
        query = query.filter(Incident.is_simulated == is_simulated)
    return query.order_by(Incident.created_at.desc()).limit(limit).all()

@router.post("", response_model=IncidentOut, dependencies=[Depends(require_role(["Organization Owner", "Organization Administrator", "Security Analyst"]))])
def create_incident(
    payload: IncidentCreate,
    user: User = Depends(get_current_user),
    org: Organization = Depends(get_current_org),
    db: Session = Depends(get_db)
):
    now = datetime.utcnow()
    incident = Incident(
        organization_id=org.id,
        title=payload.title.strip(),
        description=payload.description.strip(),
        severity=payload.severity,
        status="New",
        assigned_to_user_id=payload.assigned_to_user_id or user.id,
        related_asset_ids_json=json.dumps(payload.related_asset_ids or []),
        related_ip_addresses_json=json.dumps(payload.related_ip_addresses or []),
        is_simulated=bool(payload.is_simulated) if payload.is_simulated is not None else False,
        created_at=now,
        updated_at=now
    )
    db.add(incident)
    db.flush()

    # Create Initial Timeline Entry
    entry = IncidentTimelineEntry(
        incident_id=incident.id,
        organization_id=org.id,
        entry_type="CREATED",
        title="Incident Created",
        description=f"Incident opened by {user.full_name}: {payload.title}",
        actor_type="ANALYST",
        actor_name=user.full_name,
        timestamp=now
    )
    db.add(entry)
    db.commit()
    db.refresh(incident)
    return incident

@router.get("/{incident_id}", response_model=IncidentOut)
def get_incident(
    incident_id: str,
    org: Organization = Depends(get_current_org),
    db: Session = Depends(get_db)
):
    inc = db.query(Incident).filter(
        Incident.id == incident_id,
        Incident.organization_id == org.id
    ).first()
    if not inc:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Incident not found")
    return inc

@router.patch("/{incident_id}", response_model=IncidentOut, dependencies=[Depends(require_role(["Organization Owner", "Organization Administrator", "Security Analyst"]))])
def update_incident(
    incident_id: str,
    payload: IncidentUpdate,
    user: User = Depends(get_current_user),
    org: Organization = Depends(get_current_org),
    db: Session = Depends(get_db)
):
    inc = db.query(Incident).filter(
        Incident.id == incident_id,
        Incident.organization_id == org.id
    ).first()
    if not inc:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Incident not found")
        
    old_status = inc.status
    now = datetime.utcnow()

    if payload.title is not None:
        inc.title = payload.title
    if payload.description is not None:
        inc.description = payload.description
    if payload.severity is not None:
        inc.severity = payload.severity
    if payload.status is not None:
        inc.status = payload.status
        if payload.status == "Closed":
            inc.closed_at = now
            # Log closed timeline entry
            db.add(IncidentTimelineEntry(
                incident_id=inc.id,
                organization_id=org.id,
                entry_type="CLOSED",
                title="Incident Resolved and Closed",
                description=f"Case closed by {user.full_name}. Resolution: {payload.resolution_notes or inc.resolution_notes or 'Resolved'}",
                actor_type="ANALYST",
                actor_name=user.full_name,
                timestamp=now
            ))
        elif old_status != payload.status:
            # Log status change timeline entry
            db.add(IncidentTimelineEntry(
                incident_id=inc.id,
                organization_id=org.id,
                entry_type="STATUS_CHANGE",
                title=f"Status Changed: {old_status} -> {payload.status}",
                description=f"Status updated by {user.full_name}",
                actor_type="ANALYST",
                actor_name=user.full_name,
                timestamp=now
            ))

    if payload.assigned_to_user_id is not None:
        inc.assigned_to_user_id = payload.assigned_to_user_id
    if payload.resolution_notes is not None:
        inc.resolution_notes = payload.resolution_notes

    inc.updated_at = now
    db.commit()
    db.refresh(inc)
    return inc

@router.get("/{incident_id}/timeline", response_model=List[IncidentTimelineEntryOut])
def get_incident_timeline(
    incident_id: str,
    org: Organization = Depends(get_current_org),
    db: Session = Depends(get_db)
):
    """
    Retrieves the complete unified incident timeline sorted chronologically.
    """
    entries = db.query(IncidentTimelineEntry).filter(
        IncidentTimelineEntry.incident_id == incident_id,
        IncidentTimelineEntry.organization_id == org.id
    ).order_by(IncidentTimelineEntry.timestamp.asc()).all()
    return entries

@router.post("/{incident_id}/timeline", response_model=IncidentTimelineEntryOut, dependencies=[Depends(require_role(["Organization Owner", "Organization Administrator", "Security Analyst"]))])
def add_timeline_entry(
    incident_id: str,
    payload: IncidentTimelineEntryCreate,
    user: User = Depends(get_current_user),
    org: Organization = Depends(get_current_org),
    db: Session = Depends(get_db)
):
    """
    Appends an analyst investigation note, containment action, or evidence link to the unified timeline.
    """
    inc = db.query(Incident).filter(
        Incident.id == incident_id,
        Incident.organization_id == org.id
    ).first()
    if not inc:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Incident not found")

    entry = IncidentTimelineEntry(
        incident_id=inc.id,
        organization_id=org.id,
        entry_type=payload.entry_type,
        title=payload.title,
        description=payload.description,
        actor_type="ANALYST",
        actor_name=user.full_name,
        metadata_json=json.dumps(payload.metadata or {}),
        timestamp=datetime.utcnow()
    )
    db.add(entry)
    inc.updated_at = datetime.utcnow()
    db.commit()
    db.refresh(entry)
    return entry

@router.post("/{incident_id}/comments", response_model=IncidentCommentOut)
def add_incident_comment(
    incident_id: str,
    payload: IncidentCommentIn,
    user: User = Depends(get_current_user),
    org: Organization = Depends(get_current_org),
    db: Session = Depends(get_db)
):
    inc = db.query(Incident).filter(
        Incident.id == incident_id,
        Incident.organization_id == org.id
    ).first()
    if not inc:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Incident not found")

    now = datetime.utcnow()
    comment = IncidentComment(
        incident_id=inc.id,
        user_id=user.id,
        user_name=user.full_name,
        comment=payload.comment.strip(),
        is_ai_generated=False,
        created_at=now
    )
    db.add(comment)

    # Also log to timeline
    entry = IncidentTimelineEntry(
        incident_id=inc.id,
        organization_id=org.id,
        entry_type="COMMENT_ADDED",
        title="Analyst Case Note Added",
        description=f"{user.full_name}: {payload.comment[:100]}...",
        actor_type="ANALYST",
        actor_name=user.full_name,
        timestamp=now
    )
    db.add(entry)
    inc.updated_at = now
    db.commit()
    db.refresh(comment)
    return comment

@router.get("/{incident_id}/export/csv")
def export_incident_timeline_csv(
    incident_id: str,
    org: Organization = Depends(get_current_org),
    db: Session = Depends(get_db)
):
    """
    Exports the complete incident timeline and case details as a CSV file.
    """
    inc = db.query(Incident).filter(
        Incident.id == incident_id,
        Incident.organization_id == org.id
    ).first()
    if not inc:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Incident not found")

    entries = db.query(IncidentTimelineEntry).filter(
        IncidentTimelineEntry.incident_id == incident_id,
        IncidentTimelineEntry.organization_id == org.id
    ).order_by(IncidentTimelineEntry.timestamp.asc()).all()

    output = io.StringIO()
    writer = csv.writer(output)
    writer.writerow(["Timestamp (UTC)", "Entry Type", "Actor Type", "Actor Name", "Title", "Description", "AI Generated"])
    
    for e in entries:
        writer.writerow([
            e.timestamp.isoformat(),
            e.entry_type,
            e.actor_type,
            e.actor_name or "N/A",
            e.title,
            e.description,
            "Yes" if e.is_ai_generated else "No"
        ])

    csv_data = output.getvalue()
    filename = f"incident_{incident_id[:8]}_timeline_{datetime.utcnow().strftime('%Y%m%d_%H%M%S')}.csv"
    return Response(
        content=csv_data,
        media_type="text/csv",
        headers={"Content-Disposition": f"attachment; filename={filename}"}
    )
