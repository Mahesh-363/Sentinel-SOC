import json
from datetime import datetime
from typing import List, Optional, Dict, Any
from fastapi import APIRouter, Depends, HTTPException, status
from sqlalchemy.orm import Session

from backend.app.database import get_db
from backend.app.core.dependencies import get_current_org, get_current_user
from backend.app.core.ai.helpdesk import run_helpdesk_query
from backend.app.core.ai.redaction import sanitize_diagnostic_dict, sanitize_diagnostic_text
from backend.app.models.auth import Organization, User
from backend.app.models.ai import (
    HelpdeskConversation,
    HelpdeskMessage,
    HelpdeskFeedback,
    DiagnosticShare,
    AIUsageRecord
)
from backend.app.schemas.ai import (
    HelpdeskChatRequest,
    HelpdeskConversationOut,
    HelpdeskMessageOut,
    DiagnosticShareIn,
    HelpdeskFeedbackIn
)

router = APIRouter(prefix="/ai-helpdesk", tags=["Sentinel AI Helpdesk"])

@router.get("/conversations", response_model=List[HelpdeskConversationOut])
def list_conversations(
    user: User = Depends(get_current_user),
    org: Organization = Depends(get_current_org),
    db: Session = Depends(get_db)
):
    convs = db.query(HelpdeskConversation).filter(
        HelpdeskConversation.organization_id == org.id,
        HelpdeskConversation.user_id == user.id
    ).order_by(HelpdeskConversation.updated_at.desc()).all()
    
    results = []
    for c in convs:
        msgs = db.query(HelpdeskMessage).filter(HelpdeskMessage.conversation_id == c.id).order_by(HelpdeskMessage.created_at.asc()).all()
        msg_outs = []
        for m in msgs:
            citations = json.loads(m.citations_json) if m.citations_json else None
            msg_outs.append(HelpdeskMessageOut(
                id=m.id,
                conversation_id=m.conversation_id,
                sender_role=m.sender_role,
                message=m.message,
                citations=citations,
                created_at=m.created_at
            ))
        results.append(HelpdeskConversationOut(
            id=c.id,
            title=c.title,
            context_page=c.context_page,
            created_at=c.created_at,
            updated_at=c.updated_at,
            messages=msg_outs
        ))
    return results

@router.post("/chat", response_model=HelpdeskMessageOut)
async def chat_with_helpdesk(
    payload: HelpdeskChatRequest,
    user: User = Depends(get_current_user),
    org: Organization = Depends(get_current_org),
    db: Session = Depends(get_db)
):
    conversation = None
    if payload.conversation_id:
        conversation = db.query(HelpdeskConversation).filter(
            HelpdeskConversation.id == payload.conversation_id,
            HelpdeskConversation.organization_id == org.id,
            HelpdeskConversation.user_id == user.id
        ).first()

    if not conversation:
        title = payload.message[:40] + ("..." if len(payload.message) > 40 else "")
        conversation = HelpdeskConversation(
            organization_id=org.id,
            user_id=user.id,
            title=title,
            context_page=payload.context_page,
            created_at=datetime.utcnow(),
            updated_at=datetime.utcnow()
        )
        db.add(conversation)
        db.flush()

    # Save user message
    user_msg = HelpdeskMessage(
        conversation_id=conversation.id,
        sender_role="user",
        message=payload.message,
        created_at=datetime.utcnow()
    )
    db.add(user_msg)
    db.flush()

    # Build conversation history
    prior_messages = db.query(HelpdeskMessage).filter(
        HelpdeskMessage.conversation_id == conversation.id
    ).order_by(HelpdeskMessage.created_at.asc()).limit(10).all()
    
    history = []
    for pm in prior_messages:
        history.append({
            "role": pm.sender_role,
            "content": pm.message
        })

    # Execute Helpdesk query with RAG
    ai_res = await run_helpdesk_query(
        question=payload.message,
        context_page=payload.context_page or conversation.context_page,
        sanitized_diagnostics=payload.sanitized_diagnostics,
        conversation_history=history
    )

    # Save assistant response
    assistant_msg = HelpdeskMessage(
        conversation_id=conversation.id,
        sender_role="assistant",
        message=ai_res["content"],
        citations_json=json.dumps(ai_res.get("citations", [])),
        sanitized_diagnostic_json=json.dumps(payload.sanitized_diagnostics or {}),
        created_at=datetime.utcnow()
    )
    db.add(assistant_msg)
    
    conversation.updated_at = datetime.utcnow()
    db.commit()
    db.refresh(assistant_msg)

    return HelpdeskMessageOut(
        id=assistant_msg.id,
        conversation_id=assistant_msg.conversation_id,
        sender_role="assistant",
        message=assistant_msg.message,
        citations=ai_res.get("citations"),
        created_at=assistant_msg.created_at
    )

@router.post("/explain-error")
async def explain_error(
    error_message: str,
    module_name: str,
    error_code: Optional[str] = None,
    context_data: Optional[Dict[str, Any]] = None,
    user: User = Depends(get_current_user),
    org: Organization = Depends(get_current_org),
    db: Session = Depends(get_db)
):
    """
    Dedicated Explain This Error workflow.
    Sanitizes diagnostics and generates root-cause troubleshooting steps.
    """
    sanitized_data = sanitize_diagnostic_dict(context_data or {})
    sanitized_err = sanitize_diagnostic_text(error_message)

    prompt = f"Module: {module_name}\nError: {sanitized_err}\nError Code: {error_code or 'N/A'}"
    
    res = await run_helpdesk_query(
        question=f"Explain this application error and provide step-by-step troubleshooting: {prompt}",
        context_page=module_name,
        sanitized_diagnostics=sanitized_data
    )
    
    return {
        "status": "success",
        "module": module_name,
        "error_code": error_code,
        "explanation": res["content"],
        "citations": res.get("citations", []),
        "provider": res.get("provider", "gemini"),
        "model": res.get("model")
    }

@router.post("/feedback")
def submit_feedback(
    payload: HelpdeskFeedbackIn,
    user: User = Depends(get_current_user),
    db: Session = Depends(get_db)
):
    msg = db.query(HelpdeskMessage).filter(HelpdeskMessage.id == payload.message_id).first()
    if not msg:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Message not found")
        
    fb = HelpdeskFeedback(
        message_id=msg.id,
        user_id=user.id,
        is_helpful=payload.is_helpful,
        feedback_text=payload.feedback_text,
        created_at=datetime.utcnow()
    )
    db.add(fb)
    db.commit()
    return {"status": "success", "message": "Feedback recorded. Thank you for improving Sentinel SOC."}
