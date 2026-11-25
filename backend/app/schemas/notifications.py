from typing import Optional
from pydantic import BaseModel, ConfigDict
from backend.app.core.datetime_utils import UTCDatetime

class NotificationOut(BaseModel):
    model_config = ConfigDict(from_attributes=True)

    id: str
    organization_id: str
    user_id: Optional[str]
    title: str
    message: str
    severity: str
    notification_type: str
    is_read: bool
    read_at: Optional[UTCDatetime]
    link_url: Optional[str]
    created_at: UTCDatetime
