import uuid
from datetime import datetime
from sqlalchemy import Column, String, Boolean, DateTime, ForeignKey, Text, Integer, Index
from sqlalchemy.orm import relationship
from backend.app.database import Base

def generate_uuid():
    return str(uuid.uuid4())

class DetectionRule(Base):
    __tablename__ = "detection_rules"
    
    id = Column(String(36), primary_key=True, default=generate_uuid)
    organization_id = Column(String(36), ForeignKey("organizations.id", ondelete="CASCADE"), nullable=True, index=True) # Null means global system rule
    name = Column(String(255), nullable=False)
    rule_code = Column(String(100), unique=True, index=True, nullable=False)
    description = Column(Text, nullable=False)
    severity = Column(String(20), default="Medium", nullable=False)  # Informational, Low, Medium, High, Critical
    category = Column(String(100), default="Authentication", nullable=False) # Authentication, Network, Malware, Cloud, Policy
    is_enabled = Column(Boolean, default=True, nullable=False)
    is_correlation_rule = Column(Boolean, default=False, nullable=False)
    time_window_seconds = Column(Integer, default=300, nullable=False)
    correlation_pattern = Column(String(100), nullable=True)  # MULTI_ASSET_AUTH_FAIL, PORT_SCAN_SPREAD, C2_AFTER_EXPLOIT, etc.
    threshold = Column(Integer, default=5, nullable=False)
    parameters_json = Column(Text, nullable=True) # Thresholds, time windows, e.g. {"fail_count": 5, "window_seconds": 300}
    created_at = Column(DateTime, default=datetime.utcnow, nullable=False)
    updated_at = Column(DateTime, default=datetime.utcnow, onupdate=datetime.utcnow, nullable=False)
    
    results = relationship("DetectionResult", back_populates="rule", cascade="all, delete-orphan")

class DetectionResult(Base):
    __tablename__ = "detection_results"
    
    id = Column(String(36), primary_key=True, default=generate_uuid)
    organization_id = Column(String(36), ForeignKey("organizations.id", ondelete="CASCADE"), nullable=False, index=True)
    rule_id = Column(String(36), ForeignKey("detection_rules.id", ondelete="SET NULL"), nullable=True, index=True)
    rule_name = Column(String(255), nullable=False)
    severity = Column(String(20), nullable=False, index=True)
    title = Column(String(255), nullable=False)
    description = Column(Text, nullable=False)
    evidence_json = Column(Text, nullable=False)  # JSON structure containing event IDs, IP addresses, timestamps, counts
    confidence = Column(Integer, default=85, nullable=False)  # 0 to 100
    related_asset_id = Column(String(36), ForeignKey("assets.id", ondelete="SET NULL"), nullable=True, index=True)
    related_ip = Column(String(45), nullable=True, index=True)
    is_simulated = Column(Boolean, default=False, nullable=False, index=True)
    status = Column(String(50), default="Open", nullable=False) # Open, In Review, Converted to Incident, False Positive, Resolved
    timestamp = Column(DateTime, default=datetime.utcnow, nullable=False, index=True)
    created_at = Column(DateTime, default=datetime.utcnow, nullable=False)
    
    rule = relationship("DetectionRule", back_populates="results")

class CorrelatedEventGroup(Base):
    """
    Represents correlated security incidents grouped by time-window, multi-asset, or multi-IP relationships.
    """
    __tablename__ = "correlated_event_groups"
    
    id = Column(String(36), primary_key=True, default=generate_uuid)
    organization_id = Column(String(36), ForeignKey("organizations.id", ondelete="CASCADE"), nullable=False, index=True)
    rule_code = Column(String(100), nullable=False, index=True)
    title = Column(String(255), nullable=False)
    description = Column(Text, nullable=False)
    severity = Column(String(20), default="High", nullable=False)
    confidence = Column(Integer, default=85, nullable=False)
    time_window_start = Column(DateTime, nullable=False)
    time_window_end = Column(DateTime, nullable=False)
    event_ids_json = Column(Text, nullable=False)  # JSON list of event UUIDs
    asset_ids_json = Column(Text, nullable=True)   # JSON list of asset UUIDs involved
    ip_addresses_json = Column(Text, nullable=True)# JSON list of IPs involved
    explanation = Column(Text, nullable=False)     # Clear why-correlated explanation
    status = Column(String(50), default="Active", nullable=False)  # Active, Triaged, Escalated, Suppressed
    created_at = Column(DateTime, default=datetime.utcnow, nullable=False, index=True)
