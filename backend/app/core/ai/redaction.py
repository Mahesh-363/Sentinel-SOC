import re
from typing import Dict, Any

SENSITIVE_PATTERNS = [
    (re.compile(r'(?i)(password|passwd|pwd)\s*[:=]\s*["\']?([^"\'\s,;]+)', re.IGNORECASE), r'\1: [REDACTED_PASSWORD]'),
    (re.compile(r'(?i)bearer\s+[a-zA-Z0-9_\-\.]+', re.IGNORECASE), 'Bearer [REDACTED_BEARER_TOKEN]'),
    (re.compile(r'(?i)(api[_-]?key|secret[_-]?key|access[_-]?token|auth[_-]?token)\s*[:=]\s*["\']?([^"\'\s,;]+)', re.IGNORECASE), r'\1: [REDACTED_SECRET]'),
    (re.compile(r'(?i)(x-sensor-key|x-api-key)\s*[:=]\s*["\']?([^"\'\s,;]+)', re.IGNORECASE), r'\1: [REDACTED_SENSOR_KEY]'),
    (re.compile(r'stk_[a-zA-Z0-9_\-]{16,}', re.IGNORECASE), '[REDACTED_ENROLLMENT_TOKEN]'),
    (re.compile(r'sak_[a-zA-Z0-9]{16,}', re.IGNORECASE), '[REDACTED_SENSOR_KEY]'),
    (re.compile(r'eyJ[a-zA-Z0-9_\-]{20,}\.[a-zA-Z0-9_\-]{20,}\.[a-zA-Z0-9_\-]{20,}', re.IGNORECASE), '[REDACTED_JWT_TOKEN]'),
    (re.compile(r'AKIA[0-9A-Z]{16}', re.IGNORECASE), '[REDACTED_AWS_KEY]'),
]

SENSITIVE_HEADER_KEYS = {
    "authorization",
    "x-sensor-key",
    "x-api-key",
    "cookie",
    "set-cookie",
    "proxy-authorization",
    "x-auth-token"
}

def sanitize_diagnostic_text(text: str) -> str:
    """
    Strips passwords, API keys, JWT tokens, AWS credentials, bearer tokens,
    and sensor secrets from logs, stack traces, and diagnostics before sending to AI or sharing.
    """
    if not text:
        return ""
    sanitized = text
    for pattern, replacement in SENSITIVE_PATTERNS:
        sanitized = pattern.sub(replacement, sanitized)
    return sanitized

def sanitize_http_headers(headers: Dict[str, str]) -> Dict[str, str]:
    """
    Redacts sensitive HTTP headers such as Authorization, X-Sensor-Key, and Cookie headers.
    """
    cleaned = {}
    for k, v in headers.items():
        k_lower = k.lower()
        if k_lower in SENSITIVE_HEADER_KEYS or any(s in k_lower for s in ["auth", "token", "key", "secret", "cookie"]):
            cleaned[k] = "[REDACTED_HEADER]"
        else:
            cleaned[k] = sanitize_diagnostic_text(str(v))
    return cleaned

def sanitize_diagnostic_dict(data: Dict[str, Any]) -> Dict[str, Any]:
    cleaned = {}
    for k, v in data.items():
        k_lower = k.lower()
        if any(secret in k_lower for secret in ["password", "secret", "token", "key", "cookie", "auth"]):
            cleaned[k] = "[REDACTED]"
        elif isinstance(v, str):
            cleaned[k] = sanitize_diagnostic_text(v)
        elif isinstance(v, dict):
            cleaned[k] = sanitize_diagnostic_dict(v)
        elif isinstance(v, list):
            cleaned[k] = [sanitize_diagnostic_text(i) if isinstance(i, str) else (sanitize_diagnostic_dict(i) if isinstance(i, dict) else i) for i in v]
        else:
            cleaned[k] = v
    return cleaned
