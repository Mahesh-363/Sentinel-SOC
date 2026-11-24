from datetime import datetime
from typing import Optional, List, Dict, Any
from pydantic import BaseModel

class TelemetryEventIn(BaseModel):
    event_type: str  # auth_failure, network_connection, port_scan, process_exec, lan_discovery
    severity: str = "Informational"  # Informational, Low, Medium, High, Critical
    title: str
    description: str
    source_ip: Optional[str] = None
    destination_ip: Optional[str] = None
    source_port: Optional[int] = None
    destination_port: Optional[int] = None
    protocol: Optional[str] = "TCP"
    raw_payload: Optional[Dict[str, Any]] = None
    is_simulated: bool = False
    timestamp: Optional[datetime] = None

class DiscoveredDeviceIn(BaseModel):
    ip_address: str
    mac_address: Optional[str] = None
    hostname: Optional[str] = None
    vendor: Optional[str] = None
    device_type: str = "Workstation"

class TelemetryBatchIn(BaseModel):
    sensor_version: str = "1.0.0"
    events: List[TelemetryEventIn] = []
    discovered_devices: List[DiscoveredDeviceIn] = []
    active_connections_sample: List[Dict[str, Any]] = []

class CommandAcknowledgeIn(BaseModel):
    command_id: str
    action: str
    status: str = "SUCCESS"  # SUCCESS, FAILED, VALIDATED_DRY_RUN
    details: Optional[str] = None
    execution_time_ms: Optional[float] = None

