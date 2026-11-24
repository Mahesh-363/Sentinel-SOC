from typing import List, Optional
from datetime import datetime
from fastapi import APIRouter, Depends, HTTPException, status
from sqlalchemy.orm import Session

from backend.app.database import get_db
from backend.app.core.dependencies import get_current_org, get_current_user
from backend.app.models.auth import Organization, User
from backend.app.models.notifications import Notification
from backend.app.schemas.notifications import NotificationOut

router = APIRouter(prefix="/notifications", tags=["Notifications"])

@router.get("", response_model=List[NotificationOut])
def list_notifications(
    unread_only: bool = False,
    limit: int = 50,
    org: Organization = Depends(get_current_org),
    user: User = Depends(get_current_user),
    db: Session = Depends(get_db)
):
    query = db.query(Notification).filter(
        Notification.organization_id == org.id,
        (Notification.user_id == None) | (Notification.user_id == user.id)
    )
    if unread_only:
        query = query.filter(Notification.is_read == False)
    return query.order_by(Notification.created_at.desc()).limit(limit).all()

@router.patch("/{notification_id}/read")
def mark_read(
    notification_id: str,
    org: Organization = Depends(get_current_org),
    db: Session = Depends(get_db)
):
    notif = db.query(Notification).filter(
        Notification.id == notification_id,
        Notification.organization_id == org.id
    ).first()
    if not notif:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Notification not found")
        
    notif.is_read = True
    notif.read_at = datetime.utcnow()
    db.commit()
    return {"status": "success", "id": notif.id, "is_read": True}

@router.post("/mark-all-read")
def mark_all_read(
    org: Organization = Depends(get_current_org),
    user: User = Depends(get_current_user),
    db: Session = Depends(get_db)
):
    db.query(Notification).filter(
        Notification.organization_id == org.id,
        (Notification.user_id == None) | (Notification.user_id == user.id),
        Notification.is_read == False
    ).update({Notification.is_read: True, Notification.read_at: datetime.utcnow()}, synchronize_session=False)
    db.commit()
    return {"status": "success", "message": "All notifications marked as read"}
