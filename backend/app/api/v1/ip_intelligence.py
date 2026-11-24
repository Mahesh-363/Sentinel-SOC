import json
from typing import List, Optional, Dict, Any
from datetime import datetime
from fastapi import APIRouter, Depends, Query, HTTPException, status
from sqlalchemy import or_
from sqlalchemy.orm import Session

from backend.app.database import get_db
from backend.app.core.dependencies import get_current_org, get_current_user, require_role
from backend.app.core.ip_utils import classify_ip, get_approximate_geoip
from backend.app.core.threat_intel.adapters import (
    enrich_ip_all_providers,
    get_threat_provider_health
)
from backend.app.models.auth import Organization, User
from backend.app.models.network import IPObservation, NetworkDevice, Network
from backend.app.models.assets import Asset
from backend.app.models.events import SecurityEvent, ThreatIndicator, IPInvestigation
from backend.app.schemas.threat_intel import (
    ThreatProviderStatusOut,
    IPInvestigationCreate,
    IPInvestigationUpdate,
    IPInvestigationOut
)

router = APIRouter(prefix="/ip-intelligence", tags=["IP Intelligence"])

@router.get("/providers", response_model=List[ThreatProviderStatusOut])
def list_threat_providers(db: Session = Depends(get_db)):
    """
    Returns the real-time configuration status, daily request limits, and attribution
    for all 4 supported Threat Intelligence providers (AbuseIPDB, GreyNoise, AlienVault OTX, Spamhaus).
    """
    return get_threat_provider_health(db)

@router.get("/investigate")
async def investigate_ip(
    ip: str = Query(..., description="IPv4 or IPv6 address to investigate"),
    org: Organization = Depends(get_current_org),
    db: Session = Depends(get_db)
):
    """
    Advanced IP Investigation Engine:
    - IPv4 & IPv6 RFC classification
    - ASN & Approximate Geolocation
    - Multi-provider Threat Intelligence (AbuseIPDB, GreyNoise, OTX, Spamhaus) with TTL cache
    - Asset & Network associations
    - Observed Connection History & Related Security Events
    - Chronological Investigation Timeline
    - Explicit Grounding Breakdown: Directly Observed, Imported, Enriched, Inferred, Unavailable
    """
    classification = classify_ip(ip.strip())
    if not classification["is_valid"]:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail=f"Invalid IP address format: '{ip}'"
        )

    ip_str = classification["ip"]
    geo = get_approximate_geoip(ip_str)

    # 1. Threat Intelligence Enrichment (All 4 Providers + Cache)
    if classification["is_public"]:
        threat_intel = await enrich_ip_all_providers(ip_str, db=db)
    else:
        threat_intel = {
            "ip_address": ip_str,
            "overall_reputation": "Benign",
            "overall_confidence": 0,
            "cached": True,
            "providers": {
                "notice": {
                    "provider": "RFC Standard",
                    "status": "NOT APPLICABLE",
                    "reputation": "Benign",
                    "confidence": 0,
                    "attribution": "IETF RFC 1918 / RFC 4193 Private Address Space",
                    "raw_details": {"message": "Private IP addresses are internal to the organization and do not route to public threat intelligence databases."}
                }
            }
        }

    # 2. Local Organization Asset & Network Associations
    associated_assets = db.query(Asset).filter(
        Asset.organization_id == org.id,
        or_(Asset.private_ips.like(f"%{ip_str}%"), Asset.public_ip == ip_str)
    ).all()
    
    associated_devices = db.query(NetworkDevice).filter(
        NetworkDevice.organization_id == org.id,
        NetworkDevice.ip_address == ip_str
    ).all()

    # 3. Connection History (from IPObservation)
    obs_query = db.query(IPObservation).filter(
        IPObservation.organization_id == org.id,
        (IPObservation.ip_address == ip_str) | (IPObservation.destination_ip == ip_str)
    ).order_by(IPObservation.timestamp.desc())
    
    total_observations = obs_query.count()
    recent_observations = [
        {
            "id": o.id,
            "direction": o.direction,
            "port": o.destination_port or o.source_port,
            "protocol": o.protocol,
            "source": o.observation_source,
            "timestamp": o.timestamp.isoformat()
        }
        for o in obs_query.limit(20).all()
    ]

    # 4. Related Security Events
    events_query = db.query(SecurityEvent).filter(
        SecurityEvent.organization_id == org.id,
        (SecurityEvent.source_ip == ip_str) | (SecurityEvent.destination_ip == ip_str)
    ).order_by(SecurityEvent.timestamp.desc())

    total_events = events_query.count()
    recent_events = [
        {
            "id": e.id,
            "event_type": e.event_type,
            "severity": e.severity,
            "title": e.title,
            "timestamp": e.timestamp.isoformat(),
            "is_simulated": e.is_simulated
        }
        for e in events_query.limit(10).all()
    ]

    # 5. Local Threat Indicator Matches
    local_indicator = db.query(ThreatIndicator).filter(
        ThreatIndicator.indicator_value == ip_str
    ).first()
    local_indicator_data = None
    if local_indicator:
        local_indicator_data = {
            "threat_type": local_indicator.threat_type,
            "severity": local_indicator.severity,
            "source": local_indicator.source,
            "confidence": local_indicator.confidence,
            "description": local_indicator.description
        }

    # 6. Existing Analyst Investigation Record
    saved_investigation = db.query(IPInvestigation).filter(
        IPInvestigation.organization_id == org.id,
        IPInvestigation.ip_address == ip_str
    ).first()

    # 7. Build Chronological Investigation Timeline
    timeline = []
    if total_observations > 0:
        first_obs = obs_query.order_by(IPObservation.timestamp.asc()).first()
        if first_obs:
            timeline.append({
                "timestamp": first_obs.timestamp.isoformat(),
                "event": "First Observed on Network",
                "category": "OBSERVATION",
                "details": f"First connection observed via {first_obs.observation_source} (Direction: {first_obs.direction})"
            })
    
    for ev in recent_events[:5]:
        timeline.append({
            "timestamp": ev["timestamp"],
            "event": f"Security Alert: {ev['title']}",
            "category": "EVENT",
            "details": f"Severity: {ev['severity']} | Type: {ev['event_type']}"
        })

    if local_indicator:
        timeline.append({
            "timestamp": local_indicator.created_at.isoformat(),
            "event": f"Threat Feed Match ({local_indicator.source})",
            "category": "INTEL",
            "details": f"Identified as {local_indicator.threat_type} (Confidence: {local_indicator.confidence}%)"
        })

    if saved_investigation:
        timeline.append({
            "timestamp": saved_investigation.updated_at.isoformat(),
            "event": f"Analyst Verdict: {saved_investigation.verdict}",
            "category": "INVESTIGATION",
            "details": saved_investigation.notes or "No analyst notes provided."
        })

    # Sort timeline chronologically
    timeline.sort(key=lambda x: x["timestamp"])

    # 8. Strict Grounding Categories (Truth in Telemetry)
    directly_observed = {
        "is_observed_in_tenant": total_observations > 0 or total_events > 0,
        "total_network_connections": total_observations,
        "total_security_events": total_events,
        "enrolled_assets_using_ip": [a.hostname for a in associated_assets],
        "discovered_lan_devices": [{"mac": d.mac_address, "hostname": d.hostname, "type": d.device_type} for d in associated_devices]
    }

    imported_threat_intel = {
        "providers_queried": list(threat_intel.get("providers", {}).keys()),
        "local_blacklist_match": bool(local_indicator),
        "local_indicator_details": local_indicator_data,
        "results": threat_intel.get("providers", {})
    }

    third_party_enrichment = {
        "asn": geo.get("asn"),
        "as_org": geo.get("as_org"),
        "country": geo.get("country"),
        "country_code": geo.get("country_code"),
        "city": geo.get("city"),
        "geolocation_notice": "Approximate regional allocation based on public BGP/ISP routing blocks. Does NOT identify a physical residence or person."
    }

    inferred_information = {
        "calculated_reputation": threat_intel.get("overall_reputation", "Benign"),
        "confidence_score": threat_intel.get("overall_confidence", 0),
        "risk_explanation": f"Evaluated as {threat_intel.get('overall_reputation', 'Benign')} with confidence {threat_intel.get('overall_confidence', 0)}% based on multi-feed aggregation."
    }

    unavailable_information = []
    if not classification["is_public"]:
        unavailable_information.append("Public threat intelligence feeds (RFC1918 private space)")
    if not geo.get("city"):
        unavailable_information.append("Granular city-level GeoIP coordinates")
    if not associated_assets and not associated_devices:
        unavailable_information.append("Local hardware / MAC binding (Not an enrolled tenant device)")

    return {
        "ip_address": ip_str,
        "ip_version": f"IPv{classification['version']}",
        "version": classification["version"],
        "address_type": classification["classification"],
        "classification": classification["classification"],
        "is_public": classification["is_public"],
        "is_private": classification["is_private"],
        "is_loopback": classification["is_loopback"],
        "is_link_local": classification["is_link_local"],
        "reputation": threat_intel.get("overall_reputation", "Benign"),
        "confidence": threat_intel.get("overall_confidence", 0),
        "geolocation": third_party_enrichment,
        "associations": {
            "assets": [{"id": a.id, "hostname": a.hostname, "type": a.asset_type, "risk_level": a.risk_level} for a in associated_assets],
            "devices": [{"id": d.id, "hostname": d.hostname, "mac": d.mac_address, "type": d.device_type, "is_authorized": d.is_authorized} for d in associated_devices]
        },
        "connection_history": {
            "total_count": total_observations,
            "recent": recent_observations
        },
        "related_events": {
            "total_count": total_events,
            "recent": recent_events
        },
        "investigation_timeline": timeline,
        "threat_providers": threat_intel.get("providers", {}),
        "saved_investigation": {
            "id": saved_investigation.id,
            "verdict": saved_investigation.verdict,
            "notes": saved_investigation.notes,
            "tags": json.loads(saved_investigation.tags_json or "[]"),
            "updated_at": saved_investigation.updated_at.isoformat()
        } if saved_investigation else None,
        "investigation_notes": saved_investigation.notes if saved_investigation else None,
        "tags": json.loads(saved_investigation.tags_json or "[]") if saved_investigation else [],
        "grounding_breakdown": {
            "Directly Observed": directly_observed,
            "Imported Threat Intel": imported_threat_intel,
            "Third-Party Enrichment": third_party_enrichment,
            "Inferred Context": inferred_information,
            "Unavailable": unavailable_information
        },
        "grounding": {
            "directly_observed": directly_observed,
            "imported_threat_intel": imported_threat_intel,
            "third_party_enrichment": third_party_enrichment,
            "inferred_information": inferred_information,
            "unavailable_information": unavailable_information
        }
    }

@router.post("/investigations", response_model=IPInvestigationOut)
def create_or_update_investigation(
    payload: IPInvestigationCreate,
    user: User = Depends(get_current_user),
    org: Organization = Depends(get_current_org),
    db: Session = Depends(get_db)
):
    """
    Creates or updates an analyst investigation case for an IP address.
    Enforces multi-tenant isolation.
    """
    classification = classify_ip(payload.ip_address.strip())
    if not classification["is_valid"]:
        raise HTTPException(status_code=status.HTTP_400_BAD_REQUEST, detail="Invalid IP address")

    ip_str = classification["ip"]
    geo = get_approximate_geoip(ip_str)

    existing = db.query(IPInvestigation).filter(
        IPInvestigation.organization_id == org.id,
        IPInvestigation.ip_address == ip_str
    ).first()

    timeline_entry = {
        "timestamp": datetime.utcnow().isoformat(),
        "actor": user.full_name,
        "action": "Updated Investigation",
        "verdict": payload.verdict,
        "notes": payload.notes
    }

    if existing:
        existing.verdict = payload.verdict or existing.verdict
        existing.notes = payload.notes if payload.notes is not None else existing.notes
        if payload.tags:
            existing.tags_json = json.dumps(payload.tags)
        
        current_timeline = json.loads(existing.timeline_json or "[]")
        current_timeline.append(timeline_entry)
        existing.timeline_json = json.dumps(current_timeline)
        existing.updated_at = datetime.utcnow()
        db.commit()
        db.refresh(existing)
        target = existing
    else:
        target = IPInvestigation(
            organization_id=org.id,
            user_id=user.id,
            ip_address=ip_str,
            ip_version=classification["version"],
            classification=classification["classification"],
            asn=geo.get("asn"),
            as_org=geo.get("as_org"),
            country=geo.get("country"),
            city=geo.get("city"),
            verdict=payload.verdict or "Inconclusive",
            notes=payload.notes,
            tags_json=json.dumps(payload.tags or []),
            timeline_json=json.dumps([timeline_entry]),
            created_at=datetime.utcnow(),
            updated_at=datetime.utcnow()
        )
        db.add(target)
        db.commit()
        db.refresh(target)

    return IPInvestigationOut(
        id=target.id,
        organization_id=target.organization_id,
        user_id=target.user_id,
        ip_address=target.ip_address,
        ip_version=target.ip_version,
        classification=target.classification,
        asn=target.asn,
        as_org=target.as_org,
        country=target.country,
        city=target.city,
        verdict=target.verdict,
        notes=target.notes,
        tags=json.loads(target.tags_json or "[]"),
        timeline=json.loads(target.timeline_json or "[]"),
        created_at=target.created_at,
        updated_at=target.updated_at
    )

@router.get("/investigations", response_model=List[IPInvestigationOut])
def list_investigations(
    org: Organization = Depends(get_current_org),
    db: Session = Depends(get_db)
):
    """
    Lists all saved IP investigations for the current organization.
    """
    records = db.query(IPInvestigation).filter(
        IPInvestigation.organization_id == org.id
    ).order_by(IPInvestigation.updated_at.desc()).all()

    return [
        IPInvestigationOut(
            id=r.id,
            organization_id=r.organization_id,
            user_id=r.user_id,
            ip_address=r.ip_address,
            ip_version=r.ip_version,
            classification=r.classification,
            asn=r.asn,
            as_org=r.as_org,
            country=r.country,
            city=r.city,
            verdict=r.verdict,
            notes=r.notes,
            tags=json.loads(r.tags_json or "[]"),
            timeline=json.loads(r.timeline_json or "[]"),
            created_at=r.created_at,
            updated_at=r.updated_at
        )
        for r in records
    ]
