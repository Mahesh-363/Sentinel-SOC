import pytest
from fastapi.testclient import TestClient

def test_ai_helpdesk_and_fallback(client: TestClient):
    # Setup test user and organization
    reg = client.post("/api/v1/auth/register", json={
        "email": "helpdeskuser@defense.org",
        "password": "Password123!",
        "full_name": "Helpdesk User",
        "organization_name": "Support Wing"
    })
    token = reg.json()["access_token"]
    org_id = reg.json()["organizations"][0]["id"]
    headers = {"Authorization": f"Bearer {token}", "X-Organization-Id": org_id}

    # 1. Ask question to AI Helpdesk
    chat_res = client.post("/api/v1/ai-helpdesk/chat", headers=headers, json={
        "message": "Why is my sensor offline?",
        "context_page": "/sensors"
    })
    assert chat_res.status_code == 200, chat_res.text
    chat_data = chat_res.json()
    assert chat_data["sender_role"] == "assistant"
    assert "message" in chat_data
    conv_id = chat_data["conversation_id"]

    # 2. Verify Conversation History is Retained
    convs_res = client.get("/api/v1/ai-helpdesk/conversations", headers=headers)
    assert convs_res.status_code == 200
    convs = convs_res.json()
    assert len(convs) >= 1
    assert convs[0]["id"] == conv_id

    # 3. Test "Explain This Error" workflow
    error_res = client.post("/api/v1/ai-helpdesk/explain-error", headers=headers, params={
        "error_message": "Sensor registration failed — HTTP 401: Invalid enrollment token stk_secret12345",
        "module_name": "Sensor Management",
        "error_code": "ERR_SENSOR_401"
    })
    assert error_res.status_code == 200
    err_data = error_res.json()
    assert err_data["module"] == "Sensor Management"
    assert "explanation" in err_data
    # Verify token was sanitized
    assert "stk_secret12345" not in err_data["explanation"]
