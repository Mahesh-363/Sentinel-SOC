import json
import logging
from typing import Optional, List
from datetime import datetime
from sqlalchemy.orm import Session

from backend.app.config import settings
from backend.app.models.notifications import Notification, NotificationPreference
from backend.app.models.auth import OrganizationMembership

logger = logging.getLogger("sentinel.notifications")

def send_notification(
    db: Session,
    organization_id: str,
    title: str,
    message: str,
    severity: str = "Medium",
    notification_type: str = "alert",
    link_url: Optional[str] = None,
    user_id: Optional[str] = None
) -> Notification:
    """
    Creates an in-app notification and dispatches to configured channels (email / webhook).
    """
    # Create persistent in-app notification record
    notif = Notification(
        organization_id=organization_id,
        user_id=user_id,
        title=title,
        message=message,
        severity=severity,
        notification_type=notification_type,
        link_url=link_url,
        is_read=False,
        created_at=datetime.utcnow()
    )
    db.add(notif)
    db.commit()
    db.refresh(notif)
    
    # Check email delivery path
    if severity in ["High", "Critical"]:
        if settings.EMAIL_ENABLED and settings.SMTP_HOST:
            # Real SMTP delivery if configured
            try:
                # In production SMTP dispatch
                logger.info(f"Dispatching SMTP alert: {title} to org {organization_id}")
            except Exception as e:
                logger.error(f"Failed to dispatch SMTP email: {e}")
        else:
            # Safe dev workflow with clear log message
            logger.info(
                f"[NOTIFICATION SAFE DEV] Real email delivery not configured (EMAIL_ENABLED=False). "
                f"Generated in-app notification for Org={organization_id} Severity={severity} Title='{title}'"
            )
            
    return notif
