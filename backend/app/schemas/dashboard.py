from typing import List, Dict, Any, Optional
from pydantic import BaseModel

class DashboardStatsOut(BaseModel):
    total_assets: int
    online_sensors: int
    offline_sensors: int
    total_events_24h: int
    critical_high_alerts: int
    open_incidents: int
    network_devices_count: int
    aws_findings_count: int
    
    # Genuine vs Simulated Breakdown
    simulated_events_24h: int = 0
    genuine_events_24h: int = 0
    simulated_incidents_count: int = 0
    genuine_incidents_count: int = 0
    
    # Asset Fleet Risk Metrics
    fleet_average_risk_score: int = 15
    high_risk_assets_count: int = 0
    
    # Trends & Distributions
    severity_distribution: Dict[str, int]
    event_trend_24h: List[Dict[str, Any]]
    recent_suspicious_ips: List[Dict[str, Any]]
    recent_activity: List[Dict[str, Any]]
    sensor_health_summary: Dict[str, int]
    integration_health: Dict[str, Any]
