from typing import Optional, List
from pydantic import BaseModel, EmailStr, ConfigDict
from backend.app.core.datetime_utils import UTCDatetime

class UserRegister(BaseModel):
    email: EmailStr
    password: str
    full_name: str
    organization_name: Optional[str] = "Primary Security Operations"

class UserLogin(BaseModel):
    email: EmailStr
    password: str

class TokenResponse(BaseModel):
    access_token: str
    token_type: str = "bearer"
    user_id: str
    email: str
    full_name: str
    is_platform_admin: bool = False
    must_change_password: bool = False
    organizations: List[dict]

class UserOut(BaseModel):
    model_config = ConfigDict(from_attributes=True)

    id: str
    email: str
    full_name: str
    is_active: bool
    is_platform_admin: bool
    must_change_password: bool = False
    created_at: UTCDatetime

class PasswordChangeRequest(BaseModel):
    current_password: str
    new_password: str

class PasswordChangeResponse(BaseModel):
    status: str = "success"
    message: str = "Password changed successfully"
    must_change_password: bool = False
    access_token: str

class OrganizationCreate(BaseModel):
    name: str

class OrganizationOut(BaseModel):
    model_config = ConfigDict(from_attributes=True)

    id: str
    name: str
    slug: str
    is_active: bool
    created_at: UTCDatetime

class AuditLogOut(BaseModel):
    model_config = ConfigDict(from_attributes=True)

    id: str
    organization_id: Optional[str] = None
    user_id: Optional[str] = None
    user_email: Optional[str] = None
    action: str
    target_type: str
    target_id: Optional[str] = None
    details: Optional[str] = None
    ip_address: Optional[str] = None
    created_at: UTCDatetime

class MembershipOut(BaseModel):
    model_config = ConfigDict(from_attributes=True)

    id: str
    user_id: str
    organization_id: str
    organization_name: str
    role: str
