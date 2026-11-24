import re
from datetime import datetime
from typing import List, Optional
from fastapi import APIRouter, Depends, HTTPException, status, Request
from pydantic import TypeAdapter, EmailStr, ValidationError
from sqlalchemy.orm import Session

from backend.app.database import get_db
from backend.app.config import settings
from backend.app.core.security import hash_password, verify_password, create_access_token
from backend.app.core.dependencies import get_current_user
from backend.app.models.auth import User, Organization, OrganizationMembership, AuditLog
from backend.app.schemas.auth import UserRegister, UserLogin, TokenResponse, UserOut, MembershipOut

email_validator = TypeAdapter(EmailStr)

router = APIRouter(prefix="/auth", tags=["Authentication"])

@router.post("/register", response_model=TokenResponse)
def register(payload: UserRegister, db: Session = Depends(get_db)):
    # Check if user already exists
    existing = db.query(User).filter(User.email == payload.email.lower().strip()).first()
    if existing:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="A user with this email address already exists"
        )
    
    # Check if this is the very first user (if so, grant Platform Admin)
    user_count = db.query(User).count()
    is_admin = user_count == 0

    # Create user
    user = User(
        email=payload.email.lower().strip(),
        hashed_password=hash_password(payload.password),
        full_name=payload.full_name.strip(),
        is_active=True,
        is_platform_admin=is_admin
    )
    db.add(user)
    db.flush()

    # Create initial Organization
    org_name = payload.organization_name or f"{user.full_name}'s Org"
    slug = re.sub(r'[^a-z0-9]+', '-', org_name.lower()).strip('-')
    if not slug:
        slug = f"org-{user.id[:8]}"
    
    # Ensure slug uniqueness
    existing_org = db.query(Organization).filter(Organization.slug == slug).first()
    if existing_org:
        slug = f"{slug}-{user.id[:4]}"

    org = Organization(
        name=org_name,
        slug=slug,
        is_active=True
    )
    db.add(org)
    db.flush()

    # Grant Organization Owner role
    membership = OrganizationMembership(
        user_id=user.id,
        organization_id=org.id,
        role="Organization Owner"
    )
    db.add(membership)

    # Audit log
    audit = AuditLog(
        organization_id=org.id,
        user_id=user.id,
        user_email=user.email,
        action="USER_REGISTERED",
        target_type="user",
        target_id=user.id,
        details=f"User registered and established organization '{org.name}'"
    )
    db.add(audit)
    db.commit()
    db.refresh(user)

    token = create_access_token({"sub": user.id, "email": user.email})
    return TokenResponse(
        access_token=token,
        token_type="bearer",
        user_id=user.id,
        email=user.email,
        full_name=user.full_name,
        organizations=[{"id": org.id, "name": org.name, "slug": org.slug, "role": "Organization Owner"}]
    )

@router.post(
    "/login",
    response_model=TokenResponse,
    summary="Authenticate User & Obtain JWT Access Token",
    description="Authenticates with email and password via JSON payload or form data (OAuth2 password grant)."
)
async def login(request: Request, db: Session = Depends(get_db)):
    content_type = request.headers.get("content-type", "")
    raw_email = None
    raw_password = None

    if "application/x-www-form-urlencoded" in content_type or "multipart/form-data" in content_type:
        form = await request.form()
        raw_email = form.get("username") or form.get("email")
        raw_password = form.get("password")
    else:
        try:
            body = await request.json()
            raw_email = body.get("email") or body.get("username")
            raw_password = body.get("password")
        except Exception:
            raise HTTPException(
                status_code=status.HTTP_422_UNPROCESSABLE_ENTITY,
                detail="Invalid request payload format"
            )

    if not raw_email or raw_password is None:
        raise HTTPException(
            status_code=status.HTTP_422_UNPROCESSABLE_ENTITY,
            detail="Both email and password are required"
        )

    # Validate email format strictly against RFC email standards
    try:
        validated_email = email_validator.validate_python(str(raw_email).strip())
    except ValidationError as e:
        raise HTTPException(
            status_code=status.HTTP_422_UNPROCESSABLE_ENTITY,
            detail=f"Invalid email address format: {e.errors()[0]['msg']}"
        )

    user = db.query(User).filter(User.email == validated_email.lower()).first()
    if not user or not verify_password(raw_password, user.hashed_password):
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="Incorrect email or password",
            headers={"WWW-Authenticate": "Bearer"}
        )
    if not user.is_active:
        raise HTTPException(
            status_code=status.HTTP_403_FORBIDDEN,
            detail="Account has been suspended or deactivated"
        )

    # Fetch user's organizations
    memberships = db.query(OrganizationMembership).filter(OrganizationMembership.user_id == user.id).all()
    org_list = []
    for m in memberships:
        org = db.query(Organization).filter(Organization.id == m.organization_id, Organization.is_active == True).first()
        if org:
            org_list.append({"id": org.id, "name": org.name, "slug": org.slug, "role": m.role})

    # If platform admin and has no orgs, allow login with platform scope
    token = create_access_token({"sub": user.id, "email": user.email})
    
    # Audit log
    audit = AuditLog(
        organization_id=org_list[0]["id"] if org_list else None,
        user_id=user.id,
        user_email=user.email,
        action="USER_LOGIN",
        target_type="user",
        target_id=user.id,
        details="Successful login session created"
    )
    db.add(audit)
    db.commit()

    return TokenResponse(
        access_token=token,
        token_type="bearer",
        user_id=user.id,
        email=user.email,
        full_name=user.full_name,
        organizations=org_list
    )

@router.post("/token", response_model=TokenResponse, include_in_schema=False)
async def token_endpoint(request: Request, db: Session = Depends(get_db)):
    """OAuth2 password token alias for Swagger UI and OAuth2 clients."""
    return await login(request, db)

@router.get("/me", response_model=UserOut)
def get_current_user_profile(user: User = Depends(get_current_user)):
    return user

@router.get("/memberships", response_model=List[MembershipOut])
def get_user_memberships(user: User = Depends(get_current_user), db: Session = Depends(get_db)):
    memberships = db.query(OrganizationMembership).filter(OrganizationMembership.user_id == user.id).all()
    results = []
    for m in memberships:
        org = db.query(Organization).filter(Organization.id == m.organization_id).first()
        if org:
            results.append(MembershipOut(
                id=m.id,
                user_id=user.id,
                organization_id=org.id,
                organization_name=org.name,
                role=m.role
            ))
    return results
