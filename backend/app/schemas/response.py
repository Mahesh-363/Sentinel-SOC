from typing import Optional
from pydantic import BaseModel, ConfigDict
from backend.app.core.datetime_utils import UTCDatetime


class ResponsePlaybookOut(BaseModel):
    model_config = ConfigDict(from_attributes=True)

    id: str
    organization_id: str
    name: str
    description: str
    trigger_type: str
    action_type: str
    requires_approval: bool
    parameters_json: Optional[str] = None
    is_enabled: bool
    created_at: UTCDatetime


class ResponseExecutionOut(BaseModel):
    model_config = ConfigDict(from_attributes=True)

    id: str
    playbook_id: str
    organization_id: str
    triggered_by_user_id: Optional[str] = None
    target_asset_id: Optional[str] = None
    target_ip: Optional[str] = None
    action_preview: str
    status: str
    approved_by_user_id: Optional[str] = None
    approved_at: Optional[UTCDatetime] = None
    execution_log: Optional[str] = None
    created_at: UTCDatetime
    completed_at: Optional[UTCDatetime] = None
