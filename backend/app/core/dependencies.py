from typing import Optional, List
from fastapi import Depends, HTTPException, status, Header, Request
from fastapi.security import OAuth2PasswordBearer, HTTPBearer, HTTPAuthorizationCredentials
from sqlalchemy.orm import Session

from backend.app.database import get_db
from backend.app.core.security import decode_token, hash_token
from backend.app.models.auth import User, Organization, OrganizationMembership
from backend.app.models.assets import Sensor

oauth2_scheme = OAuth2PasswordBearer(tokenUrl="/api/v1/auth/login", auto_error=False)
http_bearer = HTTPBearer(auto_error=False)

ROLE_HIERARCHY = {
    "Platform Administrator": 100,
    "Organization Owner": 80,
    "Organization Administrator": 60,
    "Security Analyst": 40,
    "Viewer": 20
}

def get_current_user(
    db: Session = Depends(get_db),
    bearer_creds: Optional[HTTPAuthorizationCredentials] = Depends(http_bearer),
    token_oauth2: Optional[str] = Depends(oauth2_scheme)
) -> User:
    token = (bearer_creds.credentials if bearer_creds else None) or token_oauth2
    if not token:
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="Authentication required",
            headers={"WWW-Authenticate": "Bearer"},
        )
    payload = decode_token(token)
    if not payload or "sub" not in payload:
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="Invalid or expired token",
            headers={"WWW-Authenticate": "Bearer"},
        )
    user_id = payload["sub"]
    user = db.query(User).filter(User.id == user_id, User.is_active == True).first()
    if not user:
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="User account not found or deactivated"
        )
    return user

def get_current_org(
    x_organization_id: Optional[str] = Header(None, alias="X-Organization-Id"),
    user: User = Depends(get_current_user),
    db: Session = Depends(get_db)
) -> Organization:
    """
    Strict tenant enforcement:
    Validates that the user is an authorized member of the requested organization.
    Never trusts browser-supplied organization IDs blindly.
    """
    if not x_organization_id:
        # Fall back to user's first available organization membership
        membership = db.query(OrganizationMembership).filter(
            OrganizationMembership.user_id == user.id
        ).first()
        if not membership:
            raise HTTPException(
                status_code=status.HTTP_400_BAD_REQUEST,
                detail="User does not belong to any organization. Please create or join an organization."
            )
        org = db.query(Organization).filter(
            Organization.id == membership.organization_id,
            Organization.is_active == True
        ).first()
        if not org:
            raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Organization not found")
        return org

    # If x_organization_id is explicitly provided, verify membership
    membership = db.query(OrganizationMembership).filter(
        OrganizationMembership.user_id == user.id,
        OrganizationMembership.organization_id == x_organization_id
    ).first()

    # Platform Admins can view any organization, but normal users strictly cannot
    if not membership and not user.is_platform_admin:
        raise HTTPException(
            status_code=status.HTTP_403_FORBIDDEN,
            detail="Access denied: You are not a member of this organization"
        )

    org = db.query(Organization).filter(
        Organization.id == x_organization_id,
        Organization.is_active == True
    ).first()
    if not org:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Organization not found")
        
    return org

def require_role(allowed_roles: List[str]):
    def role_checker(
        user: User = Depends(get_current_user),
        org: Organization = Depends(get_current_org),
        db: Session = Depends(get_db)
    ) -> User:
        if user.is_platform_admin:
            return user
            
        membership = db.query(OrganizationMembership).filter(
            OrganizationMembership.user_id == user.id,
            OrganizationMembership.organization_id == org.id
        ).first()
        
        if not membership or membership.role not in allowed_roles:
            from backend.app.models.auth import AuditLog
            audit = AuditLog(
                organization_id=org.id,
                user_id=user.id,
                user_email=user.email,
                action="AUTHZ_DENIED",
                target_type="Authorization",
                details=f"User {user.email} (Role: {membership.role if membership else 'None'}) denied access. Required: {', '.join(allowed_roles)}."
            )
            db.add(audit)
            db.commit()
            raise HTTPException(
                status_code=status.HTTP_403_FORBIDDEN,
                detail=f"Operation requires one of the following roles: {', '.join(allowed_roles)}"
            )
        return user
    return role_checker

def get_sensor_by_key(
    request: Request,
    x_sensor_key: Optional[str] = Header(None, alias="X-Sensor-Key"),
    db: Session = Depends(get_db)
) -> Sensor:
    """
    Authenticates a local sensor via its secret API key hash.
    Enforces non-empty keys, active sensor status, active organization,
    and cross-tenant isolation checks.
    """
    if not x_sensor_key or not x_sensor_key.strip():
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="Missing or empty sensor authentication key (X-Sensor-Key header)"
        )
    key_hash = hash_token(x_sensor_key.strip())
    sensor = db.query(Sensor).filter(Sensor.api_key_hash == key_hash).first()
    if not sensor:
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="Invalid sensor authentication key"
        )
    if sensor.status == "Revoked":
        from backend.app.models.auth import AuditLog
        audit = AuditLog(
            organization_id=sensor.organization_id,
            user_id=None,
            user_email=f"sensor-{sensor.id[:8]}",
            action="REVOKED_SENSOR_ACCESS_ATTEMPT",
            target_type="Sensor",
            target_id=sensor.id,
            details=f"Access attempt rejected: Sensor '{sensor.name}' has been revoked."
        )
        db.add(audit)
        db.commit()
        raise HTTPException(
            status_code=status.HTTP_403_FORBIDDEN,
            detail="This sensor's credentials have been revoked"
        )

    # Check active organization status
    org = db.query(Organization).filter(
        Organization.id == sensor.organization_id,
        Organization.is_active == True
    ).first()
    if not org:
        raise HTTPException(
            status_code=status.HTTP_403_FORBIDDEN,
            detail="Sensor organization is inactive or not found"
        )

    # Cross-tenant boundary check: If caller provides X-Organization-Id header, verify it matches
    x_org_id = request.headers.get("x-organization-id")
    if x_org_id and x_org_id.strip() != sensor.organization_id:
        from backend.app.models.auth import AuditLog
        audit = AuditLog(
            organization_id=sensor.organization_id,
            user_id=None,
            user_email=f"sensor-{sensor.id[:8]}",
            action="CROSS_TENANT_SENSOR_ATTEMPT",
            target_type="Sensor",
            target_id=sensor.id,
            details=f"Cross-tenant access violation: Sensor '{sensor.id}' (Org: {sensor.organization_id}) attempted access to Organization '{x_org_id}'."
        )
        db.add(audit)
        db.commit()
        raise HTTPException(
            status_code=status.HTTP_403_FORBIDDEN,
            detail="Cross-tenant access violation: Sensor credentials do not match the requested organization."
        )

    return sensor
