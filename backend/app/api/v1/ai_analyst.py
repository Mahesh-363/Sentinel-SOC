import json
from datetime import datetime
from fastapi import APIRouter, Depends, HTTPException, status
from sqlalchemy.orm import Session

from backend.app.database import get_db
from backend.app.core.datetime_utils import serialize_utc_datetime
from backend.app.core.dependencies import get_current_org, get_current_user
from backend.app.core.ai.analyst import run_security_analysis
from backend.app.models.auth import Organization, User
from backend.app.models.detections import DetectionResult
from backend.app.models.incidents import Incident
from backend.app.models.assets import Asset
from backend.app.models.events import SecurityEvent
from backend.app.models.ai import AIInvestigation, AIUsageRecord
from backend.app.schemas.ai import AIAnalystInvestigateRequest, AIAnalystInvestigateResponse

router = APIRouter(prefix="/ai-analyst", tags=["AI Security Analyst"])

@router.post("/investigate", response_model=AIAnalystInvestigateResponse)
async def investigate_with_ai(
    payload: AIAnalystInvestigateRequest,
    user: User = Depends(get_current_user),
    org: Organization = Depends(get_current_org),
    db: Session = Depends(get_db)
):
    target_data = {}
    evidence_sources = []
    is_simulated = False

    # Collect authorized telemetry context based on target type
    if payload.target_type == "alert":
        alert = db.query(DetectionResult).filter(
            DetectionResult.id == payload.target_id,
            DetectionResult.organization_id == org.id
        ).first()
        if not alert:
            raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Alert not found in organization")
        target_data = {
            "title": alert.title,
            "rule": alert.rule_name,
            "severity": alert.severity,
            "evidence": alert.evidence_json,
            "related_ip": alert.related_ip,
            "confidence": alert.confidence,
            "timestamp": serialize_utc_datetime(alert.timestamp)
        }
        evidence_sources.append(f"Alert ID: {alert.id}")
        is_simulated = alert.is_simulated

    elif payload.target_type == "incident":
        inc = db.query(Incident).filter(
            Incident.id == payload.target_id,
            Incident.organization_id == org.id
        ).first()
        if not inc:
            raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Incident not found in organization")
        target_data = {
            "title": inc.title,
            "description": inc.description,
            "severity": inc.severity,
            "status": inc.status,
            "related_assets": inc.related_asset_ids_json,
            "related_ips": inc.related_ip_addresses_json,
            "created_at": serialize_utc_datetime(inc.created_at)
        }
        evidence_sources.append(f"Incident ID: {inc.id}")

    elif payload.target_type == "ip":
        target_data = {"ip_address": payload.target_id}
        # Gather recent observations in this org
        events = db.query(SecurityEvent).filter(
            SecurityEvent.organization_id == org.id,
            (SecurityEvent.source_ip == payload.target_id) | (SecurityEvent.destination_ip == payload.target_id)
        ).limit(10).all()
        target_data["recent_org_events_count"] = len(events)
        target_data["event_types"] = [e.event_type for e in events]
        evidence_sources.append(f"IP: {payload.target_id}")

    elif payload.target_type == "asset":
        asset = db.query(Asset).filter(
            Asset.id == payload.target_id,
            Asset.organization_id == org.id
        ).first()
        if not asset:
            raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Asset not found")
        target_data = {
            "hostname": asset.hostname,
            "os_family": asset.os_family,
            "health_status": asset.health_status,
            "risk_level": asset.risk_level,
            "last_seen": serialize_utc_datetime(asset.last_seen)
        }
        evidence_sources.append(f"Asset ID: {asset.id}")
    else:
        target_data = {"query": payload.query or "General SOC investigation query"}

    # Run security analysis through advisory AI provider
    result = await run_security_analysis(
        target_type=payload.target_type,
        target_data=target_data,
        user_query=payload.query
    )

    # Persist investigation record
    investigation = AIInvestigation(
        organization_id=org.id,
        user_id=user.id,
        target_type=payload.target_type,
        target_id=payload.target_id,
        prompt=payload.query or f"Investigate {payload.target_type} {payload.target_id}",
        response=result["content"],
        evidence_sources_json=json.dumps(evidence_sources),
        tokens_used=result.get("tokens_used", 0),
        is_simulated=is_simulated,
        created_at=datetime.utcnow()
    )
    db.add(investigation)

    # Track usage record
    usage = AIUsageRecord(
        organization_id=org.id,
        user_id=user.id,
        provider=result.get("provider", "gemini"),
        model=result.get("model", "gemini-1.5-flash"),
        prompt_tokens=result.get("tokens_used", 0) // 2,
        completion_tokens=result.get("tokens_used", 0) // 2,
        total_tokens=result.get("tokens_used", 0),
        timestamp=datetime.utcnow()
    )
    db.add(usage)
    db.commit()
    db.refresh(investigation)

    return AIAnalystInvestigateResponse(
        investigation_id=investigation.id,
        target_type=payload.target_type,
        target_id=payload.target_id,
        analysis=result["content"],
        provider=result.get("provider", "gemini"),
        model=result.get("model", "gemini-1.5-flash"),
        status=result.get("status", "success"),
        is_simulated=is_simulated,
        evidence_sources=evidence_sources,
        mitre_techniques=result.get("mitre_techniques", []),
        structured_breakdown=result.get("structured_breakdown"),
        created_at=investigation.created_at
    )
