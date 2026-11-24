import uuid
from datetime import datetime
from sqlalchemy import Column, String, Boolean, DateTime, ForeignKey, Text, Index
from sqlalchemy.orm import relationship
from backend.app.database import Base

def generate_uuid():
    return str(uuid.uuid4())

class Incident(Base):
    __tablename__ = "incidents"
    
    id = Column(String(36), primary_key=True, default=generate_uuid)
    organization_id = Column(String(36), ForeignKey("organizations.id", ondelete="CASCADE"), nullable=False, index=True)
    title = Column(String(255), nullable=False)
    description = Column(Text, nullable=False)
    severity = Column(String(20), nullable=False, index=True)  # Low, Medium, High, Critical
    status = Column(String(50), default="New", nullable=False, index=True)
    # Lifecycle: "New", "Acknowledged", "Investigating", "Contained", "Resolved", "Closed"
    
    assigned_to_user_id = Column(String(36), ForeignKey("users.id", ondelete="SET NULL"), nullable=True, index=True)
    related_asset_ids_json = Column(Text, nullable=True)  # JSON list
    related_ip_addresses_json = Column(Text, nullable=True)  # JSON list
    resolution_notes = Column(Text, nullable=True)
    is_simulated = Column(Boolean, default=False, nullable=False, index=True)
    
    created_at = Column(DateTime, default=datetime.utcnow, nullable=False, index=True)
    updated_at = Column(DateTime, default=datetime.utcnow, onupdate=datetime.utcnow, nullable=False)
    closed_at = Column(DateTime, nullable=True)
    
    events = relationship("IncidentEvent", back_populates="incident", cascade="all, delete-orphan")
    comments = relationship("IncidentComment", back_populates="incident", cascade="all, delete-orphan")
    timeline_entries = relationship("IncidentTimelineEntry", back_populates="incident", cascade="all, delete-orphan")

class IncidentEvent(Base):
    __tablename__ = "incident_events"
    
    id = Column(String(36), primary_key=True, default=generate_uuid)
    incident_id = Column(String(36), ForeignKey("incidents.id", ondelete="CASCADE"), nullable=False, index=True)
    security_event_id = Column(String(36), ForeignKey("security_events.id", ondelete="SET NULL"), nullable=True, index=True)
    detection_result_id = Column(String(36), ForeignKey("detection_results.id", ondelete="SET NULL"), nullable=True, index=True)
    added_at = Column(DateTime, default=datetime.utcnow, nullable=False)
    
    incident = relationship("Incident", back_populates="events")

class IncidentComment(Base):
    __tablename__ = "incident_comments"
    
    id = Column(String(36), primary_key=True, default=generate_uuid)
    incident_id = Column(String(36), ForeignKey("incidents.id", ondelete="CASCADE"), nullable=False, index=True)
    user_id = Column(String(36), ForeignKey("users.id", ondelete="SET NULL"), nullable=True, index=True)
    user_name = Column(String(255), nullable=True)
    comment = Column(Text, nullable=False)
    is_ai_generated = Column(Boolean, default=False, nullable=False)
    created_at = Column(DateTime, default=datetime.utcnow, nullable=False, index=True)
    
    incident = relationship("Incident", back_populates="comments")

class IncidentTimelineEntry(Base):
    """
    Unified chronologically ordered timeline for all events, notes, actions, and status updates on an incident.
    """
    __tablename__ = "incident_timeline_entries"
    
    id = Column(String(36), primary_key=True, default=generate_uuid)
    incident_id = Column(String(36), ForeignKey("incidents.id", ondelete="CASCADE"), nullable=False, index=True)
    organization_id = Column(String(36), ForeignKey("organizations.id", ondelete="CASCADE"), nullable=False, index=True)
    entry_type = Column(String(50), nullable=False, index=True)  
    # CREATED, DETECTION_ATTACHED, ASSET_LINKED, IP_INTEL_MATCH, ANALYST_ACTION, COMMENT_ADDED, STATUS_CHANGE, INVESTIGATION_NOTE, AI_SUMMARY, PLAYBOOK_TRIGGERED, CLOSED
    title = Column(String(255), nullable=False)
    description = Column(Text, nullable=False)
    actor_type = Column(String(50), default="SYSTEM", nullable=False)  # SYSTEM, ANALYST, AI, SENSOR
    actor_name = Column(String(255), nullable=True)
    metadata_json = Column(Text, nullable=True)  # Contextual JSON details
    is_ai_generated = Column(Boolean, default=False, nullable=False)
    timestamp = Column(DateTime, default=datetime.utcnow, nullable=False, index=True)
    
    incident = relationship("Incident", back_populates="timeline_entries")
