from typing import Optional, List, Dict, Any
from pydantic import BaseModel, ConfigDict
from backend.app.core.datetime_utils import UTCDatetime

class IncidentCreate(BaseModel):
    title: str
    description: str
    severity: str = "High"  # Low, Medium, High, Critical
    assigned_to_user_id: Optional[str] = None
    related_asset_ids: Optional[List[str]] = None
    related_ip_addresses: Optional[List[str]] = None
    is_simulated: Optional[bool] = False

class IncidentUpdate(BaseModel):
    title: Optional[str] = None
    description: Optional[str] = None
    severity: Optional[str] = None
    status: Optional[str] = None
    assigned_to_user_id: Optional[str] = None
    resolution_notes: Optional[str] = None

class IncidentCommentIn(BaseModel):
    comment: str

class IncidentCommentOut(BaseModel):
    model_config = ConfigDict(from_attributes=True)

    id: str
    incident_id: str
    user_id: Optional[str] = None
    user_name: Optional[str] = None
    comment: str
    is_ai_generated: bool
    created_at: UTCDatetime

class IncidentTimelineEntryCreate(BaseModel):
    entry_type: str  # INVESTIGATION_NOTE, STATUS_CHANGE, ANALYST_ACTION, COMMENT_ADDED
    title: str
    description: str
    actor_name: Optional[str] = None
    metadata: Optional[Dict[str, Any]] = None

class IncidentTimelineEntryOut(BaseModel):
    model_config = ConfigDict(from_attributes=True)

    id: str
    incident_id: str
    organization_id: str
    entry_type: str
    title: str
    description: str
    actor_type: str
    actor_name: Optional[str] = None
    metadata_json: Optional[str] = None
    is_ai_generated: bool
    timestamp: UTCDatetime

class IncidentOut(BaseModel):
    model_config = ConfigDict(from_attributes=True)

    id: str
    organization_id: str
    title: str
    description: str
    severity: str
    status: str
    assigned_to_user_id: Optional[str] = None
    related_asset_ids_json: Optional[str] = None
    related_ip_addresses_json: Optional[str] = None
    resolution_notes: Optional[str] = None
    is_simulated: bool = False
    created_at: UTCDatetime
    updated_at: UTCDatetime
    closed_at: Optional[UTCDatetime] = None
    comments: List[IncidentCommentOut] = []
    timeline_entries: List[IncidentTimelineEntryOut] = []
