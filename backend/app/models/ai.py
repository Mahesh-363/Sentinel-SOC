import uuid
from datetime import datetime
from sqlalchemy import Column, String, Boolean, DateTime, ForeignKey, Text, Integer, Index
from sqlalchemy.orm import relationship
from backend.app.database import Base

def generate_uuid():
    return str(uuid.uuid4())

class AIInvestigation(Base):
    __tablename__ = "ai_investigations"
    
    id = Column(String(36), primary_key=True, default=generate_uuid)
    organization_id = Column(String(36), ForeignKey("organizations.id", ondelete="CASCADE"), nullable=False, index=True)
    user_id = Column(String(36), ForeignKey("users.id", ondelete="SET NULL"), nullable=True, index=True)
    target_type = Column(String(50), nullable=False)  # incident, alert, ip, asset, general
    target_id = Column(String(100), nullable=True)
    prompt = Column(Text, nullable=False)
    response = Column(Text, nullable=False)
    evidence_sources_json = Column(Text, nullable=True)  # List of real telemetry IDs used as evidence
    tokens_used = Column(Integer, default=0, nullable=False)
    is_simulated = Column(Boolean, default=False, nullable=False)
    created_at = Column(DateTime, default=datetime.utcnow, nullable=False, index=True)

class HelpdeskConversation(Base):
    __tablename__ = "helpdesk_conversations"
    
    id = Column(String(36), primary_key=True, default=generate_uuid)
    organization_id = Column(String(36), ForeignKey("organizations.id", ondelete="CASCADE"), nullable=False, index=True)
    user_id = Column(String(36), ForeignKey("users.id", ondelete="CASCADE"), nullable=False, index=True)
    title = Column(String(255), nullable=False)
    context_page = Column(String(100), nullable=True)  # e.g. /sensors, /detections, /dashboard
    created_at = Column(DateTime, default=datetime.utcnow, nullable=False, index=True)
    updated_at = Column(DateTime, default=datetime.utcnow, onupdate=datetime.utcnow, nullable=False)
    
    messages = relationship("HelpdeskMessage", back_populates="conversation", cascade="all, delete-orphan")

class HelpdeskMessage(Base):
    __tablename__ = "helpdesk_messages"
    
    id = Column(String(36), primary_key=True, default=generate_uuid)
    conversation_id = Column(String(36), ForeignKey("helpdesk_conversations.id", ondelete="CASCADE"), nullable=False, index=True)
    sender_role = Column(String(20), nullable=False)  # "user" or "assistant"
    message = Column(Text, nullable=False)
    citations_json = Column(Text, nullable=True)  # References to approved docs
    sanitized_diagnostic_json = Column(Text, nullable=True)
    created_at = Column(DateTime, default=datetime.utcnow, nullable=False, index=True)
    
    conversation = relationship("HelpdeskConversation", back_populates="messages")
    feedbacks = relationship("HelpdeskFeedback", back_populates="message_rel", cascade="all, delete-orphan")

class HelpdeskFeedback(Base):
    __tablename__ = "helpdesk_feedbacks"
    
    id = Column(String(36), primary_key=True, default=generate_uuid)
    message_id = Column(String(36), ForeignKey("helpdesk_messages.id", ondelete="CASCADE"), nullable=False, index=True)
    user_id = Column(String(36), ForeignKey("users.id", ondelete="SET NULL"), nullable=True, index=True)
    is_helpful = Column(Boolean, nullable=False)
    feedback_text = Column(Text, nullable=True)
    created_at = Column(DateTime, default=datetime.utcnow, nullable=False)
    
    message_rel = relationship("HelpdeskMessage", back_populates="feedbacks")

class AIUsageRecord(Base):
    __tablename__ = "ai_usage_records"
    
    id = Column(String(36), primary_key=True, default=generate_uuid)
    organization_id = Column(String(36), nullable=False, index=True)
    user_id = Column(String(36), nullable=True, index=True)
    provider = Column(String(50), nullable=False)  # gemini, local, mock
    model = Column(String(100), nullable=False)
    prompt_tokens = Column(Integer, default=0, nullable=False)
    completion_tokens = Column(Integer, default=0, nullable=False)
    total_tokens = Column(Integer, default=0, nullable=False)
    timestamp = Column(DateTime, default=datetime.utcnow, nullable=False, index=True)

class DiagnosticShare(Base):
    __tablename__ = "diagnostic_shares"
    
    id = Column(String(36), primary_key=True, default=generate_uuid)
    conversation_id = Column(String(36), ForeignKey("helpdesk_conversations.id", ondelete="CASCADE"), nullable=False, index=True)
    user_id = Column(String(36), ForeignKey("users.id", ondelete="CASCADE"), nullable=False)
    application_version = Column(String(50), nullable=False)
    os_info = Column(String(100), nullable=True)
    browser_info = Column(String(255), nullable=True)
    error_code = Column(String(50), nullable=True)
    sanitized_context = Column(Text, nullable=False)
    created_at = Column(DateTime, default=datetime.utcnow, nullable=False)

class KnowledgeDocument(Base):
    __tablename__ = "knowledge_documents"
    
    id = Column(String(36), primary_key=True, default=generate_uuid)
    title = Column(String(255), nullable=False)
    category = Column(String(100), nullable=False, index=True) # Architecture, Troubleshooting, Sensor, API, Detection
    filepath = Column(String(255), nullable=False)
    content = Column(Text, nullable=False)
    summary = Column(Text, nullable=True)
    updated_at = Column(DateTime, default=datetime.utcnow, nullable=False)
