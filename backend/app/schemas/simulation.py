from typing import Optional, List, Dict, Any
from pydantic import BaseModel

class AttackSimulationRequest(BaseModel):
    simulation_type: str  # brute_force_login, port_scan, malicious_c2_outbound, new_lan_device, aws_privilege_escalation
    target_ip: Optional[str] = "127.0.0.1"
    target_port: Optional[int] = 22
    intensity: Optional[int] = 5

class AttackSimulationResult(BaseModel):
    simulation_type: str
    is_simulated: bool = True
    events_generated: int
    alerts_triggered: int
    incidents_created: int
    summary: str
    generated_event_ids: List[str]
