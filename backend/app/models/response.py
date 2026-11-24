import uuid
from datetime import datetime
from sqlalchemy import Column, String, Boolean, DateTime, ForeignKey, Text, Index
from sqlalchemy.orm import relationship
from backend.app.database import Base

def generate_uuid():
    return str(uuid.uuid4())

class ResponsePlaybook(Base):
    __tablename__ = "response_playbooks"
    
    id = Column(String(36), primary_key=True, default=generate_uuid)
    organization_id = Column(String(36), ForeignKey("organizations.id", ondelete="CASCADE"), nullable=False, index=True)
    name = Column(String(255), nullable=False)
    description = Column(Text, nullable=False)
    trigger_type = Column(String(50), default="Manual", nullable=False)  # Manual, Alert Severity, Incident
    action_type = Column(String(100), nullable=False) # isolate_endpoint, revoke_sensor_credential, block_ip_advisory, investigation_checklist
    requires_approval = Column(Boolean, default=True, nullable=False)
    parameters_json = Column(Text, nullable=True)
    is_enabled = Column(Boolean, default=True, nullable=False)
    created_at = Column(DateTime, default=datetime.utcnow, nullable=False)
    
    executions = relationship("ResponseExecution", back_populates="playbook", cascade="all, delete-orphan")

class ResponseExecution(Base):
    __tablename__ = "response_executions"
    
    id = Column(String(36), primary_key=True, default=generate_uuid)
    playbook_id = Column(String(36), ForeignKey("response_playbooks.id", ondelete="CASCADE"), nullable=False, index=True)
    organization_id = Column(String(36), ForeignKey("organizations.id", ondelete="CASCADE"), nullable=False, index=True)
    triggered_by_user_id = Column(String(36), ForeignKey("users.id", ondelete="SET NULL"), nullable=True)
    target_asset_id = Column(String(36), ForeignKey("assets.id", ondelete="SET NULL"), nullable=True)
    target_ip = Column(String(45), nullable=True)
    action_preview = Column(Text, nullable=False)
    status = Column(String(50), default="Pending Approval", nullable=False, index=True)
    # Statuses: "Pending Approval", "Approved", "Executing", "Completed", "Failed", "Rejected"
    approved_by_user_id = Column(String(36), ForeignKey("users.id", ondelete="SET NULL"), nullable=True)
    approved_at = Column(DateTime, nullable=True)
    execution_log = Column(Text, nullable=True)
    created_at = Column(DateTime, default=datetime.utcnow, nullable=False, index=True)
    completed_at = Column(DateTime, nullable=True)
    
    playbook = relationship("ResponsePlaybook", back_populates="executions")

class SensorCommand(Base):
    __tablename__ = "sensor_commands"
    
    id = Column(String(36), primary_key=True, default=generate_uuid)
    sensor_id = Column(String(36), ForeignKey("sensors.id", ondelete="CASCADE"), nullable=False, index=True)
    organization_id = Column(String(36), ForeignKey("organizations.id", ondelete="CASCADE"), nullable=False, index=True)
    execution_id = Column(String(36), ForeignKey("response_executions.id", ondelete="SET NULL"), nullable=True, index=True)
    action = Column(String(100), nullable=False)
    parameters_json = Column(Text, nullable=True)
    status = Column(String(50), default="QUEUED", nullable=False, index=True) 
    # Statuses: "QUEUED", "DISPATCHED", "ACKNOWLEDGED", "EXPIRED", "REVOKED", "FAILED"
    queued_at = Column(DateTime, default=datetime.utcnow, nullable=False)
    dispatched_at = Column(DateTime, nullable=True)
    expires_at = Column(DateTime, nullable=False)
    acknowledged_at = Column(DateTime, nullable=True)
    result_status = Column(String(50), nullable=True)
    result_details = Column(Text, nullable=True)

