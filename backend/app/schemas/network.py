from typing import Optional, List, Dict, Any
from pydantic import BaseModel, ConfigDict
from backend.app.core.datetime_utils import UTCDatetime
from backend.app.schemas.threat_intel import IPInvestigationOut

class NetworkCreate(BaseModel):
    name: str
    cidr: str
    network_type: str = "Corporate LAN"
    is_authorized: bool = True

class NetworkOut(BaseModel):
    model_config = ConfigDict(from_attributes=True)

    id: str
    organization_id: str
    name: str
    cidr: str
    network_type: str
    observation_source: str
    is_authorized: bool
    created_at: UTCDatetime

class NetworkDeviceOut(BaseModel):
    model_config = ConfigDict(from_attributes=True)

    id: str
    organization_id: str
    network_id: Optional[str] = None
    ip_address: str
    mac_address: Optional[str] = None
    hostname: Optional[str] = None
    dhcp_hostname: Optional[str] = None
    dns_name: Optional[str] = None
    gateway_ip: Optional[str] = None
    subnet_cidr: Optional[str] = None
    vendor: Optional[str] = None
    device_type: str = "Workstation"
    discovery_method: str = "ARP"
    is_authorized: bool = True
    first_seen: UTCDatetime
    last_seen: UTCDatetime

class NetworkIntegrationCreate(BaseModel):
    name: str
    integration_type: str  # pfSense, OPNsense, Ubiquiti UniFi, OpenWrt, Generic Router
    endpoint_url: Optional[str] = None
    config: Optional[Dict[str, Any]] = None

class NetworkIntegrationOut(BaseModel):
    model_config = ConfigDict(from_attributes=True)

    id: str
    organization_id: str
    name: str
    integration_type: str
    endpoint_url: Optional[str] = None
    status: str
    last_sync_at: Optional[UTCDatetime] = None
    last_error: Optional[str] = None
    created_at: UTCDatetime

class NetworkTopologyNode(BaseModel):
    id: str
    label: str
    node_type: str  # ROUTER, GATEWAY, SUBNET, ASSET, DEVICE
    ip_address: Optional[str] = None
    mac_address: Optional[str] = None
    is_monitored: bool = False
    is_authorized: bool = True
    status: str = "Online"

class NetworkTopologyLinkOut(BaseModel):
    id: str
    source: str
    target: str
    link_type: str = "OBSERVED"  # OBSERVED or INFERRED
    label: Optional[str] = None

class NetworkTopologyGraphOut(BaseModel):
    nodes: List[NetworkTopologyNode]
    links: List[NetworkTopologyLinkOut]
    total_nodes: int
    total_links: int
    observed_links: int
    inferred_links: int

class NetworkCoverageStatsOut(BaseModel):
    total_subnets: int
    monitored_subnets: int
    subnet_coverage_percent: float
    total_devices: int
    monitored_devices_count: int
    unmonitored_devices_count: int
    device_sensor_coverage_percent: float
    authorized_devices_count: int
    unauthorized_devices_count: int
