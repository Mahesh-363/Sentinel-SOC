from datetime import datetime, timedelta
from typing import List, Optional, Dict, Any
from fastapi import APIRouter, Depends, HTTPException, status
from pydantic import BaseModel
from sqlalchemy.orm import Session
from sqlalchemy import func

from backend.app.database import get_db
from backend.app.config import settings
from backend.app.core.dependencies import get_current_org, get_current_user, require_role
from backend.app.core.ai.provider import get_ai_provider
from backend.app.models.auth import Organization, User, AuditLog, OrganizationMembership
from backend.app.models.ai import AIUsageRecord
from backend.app.models.events import SecurityEvent
from backend.app.models.detections import DetectionResult

router = APIRouter(prefix="/admin", tags=["Administration"])

class RoleUpdateRequest(BaseModel):
    role: str  # "Organization Owner", "Organization Administrator", "Security Analyst", "Viewer"

class RetentionPolicyUpdate(BaseModel):
    event_retention_days: int = 90
    incident_retention_days: int = 365

@router.get("/system-health", dependencies=[Depends(require_role(["Platform Administrator", "Organization Owner", "Organization Administrator"]))])
def get_system_health(db: Session = Depends(get_db)):
    ai_provider = get_ai_provider()
    
    return {
        "app_name": settings.APP_NAME,
        "version": settings.APP_VERSION,
        "environment": settings.ENVIRONMENT,
        "timestamp": datetime.utcnow().isoformat(),
        "database": {
            "status": "HEALTHY",
            "dialect": db.bind.dialect.name
        },
        "redis": {
            "status": "ONLINE" if settings.REDIS_ENABLED else "LOCAL_FALLBACK (IN-MEMORY)",
            "enabled": settings.REDIS_ENABLED
        },
        "ai_provider": ai_provider.health_check(),
        "email_delivery": {
            "status": "CONFIGURED" if settings.EMAIL_ENABLED else "NOT CONFIGURED (DEV SAFE)",
            "enabled": settings.EMAIL_ENABLED
        },
        "aws_security": {
            "status": "CONFIGURED" if settings.AWS_ENABLED else "NOT CONFIGURED",
            "enabled": settings.AWS_ENABLED
        }
    }

@router.get("/ai-quota", dependencies=[Depends(require_role(["Platform Administrator", "Organization Owner", "Organization Administrator"]))])
def get_ai_quota_status(org: Organization = Depends(get_current_org), db: Session = Depends(get_db)):
    today_start = datetime.utcnow().replace(hour=0, minute=0, second=0, microsecond=0)
    
    today_usage = db.query(
        func.sum(AIUsageRecord.total_tokens).label("tokens"),
        func.count(AIUsageRecord.id).label("requests")
    ).filter(
        AIUsageRecord.organization_id == org.id,
        AIUsageRecord.timestamp >= today_start
    ).first()

    tokens_today = today_usage.tokens or 0
    requests_today = today_usage.requests or 0

    return {
        "provider": settings.AI_PROVIDER,
        "model": settings.GEMINI_MODEL if settings.AI_PROVIDER == "gemini" else settings.LOCAL_AI_MODEL,
        "requests_today": requests_today,
        "estimated_tokens_today": tokens_today,
        "daily_request_limit": settings.AI_DAILY_QUOTA_LIMIT,
        "quota_status": "EXHAUSTED" if requests_today >= settings.AI_DAILY_QUOTA_LIMIT else "HEALTHY",
        "free_tier_safe": True,
        "auto_switch_to_paid": False
    }

@router.get("/users", dependencies=[Depends(require_role(["Platform Administrator", "Organization Owner", "Organization Administrator"]))])
def list_organization_users(
    org: Organization = Depends(get_current_org),
    db: Session = Depends(get_db)
):
    memberships = db.query(OrganizationMembership).filter(
        OrganizationMembership.organization_id == org.id
    ).all()
    user_ids = [m.user_id for m in memberships]
    users = db.query(User).filter(User.id.in_(user_ids)).all()
    user_map = {u.id: u for u in users}

    result = []
    for m in memberships:
        u = user_map.get(m.user_id)
        if u:
            result.append({
                "user_id": u.id,
                "email": u.email,
                "full_name": u.full_name,
                "role": m.role,
                "is_active": u.is_active,
                "joined_at": m.created_at.isoformat()
            })
    return result

@router.patch("/users/{user_id}/role", dependencies=[Depends(require_role(["Platform Administrator", "Organization Owner"]))])
def update_user_role(
    user_id: str,
    payload: RoleUpdateRequest,
    current_user: User = Depends(get_current_user),
    org: Organization = Depends(get_current_org),
    db: Session = Depends(get_db)
):
    valid_roles = ["Organization Owner", "Organization Administrator", "Security Analyst", "Viewer"]
    if payload.role not in valid_roles:
        raise HTTPException(status_code=status.HTTP_400_BAD_REQUEST, detail=f"Invalid role. Must be one of {valid_roles}")

    membership = db.query(OrganizationMembership).filter(
        OrganizationMembership.organization_id == org.id,
        OrganizationMembership.user_id == user_id
    ).first()
    if not membership:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="User membership not found in this organization")

    old_role = membership.role
    membership.role = payload.role

    # Audit Log
    target_user = db.query(User).filter(User.id == user_id).first()
    audit = AuditLog(
        organization_id=org.id,
        user_id=current_user.id,
        user_email=current_user.email,
        action="USER_ROLE_UPDATED",
        target_type="User",
        target_id=user_id,
        details=f"User {target_user.email if target_user else user_id} role updated from '{old_role}' to '{payload.role}' by {current_user.email}."
    )
    db.add(audit)
    db.commit()
    return {"status": "success", "user_id": user_id, "new_role": payload.role}

@router.get("/integrations", dependencies=[Depends(require_role(["Platform Administrator", "Organization Owner", "Organization Administrator"]))])
def get_integrations_status(db: Session = Depends(get_db)):
    ai_provider = get_ai_provider()
    return {
        "integrations": [
            {
                "id": "abuseipdb",
                "name": "AbuseIPDB Threat Intelligence",
                "category": "Threat Intelligence",
                "status": "ONLINE" if settings.ABUSEIPDB_API_KEY else "NOT CONFIGURED",
                "free_tier": True,
                "description": "Reputation queries for external IPs reporting abusive behavior and scanner activity."
            },
            {
                "id": "greynoise",
                "name": "GreyNoise Community",
                "category": "Threat Intelligence",
                "status": "ONLINE" if settings.GREYNOISE_API_KEY else "NOT CONFIGURED",
                "free_tier": True,
                "description": "Noise reduction separating benign internet scanners from targeted malicious exploits."
            },
            {
                "id": "alienvault",
                "name": "AlienVault OTX",
                "category": "Threat Intelligence",
                "status": "ONLINE" if settings.ALIENVAULT_OTX_KEY else "NOT CONFIGURED",
                "free_tier": True,
                "description": "Open threat exchange pulses, CVE mappings, and malware campaign indicators."
            },
            {
                "id": "gemini_ai",
                "name": "Google Gemini Free Tier",
                "category": "Advisory AI",
                "status": ai_provider.health_check().get("status", "OFFLINE"),
                "free_tier": True,
                "description": "Advisory investigation briefings and Helpdesk RAG powered by Gemini 1.5 Flash."
            },
            {
                "id": "aws_assume_role",
                "name": "AWS AssumeRole Read-Only",
                "category": "Cloud Security",
                "status": "ONLINE" if settings.AWS_ENABLED else "NOT CONFIGURED",
                "free_tier": True,
                "description": "Cross-account STS authentication with External ID for GuardDuty and Security Hub."
            },
            {
                "id": "smtp_notifications",
                "name": "SMTP / Email Delivery",
                "category": "Notifications",
                "status": "ONLINE" if settings.EMAIL_ENABLED else "NOT CONFIGURED (DEV MOCK)",
                "free_tier": True,
                "description": "Alert email notifications and SOC operator dispatch delivery."
            }
        ]
    }

@router.get("/retention", dependencies=[Depends(require_role(["Platform Administrator", "Organization Owner", "Organization Administrator"]))])
def get_retention_policy(org: Organization = Depends(get_current_org), db: Session = Depends(get_db)):
    total_events = db.query(SecurityEvent).filter(SecurityEvent.organization_id == org.id).count()
    oldest_event = db.query(SecurityEvent.timestamp).filter(SecurityEvent.organization_id == org.id).order_by(SecurityEvent.timestamp.asc()).first()
    
    return {
        "event_retention_days": 90,
        "incident_retention_days": 365,
        "total_events_stored": total_events,
        "oldest_event_timestamp": oldest_event[0].isoformat() if oldest_event else None,
        "compliance_standard": "SOC2 / ISO 27001 Log Preservation Policy"
    }

@router.post("/retention/cleanup", dependencies=[Depends(require_role(["Platform Administrator", "Organization Owner"]))])
def run_retention_cleanup(
    payload: RetentionPolicyUpdate,
    user: User = Depends(get_current_user),
    org: Organization = Depends(get_current_org),
    db: Session = Depends(get_db)
):
    cutoff = datetime.utcnow() - timedelta(days=payload.event_retention_days)
    purged_count = db.query(SecurityEvent).filter(
        SecurityEvent.organization_id == org.id,
        SecurityEvent.timestamp < cutoff
    ).delete(synchronize_session=False)

    audit = AuditLog(
        organization_id=org.id,
        user_id=user.id,
        user_email=user.email,
        action="DATA_RETENTION_PURGE",
        target_type="SecurityEvent",
        details=f"Purged {purged_count} security events older than {payload.event_retention_days} days. Initiated by {user.email}."
    )
    db.add(audit)
    db.commit()
    return {"status": "success", "purged_events_count": purged_count, "cutoff_date": cutoff.isoformat()}

@router.get("/audit-logs", dependencies=[Depends(require_role(["Platform Administrator", "Organization Owner", "Organization Administrator"]))])
def list_audit_logs(
    limit: int = 100,
    org: Organization = Depends(get_current_org),
    db: Session = Depends(get_db)
):
    return db.query(AuditLog).filter(
        AuditLog.organization_id == org.id
    ).order_by(AuditLog.created_at.desc()).limit(limit).all()
