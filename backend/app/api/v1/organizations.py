import re
from typing import List
from fastapi import APIRouter, Depends, HTTPException, status
from pydantic import BaseModel, EmailStr
from sqlalchemy.orm import Session

from backend.app.database import get_db
from backend.app.core.dependencies import get_current_user, get_current_org, require_role
from backend.app.models.auth import User, Organization, OrganizationMembership, AuditLog
from backend.app.schemas.auth import OrganizationCreate, OrganizationOut

router = APIRouter(prefix="/organizations", tags=["Organizations"])

class InviteMemberRequest(BaseModel):
    email: EmailStr
    role: str = "Security Analyst"

@router.get("", response_model=List[OrganizationOut])
def list_organizations(user: User = Depends(get_current_user), db: Session = Depends(get_db)):
    if user.is_platform_admin:
        return db.query(Organization).filter(Organization.is_active == True).all()
        
    memberships = db.query(OrganizationMembership).filter(OrganizationMembership.user_id == user.id).all()
    org_ids = [m.organization_id for m in memberships]
    return db.query(Organization).filter(Organization.id.in_(org_ids), Organization.is_active == True).all()

@router.post("", response_model=OrganizationOut)
def create_organization(payload: OrganizationCreate, user: User = Depends(get_current_user), db: Session = Depends(get_db)):
    slug = re.sub(r'[^a-z0-9]+', '-', payload.name.lower()).strip('-')
    if not slug:
        slug = "org"
        
    existing = db.query(Organization).filter(Organization.slug == slug).first()
    if existing:
        slug = f"{slug}-{user.id[:4]}"
        
    org = Organization(name=payload.name.strip(), slug=slug, is_active=True)
    db.add(org)
    db.flush()

    membership = OrganizationMembership(
        user_id=user.id,
        organization_id=org.id,
        role="Organization Owner"
    )
    db.add(membership)
    db.commit()
    db.refresh(org)
    return org

@router.get("/current", response_model=OrganizationOut)
def get_active_organization(org: Organization = Depends(get_current_org)):
    return org

@router.post("/invite", dependencies=[Depends(require_role(["Organization Owner", "Organization Administrator"]))])
def invite_member(
    payload: InviteMemberRequest,
    org: Organization = Depends(get_current_org),
    user: User = Depends(get_current_user),
    db: Session = Depends(get_db)
):
    target_user = db.query(User).filter(User.email == payload.email.lower().strip()).first()
    if not target_user:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="User not found. They must register for Sentinel SOC before being invited."
        )

    existing = db.query(OrganizationMembership).filter(
        OrganizationMembership.user_id == target_user.id,
        OrganizationMembership.organization_id == org.id
    ).first()
    if existing:
        existing.role = payload.role
        db.commit()
        return {"status": "updated", "message": f"Updated {target_user.email} role to {payload.role}"}

    new_member = OrganizationMembership(
        user_id=target_user.id,
        organization_id=org.id,
        role=payload.role
    )
    db.add(new_member)
    db.commit()
    return {"status": "success", "message": f"Added {target_user.email} as {payload.role} to {org.name}"}
