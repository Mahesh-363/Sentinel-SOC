import uuid
from datetime import datetime
from sqlalchemy import Column, String, Boolean, DateTime, ForeignKey, Text, Float, Integer, Index
from sqlalchemy.orm import relationship
from backend.app.database import Base

def generate_uuid():
    return str(uuid.uuid4())

class Asset(Base):
    __tablename__ = "assets"
    
    id = Column(String(36), primary_key=True, default=generate_uuid)
    organization_id = Column(String(36), ForeignKey("organizations.id", ondelete="CASCADE"), nullable=False, index=True)
    hostname = Column(String(255), nullable=False, index=True)
    os_family = Column(String(50), nullable=False)  # Windows, Linux, MacOS, NetworkOS, AWS
    os_version = Column(String(100), nullable=True)
    asset_type = Column(String(50), nullable=False, default="Endpoint")  # Endpoint, Server, Network Device, Router, AWS EC2
    private_ips = Column(Text, nullable=True)  # JSON array string or comma separated
    mac_addresses = Column(Text, nullable=True)
    public_ip = Column(String(45), nullable=True, index=True)
    health_status = Column(String(50), default="unknown", nullable=False)  # online, offline, warning, critical, unknown
    risk_level = Column(String(50), default="Low", nullable=False)  # Low, Medium, High, Critical
    risk_score = Column(Integer, default=15, nullable=False)  # 0 to 100
    last_seen = Column(DateTime, default=datetime.utcnow, nullable=False, index=True)
    created_at = Column(DateTime, default=datetime.utcnow, nullable=False)
    updated_at = Column(DateTime, default=datetime.utcnow, onupdate=datetime.utcnow, nullable=False)
    
    sensors = relationship("Sensor", back_populates="asset")

class Sensor(Base):
    __tablename__ = "sensors"
    
    id = Column(String(36), primary_key=True, default=generate_uuid)
    organization_id = Column(String(36), ForeignKey("organizations.id", ondelete="CASCADE"), nullable=False, index=True)
    asset_id = Column(String(36), ForeignKey("assets.id", ondelete="SET NULL"), nullable=True, index=True)
    name = Column(String(255), nullable=False)
    os_type = Column(String(50), nullable=False)  # Windows, Linux
    version = Column(String(50), default="1.0.0", nullable=False)
    status = Column(String(50), default="Pending enrollment", nullable=False)  # Online, Offline, Pending enrollment, Revoked, Error, Updating
    
    # Token & Auth
    enrollment_token = Column(String(128), unique=True, index=True, nullable=True)
    token_expires_at = Column(DateTime, nullable=True)
    is_token_used = Column(Boolean, default=False, nullable=False)
    api_key_hash = Column(String(128), nullable=True, index=True)
    
    # Capabilities (JSON string: {"host_metrics": "Available", "connections": "Available", "security_logs": "Permission required", "network_discovery": "Available"})
    capabilities = Column(Text, nullable=True)
    pending_commands = Column(Text, nullable=True)  # JSON list of queued dispatch commands: [{"id": "...", "action": "...", "params": {}}]
    error_message = Column(Text, nullable=True)
    last_heartbeat = Column(DateTime, nullable=True, index=True)
    created_at = Column(DateTime, default=datetime.utcnow, nullable=False)
    updated_at = Column(DateTime, default=datetime.utcnow, onupdate=datetime.utcnow, nullable=False)
    
    asset = relationship("Asset", back_populates="sensors")
    heartbeats = relationship("SensorHeartbeat", back_populates="sensor", cascade="all, delete-orphan")

class SensorHeartbeat(Base):
    __tablename__ = "sensor_heartbeats"
    
    id = Column(String(36), primary_key=True, default=generate_uuid)
    sensor_id = Column(String(36), ForeignKey("sensors.id", ondelete="CASCADE"), nullable=False, index=True)
    timestamp = Column(DateTime, default=datetime.utcnow, nullable=False, index=True)
    cpu_percent = Column(Float, nullable=True)
    memory_percent = Column(Float, nullable=True)
    disk_percent = Column(Float, nullable=True)
    active_connections_count = Column(Integer, default=0, nullable=False)
    status = Column(String(50), default="Online", nullable=False)
    metadata_json = Column(Text, nullable=True)
    
    sensor = relationship("Sensor", back_populates="heartbeats")
