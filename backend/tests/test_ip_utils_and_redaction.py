import pytest
from backend.app.core.ip_utils import classify_ip
from backend.app.core.ai.redaction import (
    sanitize_diagnostic_text,
    sanitize_diagnostic_dict,
    sanitize_http_headers
)

def test_ip_classification():
    # Private IPv4
    assert classify_ip("192.168.1.1")["classification"] == "Private"
    assert classify_ip("10.0.0.5")["classification"] == "Private"
    assert classify_ip("172.16.0.1")["classification"] == "Private"

    # Public IPv4
    assert classify_ip("8.8.8.8")["classification"] == "Public"
    assert classify_ip("1.1.1.1")["classification"] == "Public"

    # Loopback IPv4 & IPv6
    assert classify_ip("127.0.0.1")["classification"] == "Loopback"
    assert classify_ip("::1")["classification"] == "Loopback"

    # Link-local
    assert classify_ip("169.254.1.1")["classification"] == "Link-local"
    assert classify_ip("fe80::1")["classification"] == "Link-local"

    # Invalid
    assert classify_ip("999.999.999.999")["classification"] == "Invalid"
    assert classify_ip("not-an-ip")["classification"] == "Invalid"

def test_diagnostic_sanitization():
    # Passwords and secrets
    dirty_text = "Database error: connect failed password=SecretSuper123! with api_key=sak_1234567890abcdef1234567890abcdef"
    clean = sanitize_diagnostic_text(dirty_text)
    assert "SecretSuper123!" not in clean
    assert "[REDACTED_PASSWORD]" in clean
    assert "sak_1234567890abcdef1234567890abcdef" not in clean

    # Enrollment token & JWT
    dirty_token = "stk_abCdeFgHiJkLmNoPqRsTuVwXyZ1234567890"
    clean_token = sanitize_diagnostic_text(dirty_token)
    assert dirty_token not in clean_token
    assert "[REDACTED_ENROLLMENT_TOKEN]" in clean_token

    # Bearer token redaction
    bearer_log = "HTTP Request failed: Authorization: Bearer eyJhbGciOiJIUzI1NiIsInR5cCI6IkpXVCJ9.eyJzdWIiOiIxMjM0NTY3ODkwIn0.doNotLeakThisSignature"
    clean_bearer = sanitize_diagnostic_text(bearer_log)
    assert "doNotLeakThisSignature" not in clean_bearer
    assert "Bearer [REDACTED_BEARER_TOKEN]" in clean_bearer

    # AWS Key redaction
    aws_log = "AWS S3 Sync Failed: credential AKIAIOSFODNN7EXAMPLE invalid"
    clean_aws = sanitize_diagnostic_text(aws_log)
    assert "AKIAIOSFODNN7EXAMPLE" not in clean_aws
    assert "[REDACTED_AWS_KEY]" in clean_aws

    # Dict redaction
    dirty_dict = {
        "user_email": "admin@test.com",
        "auth_token": "bearer xyz123",
        "nested": {"password": "mypassword", "sensor_key": "sak_99887766554433221100"},
        "list_data": ["normal string", "api_key=secret_12345"]
    }
    clean_dict = sanitize_diagnostic_dict(dirty_dict)
    assert clean_dict["auth_token"] == "[REDACTED]"
    assert clean_dict["nested"]["password"] == "[REDACTED]"
    assert clean_dict["nested"]["sensor_key"] == "[REDACTED]"
    assert clean_dict["user_email"] == "admin@test.com"
    assert clean_dict["list_data"][0] == "normal string"
    assert "secret_12345" not in clean_dict["list_data"][1]

def test_sensitive_http_headers_redaction():
    headers = {
        "Host": "api.sentinelsoc.local",
        "Authorization": "Bearer eyJhbGciOiJIUzI1NiIsInR5cCI6IkpXVCJ9.topsecret",
        "X-Sensor-Key": "sak_0123456789abcdef0123456789abcdef",
        "Cookie": "session_id=s%3A999888.unauthorized",
        "Content-Type": "application/json",
        "User-Agent": "SentinelSensor/1.0.0"
    }
    sanitized = sanitize_http_headers(headers)
    assert sanitized["Host"] == "api.sentinelsoc.local"
    assert sanitized["Content-Type"] == "application/json"
    assert sanitized["User-Agent"] == "SentinelSensor/1.0.0"
    assert sanitized["Authorization"] == "[REDACTED_HEADER]"
    assert sanitized["X-Sensor-Key"] == "[REDACTED_HEADER]"
    assert sanitized["Cookie"] == "[REDACTED_HEADER]"
