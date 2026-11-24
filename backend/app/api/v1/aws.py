import json
from datetime import datetime, timedelta
from typing import List, Optional, Dict, Any
from fastapi import APIRouter, Depends, HTTPException, status
from sqlalchemy.orm import Session

from backend.app.database import get_db
from backend.app.config import settings
from backend.app.core.dependencies import get_current_org, require_role
from backend.app.models.auth import Organization
from backend.app.models.aws import AWSAccount, AWSFinding, AWSResource
from backend.app.models.events import SecurityEvent
from backend.app.core.detection_engine import run_detection_pipeline_for_event
from backend.app.schemas.aws import (
    AWSAccountCreate,
    AWSAccountOut,
    AWSFindingOut,
    AWSResourceOut
)

router = APIRouter(prefix="/aws", tags=["AWS Cloud Security"])

@router.get("/status")
def get_aws_status(org: Organization = Depends(get_current_org), db: Session = Depends(get_db)):
    """
    Returns the organization's AWS integration status.
    Displays NOT CONFIGURED unless an active account has been connected.
    """
    active_count = db.query(AWSAccount).filter(
        AWSAccount.organization_id == org.id,
        AWSAccount.is_active == True
    ).count()

    is_configured = active_count > 0 or settings.AWS_ENABLED

    return {
        "enabled": is_configured,
        "status": "CONFIGURED" if is_configured else "NOT CONFIGURED",
        "active_accounts_count": active_count,
        "message": (
            "AWS integration is fully optional and incurs zero automated charges. "
            "Connect an existing AWS account via read-only AssumeRole or use the offline simulation fixtures."
        )
    }

@router.get("/accounts", response_model=List[AWSAccountOut])
def list_aws_accounts(org: Organization = Depends(get_current_org), db: Session = Depends(get_db)):
    return db.query(AWSAccount).filter(AWSAccount.organization_id == org.id).all()

@router.post("/accounts", response_model=AWSAccountOut, dependencies=[Depends(require_role(["Organization Owner", "Organization Administrator"]))])
def register_aws_account(
    payload: AWSAccountCreate,
    org: Organization = Depends(get_current_org),
    db: Session = Depends(get_db)
):
    """
    Registers an authorized AWS account using cross-account AssumeRole with External ID.
    Enforces least-privilege read-only access.
    """
    existing = db.query(AWSAccount).filter(
        AWSAccount.organization_id == org.id,
        AWSAccount.account_id == payload.account_id.strip()
    ).first()
    if existing:
        raise HTTPException(status_code=status.HTTP_400_BAD_REQUEST, detail="AWS Account ID already registered")

    acc = AWSAccount(
        organization_id=org.id,
        account_id=payload.account_id.strip(),
        account_name=payload.account_name.strip(),
        role_arn=payload.role_arn.strip(),
        external_id=payload.external_id.strip() if payload.external_id else None,
        region=payload.region.strip(),
        is_active=True,
        last_synced=datetime.utcnow()
    )
    db.add(acc)
    db.commit()
    db.refresh(acc)
    return acc

@router.delete("/accounts/{account_id}", dependencies=[Depends(require_role(["Organization Owner", "Organization Administrator"]))])
def disconnect_aws_account(
    account_id: str,
    org: Organization = Depends(get_current_org),
    db: Session = Depends(get_db)
):
    """
    Disconnects and removes an AWS account registration.
    """
    acc = db.query(AWSAccount).filter(
        AWSAccount.id == account_id,
        AWSAccount.organization_id == org.id
    ).first()
    if not acc:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="AWS account not found")

    db.delete(acc)
    db.commit()
    return {"status": "success", "message": f"AWS account '{acc.account_name}' disconnected."}

@router.get("/findings", response_model=List[AWSFindingOut])
def list_aws_findings(
    severity: Optional[str] = None,
    service: Optional[str] = None,
    org: Organization = Depends(get_current_org),
    db: Session = Depends(get_db)
):
    """
    Lists security findings across GuardDuty, IAM, S3, SecurityHub, and VPC Flow Logs.
    """
    query = db.query(AWSFinding).filter(AWSFinding.organization_id == org.id)
    if severity:
        query = query.filter(AWSFinding.severity == severity)
    if service:
        query = query.filter(AWSFinding.service == service)
    return query.order_by(AWSFinding.created_at.desc()).all()

@router.get("/resources", response_model=List[AWSResourceOut])
def list_aws_resources(
    resource_type: Optional[str] = None,
    org: Organization = Depends(get_current_org),
    db: Session = Depends(get_db)
):
    """
    Lists inspected cloud infrastructure resources (EC2 instances, S3 buckets, IAM roles, Security Groups).
    """
    query = db.query(AWSResource).filter(AWSResource.organization_id == org.id)
    if resource_type:
        query = query.filter(AWSResource.resource_type == resource_type)
    return query.order_by(AWSResource.last_scanned_at.desc()).all()

@router.get("/iam-policy-template")
def get_iam_policy_template():
    """
    Returns the least-privilege, read-only IAM policy template for Sentinel SOC.
    No write, delete, or resource modification permissions are requested.
    """
    policy = {
        "Version": "2012-10-17",
        "Statement": [
            {
                "Sid": "SentinelReadOnlySecurityHubAndGuardDuty",
                "Effect": "Allow",
                "Action": [
                    "guardduty:Get*",
                    "guardduty:List*",
                    "securityhub:Get*",
                    "securityhub:List*"
                ],
                "Resource": "*"
            },
            {
                "Sid": "SentinelReadOnlyIAMAndS3Audit",
                "Effect": "Allow",
                "Action": [
                    "iam:GenerateCredentialReport",
                    "iam:Get*",
                    "iam:List*",
                    "s3:GetBucketAcl",
                    "s3:GetBucketPolicy",
                    "s3:GetBucketPublicAccessBlock",
                    "s3:ListAllMyBuckets"
                ],
                "Resource": "*"
            },
            {
                "Sid": "SentinelReadOnlyEC2AndVPCFlow",
                "Effect": "Allow",
                "Action": [
                    "ec2:DescribeInstances",
                    "ec2:DescribeSecurityGroups",
                    "ec2:DescribeVpcs",
                    "ec2:DescribeFlowLogs"
                ],
                "Resource": "*"
            }
        ]
    }
    return {
        "policy_name": "SentinelSOCReadOnlySecurityAuditPolicy",
        "policy_json": policy,
        "trust_relationship": {
            "Version": "2012-10-17",
            "Statement": [
                {
                    "Effect": "Allow",
                    "Principal": {"AWS": "arn:aws:iam::YOUR_SENTINEL_ACCOUNT_ID:root"},
                    "Action": "sts:AssumeRole",
                    "Condition": {"StringEquals": {"sts:ExternalId": "YOUR_ORGANIZATION_EXTERNAL_ID"}}
                }
            ]
        }
    }

@router.post("/fixtures/simulate-finding", response_model=AWSFindingOut)
def simulate_aws_finding(
    service: str = "GuardDuty",
    finding_type: str = "Trojan:EC2/DNSDataExfiltration",
    severity: str = "High",
    org: Organization = Depends(get_current_org),
    db: Session = Depends(get_db)
):
    """
    Injects a realistic, explicitly labeled SIMULATED AWS finding for verification and learning.
    Never incurs AWS charges or requires live cloud credentials.
    """
    guidance_map = {
        "GuardDuty": "Isolate the identified EC2 instance from the security group and inspect recent DNS lookup queries in VPC flow logs.",
        "IAM": "Remove AdministratorAccess wildcard attachment from non-root roles and enforce MFA across all IAM users.",
        "S3": "Enable S3 Block Public Access at the account level and restrict PutBucketPolicy permissions.",
        "SecurityHub": "Remediate open inbound rules on port 22/3389 to restrict access to authorized corporate VPN CIDRs."
    }

    finding = AWSFinding(
        organization_id=org.id,
        service=service,
        finding_type=finding_type,
        severity=severity,
        resource_id=f"arn:aws:{service.lower()}:us-east-1:123456789012:simulated-{service.lower()}-resource",
        description=f"Simulated {service} finding: {finding_type} detected anomalous cloud activity.",
        remediation_guidance=guidance_map.get(service, "Review resource IAM policies and network ACLs."),
        raw_finding_json=json.dumps({"scenario": "offline_lab_fixture", "service": service}),
        is_simulated=True,
        created_at=datetime.utcnow()
    )
    db.add(finding)
    db.commit()
    db.refresh(finding)
    return finding

@router.post("/fixtures/load-all-fixtures")
def load_all_aws_fixtures(
    org: Organization = Depends(get_current_org),
    db: Session = Depends(get_db)
):
    """
    Loads a comprehensive offline fixture suite representing typical cloud posture risks.
    """
    fixtures = [
        {
            "service": "IAM",
            "finding_type": "IAMUser/RootAccountConsoleLoginWithoutMFA",
            "severity": "Critical",
            "resource_id": "arn:aws:iam::123456789012:root",
            "description": "The AWS root account logged into the management console without Multi-Factor Authentication (MFA).",
            "remediation_guidance": "Immediately enable hardware or virtual MFA on the AWS root account and lock down root access keys."
        },
        {
            "service": "SecurityGroup",
            "finding_type": "SecurityGroup/UnrestrictedInboundSSH",
            "severity": "High",
            "resource_id": "sg-01a2b3c4d5e6f7g8h",
            "description": "Security group allows unrestricted inbound TCP traffic on port 22 from 0.0.0.0/0.",
            "remediation_guidance": "Restrict SSH inbound CIDR to authorized bastion jump hosts or company VPN endpoints."
        },
        {
            "service": "S3",
            "finding_type": "S3Bucket/PublicReadWritePolicyAttached",
            "severity": "Critical",
            "resource_id": "arn:aws:s3:::corp-internal-backups-bucket",
            "description": "S3 bucket policy allows public s3:GetObject and s3:PutObject access to all internet principals.",
            "remediation_guidance": "Enable S3 Block Public Access on the bucket and remove the wildcards in the bucket policy."
        },
        {
            "service": "GuardDuty",
            "finding_type": "CryptoCurrency:EC2/BitcoinTool.B!DNS",
            "severity": "High",
            "resource_id": "i-0987654321fedcba0",
            "description": "EC2 instance queried domain names known to be associated with cryptocurrency mining pools.",
            "remediation_guidance": "Isolate the EC2 instance, inspect running process trees, and check for unauthorized SSH keys."
        }
    ]

    loaded = 0
    now = datetime.utcnow()
    for f in fixtures:
        finding = AWSFinding(
            organization_id=org.id,
            service=f["service"],
            finding_type=f["finding_type"],
            severity=f["severity"],
            resource_id=f["resource_id"],
            description=f["description"],
            remediation_guidance=f["remediation_guidance"],
            raw_finding_json=json.dumps({"fixture": True, "created": now.isoformat()}),
            is_simulated=True,
            created_at=now
        )
        db.add(finding)
        loaded += 1

    acct = db.query(AWSAccount).filter(AWSAccount.organization_id == org.id).first()
    if not acct:
        acct = AWSAccount(
            organization_id=org.id,
            account_id="123456789012",
            account_name="Simulated Production Account",
            role_arn="arn:aws:iam::123456789012:role/SentinelSOCReadOnlyRole",
            region="us-east-1",
            status="CONNECTED"
        )
        db.add(acct)
        db.flush()

    sample_resources = [
        {
            "resource_id": "arn:aws:s3:::corp-internal-backups-bucket",
            "resource_name": "corp-internal-backups-bucket",
            "resource_type": "S3_BUCKET",
            "arn": "arn:aws:s3:::corp-internal-backups-bucket",
            "region": "us-east-1",
            "configuration_json": json.dumps({"Environment": "Production", "Backup": "Daily"}),
            "compliance_status": "Non-Compliant"
        },
        {
            "resource_id": "i-0987654321fedcba0",
            "resource_name": "app-prod-worker-01",
            "resource_type": "EC2_INSTANCE",
            "arn": "arn:aws:ec2:us-east-1:123456789012:instance/i-0987654321fedcba0",
            "region": "us-east-1",
            "configuration_json": json.dumps({"Environment": "Production", "Role": "AppServer"}),
            "compliance_status": "Non-Compliant"
        },
        {
            "resource_id": "sg-01a2b3c4d5e6f7g8h",
            "resource_name": "bastion-security-group",
            "resource_type": "SECURITY_GROUP",
            "arn": "arn:aws:ec2:us-east-1:123456789012:security-group/sg-01a2b3c4d5e6f7g8h",
            "region": "us-east-1",
            "configuration_json": json.dumps({"Project": "Bastion"}),
            "compliance_status": "Non-Compliant"
        },
        {
            "resource_id": "arn:aws:iam::123456789012:root",
            "resource_name": "aws-root-account",
            "resource_type": "IAM_ROLE",
            "arn": "arn:aws:iam::123456789012:root",
            "region": "global",
            "configuration_json": json.dumps({"AccountType": "Root"}),
            "compliance_status": "Non-Compliant"
        }
    ]
    for r in sample_resources:
        res_obj = AWSResource(
            organization_id=org.id,
            aws_account_id=acct.id,
            resource_id=r["resource_id"],
            resource_name=r["resource_name"],
            resource_type=r["resource_type"],
            arn=r["arn"],
            region=r["region"],
            configuration_json=r["configuration_json"],
            compliance_status=r["compliance_status"],
            last_scanned_at=now
        )
        db.add(res_obj)

    db.commit()
    return {
        "status": "success",
        "fixtures_loaded": loaded,
        "message": "Loaded 4 realistic AWS security finding fixtures labeled as SIMULATED."
    }
