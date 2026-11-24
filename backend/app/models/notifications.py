import uuid
from datetime import datetime
from sqlalchemy import Column, String, Boolean, DateTime, ForeignKey, Text, Index
from backend.app.database import Base

def generate_uuid():
    return str(uuid.uuid4())

class Notification(Base):
    __tablename__ = "notifications"
    
    id = Column(String(36), primary_key=True, default=generate_uuid)
    organization_id = Column(String(36), ForeignKey("organizations.id", ondelete="CASCADE"), nullable=False, index=True)
    user_id = Column(String(36), ForeignKey("users.id", ondelete="CASCADE"), nullable=True, index=True)  # Null means all org members
    title = Column(String(255), nullable=False)
    message = Column(Text, nullable=False)
    severity = Column(String(20), default="Medium", nullable=False, index=True)  # Critical, High, Medium, Low, Informational
    notification_type = Column(String(50), default="alert", nullable=False)  # alert, incident, sensor, system
    is_read = Column(Boolean, default=False, nullable=False, index=True)
    read_at = Column(DateTime, nullable=True)
    link_url = Column(String(255), nullable=True)
    created_at = Column(DateTime, default=datetime.utcnow, nullable=False, index=True)

class NotificationPreference(Base):
    __tablename__ = "notification_preferences"
    
    id = Column(String(36), primary_key=True, default=generate_uuid)
    user_id = Column(String(36), ForeignKey("users.id", ondelete="CASCADE"), nullable=False, index=True)
    organization_id = Column(String(36), ForeignKey("organizations.id", ondelete="CASCADE"), nullable=False, index=True)
    min_severity = Column(String(20), default="Medium", nullable=False)
    in_app_enabled = Column(Boolean, default=True, nullable=False)
    email_enabled = Column(Boolean, default=False, nullable=False)
