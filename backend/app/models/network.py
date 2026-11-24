import uuid
from datetime import datetime
from sqlalchemy import Column, String, Boolean, DateTime, ForeignKey, Text, Integer, Float, Index
from sqlalchemy.orm import relationship
from backend.app.database import Base

def generate_uuid():
    return str(uuid.uuid4())

class Network(Base):
    __tablename__ = "networks"
    
    id = Column(String(36), primary_key=True, default=generate_uuid)
    organization_id = Column(String(36), ForeignKey("organizations.id", ondelete="CASCADE"), nullable=False, index=True)
    name = Column(String(255), nullable=False)
    cidr = Column(String(50), nullable=False, index=True)
    network_type = Column(String(50), default="Corporate LAN", nullable=False)  # Corporate LAN, Home Office, Cloud VPC, DMZ
    observation_source = Column(String(100), default="Sensor discovery", nullable=False)
    is_authorized = Column(Boolean, default=True, nullable=False)
    created_at = Column(DateTime, default=datetime.utcnow, nullable=False)
    
    devices = relationship("NetworkDevice", back_populates="network", cascade="all, delete-orphan")

class NetworkDevice(Base):
    __tablename__ = "network_devices"
    
    id = Column(String(36), primary_key=True, default=generate_uuid)
    organization_id = Column(String(36), ForeignKey("organizations.id", ondelete="CASCADE"), nullable=False, index=True)
    network_id = Column(String(36), ForeignKey("networks.id", ondelete="SET NULL"), nullable=True, index=True)
    ip_address = Column(String(45), nullable=False, index=True)
    mac_address = Column(String(50), nullable=True, index=True)
    hostname = Column(String(255), nullable=True)
    dhcp_hostname = Column(String(255), nullable=True)
    dns_name = Column(String(255), nullable=True)
    gateway_ip = Column(String(45), nullable=True)
    subnet_cidr = Column(String(50), nullable=True)
    vendor = Column(String(100), nullable=True)
    device_type = Column(String(50), default="Workstation", nullable=False)  # Workstation, Server, Router, Switch, IoT, Printer, Unknown
    discovery_method = Column(String(50), default="ARP", nullable=False)  # ARP, DHCP, ROUTER_API, SOCKET_OBSERVATION, MANUAL
    is_authorized = Column(Boolean, default=True, nullable=False)
    first_seen = Column(DateTime, default=datetime.utcnow, nullable=False)
    last_seen = Column(DateTime, default=datetime.utcnow, nullable=False, index=True)
    
    network = relationship("Network", back_populates="devices")

class NetworkIntegration(Base):
    """
    Router, firewall, and gateway appliance integrations (pfSense, OPNsense, UniFi, OpenWrt, etc.)
    """
    __tablename__ = "network_integrations"
    
    id = Column(String(36), primary_key=True, default=generate_uuid)
    organization_id = Column(String(36), ForeignKey("organizations.id", ondelete="CASCADE"), nullable=False, index=True)
    name = Column(String(255), nullable=False)
    integration_type = Column(String(50), nullable=False)  # pfSense, OPNsense, Ubiquiti UniFi, OpenWrt, Generic Router
    endpoint_url = Column(String(255), nullable=True)
    status = Column(String(50), default="NOT CONFIGURED", nullable=False)  # CONFIGURED, NOT CONFIGURED, CONNECTED, ERROR
    config_json = Column(Text, nullable=True)  # Non-sensitive configuration options
    last_sync_at = Column(DateTime, nullable=True)
    last_error = Column(Text, nullable=True)
    created_at = Column(DateTime, default=datetime.utcnow, nullable=False)

class NetworkTopologyLink(Base):
    """
    Graph links between routers, subnets, switches, and endpoints.
    Distinguishes OBSERVED connections from INFERRED topological associations.
    """
    __tablename__ = "network_topology_links"
    
    id = Column(String(36), primary_key=True, default=generate_uuid)
    organization_id = Column(String(36), ForeignKey("organizations.id", ondelete="CASCADE"), nullable=False, index=True)
    source_id = Column(String(100), nullable=False, index=True)
    source_label = Column(String(255), nullable=False)
    source_type = Column(String(50), nullable=False)  # ROUTER, GATEWAY, SUBNET, ASSET, DEVICE
    target_id = Column(String(100), nullable=False, index=True)
    target_label = Column(String(255), nullable=False)
    target_type = Column(String(50), nullable=False)
    link_type = Column(String(20), default="OBSERVED", nullable=False)  # OBSERVED or INFERRED
    details_json = Column(Text, nullable=True)
    last_seen = Column(DateTime, default=datetime.utcnow, nullable=False)

class IPAddress(Base):
    """
    Global / Organization cached IP catalog with classification and threat intelligence summary.
    """
    __tablename__ = "ip_addresses"
    
    id = Column(String(36), primary_key=True, default=generate_uuid)
    ip_address = Column(String(45), unique=True, index=True, nullable=False)
    ip_version = Column(Integer, default=4, nullable=False)  # 4 or 6
    classification = Column(String(50), nullable=False)  # Public, Private, Loopback, Link-local, Reserved, Invalid
    asn = Column(String(100), nullable=True)
    as_org = Column(String(255), nullable=True)
    country = Column(String(100), nullable=True)
    country_code = Column(String(10), nullable=True)
    city = Column(String(100), nullable=True)
    reputation_score = Column(Integer, default=0, nullable=False)  # 0 to 100
    threat_level = Column(String(50), default="Benign", nullable=False)  # Benign, Suspicious, Malicious, Unknown
    is_malicious = Column(Boolean, default=False, nullable=False)
    last_enriched = Column(DateTime, nullable=True)
    created_at = Column(DateTime, default=datetime.utcnow, nullable=False)

class IPObservation(Base):
    """
    Captured IP connection or observation at authorized points (Public API, Sensor telemetry, or Network probe).
    """
    __tablename__ = "ip_observations"
    
    id = Column(String(36), primary_key=True, default=generate_uuid)
    organization_id = Column(String(36), ForeignKey("organizations.id", ondelete="CASCADE"), nullable=False, index=True)
    asset_id = Column(String(36), ForeignKey("assets.id", ondelete="SET NULL"), nullable=True, index=True)
    ip_address = Column(String(45), nullable=False, index=True)
    source_port = Column(Integer, nullable=True)
    destination_ip = Column(String(45), nullable=True, index=True)
    destination_port = Column(Integer, nullable=True)
    protocol = Column(String(20), default="TCP", nullable=False)
    direction = Column(String(20), default="Outbound", nullable=False)  # Inbound, Outbound, Local
    observation_source = Column(String(100), nullable=False)  # Sentinel Public API, Endpoint Sensor, Network Scan
    timestamp = Column(DateTime, default=datetime.utcnow, nullable=False, index=True)
    metadata_json = Column(Text, nullable=True)

class IPReputation(Base):
    """
    Third-party threat feed report cache for an IP address.
    """
    __tablename__ = "ip_reputations"
    
    id = Column(String(36), primary_key=True, default=generate_uuid)
    ip_address = Column(String(45), index=True, nullable=False)
    provider = Column(String(50), nullable=False)  # AbuseIPDB, AlienVault OTX, GreyNoise, Spamhaus
    score = Column(Integer, default=0, nullable=False)
    abuse_confidence = Column(Float, default=0.0, nullable=False)
    reports_count = Column(Integer, default=0, nullable=False)
    categories = Column(Text, nullable=True)  # JSON list
    raw_data_json = Column(Text, nullable=True)
    last_checked = Column(DateTime, default=datetime.utcnow, nullable=False, index=True)
    
    __table_args__ = (
        Index("idx_ip_provider", "ip_address", "provider", unique=True),
    )
