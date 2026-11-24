import uuid
from datetime import datetime
from sqlalchemy import Column, String, Boolean, DateTime, ForeignKey, Text, Integer, Index
from backend.app.database import Base

def generate_uuid():
    return str(uuid.uuid4())

class SecurityEvent(Base):
    __tablename__ = "security_events"
    
    id = Column(String(36), primary_key=True, default=generate_uuid)
    organization_id = Column(String(36), ForeignKey("organizations.id", ondelete="CASCADE"), nullable=False, index=True)
    asset_id = Column(String(36), ForeignKey("assets.id", ondelete="SET NULL"), nullable=True, index=True)
    sensor_id = Column(String(36), ForeignKey("sensors.id", ondelete="SET NULL"), nullable=True, index=True)
    
    event_type = Column(String(100), nullable=False, index=True)  # auth_failure, port_scan, outbound_conn, process_exec, lan_device, aws_event, simulated_test
    severity = Column(String(20), nullable=False, index=True)  # Informational, Low, Medium, High, Critical
    title = Column(String(255), nullable=False)
    description = Column(Text, nullable=False)
    
    source_ip = Column(String(45), nullable=True, index=True)
    destination_ip = Column(String(45), nullable=True, index=True)
    source_port = Column(Integer, nullable=True)
    destination_port = Column(Integer, nullable=True)
    protocol = Column(String(20), nullable=True)
    
    raw_payload = Column(Text, nullable=True)  # JSON representation of raw event
    is_simulated = Column(Boolean, default=False, nullable=False, index=True)
    timestamp = Column(DateTime, default=datetime.utcnow, nullable=False, index=True)
    created_at = Column(DateTime, default=datetime.utcnow, nullable=False)
    
    __table_args__ = (
        Index("idx_org_time_severity", "organization_id", "timestamp", "severity"),
    )

class ThreatIndicator(Base):
    __tablename__ = "threat_indicators"
    
    id = Column(String(36), primary_key=True, default=generate_uuid)
    indicator_type = Column(String(50), nullable=False, index=True)  # IPv4, IPv6, Domain, Hash
    indicator_value = Column(String(255), nullable=False, index=True)
    threat_type = Column(String(100), nullable=False)  # C2, Scanner, Botnet, Phishing, Ransomware
    severity = Column(String(20), default="High", nullable=False)
    source = Column(String(100), nullable=False)  # AbuseIPDB, AlienVault, GreyNoise, Spamhaus, Sentinel Threat Lab
    description = Column(Text, nullable=True)
    confidence = Column(Integer, default=80, nullable=False)
    first_seen = Column(DateTime, nullable=True)
    last_seen = Column(DateTime, nullable=True)
    reference = Column(String(500), nullable=True)
    source_timestamp = Column(DateTime, nullable=True)
    expires_at = Column(DateTime, nullable=True, index=True)
    raw_data = Column(Text, nullable=True)  # JSON dump of provider response
    created_at = Column(DateTime, default=datetime.utcnow, nullable=False, index=True)

class ThreatProviderStatus(Base):
    """
    Tracks external threat intelligence provider integration health, limits, and status.
    """
    __tablename__ = "threat_provider_status"
    
    id = Column(String(36), primary_key=True, default=generate_uuid)
    provider_name = Column(String(50), unique=True, nullable=False, index=True)  # AbuseIPDB, GreyNoise, AlienVault OTX, Spamhaus
    status = Column(String(50), default="NOT CONFIGURED", nullable=False)  # CONFIGURED, NOT CONFIGURED, OPERATIONAL, RATE_LIMITED, ERROR
    api_endpoint = Column(String(255), nullable=True)
    requests_today = Column(Integer, default=0, nullable=False)
    daily_limit = Column(Integer, default=1000, nullable=False)
    rate_limit_reset_at = Column(DateTime, nullable=True)
    last_sync_at = Column(DateTime, nullable=True)
    last_error = Column(Text, nullable=True)
    attribution = Column(String(255), nullable=True)
    created_at = Column(DateTime, default=datetime.utcnow, nullable=False)
    updated_at = Column(DateTime, default=datetime.utcnow, onupdate=datetime.utcnow, nullable=False)

class ThreatIntelCache(Base):
    """
    Cached normalized threat indicator results to prevent redundant API queries.
    """
    __tablename__ = "threat_intel_cache"
    
    id = Column(String(36), primary_key=True, default=generate_uuid)
    indicator_value = Column(String(255), unique=True, index=True, nullable=False)
    indicator_type = Column(String(50), default="IPv4", nullable=False)
    normalized_json = Column(Text, nullable=False)  # Full normalized JSON payload
    reputation = Column(String(50), default="Unknown", nullable=False)
    confidence = Column(Integer, default=0, nullable=False)
    expires_at = Column(DateTime, nullable=False, index=True)
    created_at = Column(DateTime, default=datetime.utcnow, nullable=False)

class IPInvestigation(Base):
    """
    Persistent analyst investigation records for observed and third-party IP addresses.
    """
    __tablename__ = "ip_investigations"
    
    id = Column(String(36), primary_key=True, default=generate_uuid)
    organization_id = Column(String(36), ForeignKey("organizations.id", ondelete="CASCADE"), nullable=False, index=True)
    user_id = Column(String(36), ForeignKey("users.id", ondelete="SET NULL"), nullable=True, index=True)
    ip_address = Column(String(45), nullable=False, index=True)
    ip_version = Column(Integer, default=4, nullable=False)
    classification = Column(String(50), nullable=False)
    asn = Column(String(100), nullable=True)
    as_org = Column(String(255), nullable=True)
    country = Column(String(100), nullable=True)
    city = Column(String(100), nullable=True)
    verdict = Column(String(50), default="Inconclusive", nullable=False)  # Benign, Suspicious, Malicious, Inconclusive
    notes = Column(Text, nullable=True)
    tags_json = Column(Text, nullable=True)  # JSON array of tags, e.g. ["C2", "Scanner", "Tor Exit"]
    timeline_json = Column(Text, nullable=True)  # JSON array of investigation events
    created_at = Column(DateTime, default=datetime.utcnow, nullable=False, index=True)
    updated_at = Column(DateTime, default=datetime.utcnow, onupdate=datetime.utcnow, nullable=False)
