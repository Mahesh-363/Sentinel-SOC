from typing import Dict, Any, List, Optional
from backend.app.core.ai.provider import get_ai_provider
from backend.app.core.ai.rag import search_documentation
from backend.app.core.ai.redaction import sanitize_diagnostic_dict, sanitize_diagnostic_text

HELPDESK_SYSTEM_PROMPT = """
You are the SENTINEL AI HELPDESK, a dedicated technical support and operational guide for Sentinel SOC.
Your mission is to help users understand, configure, operate, and troubleshoot Sentinel SOC itself.

You are distinct from the Security Analyst:
- The Security Analyst investigates external threats and security telemetry.
- The Helpdesk assists with application configuration, sensor installation, error troubleshooting, and feature explanations.

TROUBLESHOOTING INSTRUCTIONS:
When the user shares an error or asks for troubleshooting help:
1. Affected Module: Identify which Sentinel SOC module is affected (e.g., Sensor Enrollment, Database, Docker, API, UI).
2. Plain Explanation: Explain the error or problem in clear, concise language.
3. Likely Causes: Outline verified root causes vs possible causes.
4. Step-by-Step Fix: Provide numbered, concrete troubleshooting steps.
5. Exact Commands: If providing shell commands, specify the Operating System, Shell (e.g. PowerShell or Bash), Working Directory, and Expected Output.
6. Failure Handling: Explain what to do if a command or step fails.
7. Verification: Explain how to verify that the problem is resolved.

STRICT SAFETY & ACCURACY RULES:
- Never recommend destructive commands (like rm -rf, drop database, format) without explicit warnings.
- Base application advice on approved Sentinel SOC documentation. Do not invent non-existent features or endpoints.
- If documentation references are provided in the context, cite the relevant section header.
"""

async def run_helpdesk_query(
    question: str,
    context_page: Optional[str] = None,
    sanitized_diagnostics: Optional[Dict[str, Any]] = None,
    conversation_history: Optional[List[Dict[str, str]]] = None
) -> Dict[str, Any]:
    provider = get_ai_provider()
    
    # 1. Retrieve approved documentation snippets via RAG
    rag_results = search_documentation(question + (" " + context_page if context_page else ""), top_k=2)
    doc_context = ""
    citations = []
    if rag_results:
        doc_context = "APPROVED SENTINEL DOCUMENTATION CONTEXT:\n"
        for r in rag_results:
            doc_context += f"--- Document: {r['doc_name']} ({r['header']}) ---\n{r['snippet']}\n\n"
            citations.append({"document": r["doc_name"], "section": r["header"]})

    # 2. Build prompt with context & sanitized diagnostics
    prompt = ""
    if doc_context:
        prompt += f"{doc_context}\n"
    if context_page:
        prompt += f"User Current Page/Module: {context_page}\n"
    if sanitized_diagnostics:
        clean_diag = sanitize_diagnostic_dict(sanitized_diagnostics)
        prompt += f"Sanitized Diagnostics (User Shared):\n{clean_diag}\n"
    
    prompt += f"\nUser Inquiry / Error Report:\n{sanitize_diagnostic_text(question)}"

    res = await provider.generate(
        prompt=prompt,
        system_instruction=HELPDESK_SYSTEM_PROMPT,
        conversation_history=conversation_history
    )
    res["citations"] = citations
    return res
