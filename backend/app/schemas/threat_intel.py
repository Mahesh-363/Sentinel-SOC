from typing import Optional, List, Dict, Any
from pydantic import BaseModel, ConfigDict
from backend.app.core.datetime_utils import UTCDatetime

class NormalizedIndicatorOut(BaseModel):
    model_config = ConfigDict(from_attributes=True)

    indicator_value: str
    indicator_type: str = "IPv4"  # IPv4, IPv6, Domain, Hash
    provider: str
    reputation: str = "Unknown"   # Benign, Suspicious, Malicious, Unknown
    confidence: Optional[int] = 0
    first_seen: Optional[UTCDatetime] = None
    last_seen: Optional[UTCDatetime] = None
    reference: Optional[str] = None
    source_timestamp: Optional[UTCDatetime] = None
    expires_at: Optional[UTCDatetime] = None
    attribution: str = ""
    status: str = "CONFIGURED"    # CONFIGURED, NOT CONFIGURED, SUCCESS, RATE_LIMITED, ERROR
    raw_details: Optional[Dict[str, Any]] = None

class ThreatProviderStatusOut(BaseModel):
    model_config = ConfigDict(from_attributes=True)

    provider_name: str
    status: str
    api_endpoint: Optional[str] = None
    requests_today: int = 0
    daily_limit: int = 1000
    last_sync_at: Optional[UTCDatetime] = None
    last_error: Optional[str] = None
    attribution: Optional[str] = None

class IPInvestigationCreate(BaseModel):
    ip_address: str
    verdict: Optional[str] = "Inconclusive"  # Benign, Suspicious, Malicious, Inconclusive
    notes: Optional[str] = None
    tags: Optional[List[str]] = []

class IPInvestigationUpdate(BaseModel):
    verdict: Optional[str] = None
    notes: Optional[str] = None
    tags: Optional[List[str]] = None

class IPInvestigationOut(BaseModel):
    model_config = ConfigDict(from_attributes=True)

    id: str
    organization_id: str
    user_id: Optional[str] = None
    ip_address: str
    ip_version: int
    classification: str
    asn: Optional[str] = None
    as_org: Optional[str] = None
    country: Optional[str] = None
    city: Optional[str] = None
    verdict: str
    notes: Optional[str] = None
    tags: List[str] = []
    timeline: List[Dict[str, Any]] = []
    created_at: UTCDatetime
    updated_at: UTCDatetime
