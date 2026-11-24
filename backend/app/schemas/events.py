from datetime import datetime
from typing import Optional, List, Dict, Any
from pydantic import BaseModel, ConfigDict

class SecurityEventCreate(BaseModel):
    asset_id: Optional[str] = None
    event_type: str
    severity: str = "Informational"
    title: str
    description: str
    source_ip: Optional[str] = None
    destination_ip: Optional[str] = None
    source_port: Optional[int] = None
    destination_port: Optional[int] = None
    protocol: Optional[str] = "TCP"
    raw_payload: Optional[Dict[str, Any]] = None
    is_simulated: bool = False

class SecurityEventOut(BaseModel):
    model_config = ConfigDict(from_attributes=True)

    id: str
    organization_id: str
    asset_id: Optional[str]
    sensor_id: Optional[str]
    event_type: str
    severity: str
    title: str
    description: str
    source_ip: Optional[str]
    destination_ip: Optional[str]
    source_port: Optional[int]
    destination_port: Optional[int]
    protocol: Optional[str]
    is_simulated: bool
    timestamp: datetime
    created_at: datetime

class ThreatIndicatorCreate(BaseModel):
    indicator_type: str  # IPv4, IPv6, Domain, Hash
    indicator_value: str
    threat_type: str
    severity: str = "High"
    source: str = "Sentinel Threat Feed"
    description: Optional[str] = None
    confidence: int = 80

class ThreatIndicatorOut(BaseModel):
    model_config = ConfigDict(from_attributes=True)

    id: str
    indicator_type: str
    indicator_value: str
    threat_type: str
    severity: str
    source: str
    description: Optional[str]
    confidence: int
    created_at: datetime
