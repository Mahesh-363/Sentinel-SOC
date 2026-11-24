import json
from datetime import datetime
from typing import List, Optional
from fastapi import APIRouter, Depends, HTTPException, status, Query
from sqlalchemy.orm import Session

from backend.app.database import get_db
from backend.app.core.dependencies import get_current_org, require_role
from backend.app.models.auth import Organization
from backend.app.models.assets import Asset
from backend.app.schemas.assets import AssetCreate, AssetUpdate, AssetOut

router = APIRouter(prefix="/assets", tags=["Assets"])

@router.get("", response_model=List[AssetOut])
def list_assets(
    os_family: Optional[str] = None,
    asset_type: Optional[str] = None,
    health_status: Optional[str] = None,
    org: Organization = Depends(get_current_org),
    db: Session = Depends(get_db)
):
    query = db.query(Asset).filter(Asset.organization_id == org.id)
    if os_family:
        query = query.filter(Asset.os_family == os_family)
    if asset_type:
        query = query.filter(Asset.asset_type == asset_type)
    if health_status:
        query = query.filter(Asset.health_status == health_status)
    assets = query.order_by(Asset.last_seen.desc()).all()
    
    # Compute dynamic risk score and level
    from backend.app.core.risk_engine import calculate_asset_risk_score
    for a in assets:
        score, level, _ = calculate_asset_risk_score(db, a)
        a.risk_score = score
        a.risk_level = level
    return assets

@router.post("", response_model=AssetOut, dependencies=[Depends(require_role(["Organization Owner", "Organization Administrator", "Security Analyst"]))])
def create_asset(
    payload: AssetCreate,
    org: Organization = Depends(get_current_org),
    db: Session = Depends(get_db)
):
    asset = Asset(
        organization_id=org.id,
        hostname=payload.hostname.strip(),
        os_family=payload.os_family,
        os_version=payload.os_version,
        asset_type=payload.asset_type,
        private_ips=json.dumps(payload.private_ips or []),
        mac_addresses=json.dumps(payload.mac_addresses or []),
        public_ip=payload.public_ip,
        health_status="online",
        risk_level="Low",
        last_seen=datetime.utcnow()
    )
    db.add(asset)
    db.commit()
    db.refresh(asset)
    return asset

@router.get("/{asset_id}", response_model=AssetOut)
def get_asset(
    asset_id: str,
    org: Organization = Depends(get_current_org),
    db: Session = Depends(get_db)
):
    asset = db.query(Asset).filter(
        Asset.id == asset_id,
        Asset.organization_id == org.id
    ).first()
    if not asset:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Asset not found")
        
    from backend.app.core.risk_engine import calculate_asset_risk_score
    score, level, _ = calculate_asset_risk_score(db, asset)
    asset.risk_score = score
    asset.risk_level = level
    return asset

@router.get("/{asset_id}/risk")
def get_asset_risk_breakdown(
    asset_id: str,
    org: Organization = Depends(get_current_org),
    db: Session = Depends(get_db)
):
    asset = db.query(Asset).filter(
        Asset.id == asset_id,
        Asset.organization_id == org.id
    ).first()
    if not asset:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Asset not found")
        
    from backend.app.core.risk_engine import calculate_asset_risk_score
    score, level, breakdown = calculate_asset_risk_score(db, asset)
    asset.risk_score = score
    asset.risk_level = level
    db.commit()
    return breakdown

@router.patch("/{asset_id}", response_model=AssetOut, dependencies=[Depends(require_role(["Organization Owner", "Organization Administrator", "Security Analyst"]))])
def update_asset(
    asset_id: str,
    payload: AssetUpdate,
    org: Organization = Depends(get_current_org),
    db: Session = Depends(get_db)
):
    asset = db.query(Asset).filter(
        Asset.id == asset_id,
        Asset.organization_id == org.id
    ).first()
    if not asset:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Asset not found")
    if payload.hostname is not None:
        asset.hostname = payload.hostname
    if payload.health_status is not None:
        asset.health_status = payload.health_status
    if payload.risk_level is not None:
        asset.risk_level = payload.risk_level
    asset.updated_at = datetime.utcnow()
    db.commit()
    db.refresh(asset)
    return asset

@router.delete("/{asset_id}", dependencies=[Depends(require_role(["Organization Owner", "Organization Administrator", "Security Analyst"]))])
def delete_asset(
    asset_id: str,
    org: Organization = Depends(get_current_org),
    db: Session = Depends(get_db)
):
    asset = db.query(Asset).filter(
        Asset.id == asset_id,
        Asset.organization_id == org.id
    ).first()
    if not asset:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Asset not found")
    db.delete(asset)
    db.commit()
    return {"status": "success", "message": "Asset deleted successfully"}
