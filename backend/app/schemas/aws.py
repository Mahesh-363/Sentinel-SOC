from datetime import datetime
from typing import Optional, List, Dict, Any
from pydantic import BaseModel, ConfigDict

class AWSAccountCreate(BaseModel):
    account_id: str
    account_name: str
    role_arn: str
    external_id: Optional[str] = None
    region: str = "us-east-1"

class AWSAccountOut(BaseModel):
    model_config = ConfigDict(from_attributes=True)

    id: str
    organization_id: str
    account_id: str
    account_name: str
    role_arn: str
    external_id: Optional[str] = None
    region: str
    is_active: bool
    last_synced: Optional[datetime] = None
    created_at: datetime

class AWSFindingOut(BaseModel):
    model_config = ConfigDict(from_attributes=True)

    id: str
    organization_id: str
    aws_account_id: Optional[str] = None
    service: str
    finding_type: str
    severity: str
    resource_id: Optional[str] = None
    description: str
    remediation_guidance: Optional[str] = None
    is_simulated: bool
    created_at: datetime

class AWSResourceOut(BaseModel):
    model_config = ConfigDict(from_attributes=True)

    id: str
    organization_id: str
    aws_account_id: str
    resource_type: str
    resource_id: str
    resource_name: str
    arn: Optional[str] = None
    region: str
    compliance_status: str
    last_scanned_at: datetime
