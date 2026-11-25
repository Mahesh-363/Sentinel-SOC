from typing import Optional, List, Dict, Any
from pydantic import BaseModel, ConfigDict
from backend.app.core.datetime_utils import UTCDatetime

class AIAnalystInvestigateRequest(BaseModel):
    target_type: str  # alert, incident, ip, asset, general
    target_id: Optional[str] = None
    query: Optional[str] = None

class AIStructuredEvidenceBreakdown(BaseModel):
    verified_facts: List[str] = []
    possible_explanations: List[str] = []
    hypotheses: List[str] = []
    recommendations: List[str] = []
    unknown_information: List[str] = []

class AIAnalystInvestigateResponse(BaseModel):
    model_config = ConfigDict(from_attributes=True)

    investigation_id: str
    target_type: str
    target_id: Optional[str] = None
    analysis: str
    provider: str
    model: str
    status: str
    is_simulated: bool = False
    evidence_sources: List[str] = []
    mitre_techniques: List[str] = []
    structured_breakdown: Optional[AIStructuredEvidenceBreakdown] = None
    created_at: UTCDatetime

class HelpdeskChatRequest(BaseModel):
    conversation_id: Optional[str] = None
    message: str
    context_page: Optional[str] = None
    sanitized_diagnostics: Optional[Dict[str, Any]] = None

class HelpdeskMessageOut(BaseModel):
    model_config = ConfigDict(from_attributes=True)

    id: str
    conversation_id: str
    sender_role: str
    message: str
    citations: Optional[List[Dict[str, Any]]] = None
    created_at: UTCDatetime

class HelpdeskConversationOut(BaseModel):
    model_config = ConfigDict(from_attributes=True)

    id: str
    title: str
    context_page: Optional[str] = None
    created_at: UTCDatetime
    updated_at: UTCDatetime
    messages: List[HelpdeskMessageOut] = []

class DiagnosticShareIn(BaseModel):
    conversation_id: str
    application_version: str
    os_info: Optional[str] = None
    browser_info: Optional[str] = None
    error_code: Optional[str] = None
    context_data: Dict[str, Any]

class HelpdeskFeedbackIn(BaseModel):
    message_id: str
    rating: int  # 1 (helpful) or -1 (unhelpful)
    feedback_text: Optional[str] = None
