import uuid
from datetime import datetime
from sqlalchemy import Column, String, Boolean, DateTime, ForeignKey, Text, Index
from backend.app.database import Base

def generate_uuid():
    return str(uuid.uuid4())

class AWSAccount(Base):
    __tablename__ = "aws_accounts"
    
    id = Column(String(36), primary_key=True, default=generate_uuid)
    organization_id = Column(String(36), ForeignKey("organizations.id", ondelete="CASCADE"), nullable=False, index=True)
    account_id = Column(String(20), nullable=False)
    account_name = Column(String(100), nullable=False)
    role_arn = Column(String(255), nullable=False)
    external_id = Column(String(100), nullable=True)
    region = Column(String(50), default="us-east-1", nullable=False)
    is_active = Column(Boolean, default=True, nullable=False)
    last_synced = Column(DateTime, nullable=True)
    created_at = Column(DateTime, default=datetime.utcnow, nullable=False)

class AWSFinding(Base):
    __tablename__ = "aws_findings"
    
    id = Column(String(36), primary_key=True, default=generate_uuid)
    organization_id = Column(String(36), ForeignKey("organizations.id", ondelete="CASCADE"), nullable=False, index=True)
    aws_account_id = Column(String(36), ForeignKey("aws_accounts.id", ondelete="CASCADE"), nullable=True, index=True)
    service = Column(String(50), nullable=False)  # GuardDuty, IAM, S3, CloudTrail, SecurityHub, VPCFlow, EC2
    finding_type = Column(String(100), nullable=False, index=True)
    severity = Column(String(20), default="Medium", nullable=False, index=True)
    resource_id = Column(String(255), nullable=True)
    description = Column(Text, nullable=False)
    remediation_guidance = Column(Text, nullable=True)
    raw_finding_json = Column(Text, nullable=True)
    is_simulated = Column(Boolean, default=False, nullable=False)
    created_at = Column(DateTime, default=datetime.utcnow, nullable=False, index=True)

class AWSResource(Base):
    """
    Inventory of inspected AWS infrastructure assets (EC2, S3, IAM Roles, Security Groups).
    """
    __tablename__ = "aws_resources"
    
    id = Column(String(36), primary_key=True, default=generate_uuid)
    organization_id = Column(String(36), ForeignKey("organizations.id", ondelete="CASCADE"), nullable=False, index=True)
    aws_account_id = Column(String(36), ForeignKey("aws_accounts.id", ondelete="CASCADE"), nullable=False, index=True)
    resource_type = Column(String(50), nullable=False, index=True)  # EC2_INSTANCE, S3_BUCKET, IAM_ROLE, SECURITY_GROUP, VPC
    resource_id = Column(String(255), nullable=False, index=True)
    resource_name = Column(String(255), nullable=False)
    arn = Column(String(255), nullable=True)
    region = Column(String(50), default="us-east-1", nullable=False)
    configuration_json = Column(Text, nullable=True)
    compliance_status = Column(String(50), default="Compliant", nullable=False)  # Compliant, Non-Compliant
    last_scanned_at = Column(DateTime, default=datetime.utcnow, nullable=False)
