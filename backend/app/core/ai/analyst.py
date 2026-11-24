import re
from typing import Dict, Any, List, Optional
from backend.app.core.ai.provider import get_ai_provider

ANALYST_SYSTEM_PROMPT = """
You are the SENTINEL AI SECURITY ANALYST, an advisory AI assistant inside Sentinel Security Operations Center.
Your role is to assist security analysts in investigating security telemetry, alerts, incidents, and threat intelligence.

CORE OPERATIONAL PRINCIPLES:
1. Grounding: Base all assessments strictly on the provided authorized telemetry and verified threat intelligence.
2. Honest Evidence Separation: Clearly separate verified facts from hypotheses and recommendations.
3. No Hallucinations: If telemetry, reputation, or context is missing or unavailable, explicitly state that it is unavailable. Never invent IP reputation, attack signatures, or event logs.
4. Advisory Guardrails: Your recommendations are strictly advisory. You cannot and must not execute destructive actions, block IPs, or isolate endpoints directly.
5. Structured Evidence Format:
   Include the following explicit sections:
   - ### VERIFIED FACTS
   - ### POSSIBLE EXPLANATIONS
   - ### HYPOTHESES & INTENT
   - ### RECOMMENDED ACTIONS
   - ### UNKNOWN / MISSING INFORMATION
"""

def extract_structured_breakdown(target_data: Dict[str, Any], content: str) -> Dict[str, Any]:
    """
    Extracts structured evidence categories from target data and model analysis.
    """
    facts = []
    explanations = []
    hypotheses = []
    recommendations = []
    unknowns = []
    mitre_techniques = []

    # 1. Facts from Telemetry
    if target_data.get("source_ip"):
        facts.append(f"Source IP identified as: {target_data['source_ip']}")
    if target_data.get("destination_port"):
        facts.append(f"Target port recorded: {target_data['destination_port']}")
    if target_data.get("severity"):
        facts.append(f"Current alert severity rating: {target_data['severity']}")
    if target_data.get("event_type"):
        facts.append(f"Telemetry event classification: {target_data['event_type']}")
    if target_data.get("failed_attempts"):
        facts.append(f"Recorded failure volume: {target_data['failed_attempts']} attempts")

    # 2. Extract MITRE techniques
    tech_matches = re.findall(r'T\d{4}(?:\.\d{3})?', content)
    for t in tech_matches:
        if t not in mitre_techniques:
            mitre_techniques.append(t)

    # MITRE ATT&CK heuristic mappings
    text_lower = (content + " " + str(target_data)).lower()
    if "brute" in text_lower or "auth_failure" in text_lower or "failed" in text_lower:
        if "T1110 (Brute Force)" not in mitre_techniques:
            mitre_techniques.append("T1110 (Brute Force)")
    if "scan" in text_lower or "port" in text_lower:
        if "T1046 (Network Service Discovery)" not in mitre_techniques:
            mitre_techniques.append("T1046 (Network Service Discovery)")
    if "outbound" in text_lower or "4444" in text_lower or "c2" in text_lower:
        if "T1071 (Application Layer Protocol)" not in mitre_techniques:
            mitre_techniques.append("T1071 (Application Layer Protocol)")
    if "powershell" in text_lower or "certutil" in text_lower:
        if "T1059 (Command and Scripting Interpreter)" not in mitre_techniques:
            mitre_techniques.append("T1059 (Command and Scripting Interpreter)")
    if "iam" in text_lower or "administratoraccess" in text_lower:
        if "T1098 (Account Manipulation)" not in mitre_techniques:
            mitre_techniques.append("T1098 (Account Manipulation)")

    # 3. Explanations & Hypotheses
    if "brute" in text_lower or "failed" in text_lower:
        explanations.append("Repeated authentication attempts indicate automated credential dictionary spray or brute-force tool.")
        hypotheses.append("Attacker attempting to discover valid account credentials for initial network footholds.")
        recommendations.append("Temporarily enforce IP block on source IP at the edge firewall.")
        recommendations.append("Audit user accounts targeted for successful logins from other IP addresses.")
    elif "port" in text_lower:
        explanations.append("Sequential TCP connect or SYN probes suggest active reconnaissance tooling (e.g. Nmap).")
        hypotheses.append("Actor mapping open perimeter services to identify vulnerable listening daemons.")
        recommendations.append("Confirm target ports are intentionally exposed and firewall ACLs are enforced.")
    else:
        explanations.append("Observed telemetry warrants analyst review against organizational baselines.")
        recommendations.append("Review endpoint process trees and socket connections during the time window.")

    # 4. Unknowns
    if not target_data.get("asset_hostname"):
        unknowns.append("Local endpoint process tree (Requires enrolled Sentinel Endpoint Sensor)")
    if not target_data.get("pcap"):
        unknowns.append("Full packet payload inspection (Sentinel does not capture raw payload packets)")
    unknowns.append("External threat actor true identity or physical residence")

    return {
        "verified_facts": facts or ["Telemetry event recorded in Sentinel security events ledger."],
        "possible_explanations": explanations,
        "hypotheses": hypotheses,
        "recommendations": recommendations,
        "unknown_information": unknowns,
        "mitre_techniques": mitre_techniques
    }

async def run_security_analysis(
    target_type: str,
    target_data: Dict[str, Any],
    user_query: Optional[str] = None,
    conversation_history: Optional[List[Dict[str, str]]] = None
) -> Dict[str, Any]:
    """
    Executes security analysis using configured free-tier/local AI or intelligent fallback.
    Returns both human-readable markdown briefing and structured evidence breakdown.
    """
    provider = get_ai_provider()
    
    context_str = f"Target Type: {target_type}\nTelemetry Context Data:\n"
    for k, v in target_data.items():
        context_str += f"- {k}: {v}\n"
        
    prompt = f"Analyze the following security telemetry context:\n\n{context_str}\n"
    if user_query:
        prompt += f"\nSpecific Analyst Question: {user_query}\n"
    else:
        prompt += "\nPlease perform a comprehensive investigation separating Verified Facts, Hypotheses, Recommendations, and Unknowns."

    res = await provider.generate(
        prompt=prompt,
        system_instruction=ANALYST_SYSTEM_PROMPT,
        conversation_history=conversation_history
    )

    # Attach structured breakdown
    breakdown = extract_structured_breakdown(target_data, res.get("content", ""))
    res["structured_breakdown"] = breakdown
    res["mitre_techniques"] = breakdown["mitre_techniques"]
    return res
