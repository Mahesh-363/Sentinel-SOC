from typing import Optional, List, Dict, Any
from pydantic import BaseModel, ConfigDict
from backend.app.core.datetime_utils import UTCDatetime

class AssetCreate(BaseModel):
    hostname: str
    os_family: str  # Windows, Linux, MacOS, NetworkOS, AWS
    os_version: Optional[str] = None
    asset_type: str = "Endpoint"  # Endpoint, Server, Network Device, Router, AWS EC2
    private_ips: Optional[List[str]] = None
    mac_addresses: Optional[List[str]] = None
    public_ip: Optional[str] = None

class AssetUpdate(BaseModel):
    hostname: Optional[str] = None
    health_status: Optional[str] = None
    risk_level: Optional[str] = None

class AssetOut(BaseModel):
    model_config = ConfigDict(from_attributes=True)

    id: str
    organization_id: str
    hostname: str
    os_family: str
    os_version: Optional[str]
    asset_type: str
    private_ips: Optional[str]
    mac_addresses: Optional[str]
    public_ip: Optional[str]
    health_status: str
    risk_level: str
    risk_score: int = 15
    last_seen: UTCDatetime
    created_at: UTCDatetime

class SensorGenerateTokenRequest(BaseModel):
    name: str
    os_type: str  # Windows, Linux
    asset_id: Optional[str] = None

class SensorEnrollRequest(BaseModel):
    enrollment_token: str
    hostname: str
    os_type: str
    os_version: Optional[str] = None
    capabilities: Dict[str, str] = {}

class SensorEnrollResponse(BaseModel):
    sensor_id: str
    asset_id: str
    api_key: str
    status: str
    message: str

class SensorHeartbeatIn(BaseModel):
    cpu_percent: Optional[float] = None
    memory_percent: Optional[float] = None
    disk_percent: Optional[float] = None
    active_connections_count: int = 0
    capabilities: Optional[Dict[str, str]] = None
    metadata: Optional[Dict[str, Any]] = None

class SensorOut(BaseModel):
    model_config = ConfigDict(from_attributes=True)

    id: str
    organization_id: str
    asset_id: Optional[str]
    name: str
    os_type: str
    version: str
    status: str
    capabilities: Optional[str]
    error_message: Optional[str]
    last_heartbeat: Optional[UTCDatetime]
    created_at: UTCDatetime
    enrollment_token: Optional[str] = None
    token_expires_at: Optional[UTCDatetime] = None
