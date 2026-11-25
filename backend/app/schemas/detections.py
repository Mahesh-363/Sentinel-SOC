from typing import Optional, List, Dict, Any
from pydantic import BaseModel, ConfigDict
from backend.app.core.datetime_utils import UTCDatetime

class DetectionRuleOut(BaseModel):
    model_config = ConfigDict(from_attributes=True)

    id: str
    organization_id: Optional[str] = None
    name: str
    rule_code: str
    description: str
    severity: str
    category: str
    is_enabled: bool
    is_correlation_rule: bool = False
    time_window_seconds: int = 300
    correlation_pattern: Optional[str] = None
    threshold: int = 5
    parameters_json: Optional[str] = None
    created_at: UTCDatetime
    updated_at: UTCDatetime

class RuleParametersUpdate(BaseModel):
    threshold: Optional[int] = None
    time_window_seconds: Optional[int] = None
    severity: Optional[str] = None
    is_enabled: Optional[bool] = None

class DetectionResultOut(BaseModel):
    model_config = ConfigDict(from_attributes=True)

    id: str
    organization_id: str
    rule_id: Optional[str] = None
    rule_name: str
    severity: str
    title: str
    description: str
    evidence_json: str
    confidence: int
    related_asset_id: Optional[str] = None
    related_ip: Optional[str] = None
    is_simulated: bool
    status: str
    timestamp: UTCDatetime
    created_at: UTCDatetime

class CorrelatedEventGroupOut(BaseModel):
    model_config = ConfigDict(from_attributes=True)

    id: str
    organization_id: str
    rule_code: str
    title: str
    description: str
    severity: str
    confidence: int
    time_window_start: UTCDatetime
    time_window_end: UTCDatetime
    event_ids: List[str] = []
    asset_ids: List[str] = []
    ip_addresses: List[str] = []
    explanation: str
    status: str
    created_at: UTCDatetime
